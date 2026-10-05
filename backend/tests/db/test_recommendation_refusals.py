"""Preconditions of U4, refused without writing (`DT-058`, `DT-061`, `DT-063`), each on a fresh database."""

from __future__ import annotations

import datetime as dt
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from _db_support import DATASET_DIR, DatabaseTestCase

from app.db.migrations import MIGRATIONS_DIR, apply_migrations
from app.ingestion.loader import load_dataset
from app.runs.config import config_sha256 as u3_config_sha256
from app.runs.forecast import run_forecast
from app.runs.recommendation import RecommendationRunError, RecommendationRunOutcome, run_recommendations

A = dt.date(2025, 12, 31)


class RefusalTestCase(DatabaseTestCase):
    def recommendation_runs(self) -> int:
        return self.conn.execute("SELECT count(*) FROM calculation_runs WHERE run_type = 'RECOMMENDATION'").fetchone()[0]

    def assert_refused(self, as_of: dt.date = A) -> RecommendationRunError:
        with self.assertRaises(RecommendationRunError) as caught:
            run_recommendations(self.conn, as_of)
        self.assertEqual(self.recommendation_runs(), 0)
        self.assertEqual(self.count("recommendations"), 0)
        return caught.exception


class SchemaAndLoadTest(RefusalTestCase):
    migrate = False

    def test_without_migration_0003_the_execution_is_refused(self) -> None:
        handle = tempfile.TemporaryDirectory(prefix="u4_migrations_")
        self.addCleanup(handle.cleanup)
        for name in ("0001_dataset_tables.sql", "0002_forecast_tables.sql"):
            shutil.copy(MIGRATIONS_DIR / name, Path(handle.name))
        apply_migrations(self.conn, Path(handle.name))
        with self.assertRaises(RecommendationRunError):
            run_recommendations(self.conn, A)

    def test_without_a_completed_load_nothing_is_written(self) -> None:
        apply_migrations(self.conn)
        self.assertIn("no COMPLETED data load", str(self.assert_refused()))


class CutAndOriginTest(RefusalTestCase):
    def setUp(self) -> None:
        super().setUp()
        load_dataset(self.conn, DATASET_DIR)

    def test_only_the_last_day_of_the_load_is_accepted(self) -> None:
        run_forecast(self.conn, A - dt.timedelta(days=1))
        for as_of in (A - dt.timedelta(days=1), A + dt.timedelta(days=1), dt.date(2024, 6, 30)):
            with self.subTest(as_of=as_of):
                self.assertIn("is not the cut", str(self.assert_refused(as_of)))

    def test_dt063_only_synthetic_loads(self) -> None:
        run_forecast(self.conn, A)
        self.conn.execute("ALTER TABLE data_loads DROP CONSTRAINT data_loads_data_origin_check")
        for origin in ("REAL", None, "MIXED"):
            with self.subTest(origin=origin):
                self.conn.execute("UPDATE data_loads SET data_origin = %s", (origin,))
                self.assertIn("DT-063", str(self.assert_refused()))
        self.conn.execute("UPDATE data_loads SET data_origin = 'SYNTHETIC'")
        self.assertIs(run_recommendations(self.conn, A).outcome, RecommendationRunOutcome.COMPLETED)


class ForecastSelectionTest(RefusalTestCase):
    """`DT-061`: only the COMPLETED forecast of the same cut, load and current U3 configuration."""

    def setUp(self) -> None:
        super().setUp()
        load_dataset(self.conn, DATASET_DIR)

    def _fake_forecast_run(self, status: str, sha: str, as_of: dt.date = A) -> int:
        reference = self.conn.execute("SELECT min(id) FROM model_versions").fetchone()[0]
        return self.conn.execute(
            """
            INSERT INTO calculation_runs (run_type, status, as_of_date, data_load_id, reference_model_version_id,
                                          config_sha256, summary, error, started_at, finished_at)
            VALUES ('FORECAST', %s, %s, (SELECT id FROM data_loads), %s, %s, '{}', %s, now(), now())
            RETURNING id
            """,
            (status, as_of, reference, sha, '{"type": "probe"}' if status == "FAILED" else None),
        ).fetchone()[0]

    def test_failed_other_configuration_and_other_cut_are_never_consumed(self) -> None:
        from app.runs.forecast import register_model_versions

        register_model_versions(self.conn)
        self._fake_forecast_run("FAILED", u3_config_sha256())
        self._fake_forecast_run("COMPLETED", "0" * 64)
        self._fake_forecast_run("COMPLETED", u3_config_sha256(), as_of=A - dt.timedelta(days=7))
        self.assertIn("no COMPLETED forecast execution", str(self.assert_refused()))
        valid = run_forecast(self.conn, A).calculation_run_id
        result = run_recommendations(self.conn, A)
        self.assertIs(result.outcome, RecommendationRunOutcome.COMPLETED)
        consumed = self.conn.execute(
            "SELECT forecast_run_id FROM calculation_runs WHERE id = %s", (result.calculation_run_id,)
        ).fetchone()[0]
        self.assertEqual(consumed, valid)

    def test_u4_never_launches_the_forecast(self) -> None:
        with mock.patch("app.runs.forecast.run_forecast", side_effect=AssertionError("U4 launched the forecast")):
            self.assert_refused()
        self.assertEqual(self.count("calculation_runs"), 0)
