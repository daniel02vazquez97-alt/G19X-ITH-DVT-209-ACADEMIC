"""Hand-built inputs for the supply-engine tests.

Not a test module. Every value is written out here as a literal: the tests never read the values
they check from the module under test (convention of `data/synthetic/tests`). No dataset, no
generator code (`docs/03` §16.4, `DT-031`: the engine's cases build their inputs by hand).
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from fractions import Fraction

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

AS_OF = dt.date(2025, 12, 31)
HORIZON_START = dt.date(2026, 1, 1)
VALID_FROM = dt.date(2023, 1, 1)


def day(offset: int) -> dt.date:
    """``AS_OF + offset`` days."""
    return AS_OF + dt.timedelta(days=offset)


def v1_policy(**overrides: object) -> PolicyParameters:
    values: dict[str, object] = dict(
        policy_set="V1_PROVISIONAL", r=7, z=Fraction(33, 20), n=12, n_min=3, lt_max=90
    )
    values.update(overrides)
    return PolicyParameters(**values)  # type: ignore[arg-type]


def product(**overrides: object) -> Product:
    values: dict[str, object] = dict(
        product_id=101, location_id=1, is_active=True, valid_from=VALID_FROM, valid_to=None
    )
    values.update(overrides)
    return Product(**values)  # type: ignore[arg-type]


def relation(**overrides: object) -> SupplierRelation:
    values: dict[str, object] = dict(
        supplier_id=7,
        is_active=True,
        is_preferred=True,
        moq=0,
        order_multiple=1,
        agreed_lead_time_days=14,
    )
    values.update(overrides)
    return SupplierRelation(**values)  # type: ignore[arg-type]


def consumption(quantities: list[object], end: dt.date = AS_OF) -> ConsumptionSeries:
    """Dense series ending on ``end`` (validation f: ``min(as_of_date, valid_to)``)."""
    start = end - dt.timedelta(days=len(quantities) - 1) if quantities else end
    return ConsumptionSeries(start_date=start, quantities=tuple(quantities))


def constant_consumption(value: object = 5, days: int = 60, end: dt.date = AS_OF) -> ConsumptionSeries:
    return consumption([value] * days, end=end)


def forecast(weeks: list[object], start: dt.date = HORIZON_START) -> Forecast:
    return Forecast(
        start_date=start,
        weekly_quantities=tuple(weeks),
        forecast_id=9001,
        model_version=3,
        method_used=MethodUsed.BASELINE,
    )


def line(po: int, expected_on: dt.date, pending: object, item: int = 1, supplier: int = 7) -> OpenLine:
    return OpenLine(
        purchase_order_id=po,
        item_id=item,
        supplier_id=supplier,
        expected_on=expected_on,
        quantity_pending=pending,
    )


def observation(issued: dt.date, completed: dt.date, supplier: int = 7) -> LeadTimeObservation:
    return LeadTimeObservation(supplier_id=supplier, issued_on=issued, completed_on=completed)


def observations_with_lead_times(lead_times: list[int], supplier: int = 7) -> tuple[LeadTimeObservation, ...]:
    """One observation per lead time, completed on distinct past days (latest first)."""
    result = []
    for index, days in enumerate(lead_times):
        completed = day(-10 - index)
        result.append(observation(completed - dt.timedelta(days=days), completed, supplier))
    return tuple(result)


def evaluation(**overrides: object) -> EvaluationInput:
    """A calculable base input: agreed lead time 14 → ``H = 21``; ``DDH = 120``; ``σ_H = 0``."""
    lines = (line(1, day(10), 10), line(2, day(46), 20))
    values: dict[str, object] = dict(
        as_of_date=AS_OF,
        product=product(),
        supplier_relations=(relation(moq=25, order_multiple=10),),
        inventory=Inventory(on_hand=17, reserved=0, total_in_transit=30),
        open_lines=lines,
        lead_time_observations=(),
        consumption=constant_consumption(),
        forecast=forecast([40, 40, 40, 40]),
        policy=v1_policy(),
    )
    values.update(overrides)
    return EvaluationInput(**values)  # type: ignore[arg-type]


def replace(obj: object, **changes: object) -> object:
    return dataclasses.replace(obj, **changes)  # type: ignore[type-var]
