"""U6 — ``GET /api/v1/recommendations/{recommendation_id}/explanation`` against PostgreSQL with the real
dataset 0.4.0 (`DT-068`, `DT-069`, `docs/09` §14.5 and §14.6).

One database is loaded, forecast (U3) and evaluated (U4) once for the module, at 2025-12-31; the API only
reads it. Every one of the persisted evaluations is explained and verified.
"""

from __future__ import annotations

import datetime as dt
import re
import time
import unittest

from _db_support import DATASET_DIR, TemporaryDatabase
from starlette.testclient import TestClient

from app.api.app import create_app
from app.api.auth import ADMIN, ANALYST, PLANNER, VIEWER, Identity
from app.api.settings import Settings
from app.db.migrations import apply_migrations
from app.genai import GENERATOR, TemplateGenerator
from app.genai.verification import figures
from app.ingestion.loader import load_dataset
from app.runs.forecast import run_forecast
from app.runs.recommendation import run_recommendations

A = dt.date(2025, 12, 31)
ROLES = (VIEWER, ANALYST, PLANNER, ADMIN)
TOKENS = {role: f"dev-{role.lower()}-token-explanation" for role in ROLES}
IDENTITIES = {token: Identity(f"it-{role.lower()}", frozenset({role})) for role, token in TOKENS.items()}

_DB: TemporaryDatabase | None = None
_RECOMMENDATION_RUN = None


def setUpModule() -> None:
    global _DB, _RECOMMENDATION_RUN
    _DB = TemporaryDatabase()
    try:
        with _DB.connect() as conn:
            apply_migrations(conn)
            load_dataset(conn, DATASET_DIR)
            run_forecast(conn, A)
            _RECOMMENDATION_RUN = run_recommendations(conn, A).calculation_run_id
    except BaseException:
        _DB.drop()
        raise


def tearDownModule() -> None:
    if _DB is not None:
        _DB.drop()


class ExplanationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(Settings("local", _DB.dsn, IDENTITIES))
        self.client = TestClient(self.app)
        self.conn = _DB.connect()
        self.addCleanup(self.conn.close)

    def get(self, path: str, role: str | None = ADMIN, expected: int = 200, **headers: str):
        if role is not None:
            headers["Authorization"] = f"Bearer {TOKENS[role]}"
        response = self.client.get(path, headers=headers)
        self.assertEqual(response.status_code, expected, (path, response.text[:300]))
        return response

    def first(self, outcome: str, flag: str | None = None) -> int:
        query = "SELECT min(id) FROM recommendations WHERE calculation_run_id = %s AND outcome = %s"
        params: tuple = (_RECOMMENDATION_RUN, outcome)
        if flag:
            query += " AND %s = ANY(flags)"
            params += (flag,)
        return self.conn.execute(query, params).fetchone()[0]

    def breakdown(self, recommendation_id: int) -> dict:
        return self.conn.execute("SELECT calculation_inputs->'breakdown' FROM recommendations WHERE id = %s",
                                 (recommendation_id,)).fetchone()[0]

    def unit(self, recommendation_id: int) -> str:
        return self.conn.execute("SELECT p.unit_of_measure FROM recommendations r JOIN products p ON p.id = r.product_id "
                                 "WHERE r.id = %s", (recommendation_id,)).fetchone()[0]


class OutcomesTest(ExplanationTestCase):
    def check_facts(self, body: dict) -> None:
        breakdown = self.breakdown(body["recommendation_id"])
        for fact in body["facts"]:
            self.assertEqual(fact["value"], breakdown[fact["key"]])  # persisted text, never recalculated
        allowed = {fact["display"] for fact in body["facts"]}
        self.assertLessEqual(set(figures(body["explanation"]["narrative"])), allowed)

    def test_recommend(self) -> None:
        rid = self.first("RECOMMEND", "UNCOUNTED_TRANSIT")
        body = self.get(f"/api/v1/recommendations/{rid}/explanation").json()
        self.assertEqual(body["outcome"], "RECOMMEND")
        self.assertEqual(body["explanation"]["status"], "VERIFIED")
        self.assertEqual((body["explanation"]["generator"], body["explanation"]["warning"]), (GENERATOR, None))
        narrative = body["explanation"]["narrative"]
        self.assertTrue(narrative.startswith("Se sugiere pedir "))
        self.assertIn(f" {self.unit(rid)}", narrative)
        self.assertNotIn("unidades", narrative)
        self.assertIn("En total hay", narrative)
        self.assertTrue(narrative.endswith("no constituyen una recomendación de negocio definitiva."))
        self.assertEqual(body["reason_details"], [])
        self.check_facts(body)

    def test_no_need(self) -> None:
        rid = self.first("NO_NEED")
        body = self.get(f"/api/v1/recommendations/{rid}/explanation", VIEWER).json()
        self.assertEqual((body["outcome"], body["explanation"]["status"]), ("NO_NEED", "VERIFIED"))
        self.assertTrue(body["explanation"]["narrative"].startswith("No se sugiere pedido: "))
        self.assertNotIn("q_final", [f["key"] for f in body["facts"]])
        self.check_facts(body)

    def test_not_calculable(self) -> None:
        rid = self.first("NOT_CALCULABLE")
        body = self.get(f"/api/v1/recommendations/{rid}/explanation").json()
        self.assertEqual(body["explanation"], {"generator": GENERATOR, "status": "NOT_APPLICABLE", "narrative": None,
                                               "warning": None})
        self.assertEqual(body["facts"], [])
        self.assertTrue(body["reasons"])
        self.assertEqual([d["code"] for d in body["reason_details"]], body["reasons"])
        for detail in body["reason_details"]:
            self.assertIsNone(re.search(r"\d", detail["text"]))

    def test_provenance_is_the_one_of_the_detail(self) -> None:
        rid = self.first("RECOMMEND")
        explanation = self.get(f"/api/v1/recommendations/{rid}/explanation").json()
        detail = self.get(f"/api/v1/recommendations/{rid}").json()
        self.assertEqual(explanation["provenance"], detail["provenance"])
        self.assertEqual(explanation["provenance"]["notices"], ["SYNTHETIC_DATA", "V1_PROVISIONAL_POLICY"])
        self.assertEqual((explanation["run_id"], explanation["flags"]), (detail["run_id"], detail["flags"]))
        self.assertNotIn("explanation", detail)  # the U5 detail does not change

    def test_every_real_evaluation(self) -> None:
        ids = [r[0] for r in self.conn.execute(
            "SELECT id FROM recommendations WHERE calculation_run_id = %s ORDER BY id", (_RECOMMENDATION_RUN,))]
        self.assertEqual(len(ids), 100)
        statuses: dict[tuple[str, str], int] = {}
        for rid in ids:
            body = self.get(f"/api/v1/recommendations/{rid}/explanation", VIEWER).json()
            key = (body["outcome"], body["explanation"]["status"])
            statuses[key] = statuses.get(key, 0) + 1
            if body["explanation"]["narrative"] is not None:
                self.check_facts(body)
        self.assertEqual(statuses, {("RECOMMEND", "VERIFIED"): 50, ("NO_NEED", "VERIFIED"): 40,
                                    ("NOT_CALCULABLE", "NOT_APPLICABLE"): 10})


class _Injecting(TemplateGenerator):
    def generate(self, context):  # type: ignore[override]
        return super().generate(context) + " Faltan 999 unidades desde 2025-12-31."


class DegradationTest(ExplanationTestCase):
    def test_rs010_through_the_endpoint(self) -> None:
        self.app.state.text_generator = _Injecting()
        rid = self.first("RECOMMEND")
        with self.assertLogs("app.genai", "WARNING") as logs:
            response = self.get(f"/api/v1/recommendations/{rid}/explanation", **{"X-Correlation-ID": "rs010-check-01"})
        body = response.json()
        self.assertEqual(body["explanation"], {"generator": GENERATOR, "status": "DEGRADED", "narrative": None,
                                               "warning": "NARRATIVE_UNVERIFIED"})
        self.assertTrue(body["facts"])
        self.assertEqual(body["provenance"]["notices"], ["SYNTHETIC_DATA", "V1_PROVISIONAL_POLICY"])
        self.assertNotIn("Faltan", response.text)  # the rejected text never leaves the server
        self.assertIn("rs010-check-01", logs.output[0])
        self.assertEqual(response.headers["X-Correlation-ID"], "rs010-check-01")


class ContractTest(ExplanationTestCase):
    def test_roles_and_errors(self) -> None:
        rid = self.first("NO_NEED")
        for role in ROLES:
            with self.subTest(role):
                self.get(f"/api/v1/recommendations/{rid}/explanation", role)
        error = self.get(f"/api/v1/recommendations/{rid}/explanation", None, 401).json()["error"]
        self.assertEqual(error["code"], "AUTHENTICATION_REQUIRED")
        missing = self.get("/api/v1/recommendations/999999/explanation", expected=404)
        self.assertEqual(missing.json()["error"]["code"], "RECOMMENDATION_NOT_FOUND")
        self.assertTrue(missing.headers["X-Correlation-ID"])
        for bad in ("0", "abc"):
            self.assertEqual(self.get(f"/api/v1/recommendations/{bad}/explanation", expected=422)
                             .json()["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(self.client.post(f"/api/v1/recommendations/{rid}/explanation",
                                          headers={"Authorization": f"Bearer {TOKENS[ADMIN]}"}).status_code, 405)


class ReadOnlyTest(ExplanationTestCase):
    def snapshot(self) -> tuple:
        time.sleep(1.2)
        self.conn.execute("SELECT pg_stat_force_next_flush()")
        writes = self.conn.execute(
            "SELECT coalesce(sum(n_tup_ins + n_tup_upd + n_tup_del), 0) FROM pg_stat_user_tables").fetchone()[0]
        tables = [r[0] for r in self.conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")]
        return writes, tuple(self.conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tables)

    def test_explanations_never_write(self) -> None:
        before = self.snapshot()
        for outcome in ("RECOMMEND", "NO_NEED", "NOT_CALCULABLE"):
            self.get(f"/api/v1/recommendations/{self.first(outcome)}/explanation")
        self.assertEqual(self.snapshot(), before)

    def test_works_without_the_demand_table(self) -> None:
        self.conn.execute("ALTER TABLE demand RENAME TO demand_hidden")
        try:
            for outcome in ("RECOMMEND", "NO_NEED", "NOT_CALCULABLE"):
                self.get(f"/api/v1/recommendations/{self.first(outcome)}/explanation")
        finally:
            self.conn.execute("ALTER TABLE demand_hidden RENAME TO demand")


if __name__ == "__main__":
    unittest.main()
