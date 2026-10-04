"""Small hand-made rows for the U4 adapter tests (no PostgreSQL)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from app.runs.recommendation_inputs import (
    ConsumptionRow,
    ForecastRow,
    InventoryRow,
    OrderLineRow,
    ProductRow,
    RelationRow,
)

A = dt.date(2025, 12, 31)
UTC = dt.timezone.utc
DAY = dt.timedelta(days=1)
WEEK = dt.timedelta(days=7)


def at(day: dt.date, hour: int = 0) -> dt.datetime:
    """Naive UTC wall time, as returned by ``AT TIME ZONE 'UTC'``."""
    return dt.datetime(day.year, day.month, day.day, hour)


def product(product_id: int = 1, active: bool = True, valid_to: dt.date | None = None) -> ProductRow:
    return ProductRow(product_id, 1, active, dt.date(2023, 1, 1), valid_to)


def relation(supplier_id: int = 7, active: bool = True, preferred: bool = True, lead: int = 20) -> RelationRow:
    return RelationRow(supplier_id, active, preferred, Decimal("0"), Decimal("1"), lead)


def inventory(on_hand: str = "10", in_transit: str = "0") -> InventoryRow:
    return InventoryRow(Decimal(on_hand), Decimal("0"), Decimal(in_transit))


def line(
    po: int,
    item: int,
    *,
    product_id: int = 1,
    supplier_id: int = 7,
    location_id: int = 1,
    status: str = "RECEIVED",
    ordered: str = "10",
    received: str = "10",
    issued: dt.date = dt.date(2025, 1, 1),
    expected: dt.date = dt.date(2025, 1, 21),
    item_expected: dt.date | None = None,
    last_received: dt.datetime | None | str = "auto",
) -> OrderLineRow:
    if last_received == "auto":
        last_received = at(expected) if Decimal(received) > 0 else None
    return OrderLineRow(
        po,
        item,
        product_id,
        supplier_id,
        location_id,
        status,
        Decimal(ordered),
        Decimal(received),
        at(issued),
        at(expected),
        None if item_expected is None else at(item_expected),
        last_received,
    )


def observations(supplier_id: int = 7, count: int = 5, lead: int = 20) -> list[OrderLineRow]:
    issued = dt.date(2025, 1, 1)
    return [
        line(100 + i, 100 + i, supplier_id=supplier_id, issued=issued + WEEK * i, expected=issued + WEEK * i + DAY * lead)
        for i in range(count)
    ]


def consumption(days: int = 400, quantity: str = "2", end: dt.date = A) -> list[ConsumptionRow]:
    start = end - DAY * (days - 1)
    return [ConsumptionRow(start + DAY * i, Decimal(quantity)) for i in range(days)]


def forecast(
    weekly: str = "14", *, start_id: int = 501, model: int = 3, primary: bool = True, weeks: int = 14, as_of: dt.date = A
) -> list[ForecastRow]:
    first = as_of + DAY
    return [
        ForecastRow(start_id + k, first + WEEK * k, first + WEEK * (k + 1), "WEEKLY", Decimal(weekly), "BASELINE", model, primary)
        for k in range(weeks)
    ]
