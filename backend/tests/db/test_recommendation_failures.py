"""Rollback, FAILED runs, data errors, `demand` never read and concurrency of U4 (`DT-059`, `DT-062`).

Every test works on a fresh database with the dataset 0.4.0 loaded and forecast at 2025-12-31.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import threading

from _db_support import DATASET_DIR, DatabaseTestCase

from app.ingestion.loader import load_dataset
from app.runs.forecast import run_forecast
from app.runs.recommendation import RecommendationRunOutcome, run_recommendations
from app.supply_engine import InvalidInputError, Outcome, evaluate

A = dt.date(2025, 12, 31)


class FailureTestCase(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        load_dataset(self.conn, DATASET_DIR)
        self.forecast_run_id = run_forecast(self.conn, A).calculation_run_id

    def run_row(self, run_id: int) -> tuple:
        return self.conn.execute(
            "SELECT status, error, forecast_run_id, engine_version FROM calculation_runs WHERE id = %s", (run_id,)
        ).fetchone()

    def assert_failed(self, result) -> dict:
        self.assertIs(result.outcome, RecommendationRunOutcome.FAILED)
        status, error, forecast_run_id, engine_version = self.run_row(result.calculation_run_id)
        self.assertEqual(status, "FAILED")
        self.assertEqual(forecast_run_id, self.forecast_run_id)
        self.assertIsNotNone(engine_version)
        self.assertEqual(self.count("recommendations"), 0)  # nothing partial: NOT_CALCULABLE != FAILED
        return error


class RollbackTest(FailureTestCase):
    def test_invalid_input_error_fails_the_run_and_a_retry_completes(self) -> None:
        def broken(inputs):
            if inputs.product.product_id == 42:
                raise InvalidInputError("inventory.total_in_transit", "must equal the sum of open_lines.quantity_pending")
            return evaluate(inputs)

        error = self.assert_failed(run_recommendations(self.conn, A, evaluator=broken))
        self.assertEqual(
            error,
            {
                "product_id": 42,
                "location_id": 1,
                "type": "InvalidInputError",
                "message": "inventory.total_in_transit: must equal the sum of open_lines.quantity_pending",
                "field": "inventory.total_in_transit",
            },
        )
        retry = run_recommendations(self.conn, A)  # a FAILED run does not block the identity
        self.assertIs(retry.outcome, RecommendationRunOutcome.COMPLETED)
        self.assertEqual(self.count("recommendations"), 100)
        statuses = self.conn.execute(
            "SELECT status FROM calculation_runs WHERE run_type = 'RECOMMENDATION' ORDER BY id"
        ).fetchall()
        self.assertEqual([s[0] for s in statuses], ["FAILED", "COMPLETED"])

    def test_database_error_after_partial_inserts_leaves_nothing(self) -> None:
        def violating(inputs):
            result = evaluate(inputs)
            if result.outcome is Outcome.NOT_CALCULABLE:  # a row the CHECK constraints reject
                return dataclasses.replace(result, outcome=Outcome.RECOMMEND)
            return result

        error = self.assert_failed(run_recommendations(self.conn, A, evaluator=violating))
        self.assertEqual(error["sqlstate"], "23514")  # check_violation
        self.assertEqual(error["type"], "CheckViolation")
        self.assertIs(run_recommendations(self.conn, A).outcome, RecommendationRunOutcome.COMPLETED)


class DataErrorTest(FailureTestCase):
    def test_missing_inventory_row_fails_instead_of_zeros(self) -> None:
        self.conn.execute("DELETE FROM inventory WHERE product_id = 5")
        error = self.assert_failed(run_recommendations(self.conn, A))
        self.assertEqual((error["product_id"], error["code"], error["field"]), (5, "MISSING_INVENTORY", "inventory"))

    def test_consumption_gap_fails_without_imputation(self) -> None:
        self.conn.execute("DELETE FROM consumption WHERE product_id = 8 AND occurred_on = '2025-06-01'")
        error = self.assert_failed(run_recommendations(self.conn, A))
        self.assertEqual((error["product_id"], error["code"]), (8, "CONSUMPTION_GAP"))

    def test_demand_is_never_read(self) -> None:
        self.conn.execute("ALTER TABLE demand RENAME TO demand_hidden")
        result = run_recommendations(self.conn, A)
        self.assertIs(result.outcome, RecommendationRunOutcome.COMPLETED)
        self.assertEqual(self.count("recommendations"), 100)


class ConcurrencyTest(FailureTestCase):
    def test_two_concurrent_executions_give_one_effective_run(self) -> None:
        barrier = threading.Barrier(2)
        results = []

        def worker() -> None:
            with self.database.connect() as conn:
                barrier.wait()
                results.append(run_recommendations(conn, A))

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=120)
        self.assertEqual(sorted(r.outcome for r in results), ["ALREADY_COMPUTED", "COMPLETED"])
        self.assertEqual(len({r.calculation_run_id for r in results}), 1)
        self.assertEqual(self.count("recommendations"), 100)
        self.assertEqual(
            self.conn.execute("SELECT count(*) FROM calculation_runs WHERE run_type = 'RECOMMENDATION'").fetchone()[0], 1
        )
