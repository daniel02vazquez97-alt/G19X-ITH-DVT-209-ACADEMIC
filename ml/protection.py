"""Protection horizon ``L + R`` and the demand forecast over it (`DT-076` point 3).

``L`` is the lead time U1 would use at the cut: the same rule functions ``evaluate()`` composes
(`V1-10` supplier, `V1-09` observed lead time with its window and fallback, `V1-09.2` cap, `V1-03`
horizon), with U1's own provisional policy. The weekly → daily conversion is
``supply_engine.rules.demand_over_horizon`` (`V1-04`, `DT-019`), the only one of the system; the
engine keeps that value exact (``Fraction``) and so does F5a. Only ``Fraction`` / ``Decimal`` /
``int`` values are passed to U1.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from app.supply_engine import LeadTimeObservation, LeadTimeSource, PolicyParameters, SupplierRelation
from app.supply_engine import rules


@dataclass(frozen=True, slots=True)
class ProtectionHorizon:
    supplier_id: int
    lead_time_days: int
    lead_time_source: LeadTimeSource
    observation_count: int
    capped: bool
    review_period_days: int
    coverage_days: int


def protection_horizon(
    relations: Sequence[SupplierRelation],
    observations: Sequence[LeadTimeObservation],
    as_of: _dt.date,
    policy: PolicyParameters,
) -> ProtectionHorizon | None:
    """``L + R`` at ``as_of``, or ``None`` if U1 would not reach ``H`` (no supplier or no policy)."""
    supplier = rules.select_supplier(tuple(relations))
    if supplier is None or None in (policy.n, policy.n_min, policy.lt_max, policy.r):
        return None
    uncapped, source, count = rules.observed_lead_time(
        tuple(observations), supplier.supplier_id, as_of, policy.n, policy.n_min, supplier.agreed_lead_time_days
    )
    lead_time, capped = rules.cap_lead_time(uncapped, policy.lt_max)
    return ProtectionHorizon(
        supplier_id=supplier.supplier_id,
        lead_time_days=lead_time,
        lead_time_source=source,
        observation_count=count,
        capped=capped,
        review_period_days=policy.r,
        coverage_days=rules.coverage_horizon(lead_time, policy.r),
    )


def demand_over(weekly: Sequence[Decimal], days: int) -> Fraction:
    """Forecast demand over ``days`` with the engine's conversion; inputs must be contract ``Decimal``."""
    exact = []
    for value in weekly:
        if not isinstance(value, Decimal):
            raise TypeError(f"{type(value).__name__} cannot cross into U1 (DT-074)")
        exact.append(Fraction(value))
    return rules.demand_over_horizon(exact, days)
