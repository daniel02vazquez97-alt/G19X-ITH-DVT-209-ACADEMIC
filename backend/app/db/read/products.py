"""Products, their inventory snapshot and supplier relations."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg import sql

from . import like_pattern

SORT_COLUMNS = {"sku": "p.sku", "name": "p.name", "id": "p.id"}

_SELECT = """
    SELECT p.id, p.sku, p.name, p.unit_of_measure, p.is_active, p.valid_from, p.valid_to, p.data_origin,
           c.id AS category_id, c.code AS category_code, c.name AS category_name
    FROM products p JOIN categories c ON c.id = p.category_id
"""


def list_products(
    conn: psycopg.Connection,
    *,
    search: str | None,
    category_id: int | None,
    is_active: bool | None,
    sort: str,
    descending: bool,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    where, params = ["TRUE"], []
    if search is not None:
        where.append("(p.sku ILIKE %s ESCAPE '\\' OR p.name ILIKE %s ESCAPE '\\')")
        params += [like_pattern(search)] * 2
    if category_id is not None:
        where.append("p.category_id = %s")
        params.append(category_id)
    if is_active is not None:
        where.append("p.is_active = %s")
        params.append(is_active)
    condition = sql.SQL(" AND ".join(where))
    total = conn.execute(
        sql.SQL("SELECT count(*) AS n FROM products p WHERE {}").format(condition), params
    ).fetchone()["n"]
    order = sql.SQL(f"{SORT_COLUMNS[sort]} {'DESC' if descending else 'ASC'}, p.id {'DESC' if descending else 'ASC'}")
    rows = conn.execute(
        sql.SQL(_SELECT + " WHERE {} ORDER BY {} LIMIT %s OFFSET %s").format(condition, order),
        params + [limit, offset],
    ).fetchall()
    return total, rows


def get_product(conn: psycopg.Connection, product_id: int) -> dict[str, Any] | None:
    return conn.execute(_SELECT + " WHERE p.id = %s", (product_id,)).fetchone()


def product_exists(conn: psycopg.Connection, product_id: int) -> bool:
    return conn.execute("SELECT 1 FROM products WHERE id = %s", (product_id,)).fetchone() is not None


def product_inventory(conn: psycopg.Connection, product_id: int) -> dict[str, Any] | None:
    return conn.execute(
        """
        SELECT quantity_on_hand AS on_hand, quantity_reserved AS reserved, quantity_in_transit AS in_transit_total,
               last_movement_at
        FROM inventory WHERE product_id = %s ORDER BY location_id LIMIT 1
        """,
        (product_id,),
    ).fetchone()


def product_suppliers(conn: psycopg.Connection, product_id: int) -> list[dict[str, Any]]:
    return conn.execute(
        """
        SELECT s.id AS supplier_id, s.code AS supplier_code, s.name AS supplier_name, ps.moq, ps.order_multiple,
               ps.unit_cost, ps.agreed_lead_time_days, ps.is_preferred, ps.is_active
        FROM product_suppliers ps JOIN suppliers s ON s.id = ps.supplier_id
        WHERE ps.product_id = %s ORDER BY s.id
        """,
        (product_id,),
    ).fetchall()
