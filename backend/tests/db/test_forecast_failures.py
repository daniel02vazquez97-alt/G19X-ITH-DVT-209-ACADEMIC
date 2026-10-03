"""Refused executions, version mismatches and invalid histories (`DT-057`), each on a fresh database."""

from __future__ import annotations

import datetime as dt

from _db_support import DATASET_DIR, DatabaseTestCase

from app.forecasting import NAIVE
from app.ingestion.loader import load_dataset
from app.runs.forecast import ForecastRunError, ForecastRunOutcome, register_model_versions, run_forecast

A = dt.date(2025, 12, 31)


class RefusedExecutionTest(DatabaseTestCase):
    def test_without_a_completed_load_nothing_is_written(self) -> None:
        with self.assertRaises(ForecastRunError):
            run_forecast(self.conn, A)
        self.assertEqual(self.count("calculation_runs"), 0)
        self.assertEqual(self.count("model_versions"), 0)

    def test_without_the_schema_the_execution_is_refused(self) -> None:
        self.conn.execute("DROP TABLE forecasts, calculation_runs")
        with self.assertRaises(ForecastRunError):
            run_forecast(self.conn, A)


class ModelVersionRegistrationTest(DatabaseTestCase):
    def test_registration_is_idempotent(self) -> None:
        first = register_model_versions(self.conn)
        second = register_model_versions(self.conn)
        self.assertEqual(first, second)
        self.assertEqual(self.count("model_versions"), 3)

    def test_a_changed_definition_under_the_same_version_is_an_error(self) -> None:
        self.conn.execute(
            "INSERT INTO model_versions (name, version, algorithm, hyperparameters, is_baseline) "
            "VALUES (%s, %s, %s, '{\"horizon_weeks\": 13}', true)",
            (NAIVE.name, NAIVE.version, NAIVE.algorithm),
        )
        with self.assertRaises(ForecastRunError):
            register_model_versions(self.conn)
        # Nothing was overwritten, and the other two were not registered either.
        self.assertEqual(self.count("model_versions"), 1)
        stored = self.conn.execute("SELECT hyperparameters FROM model_versions").fetchone()[0]
        self.assertEqual(stored, {"horizon_weeks": 13})


class InvalidHistoryTest(DatabaseTestCase):
    def test_a_gap_excludes_the_series_without_imputation(self) -> None:
        load_dataset(self.conn, DATASET_DIR)
        product = self.conn.execute(
            "SELECT min(id) FROM products WHERE is_active AND valid_to IS NULL"
        ).fetchone()[0]
        self.conn.execute(
            "DELETE FROM consumption WHERE product_id = %s AND occurred_on = %s", (product, dt.date(2025, 6, 1))
        )
        result = run_forecast(self.conn, A)
        self.assertIs(result.outcome, ForecastRunOutcome.COMPLETED)
        invalid = [e for e in result.summary["excluded"] if e["reason"] == "INVALID_HISTORY"]
        self.assertEqual(invalid, [{"product_id": product, "location_id": 1, "reason": "INVALID_HISTORY", "detail": "GAP"}])
        self.assertEqual(result.summary["forecasted"], 94)
        self.assertEqual(
            self.conn.execute("SELECT count(*) FROM forecasts WHERE product_id = %s", (product,)).fetchone()[0], 0
        )
