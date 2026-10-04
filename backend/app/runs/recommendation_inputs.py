"""Pure adapter of U4: rows already read from PostgreSQL → `EvaluationInput` of U1 (`docs/06` §16.13.2).

No SQL and no I/O: every function receives plain rows and returns the values of the U1 contract, so the
reading rules (``INPUT_RULES_VERSION``) are tested without a database. The adapter never decides
anything that belongs to U1: it does not choose the supplier, does not classify open lines against the
horizon, does not filter lead-time observations by date and does not exclude products. It only maps,
orders canonically and rejects rows that cannot be mapped without inventing data (`AdapterError`).
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.forecasting import HORIZON_WEEKS, METHOD_USED
from app.supply_engine import (
    V1_PROVISIONAL_PARAMETERS,
    ConsumptionSeries,
    EvaluationInput,
    Forecast,
    Inventory,
    LeadTimeObservation,
    MethodUsed,
    OpenLine,
    PolicyParameters,
    Product,
    SupplierRelation,
)

#: Purchase-order header statuses whose lines are open (`docs/06` §16.3, `DT-012`).
OPEN_STATUSES = frozenset({"ISSUED", "PARTIALLY_RECEIVED"})
GRANULARITY = "WEEKLY"
_ONE_DAY = _dt.timedelta(days=1)
_ONE_WEEK = _dt.timedelta(days=7)


class AdapterError(ValueError):
    """A row cannot be mapped to the U1 contract without inventing data: the execution fails."""

    def __init__(self, code: str, field: str, message: str) -> None:
        self.code = code
        self.field = field
        self.message = message
        super().__init__(f"{code} ({field}): {message}")


# --------------------------------------------------------------------------------------------
# Rows as read by the orchestrator (one dataclass per query shape)
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProductRow:
    product_id: int
    location_id: int
    is_active: bool
    valid_from: _dt.date
    valid_to: _dt.date | None


@dataclass(frozen=True)
class RelationRow:
    supplier_id: int
    is_active: bool
    is_preferred: bool
    moq: Decimal
    order_multiple: Decimal
    agreed_lead_time_days: int


@dataclass(frozen=True)
class InventoryRow:
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_in_transit: Decimal


@dataclass(frozen=True)
class OrderLineRow:
    """One purchase-order line with its header and its last receipt (``None`` without receipts).

    Timestamps come from the query already converted to UTC (``AT TIME ZONE 'UTC'``, naive) or as
    aware datetimes; `utc_date` accepts both.
    """

    purchase_order_id: int
    item_id: int
    product_id: int
    supplier_id: int
    location_id: int
    status: str
    quantity_ordered: Decimal
    quantity_received: Decimal
    issued_at: _dt.datetime
    header_expected_at: _dt.datetime
    item_expected_at: _dt.datetime | None
    last_received_at: _dt.datetime | None


@dataclass(frozen=True)
class ConsumptionRow:
    occurred_on: _dt.date
    quantity: Decimal


@dataclass(frozen=True)
class ForecastRow:
    id: int
    period_start: _dt.date
    period_end: _dt.date
    granularity: str
    predicted_quantity: Decimal
    method_used: str
    model_version_id: int
    is_primary: bool


# --------------------------------------------------------------------------------------------
# Mapping rules
# --------------------------------------------------------------------------------------------


def utc_date(value: _dt.datetime | _dt.date) -> _dt.date:
    """Calendar date in UTC (`docs/04` §9.7): aware datetimes are converted, naive ones are UTC."""
    if isinstance(value, _dt.datetime):
        if value.tzinfo is not None:
            value = value.astimezone(_dt.timezone.utc)
        return value.date()
    return value


def map_product(row: ProductRow) -> Product:
    """Product block as stored: inactive or out-of-validity products are NOT filtered (U1 decides)."""
    return Product(
        product_id=row.product_id,
        location_id=row.location_id,
        is_active=row.is_active,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
    )


def map_supplier_relations(rows: Iterable[RelationRow]) -> tuple[SupplierRelation, ...]:
    """Every relation of the product, ordered by ``supplier_id``; U1 selects the supplier (`V1-10`)."""
    return tuple(
        SupplierRelation(
            supplier_id=r.supplier_id,
            is_active=r.is_active,
            is_preferred=r.is_preferred,
            moq=r.moq,
            order_multiple=r.order_multiple,
            agreed_lead_time_days=r.agreed_lead_time_days,
        )
        for r in sorted(rows, key=lambda r: r.supplier_id)
    )


def map_inventory(row: InventoryRow | None) -> Inventory:
    """The ``inventory`` row of the pair; without it the execution fails, never zeros (`DT-059`)."""
    if row is None:
        raise AdapterError("MISSING_INVENTORY", "inventory", "no inventory row for the product-location")
    return Inventory(
        on_hand=row.quantity_on_hand,
        reserved=row.quantity_reserved,
        total_in_transit=row.quantity_in_transit,
    )


def map_open_lines(rows: Iterable[OrderLineRow], product_id: int, location_id: int) -> tuple[OpenLine, ...]:
    """Open lines at the cut: header ``ISSUED``/``PARTIALLY_RECEIVED``, same location, pending ``> 0``.

    ``expected_on`` is the UTC date of the line's expected date or, if null, the header's. Whether a
    line counts for the horizon is decided by U1 (`V1-02`).
    """
    lines = []
    for r in rows:
        if r.product_id != product_id or r.location_id != location_id or r.status not in OPEN_STATUSES:
            continue
        pending = r.quantity_ordered - r.quantity_received
        if pending <= 0:
            continue
        expected = r.item_expected_at if r.item_expected_at is not None else r.header_expected_at
        lines.append(
            OpenLine(
                purchase_order_id=r.purchase_order_id,
                item_id=r.item_id,
                supplier_id=r.supplier_id,
                expected_on=utc_date(expected),
                quantity_pending=pending,
            )
        )
    lines.sort(key=lambda line: (line.purchase_order_id, line.item_id))
    return tuple(lines)


def map_lead_time_observations(
    rows: Iterable[OrderLineRow], supplier_ids: Iterable[int]
) -> tuple[LeadTimeObservation, ...]:
    """Fully received lines (``received = ordered``, at least one receipt) of the related suppliers.

    The header status is not read and nothing is filtered by date: U1 applies ``completed_on ≤
    as_of_date`` and the window of `V1-09`.
    """
    suppliers = set(supplier_ids)
    observations = [
        LeadTimeObservation(
            supplier_id=r.supplier_id,
            issued_on=utc_date(r.issued_at),
            completed_on=utc_date(r.last_received_at),
        )
        for r in rows
        if r.supplier_id in suppliers
        and r.last_received_at is not None
        and r.quantity_received == r.quantity_ordered
    ]
    observations.sort(key=lambda o: (o.supplier_id, o.issued_on, o.completed_on))
    return tuple(observations)


def map_consumption(rows: Sequence[ConsumptionRow], as_of_date: _dt.date, valid_from: _dt.date) -> ConsumptionSeries:
    """Dense daily series of ``consumption`` up to ``as_of_date``; a gap or a duplicate fails.

    Never ``demand``; nothing is imputed, filled or rescaled. Without rows the series is empty and
    anchored on ``valid_from`` (U1 then reports ``INSUFFICIENT_HISTORY`` if it needs it).
    """
    ordered = sorted((r for r in rows if r.occurred_on <= as_of_date), key=lambda r: r.occurred_on)
    if not ordered:
        return ConsumptionSeries(start_date=valid_from, quantities=())
    start = ordered[0].occurred_on
    for index, row in enumerate(ordered):
        expected = start + _ONE_DAY * index
        if row.occurred_on != expected:
            code = "CONSUMPTION_DUPLICATE" if row.occurred_on < expected else "CONSUMPTION_GAP"
            raise AdapterError(code, "consumption", "the daily consumption series is not dense")
    return ConsumptionSeries(start_date=start, quantities=tuple(r.quantity for r in ordered))


def map_forecast(rows: Iterable[ForecastRow], as_of_date: _dt.date) -> Forecast | None:
    """The primary series of the selected forecast execution → `Forecast` (`DT-060`).

    Non-primary rows are ignored. Without primary rows: ``None`` (U1 reports ``FORECAST_MISSING``).
    Otherwise exactly ``HORIZON_WEEKS`` weekly rows ``period_start = as_of + 1 + 7(k−1)``, the same
    ``model_version_id``, ``WEEKLY`` and ``BASELINE``; anything else fails, never repaired.
    ``forecast_id`` is the id of row h=1, the anchor of the logical series.
    """
    primary = sorted((r for r in rows if r.is_primary), key=lambda r: (r.period_start, r.id))
    if not primary:
        return None
    start = as_of_date + _ONE_DAY
    if len(primary) != HORIZON_WEEKS:
        raise AdapterError("INVALID_FORECAST_SERIES", "forecast", f"the primary series must have {HORIZON_WEEKS} periods")
    model = primary[0].model_version_id
    for k, row in enumerate(primary):
        period_start = start + _ONE_WEEK * k
        if row.period_start != period_start or row.period_end != period_start + _ONE_WEEK:
            raise AdapterError("INVALID_FORECAST_SERIES", f"forecast[{k}]", "periods are not the contiguous weeks from as_of_date + 1")
        if row.model_version_id != model:
            raise AdapterError("INVALID_FORECAST_SERIES", f"forecast[{k}]", "the primary series mixes model versions")
        if row.granularity != GRANULARITY or row.method_used != METHOD_USED:
            raise AdapterError("INVALID_FORECAST_SERIES", f"forecast[{k}]", "the primary series is not WEEKLY BASELINE")
    return Forecast(
        start_date=start,
        weekly_quantities=tuple(r.predicted_quantity for r in primary),
        forecast_id=primary[0].id,
        model_version=model,
        method_used=MethodUsed(METHOD_USED),
    )


def build_evaluation_input(
    as_of_date: _dt.date,
    product: ProductRow,
    relations: Iterable[RelationRow],
    inventory: InventoryRow | None,
    order_lines: Sequence[OrderLineRow],
    consumption: Sequence[ConsumptionRow],
    forecast_rows: Iterable[ForecastRow],
    policy: PolicyParameters = V1_PROVISIONAL_PARAMETERS,
) -> EvaluationInput:
    """One `EvaluationInput`, blocks in the contractual order (`DT-051`); the policy is U1's own."""
    relation_rows = list(relations)
    supplier_relations = map_supplier_relations(relation_rows)
    return EvaluationInput(
        as_of_date=as_of_date,
        product=map_product(product),
        supplier_relations=supplier_relations,
        inventory=map_inventory(inventory),
        open_lines=map_open_lines(order_lines, product.product_id, product.location_id),
        lead_time_observations=map_lead_time_observations(order_lines, (r.supplier_id for r in supplier_relations)),
        consumption=map_consumption(consumption, as_of_date, product.valid_from),
        forecast=map_forecast(forecast_rows, as_of_date),
        policy=policy,
    )
