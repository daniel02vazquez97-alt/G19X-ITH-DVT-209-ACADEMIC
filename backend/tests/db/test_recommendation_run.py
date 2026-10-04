"""The recommendation execution of U4 on the real dataset 0.4.0 (`DT-058` to `DT-063`, `docs/06` §16.13).

One database is loaded, forecast and evaluated once for the whole module at ``as_of_date = 2025-12-31``,
with a spy around `supply_engine.evaluate` that records every input it received and every result it
returned, unchanged. Tests read that state; none of them writes recommendations.
"""

from __future__ import annotations

import contextlib
import dataclasses
import datetime as dt
import io
import os
import unittest
from collections import Counter
from decimal import Decimal
from unittest import mock

import psycopg
from psycopg import errors as pg_errors
from _db_support import DATASET_DIR, TemporaryDatabase

from app.db.migrations import apply_migrations
from app.ingestion.loader import load_dataset
from app.runs.__main__ import main
from app.runs.config import canonical_json
from app.runs.config import config_sha256 as u3_config_sha256
from app.runs.forecast import run_forecast
from app.runs.recommendation import (
    RecommendationRunOutcome,
    evaluate_context,
    read_context,
    run_recommendations,
)
from app.runs.recommendation_config import breakdown_document, config_sha256, input_sha256, run_configuration
from app.supply_engine import ENGINE_VERSION, V1_PROVISIONAL_PARAMETERS, EvaluationInput, Outcome, evaluate

A = dt.date(2025, 12, 31)
H1 = A + dt.timedelta(days=1)
INACTIVE = [21, 26, 37, 56, 61]
WITHOUT_PREFERRED = [3, 20, 57, 71, 74]

_DB: TemporaryDatabase | None = None
_FORECAST = None
_RUN = None
_CALLS: list[tuple[EvaluationInput, object]] = []


def _spy(inputs: EvaluationInput):
    result = evaluate(inputs)
    _CALLS.append((inputs, result))
    return result


def setUpModule() -> None:
    global _DB, _FORECAST, _RUN
    _DB = TemporaryDatabase()
    try:
        with _DB.connect() as conn:
            apply_migrations(conn)
            load_dataset(conn, DATASET_DIR)
            _FORECAST = run_forecast(conn, A)
            _RUN = run_recommendations(conn, A, evaluator=_spy)
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

    def rows(self) -> dict[int, dict]:
        cur = self.conn.cursor(row_factory=psycopg.rows.dict_row)
        rows = cur.execute(
            "SELECT * FROM recommendations WHERE calculation_run_id = %s ORDER BY product_id", (_RUN.calculation_run_id,)
        ).fetchall()
        return {r["product_id"]: r for r in rows}


class RealExecutionTest(RunTestCase):
    def test_completed_with_the_documented_identity(self) -> None:
        self.assertIs(_RUN.outcome, RecommendationRunOutcome.COMPLETED)
        run = self.conn.execute(
            "SELECT run_type, status, as_of_date, forecast_run_id, engine_version, reference_model_version_id, "
            "config_sha256, error FROM calculation_runs WHERE id = %s",
            (_RUN.calculation_run_id,),
        ).fetchone()
        self.assertEqual(
            run,
            ("RECOMMENDATION", "COMPLETED", A, _FORECAST.calculation_run_id, ENGINE_VERSION, None,
             config_sha256(run_configuration()), None),
        )

    def test_one_evaluation_per_candidate(self) -> None:
        self.assertEqual((_RUN.summary["candidates"], _RUN.summary["evaluated"], _RUN.summary["rows"]), (100, 100, 100))
        self.assertEqual(self.one("SELECT count(*) FROM recommendations"), 100)
        self.assertEqual(len(_CALLS), 100)
        self.assertEqual(sum(_RUN.summary["by_outcome"].values()), 100)

    def test_the_ten_not_calculable_known_by_construction(self) -> None:
        rows = self.rows()
        not_calculable = sorted(p for p, r in rows.items() if r["outcome"] == "NOT_CALCULABLE")
        self.assertEqual(not_calculable, sorted(INACTIVE + WITHOUT_PREFERRED))
        for product in INACTIVE:
            self.assertEqual(rows[product]["reasons"], ["PRODUCT_INACTIVE", "PRODUCT_OUT_OF_VALIDITY", "FORECAST_MISSING"])
            self.assertIsNone(rows[product]["forecast_id"])
        for product in WITHOUT_PREFERRED:
            self.assertEqual(rows[product]["reasons"], ["NO_ACTIVE_PREFERRED_SUPPLIER"])
            self.assertIsNotNone(rows[product]["forecast_id"])
        self.assertEqual(
            _RUN.summary["forecast_missing"], [{"product_id": p, "location_id": 1} for p in INACTIVE]
        )

    def test_summary_is_deterministic_and_complete(self) -> None:
        summary = _RUN.summary
        self.assertEqual(
            set(summary),
            {"dataset_version", "data_load_id", "as_of_date", "forecast_run_id", "forecast_config_sha256",
             "engine_version", "policy_set", "input_rules_version", "candidates", "evaluated", "by_outcome",
             "by_reason", "by_flag", "forecast_missing", "rows"},
        )
        self.assertEqual(summary["dataset_version"], "ds-6c8ad65b4999")
        self.assertEqual(summary["forecast_config_sha256"], u3_config_sha256())
        self.assertEqual(summary["policy_set"], "V1_PROVISIONAL")
        rows = self.rows().values()
        self.assertEqual(summary["by_outcome"], dict(Counter(r["outcome"] for r in rows)))
        self.assertEqual(summary["by_flag"], dict(Counter(f for r in rows for f in r["flags"])))


class DtP18Test(RunTestCase):
    """Every outcome is one persisted row; NO_NEED is a row, never an absence (`DT-059`)."""

    def test_each_outcome_is_persisted_as_rows(self) -> None:
        counts = dict(
            self.conn.execute(
                "SELECT outcome, count(*) FROM recommendations WHERE calculation_run_id = %s GROUP BY outcome",
                (_RUN.calculation_run_id,),
            ).fetchall()
        )
        self.assertEqual(set(counts), {"RECOMMEND", "NO_NEED", "NOT_CALCULABLE"})
        self.assertEqual(counts, _RUN.summary["by_outcome"])

    def test_invariants_by_outcome(self) -> None:
        for product, row in self.rows().items():
            with self.subTest(product=product, outcome=row["outcome"]):
                if row["outcome"] == "RECOMMEND":
                    self.assertGreater(row["recommended_quantity"], 0)
                    self.assertGreater(row["raw_quantity"], 0)
                    self.assertEqual(row["suggested_order_date"], A)
                    self.assertEqual(row["reasons"], [])
                elif row["outcome"] == "NO_NEED":
                    self.assertEqual(row["raw_quantity"], 0)
                    self.assertIsNone(row["recommended_quantity"])
                    self.assertIsNone(row["suggested_order_date"])
                    self.assertEqual(row["reasons"], [])
                else:
                    self.assertTrue(row["reasons"])
                    self.assertIsNone(row["raw_quantity"])
                    self.assertIsNone(row["recommended_quantity"])
                self.assertEqual(row["policy_set"], "V1_PROVISIONAL")
                self.assertEqual(row["engine_version"], ENGINE_VERSION)
                self.assertEqual(row["as_of_date"], A)

    def test_no_human_workflow_columns(self) -> None:
        columns = {
            r[0]
            for r in self.conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'recommendations'"
            )
        }
        self.assertFalse({"status", "resolved_by", "resolved_at", "resolution_note", "urgency", "data_origin"} & columns)


class U1IntegrationTest(RunTestCase):
    """U4 builds the right input and persists U1's result unchanged."""

    def test_evaluate_receives_every_block(self) -> None:
        by_product = {inputs.product.product_id: inputs for inputs, _ in _CALLS}
        self.assertEqual(sorted(by_product), list(range(1, 101)))
        sample = by_product[1]
        self.assertEqual(sample.as_of_date, A)
        self.assertIs(sample.policy, V1_PROVISIONAL_PARAMETERS)
        self.assertTrue(sample.supplier_relations)
        self.assertTrue(sample.lead_time_observations)
        self.assertEqual(sample.consumption.start_date, dt.date(2023, 1, 1))
        self.assertEqual(len(sample.consumption.quantities), (A - dt.date(2023, 1, 1)).days + 1)
        self.assertEqual(sample.forecast.start_date, H1)
        self.assertEqual(len(sample.forecast.weekly_quantities), 14)
        self.assertIsNone(by_product[21].forecast)
        self.assertFalse(by_product[21].product.is_active)
        # Open lines: as many as the dataset has open with pending > 0 (89 lines in 0.4.0).
        self.assertEqual(sum(len(i.open_lines) for i in by_product.values()), 89)

    def test_result_persisted_without_transformation(self) -> None:
        rows = self.rows()
        for inputs, result in _CALLS:
            row = rows[inputs.product.product_id]
            with self.subTest(product=inputs.product.product_id):
                self.assertEqual(row["outcome"], result.outcome.value)
                self.assertEqual(row["reasons"], [r.value for r in result.reasons])
                self.assertEqual(row["flags"], [f.value for f in result.flags])
                self.assertEqual(row["missing_policy_parameters"], [p.value for p in result.missing_policy_parameters])
                self.assertEqual(row["forecast_id"], result.forecast_id)
                self.assertEqual(row["engine_version"], result.engine_version)
                document, approximate = breakdown_document(result.breakdown)
                self.assertEqual(row["calculation_inputs"]["breakdown"], document)
                self.assertEqual(row["calculation_inputs"]["approximate_terms"], approximate)
                self.assertEqual(len(document), len(dataclasses.fields(result.breakdown)))
                self.assertEqual(row["suggested_supplier_id"], result.breakdown.supplier_id)
                self.assertEqual(row["lead_time_used_days"], result.breakdown.lead_time_days)
                if result.outcome is Outcome.RECOMMEND:
                    self.assertEqual(row["recommended_quantity"], Decimal(result.breakdown.q_final.numerator) / result.breakdown.q_final.denominator)

    def test_reasons_and_flags_keep_the_canonical_order(self) -> None:
        canonical_flags = ["LEAD_TIME_AGREED_FALLBACK", "LEAD_TIME_CAPPED", "MOQ_APPLIED", "ORDER_MULTIPLE_ROUNDING",
                           "UNCOUNTED_TRANSIT", "OVERDUE_ORDERS_EXCLUDED", "ZERO_FORECAST_DEMAND"]
        for row in self.rows().values():
            self.assertEqual(row["flags"], sorted(row["flags"], key=canonical_flags.index))


class ForecastTest(RunTestCase):
    """`DT-058`, `DT-060`, `DT-061`: same cut, primary series, h=1 anchor, 14 copied quantities."""

    def test_forecast_id_is_the_h1_row_of_the_primary_series_of_the_same_cut(self) -> None:
        bad = self.one(
            """
            SELECT count(*) FROM recommendations r
            WHERE r.calculation_run_id = %s AND r.forecast_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM forecasts f WHERE f.id = r.forecast_id AND f.calculation_run_id = %s
                  AND f.product_id = r.product_id AND f.location_id = r.location_id AND f.is_primary
                  AND f.period_start = %s AND f.as_of_date = %s)
            """,
            (_RUN.calculation_run_id, _FORECAST.calculation_run_id, H1, A),
        )
        self.assertEqual(bad, 0)
        self.assertEqual(self.one("SELECT count(forecast_id) FROM recommendations"), 95)

    def test_calculation_inputs_copy_the_fourteen_quantities(self) -> None:
        for product, row in self.rows().items():
            block = row["calculation_inputs"]["forecast"]
            if row["forecast_id"] is None:
                self.assertIsNone(block)
                continue
            with self.subTest(product=product):
                stored = self.conn.execute(
                    """
                    SELECT f.predicted_quantity, m.name, m.version, f.confidence_flag FROM forecasts f
                    JOIN model_versions m ON m.id = f.model_version_id
                    WHERE f.calculation_run_id = %s AND f.product_id = %s AND f.is_primary ORDER BY f.period_start
                    """,
                    (_FORECAST.calculation_run_id, product),
                ).fetchall()
                self.assertEqual([Decimal(q) for q in block["weekly_quantities"]], [r[0] for r in stored])
                self.assertEqual(len(block["weekly_quantities"]), 14)
                self.assertEqual(block["model"], {"name": stored[0][1], "version": stored[0][2]})
                self.assertEqual(block["confidence_flag"], stored[0][3])
                self.assertEqual(block["start_date"], H1.isoformat())
                self.assertEqual(block["forecast_run_id"], str(_FORECAST.calculation_run_id))
                self.assertEqual(block["forecast_id"], str(row["forecast_id"]))
                self.assertEqual(block["method_used"], "BASELINE")

    def test_u4_does_not_call_the_forecast(self) -> None:
        self.assertEqual(self.one("SELECT count(*) FROM calculation_runs WHERE run_type = 'FORECAST'"), 1)


class PolicyTest(RunTestCase):
    def test_policy_snapshot_and_set(self) -> None:
        snapshots = {canonical_json(r["policy_snapshot"]) for r in self.rows().values()}
        self.assertEqual(snapshots, {'{"LT_MAX":90,"N":12,"N_MIN":3,"R":7,"policy_set":"V1_PROVISIONAL","z":"1.65"}'})


class TraceabilityTest(RunTestCase):
    def test_recommendation_to_dataset_version(self) -> None:
        chain = self.conn.execute(
            """
            SELECT rr.run_type, fr.run_type, f.period_start, d.dataset_version, d.data_origin,
                   rr.data_load_id = fr.data_load_id, rr.as_of_date = fr.as_of_date, m.name, r.engine_version,
                   r.policy_set, r.calculation_inputs->>'input_sha256'
            FROM recommendations r
            JOIN calculation_runs rr ON rr.id = r.calculation_run_id
            JOIN calculation_runs fr ON fr.id = rr.forecast_run_id
            JOIN forecasts f ON f.id = r.forecast_id
            JOIN model_versions m ON m.id = f.model_version_id
            JOIN data_loads d ON d.id = fr.data_load_id
            WHERE r.product_id = 1
            """
        ).fetchone()
        self.assertEqual(chain[:9], ("RECOMMENDATION", "FORECAST", H1, "ds-6c8ad65b4999", "SYNTHETIC", True, True,
                                     "baseline.moving_average", ENGINE_VERSION))
        self.assertEqual(chain[9], "V1_PROVISIONAL")
        self.assertRegex(chain[10], "^[0-9a-f]{64}$")


class ReconstructionTest(RunTestCase):
    """Re-reading the database and re-evaluating gives the same canonical rows, byte for byte."""

    @staticmethod
    def _canonical(row: dict) -> str:
        return canonical_json({k: (v.isoformat() if isinstance(v, dt.date) else str(v) if isinstance(v, Decimal) else v)
                               for k, v in row.items() if k not in ("id", "generated_at", "calculation_run_id")})

    def test_byte_for_byte_and_input_sha256(self) -> None:
        context = read_context(self.conn, A, _FORECAST.calculation_run_id)
        rebuilt = {r["product_id"]: r for r in evaluate_context(context)}
        stored = self.rows()
        self.assertEqual(sorted(rebuilt), sorted(stored))
        for product, row in stored.items():
            with self.subTest(product=product):
                self.assertEqual(self._canonical(row), self._canonical(rebuilt[product]))
        inputs = {i.product.product_id: i for i, _ in _CALLS}
        meta = context.forecast_meta
        for product, row in stored.items():
            model = None if inputs[product].forecast is None else {k: meta[(product, 1)][k] for k in ("name", "version")}
            self.assertEqual(row["calculation_inputs"]["input_sha256"], input_sha256(inputs[product], model))

    def test_session_time_zone_does_not_shift_dates(self) -> None:
        reference = read_context(self.conn, A, _FORECAST.calculation_run_id)
        with _DB.connect() as other:
            other.execute("SET TimeZone = 'Pacific/Kiritimati'")
            shifted = read_context(other, A, _FORECAST.calculation_run_id)
        self.assertEqual(shifted.order_lines, reference.order_lines)
        rebuilt = {r["product_id"]: r["calculation_inputs"]["input_sha256"] for r in evaluate_context(shifted)}
        self.assertEqual(rebuilt, {p: r["calculation_inputs"]["input_sha256"] for p, r in self.rows().items()})


class IdempotenceTest(RunTestCase):
    def test_second_execution_is_already_computed(self) -> None:
        before = self.one("SELECT count(*) FROM recommendations")
        again = run_recommendations(self.conn, A)
        self.assertIs(again.outcome, RecommendationRunOutcome.ALREADY_COMPUTED)
        self.assertEqual(again.calculation_run_id, _RUN.calculation_run_id)
        self.assertEqual(self.one("SELECT count(*) FROM recommendations"), before)
        self.assertEqual(self.one("SELECT count(*) FROM calculation_runs WHERE run_type = 'RECOMMENDATION'"), 1)

    def test_cli_twice_is_already_computed(self) -> None:
        with mock.patch.dict(os.environ, {"DATABASE_URL": _DB.dsn}):
            for _ in range(2):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(main(["recommend", "--as-of", "2025-12-31"]), 0)
                self.assertIn(f"ALREADY_COMPUTED: calculation_run {_RUN.calculation_run_id}", out.getvalue())
        self.assertEqual(self.one("SELECT count(*) FROM recommendations"), 100)


class ImmutabilityTest(RunTestCase):
    def test_update_and_delete_are_rejected(self) -> None:
        statements = [
            "UPDATE recommendations SET outcome = 'NO_NEED' WHERE product_id = 1",
            "DELETE FROM recommendations WHERE product_id = 1",
            f"UPDATE calculation_runs SET engine_version = '9.9.9' WHERE id = {_RUN.calculation_run_id}",
            f"DELETE FROM calculation_runs WHERE id = {_RUN.calculation_run_id}",
        ]
        for statement in statements:
            with self.subTest(statement), self.assertRaises(pg_errors.RaiseException):
                self.conn.execute(statement)
        self.assertEqual(self.one("SELECT count(*) FROM recommendations"), 100)


if __name__ == "__main__":
    unittest.main()
