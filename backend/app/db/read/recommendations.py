"""Persisted evaluations of U4 (`DT-059`): the three outcomes, never recalculated."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg import sql

SORT_COLUMNS = {"sku": "p.sku", "recommended_quantity": "r.recommended_quantity", "suggested_order_date": "r.suggested_order_date"}

_ITEM = """
    SELECT r.id, r.product_id, p.sku AS product_sku, p.name AS product_name,
           s.id AS supplier_id, s.code AS supplier_code, s.name AS supplier_name,
           r.recommended_quantity, r.raw_quantity, r.suggested_order_date, r.outcome, r.flags
    FROM recommendations r
    JOIN products p ON p.id = r.product_id
    LEFT JOIN suppliers s ON s.id = r.suggested_supplier_id
"""

_DETAIL = """
    SELECT r.id, r.calculation_run_id, r.product_id, p.sku AS product_sku, p.name AS product_name,
           s.id AS supplier_id, s.code AS supplier_code, s.name AS supplier_name, r.as_of_date, r.outcome,
           r.reasons, r.flags, r.missing_policy_parameters, r.forecast_id, r.suggested_order_date,
           r.recommended_quantity, r.raw_quantity, r.reorder_point, r.safety_stock, r.lead_time_used_days,
           r.demand_during_lead_time, r.inventory_position_at_calc, r.policy_set, r.policy_snapshot,
           r.calculation_inputs, r.engine_version, r.generated_at
    FROM recommendations r
    JOIN products p ON p.id = r.product_id
    LEFT JOIN suppliers s ON s.id = r.suggested_supplier_id
"""


def list_recommendations(
    conn: psycopg.Connection,
    run_id: int,
    *,
    outcome: str,
    product_id: int | None,
    category_id: int | None,
    supplier_id: int | None,
    sort: str,
    descending: bool,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    where, params = ["r.calculation_run_id = %s", "r.outcome = %s"], [run_id, outcome]
    for column, value in (("r.product_id", product_id), ("p.category_id", category_id), ("r.suggested_supplier_id", supplier_id)):
        if value is not None:
            where.append(f"{column} = %s")
            params.append(value)
    condition = sql.SQL(" AND ".join(where))
    total = conn.execute(
        sql.SQL("SELECT count(*) AS n FROM recommendations r JOIN products p ON p.id = r.product_id WHERE {}").format(condition),
        params,
    ).fetchone()["n"]
    direction = "DESC" if descending else "ASC"
    order = sql.SQL(f"{SORT_COLUMNS[sort]} {direction} NULLS LAST, r.id {direction}")
    rows = conn.execute(
        sql.SQL(_ITEM + " WHERE {} ORDER BY {} LIMIT %s OFFSET %s").format(condition, order), params + [limit, offset]
    ).fetchall()
    return total, rows


def get_recommendation(conn: psycopg.Connection, recommendation_id: int) -> dict[str, Any] | None:
    return conn.execute(_DETAIL + " WHERE r.id = %s", (recommendation_id,)).fetchone()


def product_recommendation(conn: psycopg.Connection, run_id: int, product_id: int) -> dict[str, Any] | None:
    return conn.execute(
        _DETAIL + " WHERE r.calculation_run_id = %s AND r.product_id = %s ORDER BY r.location_id LIMIT 1",
        (run_id, product_id),
    ).fetchone()


def explanation_source(conn: psycopg.Connection, recommendation_id: int) -> dict[str, Any] | None:
    """What the explanation of U6 reads (`DT-068`): the persisted evaluation and the product's
    ``unit_of_measure`` as metadata. Never ``demand``, never a recalculation."""
    return conn.execute(
        """
        SELECT r.id, r.calculation_run_id, r.outcome, r.reasons, r.flags, r.missing_policy_parameters,
               r.calculation_inputs, p.unit_of_measure
        FROM recommendations r
        JOIN products p ON p.id = r.product_id
        WHERE r.id = %s
        """,
        (recommendation_id,),
    ).fetchone()
