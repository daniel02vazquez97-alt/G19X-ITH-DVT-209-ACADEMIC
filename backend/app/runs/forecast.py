"""Forecast execution of U3 (`DT-057`): consumption → `ForecastProvider` → persisted forecasts.

1. the single ``COMPLETED`` data load and ``as_of_date`` within its ``time_range``;
2. the three ``model_versions`` registered (or verified) in their own transaction;
3. ``config_sha256`` and an advisory lock on the logical identity of the execution;
4. idempotence: a ``COMPLETED`` run with the same identity → ``ALREADY_COMPUTED``, nothing written;
5. in ONE transaction: eligible series, consumption ``≤ as_of_date``, provider, the run row and its
   forecasts; on any failure, rollback and a ``FAILED`` row in a separate transaction.

The baseline formulas live in `app.forecasting`; this module only orchestrates and persists.
"""

from __future__ import annotations

import datetime as _dt
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from app.forecasting import (
    BASELINES,
    CONFIDENCE_LEVEL,
    METHOD_USED,
    REFERENCE,
    ConfidenceFlag,
    ForecastRequest,
    ForecastResult,
    InvalidForecastInputError,
    build_request,
    forecast,
)

from .config import CATALOG_POLICY, GRANULARITY, RUN_TYPE, config_sha256, lock_key, run_configuration

Provider = Callable[[ForecastRequest], ForecastResult]

INACTIVE_OR_OUT_OF_VALIDITY = "INACTIVE_OR_OUT_OF_VALIDITY"
INVALID_HISTORY = "INVALID_HISTORY"

_FORECAST_COLUMNS = (
    "calculation_run_id",
    "product_id",
    "location_id",
    "model_version_id",
    "as_of_date",
    "period_start",
    "period_end",
    "granularity",
    "predicted_quantity",
    "lower_bound",
    "upper_bound",
    "confidence_level",
    "method_used",
    "confidence_flag",
    "is_primary",
)


class ForecastRunOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    ALREADY_COMPUTED = "ALREADY_COMPUTED"
    FAILED = "FAILED"

    @property
    def ok(self) -> bool:
        return self is not ForecastRunOutcome.FAILED


@dataclass(frozen=True)
class ForecastRunResult:
    outcome: ForecastRunOutcome
    calculation_run_id: int
    as_of_date: _dt.date
    summary: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None


class ForecastRunError(RuntimeError):
    """The execution cannot start (no schema, no completed load, invalid date, version mismatch).

    Nothing is written: there is no run to attribute it to.
    """


def run_forecast(conn: psycopg.Connection, as_of_date: _dt.date, provider: Provider = forecast) -> ForecastRunResult:
    """Forecast every eligible series at ``as_of_date`` and persist the result.

    ``conn`` must be in autocommit mode: this function opens its own transactions.
    """
    if not conn.autocommit:
        raise ValueError("run_forecast needs an autocommit connection")
    if conn.execute("SELECT to_regclass('calculation_runs')").fetchone()[0] is None:
        raise ForecastRunError("schema missing: run `python -m app.db migrate` first")
    load = _completed_load(conn, as_of_date)
    started_at = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    model_ids = register_model_versions(conn)
    sha = config_sha256(run_configuration())
    key = lock_key(as_of_date, load["id"], sha)

    conn.execute("SELECT pg_advisory_lock(%s)", (key,))
    try:
        existing = conn.execute(
            """
            SELECT id, summary FROM calculation_runs
            WHERE run_type = %s AND status = 'COMPLETED' AND as_of_date = %s
              AND data_load_id = %s AND config_sha256 = %s
            """,
            (RUN_TYPE, as_of_date, load["id"], sha),
        ).fetchone()
        if existing is not None:
            return ForecastRunResult(ForecastRunOutcome.ALREADY_COMPUTED, existing[0], as_of_date, existing[1])
        try:
            with conn.transaction():
                summary, rows = _compute(conn, as_of_date, load, model_ids, provider)
                run_id = _insert_run(conn, as_of_date, load["id"], model_ids, sha, summary, started_at, None)
                _insert_forecasts(conn, run_id, rows)
                _check_persisted(conn, run_id, summary)
        except Exception as exc:  # noqa: BLE001 — every failure is recorded, then reported
            error = _describe(exc)
            failed_summary = {"as_of_date": as_of_date.isoformat(), "model_versions": model_ids}
            with conn.transaction():
                run_id = _insert_run(
                    conn, as_of_date, load["id"], model_ids, sha, failed_summary, started_at, error
                )
            return ForecastRunResult(ForecastRunOutcome.FAILED, run_id, as_of_date, failed_summary, error)
        return ForecastRunResult(ForecastRunOutcome.COMPLETED, run_id, as_of_date, summary)
    finally:
        conn.execute("SELECT pg_advisory_unlock(%s)", (key,))


def _completed_load(conn: psycopg.Connection, as_of_date: _dt.date) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT id, dataset_version, lower(time_range), upper(time_range)
        FROM data_loads WHERE status = 'COMPLETED'
        """
    ).fetchone()
    if row is None:
        raise ForecastRunError("no COMPLETED data load: load a dataset first (`python -m app.ingestion`)")
    load_id, version, start, end = row
    if start is None or end is None or not (start <= as_of_date < end):
        raise ForecastRunError(f"as_of_date {as_of_date} is outside the data load time_range [{start}, {end})")
    return {"id": load_id, "dataset_version": version}


def register_model_versions(conn: psycopg.Connection) -> dict[str, int]:
    """Register the three baselines once; an existing row must match the code exactly.

    A different definition under the same ``(name, version)`` is an error: the version must be
    bumped, never overwritten.
    """
    ids: dict[str, int] = {}
    with conn.transaction():
        for definition in BASELINES:
            conn.execute(
                """
                INSERT INTO model_versions (name, version, algorithm, hyperparameters, is_baseline)
                VALUES (%s, %s, %s, %s, true)
                ON CONFLICT (name, version) DO NOTHING
                """,
                (definition.name, definition.version, definition.algorithm, Jsonb(definition.hyperparameters)),
            )
            row = conn.execute(
                """
                SELECT id, algorithm, hyperparameters, is_baseline, status, trained_at, training_data_from,
                       training_data_to, metrics, baseline_metrics, external_ref
                FROM model_versions WHERE name = %s AND version = %s
                """,
                (definition.name, definition.version),
            ).fetchone()
            expected = (definition.algorithm, definition.hyperparameters, True) + (None,) * 7
            if tuple(row[1:]) != expected:
                raise ForecastRunError(
                    f"model_versions {definition.name} {definition.version} differs from its definition: "
                    "bump the version instead of changing it"
                )
            ids[definition.name] = row[0]
    return ids


def _compute(
    conn: psycopg.Connection,
    as_of_date: _dt.date,
    load: dict[str, Any],
    model_ids: dict[str, int],
    provider: Provider,
) -> tuple[dict[str, Any], list[tuple[Any, ...]]]:
    """Run the provider on every eligible series; return the summary and the forecast rows.

    Rows carry ``None`` in place of ``calculation_run_id``, filled in at insertion.
    """
    candidates = conn.execute(
        """
        SELECT p.id, l.id,
               p.is_active AND p.valid_from <= %(a)s AND (p.valid_to IS NULL OR %(a)s <= p.valid_to)
        FROM products p CROSS JOIN locations l
        ORDER BY p.id, l.id
        """,
        {"a": as_of_date},
    ).fetchall()
    eligible = [(product, location) for product, location, ok in candidates if ok]
    excluded = [
        {"product_id": p, "location_id": l, "reason": INACTIVE_OR_OUT_OF_VALIDITY, "detail": None}
        for p, l, ok in candidates
        if not ok
    ]

    history: dict[tuple[int, int], list[tuple[_dt.date, Any, bool]]] = defaultdict(list)
    for product, location, day, quantity, flag in conn.execute(
        """
        SELECT product_id, location_id, occurred_on, quantity, is_stockout_affected
        FROM consumption
        WHERE occurred_on <= %s AND product_id = ANY(%s)
        ORDER BY product_id, location_id, occurred_on
        """,
        (as_of_date, sorted({p for p, _ in eligible})),
    ):
        history[(product, location)].append((day, quantity, flag))

    rows: list[tuple[Any, ...]] = []
    fallback, no_forecast, unavailable = [], [], []
    primary_by_model: Counter[str] = Counter()
    series_by_model: Counter[str] = Counter()
    for product, location in eligible:
        try:
            request = build_request(product, location, as_of_date, history.get((product, location), []))
        except InvalidForecastInputError as exc:
            excluded.append(
                {"product_id": product, "location_id": location, "reason": INVALID_HISTORY, "detail": exc.code}
            )
            continue
        result = provider(request)
        for missing in result.unavailable:
            unavailable.append(
                {
                    "product_id": product,
                    "location_id": location,
                    "baseline": missing.definition.name,
                    "reason": str(missing.reason),
                }
            )
        if result.primary is None:
            no_forecast.append(
                {
                    "product_id": product,
                    "location_id": location,
                    "reason": str(result.no_forecast_reason),
                    "history_weeks": result.history_weeks,
                }
            )
            continue
        primary_by_model[result.primary.name] += 1
        if result.primary != REFERENCE:
            fallback.append(
                {
                    "product_id": product,
                    "location_id": location,
                    "primary": result.primary.name,
                    "history_weeks": result.history_weeks,
                }
            )
        for series in result.series:
            series_by_model[series.definition.name] += 1
            is_primary = series.definition == result.primary
            flag = result.confidence_flag if is_primary else ConfidenceFlag.STANDARD
            for period in series.periods:
                rows.append(
                    (
                        None,
                        product,
                        location,
                        model_ids[series.definition.name],
                        as_of_date,
                        period.period_start,
                        period.period_end,
                        GRANULARITY,
                        period.predicted_quantity,
                        period.lower_bound,
                        period.upper_bound,
                        CONFIDENCE_LEVEL,
                        METHOD_USED,
                        str(flag),
                        is_primary,
                    )
                )

    excluded.sort(key=lambda e: (e["product_id"], e["location_id"]))
    summary = {
        "dataset_version": load["dataset_version"],
        "data_load_id": load["id"],
        "as_of_date": as_of_date.isoformat(),
        "catalog_policy": CATALOG_POLICY,
        "reference": REFERENCE.name,
        "model_versions": model_ids,
        "candidates": len(candidates),
        "eligible": len(eligible),
        "excluded": excluded,
        "excluded_count": len(excluded),
        "excluded_by_reason": dict(sorted(Counter(e["reason"] for e in excluded).items())),
        "forecasted": sum(primary_by_model.values()),
        "primary_by_model": dict(sorted(primary_by_model.items())),
        "series_by_model": dict(sorted(series_by_model.items())),
        "fallback": fallback,
        "fallback_count": len(fallback),
        "no_forecast": no_forecast,
        "no_forecast_count": len(no_forecast),
        "unavailable_series": unavailable,
        "forecast_rows": len(rows),
        "primary_rows": sum(1 for row in rows if row[-1]),
    }
    return summary, rows


def _insert_run(
    conn: psycopg.Connection,
    as_of_date: _dt.date,
    data_load_id: int,
    model_ids: dict[str, int],
    sha: str,
    summary: dict[str, Any],
    started_at: _dt.datetime,
    error: dict[str, Any] | None,
) -> int:
    return conn.execute(
        """
        INSERT INTO calculation_runs (run_type, status, as_of_date, data_load_id, reference_model_version_id,
                                      config_sha256, summary, error, started_at, finished_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, clock_timestamp())
        RETURNING id
        """,
        (
            RUN_TYPE,
            "FAILED" if error is not None else "COMPLETED",
            as_of_date,
            data_load_id,
            model_ids[REFERENCE.name],
            sha,
            Jsonb(summary),
            None if error is None else Jsonb(error),
            started_at,
        ),
    ).fetchone()[0]


def _insert_forecasts(conn: psycopg.Connection, run_id: int, rows: list[tuple[Any, ...]]) -> None:
    """``generated_at`` is left to its default, ``transaction_timestamp()``: one instant per run."""
    statement = sql.SQL("COPY forecasts ({}) FROM STDIN").format(
        sql.SQL(", ").join(map(sql.Identifier, _FORECAST_COLUMNS))
    )
    with conn.cursor() as cur, cur.copy(statement) as copy:
        for row in rows:
            copy.write_row((run_id,) + row[1:])


def _check_persisted(conn: psycopg.Connection, run_id: int, summary: dict[str, Any]) -> None:
    """Inside the transaction: the rows written are exactly the rows computed."""
    total, primary = conn.execute(
        "SELECT count(*), count(*) FILTER (WHERE is_primary) FROM forecasts WHERE calculation_run_id = %s",
        (run_id,),
    ).fetchone()
    if (total, primary) != (summary["forecast_rows"], summary["primary_rows"]):
        raise RuntimeError(f"persisted {total}/{primary} forecasts, computed {summary['forecast_rows']}/{summary['primary_rows']}")


def _describe(exc: Exception) -> dict[str, Any]:
    error: dict[str, Any] = {"type": type(exc).__name__, "message": str(exc)}
    if isinstance(exc, psycopg.Error) and exc.diag.sqlstate:
        error["sqlstate"] = exc.diag.sqlstate
    if isinstance(exc, InvalidForecastInputError):
        error["code"] = exc.code
    return error
