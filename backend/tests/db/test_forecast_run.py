"""The forecast execution of U3 on the real dataset 0.4.0 (`DT-056`, `DT-057`, `docs/05` §19.9).

One database is loaded and forecast once for the whole module, at ``as_of_date = 2025-12-31``.
Tests either read it, change it inside always-rolled-back transactions, or add runs at other cuts
and look only at those runs.
"""

from __future__ import annotations

import datetime as dt
import unittest
from decimal import Decimal
from unittest import mock

import psycopg
from psycopg import errors as pg_errors
from _db_support import DATASET_DIR, TemporaryDatabase

from app.db.migrations import apply_migrations
from app.forecasting import MOVING_AVERAGE, NAIVE, SEASONAL_NAIVE, build_request, forecast
from app.ingestion.loader import load_dataset
from app.runs import forecast as forecast_module
from app.runs.config import config_sha256
from app.runs.forecast import ForecastRunOutcome, run_forecast

A = dt.date(2025, 12, 31)
DAY = dt.timedelta(days=1)

_DB: TemporaryDatabase | None = None
_RUN = None


def setUpModule() -> None:
    global _DB, _RUN
    _DB = TemporaryDatabase()
    try:
        with _DB.connect() as conn:
            apply_migrations(conn)
            load_dataset(conn, DATASET_DIR)
            _RUN = run_forecast(conn, A)
    except BaseException:
        _DB.drop()
        raise


def tearDownModule() -> None:
    if _DB is not None:
        _DB.drop()


class RunTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = _DB.connect()
        self.addCleanup(self.conn.close)

    def one(self, query: str, params: tuple = ()) -> object:
        return self.conn.execute(query, params).fetchone()[0]

    def model_ids(self) -> dict[str, int]:
        return dict(self.conn.execute("SELECT name, id FROM model_versions").fetchall())


class RealExecutionTest(RunTestCase):
    def test_the_execution_is_completed(self) -> None:
        self.assertIs(_RUN.outcome, ForecastRunOutcome.COMPLETED)
        status, run_type, as_of, reference, sha = self.conn.execute(
            "SELECT status, run_type, as_of_date, reference_model_version_id, config_sha256 "
            "FROM calculation_runs WHERE id = %s",
            (_RUN.calculation_run_id,),
        ).fetchone()
        self.assertEqual((status, run_type, as_of), ("COMPLETED", "FORECAST", A))
        self.assertEqual(reference, self.model_ids()[MOVING_AVERAGE.name])
        self.assertEqual(sha, config_sha256())

    def test_expected_counts(self) -> None:
        summary = _RUN.summary
        self.assertEqual(
            (summary["candidates"], summary["eligible"], summary["excluded_count"], summary["forecasted"]),
            (100, 95, 5, 95),
        )
        self.assertEqual((summary["fallback_count"], summary["no_forecast_count"]), (0, 0))
        self.assertEqual(summary["excluded_by_reason"], {"INACTIVE_OR_OUT_OF_VALIDITY": 5})
        self.assertEqual(summary["primary_by_model"], {MOVING_AVERAGE.name: 95})
        self.assertEqual(summary["series_by_model"], {d.name: 95 for d in (NAIVE, SEASONAL_NAIVE, MOVING_AVERAGE)})
        self.assertEqual((summary["forecast_rows"], summary["primary_rows"]), (3990, 1330))
        total, primary = self.conn.execute(
            "SELECT count(*), count(*) FILTER (WHERE is_primary) FROM forecasts WHERE calculation_run_id = %s",
            (_RUN.calculation_run_id,),
        ).fetchone()
        self.assertEqual((total, primary), (3990, 1330))

    def test_excluded_products_are_the_five_discontinued(self) -> None:
        discontinued = {
            r[0]
            for r in self.conn.execute(
                "SELECT id FROM products WHERE NOT is_active OR valid_to < %s", (A,)
            )
        }
        excluded = {e["product_id"] for e in _RUN.summary["excluded"]}
        self.assertEqual(excluded, discontinued)
        self.assertEqual(len(excluded), 5)
        forecast_products = {
            r[0] for r in self.conn.execute("SELECT DISTINCT product_id FROM forecasts")
        }
        self.assertFalse(excluded & forecast_products)

    def test_every_product_has_three_series_and_the_moving_average_is_primary(self) -> None:
        rows = self.conn.execute(
            """
            SELECT product_id, count(DISTINCT model_version_id), count(*),
                   array_agg(DISTINCT model_version_id) FILTER (WHERE is_primary),
                   array_agg(DISTINCT confidence_flag)
            FROM forecasts WHERE calculation_run_id = %s GROUP BY product_id
            """,
            (_RUN.calculation_run_id,),
        ).fetchall()
        ma = self.model_ids()[MOVING_AVERAGE.name]
        self.assertEqual(len(rows), 95)
        for product, models, count, primary, flags in rows:
            with self.subTest(product=product):
                self.assertEqual((models, count, primary, flags), (3, 42, [ma], ["STANDARD"]))

    def test_rows_match_the_provider_exactly(self) -> None:
        product = self.one("SELECT min(product_id) FROM forecasts WHERE calculation_run_id = %s", (_RUN.calculation_run_id,))
        history = self.conn.execute(
            "SELECT occurred_on, quantity, is_stockout_affected FROM consumption "
            "WHERE product_id = %s AND occurred_on <= %s ORDER BY occurred_on",
            (product, A),
        ).fetchall()
        result = forecast(build_request(product, 1, A, history))
        names = {v: k for k, v in self.model_ids().items()}
        stored = self.conn.execute(
            """
            SELECT model_version_id, period_start, period_end, predicted_quantity, lower_bound, upper_bound
            FROM forecasts WHERE calculation_run_id = %s AND product_id = %s
            ORDER BY model_version_id, period_start
            """,
            (_RUN.calculation_run_id, product),
        ).fetchall()
        expected = sorted(
            (self.model_ids()[s.definition.name], p.period_start, p.period_end, p.predicted_quantity, p.lower_bound, p.upper_bound)
            for s in result.series
            for p in s.periods
        )
        self.assertEqual(stored, expected)
        self.assertEqual({names[r[0]] for r in stored}, {NAIVE.name, SEASONAL_NAIVE.name, MOVING_AVERAGE.name})

    def test_row_values_follow_the_contract(self) -> None:
        bad = self.one(
            """
            SELECT count(*) FROM forecasts WHERE calculation_run_id = %s AND NOT (
                granularity = 'WEEKLY' AND method_used = 'BASELINE' AND confidence_level = 0.80
                AND as_of_date = %s AND period_end = period_start + 7
                AND period_start >= %s AND period_start <= %s
                AND (period_start - %s) %% 7 = 1
                AND 0 <= lower_bound AND lower_bound <= predicted_quantity AND predicted_quantity <= upper_bound
                AND scale(predicted_quantity) = 6)
            """,
            (_RUN.calculation_run_id, A, A + DAY, A + DAY * 92, A),
        )
        self.assertEqual(bad, 0)
        periods = self.conn.execute(
            "SELECT DISTINCT period_start FROM forecasts WHERE calculation_run_id = %s ORDER BY 1",
            (_RUN.calculation_run_id,),
        ).fetchall()
        self.assertEqual([r[0] for r in periods], [A + DAY * (1 + 7 * k) for k in range(14)])

    def test_generated_at_is_one_transaction_instant(self) -> None:
        stamps, started, finished = self.conn.execute(
            """
            SELECT count(DISTINCT f.generated_at), min(r.started_at), min(r.finished_at)
            FROM forecasts f JOIN calculation_runs r ON r.id = f.calculation_run_id
            WHERE f.calculation_run_id = %s
            """,
            (_RUN.calculation_run_id,),
        ).fetchone()
        self.assertEqual(stamps, 1)
        stamp = self.one("SELECT min(generated_at) FROM forecasts WHERE calculation_run_id = %s", (_RUN.calculation_run_id,))
        self.assertTrue(started <= stamp <= finished)

    def test_traceability_to_the_dataset(self) -> None:
        versions = self.conn.execute(
            """
            SELECT DISTINCT d.dataset_version, d.status
            FROM forecasts f
            JOIN calculation_runs r ON r.id = f.calculation_run_id
            JOIN data_loads d ON d.id = r.data_load_id
            """
        ).fetchall()
        self.assertEqual(versions, [("ds-6c8ad65b4999", "COMPLETED")])
        orphans = self.one(
            "SELECT count(*) FROM forecasts f LEFT JOIN calculation_runs r ON r.id = f.calculation_run_id "
            "WHERE r.data_load_id IS NULL"
        )
        self.assertEqual(orphans, 0)

    def test_the_advisory_lock_is_released(self) -> None:
        self.assertEqual(self.one("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory'"), 0)


class ModelVersionsTest(RunTestCase):
    def test_three_baselines_without_training_fields(self) -> None:
        rows = self.conn.execute(
            """
            SELECT name, version, algorithm, hyperparameters, is_baseline, status, trained_at,
                   training_data_from, training_data_to, metrics, baseline_metrics, external_ref
            FROM model_versions ORDER BY name
            """
        ).fetchall()
        expected = sorted(
            (d.name, d.version, d.algorithm, d.hyperparameters, True) + (None,) * 7
            for d in (NAIVE, SEASONAL_NAIVE, MOVING_AVERAGE)
        )
        self.assertEqual(rows, expected)

    def test_name_and_version_are_unique(self) -> None:
        with self.conn.transaction(force_rollback=True):
            with self.assertRaises(pg_errors.UniqueViolation), self.conn.transaction():
                self.conn.execute(
                    "INSERT INTO model_versions (name, version, algorithm, hyperparameters, is_baseline) "
                    "VALUES ('baseline.naive', '1.0.0', 'NAIVE', '{}', true)"
                )

    def test_a_baseline_has_no_status_and_a_model_has_one(self) -> None:
        for statement in (
            "INSERT INTO model_versions (name, version, algorithm, hyperparameters, is_baseline, status) "
            "VALUES ('x', '1', 'X', '{}', true, 'PRODUCTION')",
            "INSERT INTO model_versions (name, version, algorithm, hyperparameters, is_baseline) "
            "VALUES ('y', '1', 'Y', '{}', false)",
        ):
            with self.subTest(statement=statement), self.conn.transaction(force_rollback=True):
                with self.assertRaises(pg_errors.CheckViolation), self.conn.transaction():
                    self.conn.execute(statement)


class IdempotenceTest(RunTestCase):
    def test_repeating_the_execution_writes_nothing(self) -> None:
        before = self.conn.execute(
            "SELECT (SELECT count(*) FROM calculation_runs), (SELECT count(*) FROM forecasts), "
            "(SELECT count(*) FROM model_versions)"
        ).fetchone()
        result = run_forecast(self.conn, A)
        self.assertIs(result.outcome, ForecastRunOutcome.ALREADY_COMPUTED)
        self.assertEqual(result.calculation_run_id, _RUN.calculation_run_id)
        after = self.conn.execute(
            "SELECT (SELECT count(*) FROM calculation_runs), (SELECT count(*) FROM forecasts), "
            "(SELECT count(*) FROM model_versions)"
        ).fetchone()
        self.assertEqual(after, before)

    def test_a_second_completed_run_for_the_same_identity_is_impossible(self) -> None:
        with self.conn.transaction(force_rollback=True):
            with self.assertRaises(pg_errors.UniqueViolation), self.conn.transaction():
                self.conn.execute(
                    """
                    INSERT INTO calculation_runs (run_type, status, as_of_date, data_load_id,
                        reference_model_version_id, config_sha256, summary, started_at, finished_at)
                    SELECT run_type, status, as_of_date, data_load_id, reference_model_version_id,
                           config_sha256, '{}', now(), now()
                    FROM calculation_runs WHERE id = %s
                    """,
                    (_RUN.calculation_run_id,),
                )


class ConstraintAndImmutabilityTest(RunTestCase):
    def assertViolates(self, error: type[Exception], statement: str, params: tuple = ()) -> None:
        with self.conn.transaction(force_rollback=True):
            with self.assertRaises(error, msg=statement), self.conn.transaction():
                self.conn.execute(statement, params)

    def test_forecasts_and_runs_are_immutable(self) -> None:
        run = _RUN.calculation_run_id
        for statement in (
            "UPDATE forecasts SET predicted_quantity = predicted_quantity + 1 WHERE calculation_run_id = %s",
            "DELETE FROM forecasts WHERE calculation_run_id = %s",
            "UPDATE calculation_runs SET summary = '{}' WHERE id = %s",
            "DELETE FROM calculation_runs WHERE id = %s",
        ):
            with self.subTest(statement=statement):
                self.assertViolates(pg_errors.RaiseException, statement, (run,))

    def _copy_row(self, **changes: str) -> str:
        columns = [
            "calculation_run_id", "product_id", "location_id", "model_version_id", "as_of_date",
            "period_start", "period_end", "granularity", "predicted_quantity", "lower_bound",
            "upper_bound", "confidence_level", "method_used", "confidence_flag", "is_primary",
        ]
        values = [changes.get(c, c) for c in columns]
        return (
            f"INSERT INTO forecasts ({', '.join(columns)}) SELECT {', '.join(values)} FROM forecasts "
            f"WHERE calculation_run_id = {_RUN.calculation_run_id} AND is_primary ORDER BY id LIMIT 1"
        )

    def test_checks_and_unique_keys(self) -> None:
        check, unique, fk = pg_errors.CheckViolation, pg_errors.UniqueViolation, pg_errors.ForeignKeyViolation
        self.assertViolates(unique, self._copy_row())
        self.assertViolates(unique, self._copy_row(model_version_id=str(self.model_ids()[NAIVE.name])))
        self.assertViolates(check, self._copy_row(period_end="period_start + 8", is_primary="false"))
        self.assertViolates(check, self._copy_row(lower_bound="predicted_quantity + 1", is_primary="false"))
        self.assertViolates(check, self._copy_row(upper_bound="predicted_quantity - 1", is_primary="false"))
        self.assertViolates(check, self._copy_row(lower_bound="-1", is_primary="false"))
        self.assertViolates(check, self._copy_row(predicted_quantity="predicted_quantity + 0.0000001", upper_bound="upper_bound + 1", is_primary="false"))
        self.assertViolates(check, self._copy_row(confidence_level="1", is_primary="false"))
        self.assertViolates(check, self._copy_row(method_used="'ML'", is_primary="false"))
        self.assertViolates(check, self._copy_row(confidence_flag="'LOW'", is_primary="false"))
        self.assertViolates(check, self._copy_row(granularity="'HOURLY'", is_primary="false"))
        self.assertViolates(check, self._copy_row(period_start="as_of_date", period_end="as_of_date + 7", is_primary="false"))
        self.assertViolates(fk, self._copy_row(product_id="999999", is_primary="false"))
        self.assertViolates(fk, self._copy_row(model_version_id="999999", is_primary="false"))
        self.assertViolates(fk, self._copy_row(calculation_run_id="999999", is_primary="false"))

    def test_run_checks(self) -> None:
        check, fk = pg_errors.CheckViolation, pg_errors.ForeignKeyViolation
        base = (
            "INSERT INTO calculation_runs (run_type, status, as_of_date, data_load_id, reference_model_version_id, "
            "config_sha256, summary, error, started_at, finished_at) VALUES ({}, {}, '2025-12-30', {}, {}, {}, '{{}}', {}, now(), now())"
        )
        ok = dict(rt="'FORECAST'", st="'COMPLETED'", dl="1", ref=str(self.model_ids()[MOVING_AVERAGE.name]), sha=f"'{'0' * 64}'", err="NULL")

        def stmt(**c: str) -> str:
            v = {**ok, **c}
            return base.format(v["rt"], v["st"], v["dl"], v["ref"], v["sha"], v["err"])

        self.assertViolates(check, stmt(st="'RUNNING'"))
        self.assertViolates(check, stmt(rt="'BACKTEST'"))
        self.assertViolates(check, stmt(ref="NULL"))
        self.assertViolates(check, stmt(sha="'abc'"))
        self.assertViolates(check, stmt(st="'FAILED'"))  # FAILED needs an error
        self.assertViolates(check, stmt(err="'{\"type\": \"X\"}'"))  # COMPLETED has no error
        self.assertViolates(fk, stmt(dl="999"))


class FailureAndRecoveryTest(RunTestCase):
    CUT = A - DAY  # a cut not computed by the module run

    def runs_at(self, cut: dt.date) -> list[tuple]:
        return self.conn.execute(
            "SELECT id, status FROM calculation_runs WHERE as_of_date = %s ORDER BY id", (cut,)
        ).fetchall()

    def test_failure_before_commit_rolls_back_and_records_failed_then_retry_completes(self) -> None:
        models_before = self.one("SELECT count(*) FROM model_versions")
        with mock.patch.object(forecast_module, "_check_persisted", side_effect=RuntimeError("injected failure")):
            failed = run_forecast(self.conn, self.CUT)
        self.assertIs(failed.outcome, ForecastRunOutcome.FAILED)
        self.assertEqual(failed.error["message"], "injected failure")
        self.assertEqual(self.runs_at(self.CUT), [(failed.calculation_run_id, "FAILED")])
        self.assertEqual(self.one("SELECT count(*) FROM forecasts WHERE as_of_date = %s", (self.CUT,)), 0)
        self.assertEqual(self.one("SELECT count(*) FROM model_versions"), models_before)
        error = self.one("SELECT error FROM calculation_runs WHERE id = %s", (failed.calculation_run_id,))
        self.assertEqual(error, {"type": "RuntimeError", "message": "injected failure"})
        # A FAILED run does not block the next one.
        retry = run_forecast(self.conn, self.CUT)
        self.assertIs(retry.outcome, ForecastRunOutcome.COMPLETED)
        self.assertEqual(
            self.one("SELECT count(*) FROM forecasts WHERE calculation_run_id = %s", (retry.calculation_run_id,)), 3990
        )

    def test_a_database_error_is_also_recorded(self) -> None:
        cut = A - DAY * 2
        original = forecast_module._insert_forecasts

        def broken(conn: psycopg.Connection, run_id: int, rows: list) -> None:
            original(conn, run_id, rows[:-1] + [rows[-1][:8] + (Decimal(-1),) + rows[-1][9:]])

        with mock.patch.object(forecast_module, "_insert_forecasts", side_effect=broken):
            failed = run_forecast(self.conn, cut)
        self.assertIs(failed.outcome, ForecastRunOutcome.FAILED)
        self.assertEqual(failed.error["sqlstate"], "23514")  # check_violation
        self.assertEqual(self.one("SELECT count(*) FROM forecasts WHERE as_of_date = %s", (cut,)), 0)

    def test_dates_outside_the_load_are_refused_without_writing(self) -> None:
        before = self.one("SELECT count(*) FROM calculation_runs")
        for cut in (dt.date(2026, 1, 1), dt.date(2022, 12, 31)):
            with self.subTest(cut=cut), self.assertRaises(forecast_module.ForecastRunError):
                run_forecast(self.conn, cut)
        self.assertEqual(self.one("SELECT count(*) FROM calculation_runs"), before)


class FallbackOnRealDataTest(RunTestCase):
    def test_short_history_falls_back_to_naive(self) -> None:
        # 2023-01-01 … 2023-07-15 = 196 days = 28 complete weeks: naïve only.
        cut = dt.date(2023, 7, 15)
        result = run_forecast(self.conn, cut)
        self.assertIs(result.outcome, ForecastRunOutcome.COMPLETED)
        self.assertEqual((result.summary["fallback_count"], result.summary["forecasted"]), (95, 95))
        self.assertEqual(result.summary["primary_by_model"], {NAIVE.name: 95})
        flags = self.conn.execute(
            "SELECT DISTINCT is_primary, confidence_flag FROM forecasts WHERE calculation_run_id = %s",
            (result.calculation_run_id,),
        ).fetchall()
        self.assertEqual(flags, [(True, "INSUFFICIENT_HISTORY")])
        self.assertEqual(result.summary["forecast_rows"], 95 * 14)

    def test_too_short_history_gives_no_forecast(self) -> None:
        cut = dt.date(2023, 5, 1)  # 121 days = 17 weeks
        result = run_forecast(self.conn, cut)
        self.assertIs(result.outcome, ForecastRunOutcome.COMPLETED)
        self.assertEqual((result.summary["no_forecast_count"], result.summary["forecasted"]), (95, 0))
        self.assertEqual({e["reason"] for e in result.summary["no_forecast"]}, {"INSUFFICIENT_HISTORY"})
        self.assertEqual(self.one("SELECT count(*) FROM forecasts WHERE calculation_run_id = %s", (result.calculation_run_id,)), 0)


class U1FormatCompatibilityTest(RunTestCase):
    """Test only: the primary series has the format U1 expects. No production path U3 → U1."""

    def test_every_primary_series_is_a_valid_u1_forecast(self) -> None:
        import supply_engine.builders as builders  # tests/supply_engine, through _db_support's path

        from app.supply_engine import Forecast, InvalidInputError, MethodUsed, evaluate

        rows = self.conn.execute(
            """
            SELECT product_id, min(id), min(model_version_id),
                   array_agg(predicted_quantity ORDER BY period_start), min(period_start)
            FROM forecasts WHERE calculation_run_id = %s AND is_primary GROUP BY product_id
            """,
            (_RUN.calculation_run_id,),
        ).fetchall()
        self.assertEqual(len(rows), 95)
        for product, first_id, model_version, weekly, start in rows:
            with self.subTest(product=product):
                u1_forecast = Forecast(
                    start_date=start,
                    weekly_quantities=tuple(weekly),
                    forecast_id=first_id,
                    model_version=model_version,
                    method_used=MethodUsed.BASELINE,
                )
                try:
                    result = evaluate(builders.evaluation(as_of_date=A, forecast=u1_forecast))
                except InvalidInputError as exc:  # pragma: no cover - the assertion is the point
                    self.fail(f"U1 rejected the forecast of product {product}: {exc}")
                self.assertEqual(result.forecast_id, first_id)


if __name__ == "__main__":
    unittest.main()
