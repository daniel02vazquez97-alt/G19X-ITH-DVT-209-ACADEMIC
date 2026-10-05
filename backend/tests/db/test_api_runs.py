"""Deterministic run selection of the API V1 (`DT-066`) on hand-built ``calculation_runs``.

The rule: the single COMPLETED load → its COMPLETED runs of the expected type → max ``as_of_date`` →
max ``id``. An explicit ``run_id`` must exist, be of the expected type and be COMPLETED; otherwise 404
``RUN_NOT_FOUND``. Each test builds its own migrated database with only the rows the rule reads
(no dataset is loaded: the endpoints only list the forecasts and recommendations of the chosen run).
"""

from __future__ import annotations

import datetime as dt
import json
import unittest

from _db_support import DatabaseTestCase
from starlette.testclient import TestClient

from app.api.app import create_app
from app.api.auth import ADMIN, Identity
from app.api.settings import Settings

TOKEN = "dev-admin-token-run-selection"
IDENTITIES = {TOKEN: Identity("it-admin", frozenset({ADMIN}))}
T0 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)


class RunSelectionTest(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = TestClient(create_app(Settings("local", self.database.dsn, IDENTITIES)))
        self.load = self._load("COMPLETED")
        self.model = self.conn.execute(
            "INSERT INTO model_versions (name, version, algorithm, hyperparameters, is_baseline) "
            "VALUES ('api-run-selection', '0.0.1', 'test', '{}', true) RETURNING id").fetchone()[0]
        self._config = 0

    # -- builders ----------------------------------------------------------------------------------------
    def _load(self, status: str) -> int:
        return self.conn.execute(
            "INSERT INTO data_loads (dataset_version, generator_version, data_origin, manifest, manifest_sha256, "
            "files, status, outcome, started_at, finished_at) "
            "VALUES ('0.4.0', '0.4.0', 'SYNTHETIC', '{}', %s, '[]', %s, %s, %s, %s) RETURNING id",
            ("0" * 64, status, "COMPLETED" if status == "COMPLETED" else "FAILED", T0, T0)).fetchone()[0]

    def _run(self, run_type: str, as_of: str, *, status: str = "COMPLETED", load: int | None = None,
             forecast_run: int | None = None) -> int:
        self._config += 1
        recommendation = run_type == "RECOMMENDATION"
        return self.conn.execute(
            "INSERT INTO calculation_runs (run_type, status, as_of_date, data_load_id, reference_model_version_id, "
            "config_sha256, summary, error, started_at, finished_at, forecast_run_id, engine_version) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (run_type, status, as_of, self.load if load is None else load, None if recommendation else self.model,
             f"{self._config:064x}", json.dumps({"policy_set": "V1_PROVISIONAL"} if recommendation else {}),
             json.dumps({"code": "TEST"}) if status == "FAILED" else None, T0, T0,
             forecast_run if recommendation else None, "1.0.0" if recommendation else None)).fetchone()[0]

    def get(self, path: str, expected: int = 200) -> dict:
        response = self.client.get(path, headers={"Authorization": f"Bearer {TOKEN}"})
        self.assertEqual(response.status_code, expected, (path, response.text[:300]))
        return response.json()

    def selected(self, path: str) -> int:
        return self.get(path)["provenance"]["run_id"]

    # -- tests ---------------------------------------------------------------------------------------------
    def test_no_run_is_404(self) -> None:
        for path, run_type in (("/api/v1/forecasts", "FORECAST"), ("/api/v1/recommendations", "RECOMMENDATION")):
            with self.subTest(path):
                error = self.get(path, expected=404)["error"]
                self.assertEqual((error["code"], error["details"]), ("RUN_NOT_FOUND", {"run_type": run_type}))

    def test_default_takes_the_latest_as_of_date(self) -> None:
        older = self._run("FORECAST", "2025-12-31")
        newer = self._run("FORECAST", "2026-01-31")
        self._run("FORECAST", "2025-06-30")  # higher id, earlier cut: not chosen
        self.assertGreater(newer, older)
        self.assertEqual(self.selected("/api/v1/forecasts"), newer)

    def test_tie_on_as_of_date_takes_the_highest_id(self) -> None:
        first = self._run("FORECAST", "2025-12-31")
        second = self._run("FORECAST", "2025-12-31")  # same cut, other configuration
        self.assertGreater(second, first)
        self.assertEqual(self.selected("/api/v1/forecasts"), second)
        rec_first = self._run("RECOMMENDATION", "2025-12-31", forecast_run=first)
        rec_second = self._run("RECOMMENDATION", "2025-12-31", forecast_run=second)
        self.assertEqual(self.selected("/api/v1/recommendations"), max(rec_first, rec_second))

    def test_failed_runs_and_runs_of_other_loads_are_ignored(self) -> None:
        completed = self._run("FORECAST", "2025-12-31")
        self._run("FORECAST", "2026-03-31", status="FAILED")
        self._run("FORECAST", "2026-06-30", load=self._load("FAILED"))  # not the COMPLETED load
        self.assertEqual(self.selected("/api/v1/forecasts"), completed)

    def test_only_failed_runs_is_404(self) -> None:
        self._run("FORECAST", "2025-12-31", status="FAILED")
        self.assertEqual(self.get("/api/v1/forecasts", expected=404)["error"]["code"], "RUN_NOT_FOUND")

    def test_explicit_run_id(self) -> None:
        forecast = self._run("FORECAST", "2025-12-31")
        latest = self._run("FORECAST", "2026-01-31")
        failed = self._run("FORECAST", "2026-02-28", status="FAILED")
        recommendation = self._run("RECOMMENDATION", "2025-12-31", forecast_run=forecast)
        self.assertEqual(self.selected(f"/api/v1/forecasts?run_id={forecast}"), forecast)  # older, explicit
        self.assertNotEqual(forecast, latest)
        cases = {
            failed: "not_completed",
            recommendation: "wrong_type",
            9999: "not_found",
        }
        for run_id, reason in cases.items():
            with self.subTest(run_id=run_id):
                error = self.get(f"/api/v1/forecasts?run_id={run_id}", expected=404)["error"]
                self.assertEqual((error["code"], error["details"]["reason"]), ("RUN_NOT_FOUND", reason))
        error = self.get(f"/api/v1/recommendations?run_id={forecast}", expected=404)["error"]
        self.assertEqual(error["details"]["reason"], "wrong_type")
        self.assertEqual(self.get("/api/v1/forecasts?run_id=0", expected=422)["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(self.get("/api/v1/forecasts?run_id=abc", expected=422)["error"]["code"], "VALIDATION_ERROR")

    def test_product_endpoints_use_the_same_rule(self) -> None:
        self._run("FORECAST", "2025-12-31", status="FAILED")
        # without products the product endpoints answer 404 PRODUCT_NOT_FOUND before resolving the run
        self.assertEqual(self.get("/api/v1/products/1/forecast", expected=404)["error"]["code"], "PRODUCT_NOT_FOUND")

    def test_run_detail_shows_failed_runs_with_their_error(self) -> None:
        failed = self._run("FORECAST", "2025-12-31", status="FAILED")
        detail = self.get(f"/api/v1/runs/{failed}")
        self.assertEqual((detail["status"], detail["error"]), ("FAILED", {"code": "TEST"}))
        self.assertEqual(self.get("/api/v1/runs/9999", expected=404)["error"]["code"], "RUN_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
