"""Inventory snapshot and open purchase-order lines (`docs/07` §7.2, `docs/06` §16.13.2).

``available`` and ``inventory_position_accounting`` are stored-state derivations (`DT-012`,
`docs/06` §4.1); the effective transit is relative to a decision and is not exposed here.
"""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg import sql

SORT_COLUMNS = {"sku": "p.sku", "on_hand": "i.quantity_on_hand", "available": "available"}

_SELECT = """
    SELECT i.product_id, p.sku, i.quantity_on_hand AS on_hand, i.quantity_reserved AS reserved,
           i.quantity_on_hand - i.quantity_reserved AS available, i.quantity_in_transit AS in_transit_total,
           i.quantity_on_hand + i.quantity_in_transit - i.quantity_reserved AS inventory_position_accounting,
           i.last_movement_at, i.data_origin, i.location_id
    FROM inventory i JOIN products p ON p.id = i.product_id
"""


def list_inventory(
    conn: psycopg.Connection,
    *,
    product_id: int | None,
    category_id: int | None,
    sort: str,
    descending: bool,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    where, params = ["TRUE"], []
    if product_id is not None:
        where.append("i.product_id = %s")
        params.append(product_id)
    if category_id is not None:
        where.append("p.category_id = %s")
        params.append(category_id)
    condition = sql.SQL(" AND ".join(where))
    total = conn.execute(
        sql.SQL("SELECT count(*) AS n FROM inventory i JOIN products p ON p.id = i.product_id WHERE {}").format(condition),
        params,
    ).fetchone()["n"]
    direction = "DESC" if descending else "ASC"
    order = sql.SQL(f"{SORT_COLUMNS[sort]} {direction}, i.product_id {direction}, i.location_id {direction}")
    rows = conn.execute(
        sql.SQL(_SELECT + " WHERE {} ORDER BY {} LIMIT %s OFFSET %s").format(condition, order),
        params + [limit, offset],
    ).fetchall()
    return total, rows


def get_inventory(conn: psycopg.Connection, product_id: int) -> dict[str, Any] | None:
    return conn.execute(_SELECT + " WHERE i.product_id = %s ORDER BY i.location_id LIMIT 1", (product_id,)).fetchone()


def open_lines(conn: psycopg.Connection, product_id: int, location_id: int) -> list[dict[str, Any]]:
    """Same rule as U4 (`docs/06` §16.13.2): header ISSUED/PARTIALLY_RECEIVED, same location, pending > 0,
    ``expected_on`` = UTC date of the line's expected date or else the header's."""
    return conn.execute(
        """
        SELECT po.order_number, s.id AS supplier_id, s.code AS supplier_code, s.name AS supplier_name, po.status,
               (coalesce(i.expected_at, po.expected_at) AT TIME ZONE 'UTC')::date AS expected_on,
               i.quantity_ordered - i.quantity_received AS quantity_pending
        FROM purchase_order_items i
        JOIN purchase_orders po ON po.id = i.purchase_order_id
        JOIN suppliers s ON s.id = po.supplier_id
        WHERE i.product_id = %s AND po.location_id = %s
          AND po.status IN ('ISSUED', 'PARTIALLY_RECEIVED')
          AND i.quantity_ordered - i.quantity_received > 0
        ORDER BY po.id, i.id
        """,
        (product_id, location_id),
    ).fetchall()
