"""Primary forecast series of a run (`DT-066`, `DT-060`): only ``is_primary``; never recalculated."""

from __future__ import annotations

from typing import Any

import psycopg

_PERIODS = """
    SELECT f.product_id, p.sku, m.name AS model_name, m.version AS model_version, f.period_start, f.period_end,
           f.predicted_quantity, f.lower_bound, f.upper_bound, f.confidence_level, f.method_used, f.confidence_flag
    FROM forecasts f
    JOIN products p ON p.id = f.product_id
    JOIN model_versions m ON m.id = f.model_version_id
    WHERE f.calculation_run_id = %s AND f.is_primary AND f.product_id = ANY(%s)
    ORDER BY f.product_id, f.location_id, f.period_start
"""


def series_page(
    conn: psycopg.Connection,
    run_id: int,
    *,
    product_id: int | None,
    category_id: int | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Paginated by series (product); returns the total of series and the periods of the page."""
    where, params = ["f.calculation_run_id = %s", "f.is_primary"], [run_id]
    if product_id is not None:
        where.append("f.product_id = %s")
        params.append(product_id)
    if category_id is not None:
        where.append("p.category_id = %s")
        params.append(category_id)
    base = (
        "SELECT DISTINCT f.product_id FROM forecasts f JOIN products p ON p.id = f.product_id WHERE "
        + " AND ".join(where)
    )
    total = conn.execute(f"SELECT count(*) AS n FROM ({base}) s", params).fetchone()["n"]
    ids = [r["product_id"] for r in conn.execute(f"{base} ORDER BY f.product_id LIMIT %s OFFSET %s", params + [limit, offset])]
    if not ids:
        return total, []
    return total, conn.execute(_PERIODS, (run_id, ids)).fetchall()


def product_series(conn: psycopg.Connection, run_id: int, product_id: int) -> list[dict[str, Any]]:
    return conn.execute(_PERIODS, (run_id, [product_id])).fetchall()
