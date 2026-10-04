"""Recommendation execution of U4 (`DT-058` to `DT-063`, `docs/06` §16.13).

PostgreSQL (U2) → forecast execution of U3 → `EvaluationInput` → `supply_engine.evaluate` → one
immutable ``recommendations`` row per evaluation, with traceability up to ``data_loads``.

1. Preconditions, refused without writing (`RecommendationRunError`): schema, the single ``COMPLETED``
   load, ``data_origin = 'SYNTHETIC'`` (`DT-063`), ``as_of_date = upper(time_range) − 1`` (`DT-058`)
   and the ``FORECAST`` ``COMPLETED`` execution with the same cut, load and current U3 configuration
   (`DT-061`). U4 never launches the forecast.
2. ``config_sha256`` and an advisory lock on the logical identity; an equal ``COMPLETED`` execution →
   ``ALREADY_COMPUTED``, nothing written (`DT-062`).
3. In ONE transaction: read, adapt, evaluate every product × location, insert the run and its rows and
   check them; on any failure, rollback and a ``FAILED`` row in a separate transaction.

The supply decision is U1's: this module only reads, adapts, calls `evaluate` and persists its result
unchanged.
"""

from __future__ import annotations

import datetime as _dt
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.supply_engine import (
    ENGINE_VERSION,
    V1_PROVISIONAL_PARAMETERS,
    EvaluationInput,
    EvaluationResult,
    InvalidInputError,
    Outcome,
    evaluate,
)

from .recommendation_config import (
    INPUT_RULES_VERSION,
    RUN_TYPE,
    breakdown_document,
    config_sha256,
    exact_text,
    forecast_config_sha256,
    input_sha256,
    lock_key,
    numeric_value,
    policy_snapshot,
    run_configuration,
)
from .recommendation_inputs import (
    AdapterError,
    ConsumptionRow,
    ForecastRow,
    InventoryRow,
    OrderLineRow,
    ProductRow,
    RelationRow,
    build_evaluation_input,
)

Evaluator = Callable[[EvaluationInput], EvaluationResult]

SYNTHETIC = "SYNTHETIC"

RECOMMENDATION_COLUMNS = (
    "calculation_run_id",
    "product_id",
    "location_id",
    "as_of_date",
    "outcome",
    "reasons",
    "flags",
    "missing_policy_parameters",
    "forecast_id",
    "suggested_supplier_id",
    "suggested_order_date",
    "recommended_quantity",
    "raw_quantity",
    "reorder_point",
    "safety_stock",
    "lead_time_used_days",
    "demand_during_lead_time",
    "inventory_position_at_calc",
    "policy_set",
    "policy_snapshot",
    "calculation_inputs",
    "engine_version",
)


class RecommendationRunOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    ALREADY_COMPUTED = "ALREADY_COMPUTED"
    FAILED = "FAILED"

    @property
    def ok(self) -> bool:
        return self is not RecommendationRunOutcome.FAILED


@dataclass(frozen=True)
class RecommendationRunResult:
    outcome: RecommendationRunOutcome
    calculation_run_id: int
    as_of_date: _dt.date
    summary: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None


class RecommendationRunError(RuntimeError):
    """The execution cannot start (schema, load, origin, cut or forecast execution). Nothing is written."""


class CandidateError(RuntimeError):
    """An evaluation could not be built or run: carries the product-location for the ``FAILED`` row."""

    def __init__(self, product_id: int, location_id: int, cause: Exception) -> None:
        self.product_id = product_id
        self.location_id = location_id
        self.cause = cause
        super().__init__(f"product {product_id}, location {location_id}: {cause}")


@dataclass(frozen=True)
class LoadContext:
    id: int
    dataset_version: str
    data_origin: str | None
    as_of_date: _dt.date


@dataclass
class EvaluationContext:
    """Everything read from PostgreSQL for one execution, grouped for the pure adapter."""

    as_of_date: _dt.date
    forecast_run_id: int
    candidates: list[ProductRow]
    relations: dict[int, list[RelationRow]]
    inventory: dict[tuple[int, int], InventoryRow]
    order_lines: list[OrderLineRow]
    consumption: dict[tuple[int, int], list[ConsumptionRow]]
    forecasts: dict[tuple[int, int], list[ForecastRow]]
    forecast_meta: dict[tuple[int, int], dict[str, str]]


# --------------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------------


def run_recommendations(
    conn: psycopg.Connection, as_of_date: _dt.date, evaluator: Evaluator = evaluate
) -> RecommendationRunResult:
    """Evaluate every product × location at ``as_of_date`` and persist the result.

    ``conn`` must be in autocommit mode: this function opens its own transactions.
    """
    if not conn.autocommit:
        raise ValueError("run_recommendations needs an autocommit connection")
    if conn.execute("SELECT to_regclass('recommendations')").fetchone()[0] is None:
        raise RecommendationRunError("schema missing: run `python -m app.db migrate` first")
    load = completed_load(conn, as_of_date)
    forecast_sha = forecast_config_sha256()
    forecast_run_id = select_forecast_run(conn, as_of_date, load.id, forecast_sha)
    started_at = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    sha = config_sha256(run_configuration(forecast_config=forecast_sha))
    key = lock_key(as_of_date, load.id, sha)

    conn.execute("SELECT pg_advisory_lock(%s)", (key,))
    try:
        existing = conn.execute(
            """
            SELECT id, summary FROM calculation_runs
            WHERE run_type = %s AND status = 'COMPLETED' AND as_of_date = %s
              AND data_load_id = %s AND config_sha256 = %s
            """,
            (RUN_TYPE, as_of_date, load.id, sha),
        ).fetchone()
        if existing is not None:
            return RecommendationRunResult(RecommendationRunOutcome.ALREADY_COMPUTED, existing[0], as_of_date, existing[1])
        try:
            with conn.transaction():
                context = read_context(conn, as_of_date, forecast_run_id)
                rows = evaluate_context(context, evaluator)
                summary = build_summary(load, forecast_run_id, forecast_sha, context, rows)
                run_id = _insert_run(conn, load, forecast_run_id, sha, summary, started_at, None)
                _insert_recommendations(conn, run_id, rows)
                _check_persisted(conn, run_id, forecast_run_id, len(context.candidates))
        except Exception as exc:  # noqa: BLE001 — every failure is recorded, then reported
            error = describe_error(exc)
            failed_summary = {
                "as_of_date": as_of_date.isoformat(),
                "data_load_id": load.id,
                "forecast_run_id": forecast_run_id,
                "engine_version": ENGINE_VERSION,
            }
            with conn.transaction():
                run_id = _insert_run(conn, load, forecast_run_id, sha, failed_summary, started_at, error)
            return RecommendationRunResult(RecommendationRunOutcome.FAILED, run_id, as_of_date, failed_summary, error)
        return RecommendationRunResult(RecommendationRunOutcome.COMPLETED, run_id, as_of_date, summary)
    finally:
        conn.execute("SELECT pg_advisory_unlock(%s)", (key,))


# --------------------------------------------------------------------------------------------
# Preconditions (nothing is written)
# --------------------------------------------------------------------------------------------


def completed_load(conn: psycopg.Connection, as_of_date: _dt.date) -> LoadContext:
    """The single ``COMPLETED`` load, ``SYNTHETIC`` (`DT-063`), whose last day is ``as_of_date`` (`DT-058`)."""
    row = conn.execute(
        "SELECT id, dataset_version, data_origin, upper(time_range) FROM data_loads WHERE status = 'COMPLETED'"
    ).fetchone()
    if row is None:
        raise RecommendationRunError("no COMPLETED data load: load a dataset first (`python -m app.ingestion`)")
    load_id, version, origin, end = row
    if origin != SYNTHETIC:
        raise RecommendationRunError(
            f"data load {load_id} has data_origin {origin!r}: V1_PROVISIONAL only runs on SYNTHETIC loads (DT-063)"
        )
    if end is None:
        raise RecommendationRunError(f"data load {load_id} has no time_range")
    cut = end - _dt.timedelta(days=1)
    if as_of_date != cut:
        raise RecommendationRunError(f"as_of_date {as_of_date} is not the cut of the data load ({cut}) (DT-058)")
    return LoadContext(load_id, version, origin, cut)


def select_forecast_run(conn: psycopg.Connection, as_of_date: _dt.date, data_load_id: int, forecast_sha: str) -> int:
    """The ``FORECAST`` ``COMPLETED`` execution with the same cut, load and U3 configuration (`DT-061`)."""
    row = conn.execute(
        """
        SELECT id FROM calculation_runs
        WHERE run_type = 'FORECAST' AND status = 'COMPLETED' AND as_of_date = %s
          AND data_load_id = %s AND config_sha256 = %s
        """,
        (as_of_date, data_load_id, forecast_sha),
    ).fetchone()
    if row is None:
        raise RecommendationRunError(
            f"no COMPLETED forecast execution for {as_of_date} with the current configuration: "
            f"run `python -m app.runs forecast --as-of {as_of_date}` first"
        )
    return row[0]


# --------------------------------------------------------------------------------------------
# Reading (SQL only here) and evaluation
# --------------------------------------------------------------------------------------------


def read_context(conn: psycopg.Connection, as_of_date: _dt.date, forecast_run_id: int) -> EvaluationContext:
    """Read every input of the execution. Timestamps are converted to UTC in the query (`docs/04` §9.7)."""
    candidates = [
        ProductRow(*r)
        for r in conn.execute(
            """
            SELECT p.id, l.id, p.is_active, p.valid_from, p.valid_to
            FROM products p CROSS JOIN locations l
            ORDER BY p.id, l.id
            """
        )
    ]
    relations: dict[int, list[RelationRow]] = defaultdict(list)
    for product_id, *rest in conn.execute(
        """
        SELECT product_id, supplier_id, is_active, is_preferred, moq, order_multiple, agreed_lead_time_days
        FROM product_suppliers ORDER BY product_id, supplier_id
        """
    ):
        relations[product_id].append(RelationRow(*rest))
    inventory = {
        (p, l): InventoryRow(on_hand, reserved, in_transit)
        for p, l, on_hand, reserved, in_transit in conn.execute(
            "SELECT product_id, location_id, quantity_on_hand, quantity_reserved, quantity_in_transit FROM inventory"
        )
    }
    order_lines = [
        OrderLineRow(*r)
        for r in conn.execute(
            """
            SELECT po.id, i.id, i.product_id, po.supplier_id, po.location_id, po.status,
                   i.quantity_ordered, i.quantity_received,
                   po.issued_at AT TIME ZONE 'UTC', po.expected_at AT TIME ZONE 'UTC',
                   i.expected_at AT TIME ZONE 'UTC',
                   (SELECT max(r.received_at) FROM purchase_order_receipts r
                    WHERE r.purchase_order_item_id = i.id) AT TIME ZONE 'UTC'
            FROM purchase_order_items i JOIN purchase_orders po ON po.id = i.purchase_order_id
            ORDER BY po.id, i.id
            """
        )
    ]
    consumption: dict[tuple[int, int], list[ConsumptionRow]] = defaultdict(list)
    for p, l, day, quantity in conn.execute(
        """
        SELECT product_id, location_id, occurred_on, quantity FROM consumption
        WHERE occurred_on <= %s ORDER BY product_id, location_id, occurred_on
        """,
        (as_of_date,),
    ):
        consumption[(p, l)].append(ConsumptionRow(day, quantity))
    forecasts: dict[tuple[int, int], list[ForecastRow]] = defaultdict(list)
    meta: dict[tuple[int, int], dict[str, str]] = {}
    for fid, p, l, start, end, granularity, quantity, method, model_id, primary, flag, name, version in conn.execute(
        """
        SELECT f.id, f.product_id, f.location_id, f.period_start, f.period_end, f.granularity,
               f.predicted_quantity, f.method_used, f.model_version_id, f.is_primary, f.confidence_flag,
               m.name, m.version
        FROM forecasts f JOIN model_versions m ON m.id = f.model_version_id
        WHERE f.calculation_run_id = %s AND f.is_primary
        ORDER BY f.product_id, f.location_id, f.period_start
        """,
        (forecast_run_id,),
    ):
        forecasts[(p, l)].append(ForecastRow(fid, start, end, granularity, quantity, method, model_id, primary))
        meta.setdefault((p, l), {"name": name, "version": version, "confidence_flag": flag})
    return EvaluationContext(
        as_of_date, forecast_run_id, candidates, relations, inventory, order_lines, consumption, forecasts, meta
    )


def evaluate_context(context: EvaluationContext, evaluator: Evaluator = evaluate) -> list[dict[str, Any]]:
    """One row per candidate: adapt, call U1, map its result unchanged. Errors carry the candidate."""
    rows = []
    for product in context.candidates:
        key = (product.product_id, product.location_id)
        try:
            inputs = build_evaluation_input(
                context.as_of_date,
                product,
                context.relations.get(product.product_id, []),
                context.inventory.get(key),
                context.order_lines,
                context.consumption.get(key, []),
                context.forecasts.get(key, []),
                V1_PROVISIONAL_PARAMETERS,
            )
            result = evaluator(inputs)
        except (AdapterError, InvalidInputError) as exc:
            raise CandidateError(product.product_id, product.location_id, exc) from exc
        rows.append(result_row(context, inputs, result))
    return rows


def result_row(context: EvaluationContext, inputs: EvaluationInput, result: EvaluationResult) -> dict[str, Any]:
    """The ``recommendations`` columns of one evaluation (`DT-059`), without ``calculation_run_id``."""
    key = (inputs.product.product_id, inputs.product.location_id)
    breakdown = result.breakdown
    document, approximate = breakdown_document(breakdown)
    meta = context.forecast_meta.get(key)
    model = None if inputs.forecast is None else {"name": meta["name"], "version": meta["version"]}
    forecast_block = None
    if inputs.forecast is not None:
        forecast_block = {
            "forecast_run_id": exact_text(context.forecast_run_id),
            "forecast_id": exact_text(inputs.forecast.forecast_id),
            "model": model,
            "method_used": str(inputs.forecast.method_used.value),
            "confidence_flag": meta["confidence_flag"],
            "start_date": inputs.forecast.start_date.isoformat(),
            "weekly_quantities": [exact_text(q) for q in inputs.forecast.weekly_quantities],
        }
    recommend = result.outcome is Outcome.RECOMMEND
    return {
        "product_id": key[0],
        "location_id": key[1],
        "as_of_date": inputs.as_of_date,
        "outcome": str(result.outcome.value),
        "reasons": [str(r.value) for r in result.reasons],
        "flags": [str(f.value) for f in result.flags],
        "missing_policy_parameters": [str(p.value) for p in result.missing_policy_parameters],
        "forecast_id": result.forecast_id,
        "suggested_supplier_id": breakdown.supplier_id,
        "suggested_order_date": inputs.as_of_date if recommend else None,
        "recommended_quantity": numeric_value(breakdown.q_final) if recommend else None,
        "raw_quantity": numeric_value(breakdown.raw_need),
        "reorder_point": numeric_value(breakdown.target_level),
        "safety_stock": numeric_value(breakdown.safety_stock),
        "lead_time_used_days": breakdown.lead_time_days,
        "demand_during_lead_time": numeric_value(breakdown.demand_over_lead_time),
        "inventory_position_at_calc": numeric_value(breakdown.inventory_position_decision),
        "policy_set": result.policy_set,
        "policy_snapshot": policy_snapshot(inputs.policy),
        "calculation_inputs": {
            "breakdown": document,
            "approximate_terms": approximate,
            "forecast": forecast_block,
            "input_sha256": input_sha256(inputs, model),
        },
        "engine_version": result.engine_version,
    }


def build_summary(
    load: LoadContext,
    forecast_run_id: int,
    forecast_sha: str,
    context: EvaluationContext,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Deterministic summary: versions, counts by outcome, reason and flag; no timestamps."""
    return {
        "dataset_version": load.dataset_version,
        "data_load_id": load.id,
        "as_of_date": context.as_of_date.isoformat(),
        "forecast_run_id": forecast_run_id,
        "forecast_config_sha256": forecast_sha,
        "engine_version": ENGINE_VERSION,
        "policy_set": V1_PROVISIONAL_PARAMETERS.policy_set,
        "input_rules_version": INPUT_RULES_VERSION,
        "candidates": len(context.candidates),
        "evaluated": len(rows),
        "by_outcome": dict(sorted(Counter(r["outcome"] for r in rows).items())),
        "by_reason": dict(sorted(Counter(x for r in rows for x in r["reasons"]).items())),
        "by_flag": dict(sorted(Counter(x for r in rows for x in r["flags"]).items())),
        "forecast_missing": [
            {"product_id": r["product_id"], "location_id": r["location_id"]}
            for r in rows
            if "FORECAST_MISSING" in r["reasons"]
        ],
        "rows": len(rows),
    }


# --------------------------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------------------------


def _insert_run(
    conn: psycopg.Connection,
    load: LoadContext,
    forecast_run_id: int,
    sha: str,
    summary: dict[str, Any],
    started_at: _dt.datetime,
    error: dict[str, Any] | None,
) -> int:
    return conn.execute(
        """
        INSERT INTO calculation_runs (run_type, status, as_of_date, data_load_id, reference_model_version_id,
                                      config_sha256, summary, error, started_at, finished_at,
                                      forecast_run_id, engine_version)
        VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s, clock_timestamp(), %s, %s)
        RETURNING id
        """,
        (
            RUN_TYPE,
            "FAILED" if error is not None else "COMPLETED",
            load.as_of_date,
            load.id,
            sha,
            Jsonb(summary),
            None if error is None else Jsonb(error),
            started_at,
            forecast_run_id,
            ENGINE_VERSION,
        ),
    ).fetchone()[0]


def _insert_recommendations(conn: psycopg.Connection, run_id: int, rows: list[dict[str, Any]]) -> None:
    """``generated_at`` is left to its default, ``transaction_timestamp()``: one instant per run."""
    columns = ", ".join(RECOMMENDATION_COLUMNS)
    placeholders = ", ".join(["%s"] * len(RECOMMENDATION_COLUMNS))
    values = []
    for row in rows:
        record = dict(row, calculation_run_id=run_id)
        record["policy_snapshot"] = Jsonb(record["policy_snapshot"])
        record["calculation_inputs"] = Jsonb(record["calculation_inputs"])
        values.append(tuple(record[c] for c in RECOMMENDATION_COLUMNS))
    statement = f"INSERT INTO recommendations ({columns}) VALUES ({placeholders})"
    with conn.cursor() as cur:
        for value in values:
            cur.execute(statement, value)


def _check_persisted(conn: psycopg.Connection, run_id: int, forecast_run_id: int, candidates: int) -> None:
    """Inside the transaction: one row per candidate, coherent ``forecast_id`` and versions (`DT-061`)."""
    total, versions, bad_forecast = conn.execute(
        """
        SELECT count(*),
               count(*) FILTER (WHERE r.engine_version <> c.engine_version),
               count(*) FILTER (WHERE r.forecast_id IS NOT NULL AND NOT EXISTS (
                   SELECT 1 FROM forecasts f
                   WHERE f.id = r.forecast_id AND f.calculation_run_id = c.forecast_run_id
                     AND f.product_id = r.product_id AND f.location_id = r.location_id
                     AND f.is_primary AND f.period_start = r.as_of_date + 1))
        FROM recommendations r JOIN calculation_runs c ON c.id = r.calculation_run_id
        WHERE r.calculation_run_id = %s
        """,
        (run_id,),
    ).fetchone()
    if total != candidates or versions or bad_forecast:
        raise RuntimeError(
            f"persisted {total} recommendations for {candidates} candidates; "
            f"{versions} engine_version mismatches; {bad_forecast} incoherent forecast_id"
        )
    forecast_ok = conn.execute(
        """
        SELECT f.run_type = 'FORECAST' AND f.status = 'COMPLETED' AND f.as_of_date = c.as_of_date
               AND f.data_load_id = c.data_load_id
        FROM calculation_runs c JOIN calculation_runs f ON f.id = c.forecast_run_id
        WHERE c.id = %s
        """,
        (run_id,),
    ).fetchone()
    if forecast_ok is None or not forecast_ok[0]:
        raise RuntimeError(f"forecast execution {forecast_run_id} is not a COMPLETED forecast of the same cut and load")


def describe_error(exc: Exception) -> dict[str, Any]:
    """``{type, message, field?, code?, product_id?, location_id?, sqlstate?}`` — only what is known."""
    error: dict[str, Any] = {}
    cause = exc
    if isinstance(exc, CandidateError):
        error["product_id"] = exc.product_id
        error["location_id"] = exc.location_id
        cause = exc.cause
    error["type"] = type(cause).__name__
    error["message"] = str(cause)
    if isinstance(cause, (InvalidInputError, AdapterError)):
        error["field"] = cause.field
    if isinstance(cause, AdapterError):
        error["code"] = cause.code
    if isinstance(cause, psycopg.Error) and cause.diag.sqlstate:
        error["sqlstate"] = cause.diag.sqlstate
    return error
