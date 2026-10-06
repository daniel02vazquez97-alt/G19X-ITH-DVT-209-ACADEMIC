"""U1 ``EvaluationInput`` of one branch at a decision date, with the mapping of the pure U4 adapter.

Same rules as ``app.runs.recommendation_inputs.build_evaluation_input`` (`docs/06` §16.13.2), applied to the
simulated state instead of database rows; a parity test compares both. ``ml/`` never imports ``app.runs``
(`docs/03` §16.2, `docs/13` §14).

Differences that come from the simulation, not from the mapping:

* ``product.is_active`` is ``True``: the published flag is a snapshot of the dataset end and the population
  is decided by validity on the date (`DT-087`); U1 still applies its own validity rules (`DT-049`, `DT-P22`).
* ``reserved = 0`` (`DT-080` point 5) and ``total_in_transit`` is the pending quantity of the open lines.
* Only exact values cross into U1 (``Decimal``); no ``float`` (`DT-074`).
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.supply_engine import (
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

from ..data import ProductRecord

_ONE_DAY = _dt.timedelta(days=1)


@dataclass(frozen=True, slots=True)
class LineState:
    """An open line at a decision date: exogenous (real) or simulated order."""

    purchase_order_id: int
    item_id: int
    supplier_id: int
    expected_on: _dt.date
    quantity_pending: Decimal


def _exact(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field}: {type(value).__name__} cannot cross into U1 (DT-074)")
    return value


def evaluation_input(
    as_of: _dt.date,
    product: ProductRecord,
    location_id: int,
    relations: Sequence[SupplierRelation],
    on_hand: Decimal,
    lines: Sequence[LineState],
    observations: Sequence[LeadTimeObservation],
    consumption_start: _dt.date,
    consumption: Sequence[Decimal],
    forecast_points: Sequence[Decimal] | None,
    forecast_id: int,
    model_version: int,
    method_used: MethodUsed,
    policy: PolicyParameters,
) -> EvaluationInput:
    """The canonical blocks of `DT-051`, in order. ``consumption`` starts on ``consumption_start``."""
    end = as_of if product.valid_to is None else min(as_of, product.valid_to)
    days = (end - consumption_start).days + 1
    quantities = tuple(_exact(q, "consumption") for q in consumption[: max(days, 0)])
    open_lines = tuple(
        sorted(
            (
                OpenLine(
                    purchase_order_id=line.purchase_order_id,
                    item_id=line.item_id,
                    supplier_id=line.supplier_id,
                    expected_on=line.expected_on,
                    quantity_pending=_exact(line.quantity_pending, "quantity_pending"),
                )
                for line in lines
                if line.quantity_pending > 0
            ),
            key=lambda line: (line.purchase_order_id, line.item_id),
        )
    )
    in_transit = sum((line.quantity_pending for line in open_lines), Decimal(0))
    forecast = None
    if forecast_points is not None:
        forecast = Forecast(
            start_date=as_of + _ONE_DAY,
            weekly_quantities=tuple(_exact(q, "forecast") for q in forecast_points),
            forecast_id=forecast_id,
            model_version=model_version,
            method_used=method_used,
        )
    return EvaluationInput(
        as_of_date=as_of,
        product=Product(
            product_id=product.product_id,
            location_id=location_id,
            is_active=True,
            valid_from=product.valid_from,
            valid_to=product.valid_to,
        ),
        supplier_relations=tuple(sorted(relations, key=lambda r: r.supplier_id)),
        inventory=Inventory(on_hand=_exact(on_hand, "on_hand"), reserved=Decimal(0), total_in_transit=in_transit),
        open_lines=open_lines,
        lead_time_observations=tuple(
            sorted(
                (o for o in observations if o.supplier_id in {r.supplier_id for r in relations}),
                key=lambda o: (o.supplier_id, o.issued_on, o.completed_on),
            )
        ),
        consumption=ConsumptionSeries(start_date=consumption_start, quantities=quantities),
        forecast=forecast,
        policy=policy,
    )
