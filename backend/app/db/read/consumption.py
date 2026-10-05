"""Daily consumption of one product (`DT-067`): the only source of the history. Never ``demand``."""

from __future__ import annotations

import datetime as _dt
from typing import Any

import psycopg


def bounds(conn: psycopg.Connection, product_id: int) -> tuple[_dt.date | None, _dt.date | None]:
    row = conn.execute(
        "SELECT min(occurred_on) AS first, max(occurred_on) AS last FROM consumption WHERE product_id = %s",
        (product_id,),
    ).fetchone()
    return row["first"], row["last"]


def daily(conn: psycopg.Connection, product_id: int, date_from: _dt.date, date_to: _dt.date) -> list[dict[str, Any]]:
    """One row per day with data, summed over locations; ``stockout`` if any location was affected."""
    return conn.execute(
        """
        SELECT occurred_on AS day, sum(quantity) AS quantity, bool_or(is_stockout_affected) AS stockout
        FROM consumption
        WHERE product_id = %s AND occurred_on BETWEEN %s AND %s
        GROUP BY occurred_on ORDER BY occurred_on
        """,
        (product_id, date_from, date_to),
    ).fetchall()
