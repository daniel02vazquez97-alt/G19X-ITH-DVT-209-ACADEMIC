"""Migration 0003 (U4, `DT-059` to `DT-062`): from scratch, over 0001 + 0002 with data, idempotent,
sha-guarded, and the constraints that make every invalid row impossible."""

from __future__ import annotations

import datetime as dt
import shutil
import tempfile
import unittest
from pathlib import Path

import psycopg
from psycopg import errors as pg_errors
from psycopg.types.json import Jsonb
from _db_support import DATASET_DIR, DatabaseTestCase, TemporaryDatabase

from app.db.migrations import MIGRATIONS_DIR, MigrationError, apply_migrations, discover
from app.ingestion.loader import load_dataset
from app.runs.forecast import run_forecast
from app.runs.recommendation import RecommendationRunOutcome, run_recommendations

A = dt.date(2025, 12, 31)
U4_COLUMNS = {"forecast_run_id", "engine_version"}


class RecommendationMigrationTest(DatabaseTestCase):
    migrate = False

    def _only(self, *names: str) -> Path:
        handle = tempfile.TemporaryDirectory(prefix="u4_migrations_")
        self.addCleanup(handle.cleanup)
        for name in names:
            shutil.copy(MIGRATIONS_DIR / name, Path(handle.name))
        return Path(handle.name)

    def columns(self, table: str) -> set[str]:
        return {
            r[0]
            for r in self.conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table,))
        }

    def test_from_scratch_the_three_migrations_apply_in_order_and_once(self) -> None:
        applied = apply_migrations(self.conn)
        self.assertEqual(  # U9 adds 0004 after them
            applied[:3], ["0001_dataset_tables", "0002_forecast_tables", "0003_recommendation_tables"]
        )
        self.assertEqual(applied, [m.version for m in discover()])
        self.assertEqual(apply_migrations(self.conn), [])
        stored = dict(self.conn.execute("SELECT version, sha256 FROM schema_migrations").fetchall())
        self.assertEqual(stored, {m.version: m.sha256 for m in discover()})
        self.assertTrue(U4_COLUMNS <= self.columns("calculation_runs"))
        self.assertIn("calculation_inputs", self.columns("recommendations"))

    def test_over_0001_and_0002_with_a_forecast_already_persisted(self) -> None:
        apply_migrations(self.conn, self._only("0001_dataset_tables.sql", "0002_forecast_tables.sql"))
        load_dataset(self.conn, DATASET_DIR)
        forecast = run_forecast(self.conn, A)
        self.assertEqual(apply_migrations(self.conn)[0], "0003_recommendation_tables")  # U9 adds 0004 after it
        row = self.conn.execute(
            "SELECT run_type, status, forecast_run_id, engine_version FROM calculation_runs WHERE id = %s",
            (forecast.calculation_run_id,),
        ).fetchone()
        self.assertEqual(row, ("FORECAST", "COMPLETED", None, None))  # untouched, still valid
        self.assertIs(run_recommendations(self.conn, A).outcome, RecommendationRunOutcome.COMPLETED)

    def test_a_changed_0003_is_an_error(self) -> None:
        apply_migrations(self.conn)
        directory = self._only(*(m.path.name for m in discover()))
        (directory / "0003_recommendation_tables.sql").write_text("-- changed\n", encoding="utf-8")
        with self.assertRaises(MigrationError):
            apply_migrations(self.conn, directory)

    def test_foreign_keys_and_trigger(self) -> None:
        apply_migrations(self.conn)
        rows = self.conn.execute(
            """
            SELECT c.conrelid::regclass::text, a.attname, c.confrelid::regclass::text
            FROM pg_constraint c
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
            WHERE c.contype = 'f' AND (c.conrelid::regclass::text = 'recommendations'
                                       OR (c.conrelid::regclass::text = 'calculation_runs' AND a.attname = 'forecast_run_id'))
            """
        ).fetchall()
        self.assertEqual(
            {(t, c): r for t, c, r in rows},
            {
                ("calculation_runs", "forecast_run_id"): "calculation_runs",
                ("recommendations", "calculation_run_id"): "calculation_runs",
                ("recommendations", "product_id"): "products",
                ("recommendations", "location_id"): "locations",
                ("recommendations", "forecast_id"): "forecasts",
                ("recommendations", "suggested_supplier_id"): "suppliers",
            },
        )
        triggers = {r[0] for r in self.conn.execute("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal")}
        self.assertIn("recommendations_immutable", triggers)


_DB: TemporaryDatabase | None = None


def setUpModule() -> None:
    global _DB
    _DB = TemporaryDatabase()
    try:
        with _DB.connect() as conn:
            apply_migrations(conn)
            load_dataset(conn, DATASET_DIR)
            run_forecast(conn, A)
    except BaseException:
        _DB.drop()
        raise


def tearDownModule() -> None:
    if _DB is not None:
        _DB.drop()


class _Rollback(Exception):
    pass


class ConstraintTest(unittest.TestCase):
    """Each invalid row is rejected by the schema itself; every probe is rolled back."""

    def setUp(self) -> None:
        self.conn = _DB.connect()
        self.addCleanup(self.conn.close)
        self.load_id, self.forecast_run_id, self.h1 = self.conn.execute(
            """
            SELECT c.data_load_id, c.id, (SELECT min(f.id) FROM forecasts f
                                          WHERE f.calculation_run_id = c.id AND f.product_id = 1 AND f.is_primary)
            FROM calculation_runs c WHERE c.run_type = 'FORECAST'
            """
        ).fetchone()

    def run_insert(self, **overrides) -> None:
        values = {
            "run_type": "RECOMMENDATION", "status": "COMPLETED", "as_of_date": A, "data_load_id": self.load_id,
            "reference_model_version_id": None, "config_sha256": "a" * 64, "summary": Jsonb({}), "error": None,
            "forecast_run_id": self.forecast_run_id, "engine_version": "0.1.0",
        }
        values.update(overrides)
        columns = ", ".join(values)
        self.conn.execute(
            f"INSERT INTO calculation_runs ({columns}, started_at, finished_at) "
            f"VALUES ({', '.join(['%s'] * len(values))}, now(), now()) RETURNING id",
            tuple(values.values()),
        )

    def recommendation_insert(self, **overrides) -> None:
        run_id = self.conn.execute(
            """
            INSERT INTO calculation_runs (run_type, status, as_of_date, data_load_id, config_sha256, summary,
                                          started_at, finished_at, forecast_run_id, engine_version)
            VALUES ('RECOMMENDATION', 'COMPLETED', %s, %s, %s, '{}', now(), now(), %s, '0.1.0') RETURNING id
            """,
            (A, self.load_id, "b" * 64, self.forecast_run_id),
        ).fetchone()[0]
        values = {
            "calculation_run_id": run_id, "product_id": 1, "location_id": 1, "as_of_date": A, "outcome": "NO_NEED",
            "reasons": [], "flags": [], "missing_policy_parameters": [], "forecast_id": self.h1,
            "suggested_supplier_id": None, "suggested_order_date": None, "recommended_quantity": None,
            "raw_quantity": 0, "policy_set": "V1_PROVISIONAL", "policy_snapshot": Jsonb({}),
            "calculation_inputs": Jsonb({}), "engine_version": "0.1.0",
        }
        values.update(overrides)
        self.conn.execute(
            f"INSERT INTO recommendations ({', '.join(values)}) VALUES ({', '.join(['%s'] * len(values))})",
            tuple(values.values()),
        )

    def assert_rejected(self, insert, **overrides) -> None:
        with self.assertRaises((pg_errors.CheckViolation, pg_errors.ForeignKeyViolation, pg_errors.UniqueViolation)):
            with self.conn.transaction():
                insert(**overrides)

    def assert_accepted(self, insert, **overrides) -> None:
        with self.assertRaises(_Rollback):
            with self.conn.transaction():
                insert(**overrides)
                raise _Rollback

    def test_calculation_runs_columns_of_u4(self) -> None:
        self.assert_accepted(self.run_insert)
        cases = {
            "recommendation without forecast run": {"forecast_run_id": None},
            "recommendation without engine version": {"engine_version": None},
            "engine version not semver": {"engine_version": "v1"},
            "recommendation with a reference model": {"reference_model_version_id": 1},
            "forecast with a forecast run": {"run_type": "FORECAST", "reference_model_version_id": 1, "engine_version": None},
            "forecast with an engine version": {"run_type": "FORECAST", "reference_model_version_id": 1, "forecast_run_id": None},
            "unknown forecast run": {"forecast_run_id": 999999},
        }
        for name, overrides in cases.items():
            with self.subTest(name):
                self.assert_rejected(self.run_insert, **overrides)

    def test_recommendation_rows(self) -> None:
        self.assert_accepted(self.recommendation_insert)
        self.assert_accepted(
            self.recommendation_insert, outcome="RECOMMEND", raw_quantity=3, recommended_quantity=5,
            suggested_order_date=A, flags=["MOQ_APPLIED"], suggested_supplier_id=1,
        )
        self.assert_accepted(
            self.recommendation_insert, outcome="NOT_CALCULABLE", raw_quantity=None,
            reasons=["FORECAST_MISSING"], forecast_id=None,
        )
        cases = {
            "other policy set": {"policy_set": "POLICY_SET_V1_PROVISIONAL"},
            "unknown outcome": {"outcome": "FAILED"},
            "unknown reason": {"outcome": "NOT_CALCULABLE", "raw_quantity": None, "reasons": ["OTHER"]},
            "unknown flag": {"flags": ["OTHER"]},
            "not calculable without reasons": {"outcome": "NOT_CALCULABLE", "raw_quantity": None},
            "reasons on no need": {"reasons": ["NEGATIVE_ON_HAND"]},
            "no need with positive raw": {"raw_quantity": 1},
            "no need without raw": {"raw_quantity": None},
            "recommend without quantity": {"outcome": "RECOMMEND", "raw_quantity": 1, "suggested_order_date": A},
            "recommend with zero quantity": {"outcome": "RECOMMEND", "raw_quantity": 1, "recommended_quantity": 0, "suggested_order_date": A},
            "recommend without order date": {"outcome": "RECOMMEND", "raw_quantity": 1, "recommended_quantity": 1},
            "order date other than the cut": {"outcome": "RECOMMEND", "raw_quantity": 1, "recommended_quantity": 1,
                                              "suggested_order_date": A + dt.timedelta(days=1)},
            "moq flag without recommend": {"flags": ["MOQ_APPLIED"]},
            "forecast missing with a forecast": {"outcome": "NOT_CALCULABLE", "raw_quantity": None, "reasons": ["FORECAST_MISSING"]},
            "no forecast without forecast missing": {"forecast_id": None},
            "missing parameters without the reason": {"missing_policy_parameters": ["z"]},
            "missing reason without parameters": {"outcome": "NOT_CALCULABLE", "raw_quantity": None,
                                                  "reasons": ["MISSING_POLICY_PARAMETER"]},
            "engine version not semver": {"engine_version": "x"},
            "unknown product": {"product_id": 999999},
        }
        for name, overrides in cases.items():
            with self.subTest(name):
                self.assert_rejected(self.recommendation_insert, **overrides)


if __name__ == "__main__":
    unittest.main()
