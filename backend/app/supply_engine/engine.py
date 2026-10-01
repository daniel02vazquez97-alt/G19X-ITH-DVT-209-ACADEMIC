"""Composition of the V1 rules: the engine's single entry point (`docs/06` §16.1, §16.4).

Flow: validate everything (`DT-052`) → reasons that do not need ``H`` → descriptive magnitudes, unless
the product is excluded → reasons that need ``H`` → the decision, only when ``reasons == ()``.

* Every evaluable reason is accumulated; output order is canonical, never discovery order (`DT-051`).
* ``PRODUCT_INACTIVE`` and case A of ``PRODUCT_OUT_OF_VALIDITY`` exclude the product from the
  operational calculation: no magnitude is produced, so the reasons that need ``H`` are not
  evaluable (`DT-053`).
* Case B never adapts the horizon: ``H = L + R`` is kept and the descriptive magnitudes are computed
  over the whole horizon (`DT-P22`, `DT-053`).
* ``raw_need``, ``Q_moq`` and ``Q_final`` exist only with ``reasons == ()``; ``MOQ_APPLIED`` and
  ``ORDER_MULTIPLE_ROUNDING`` only with ``RECOMMEND`` (`DT-053`).
"""

from __future__ import annotations

import datetime as _dt
from fractions import Fraction
from typing import Any

from . import rules
from .contract import (
    ENGINE_VERSION,
    Breakdown,
    EvaluationInput,
    EvaluationResult,
    Flag,
    LeadTimeSource,
    Outcome,
    PolicyParameter,
    Reason,
)
from .exact import Surd
from .validation import to_fraction, validate

_ONE_DAY = _dt.timedelta(days=1)

_POLICY_FIELDS = {
    PolicyParameter.R: "r",
    PolicyParameter.Z: "z",
    PolicyParameter.N: "n",
    PolicyParameter.N_MIN: "n_min",
    PolicyParameter.LT_MAX: "lt_max",
}


def _component(value: Fraction) -> int | Fraction:
    """B3 components are integers with integer consumption (§16.6); kept exact otherwise."""
    return value.numerator if value.denominator == 1 else value


def evaluate(inputs: EvaluationInput) -> EvaluationResult:
    """Evaluate one product-location at ``inputs.as_of_date``.

    Raises `InvalidInputError` for the first contract violation. Never reads the clock, never
    mutates ``inputs``.
    """
    validate(inputs)

    as_of = inputs.as_of_date
    product = inputs.product
    policy = inputs.policy
    reasons: set[Reason] = set()
    flags: set[Flag] = set()
    terms: dict[str, Any] = {}

    # --- Reasons evaluated always: they do not need H ------------------------------------------
    excluded = False
    if not product.is_active:
        reasons.add(Reason.PRODUCT_INACTIVE)
        excluded = True
    if not rules.is_valid_on(product, as_of):  # case A (DT-P22)
        reasons.add(Reason.PRODUCT_OUT_OF_VALIDITY)
        excluded = True
    on_hand = to_fraction(inputs.inventory.on_hand)
    if on_hand < 0:
        reasons.add(Reason.NEGATIVE_ON_HAND)
    if inputs.forecast is None:
        reasons.add(Reason.FORECAST_MISSING)
    missing = tuple(p for p in PolicyParameter if getattr(policy, _POLICY_FIELDS[p]) is None)
    if missing:
        reasons.add(Reason.MISSING_POLICY_PARAMETER)
    supplier = rules.select_supplier(inputs.supplier_relations)
    if supplier is None:
        reasons.add(Reason.NO_ACTIVE_PREFERRED_SUPPLIER)

    # --- Descriptive magnitudes, unless the product is excluded (DT-053) ----------------------
    x: Surd | None = None
    if not excluded:
        x = _describe(inputs, supplier, on_hand, reasons, flags, terms)

    # --- Decision: only with no reason --------------------------------------------------------
    if reasons:
        outcome = Outcome.NOT_CALCULABLE
    else:
        assert x is not None and supplier is not None  # every precondition holds without reasons
        outcome = _decide(x, terms, flags)

    breakdown = Breakdown(as_of_date=as_of, horizon_start=as_of + _ONE_DAY, **terms)
    return EvaluationResult(
        outcome=outcome,
        reasons=tuple(r for r in Reason if r in reasons),
        missing_policy_parameters=missing,
        flags=tuple(f for f in Flag if f in flags),
        breakdown=breakdown,
        forecast_id=None if inputs.forecast is None else inputs.forecast.forecast_id,
        policy_set=policy.policy_set,
        engine_version=ENGINE_VERSION,
    )


def _describe(
    inputs: EvaluationInput,
    supplier: Any,
    on_hand: Fraction,
    reasons: set[Reason],
    flags: set[Flag],
    terms: dict[str, Any],
) -> Surd | None:
    """Compute every descriptive magnitude whose preconditions hold; return ``x`` if computable."""
    as_of = inputs.as_of_date
    policy = inputs.policy
    reserved = to_fraction(inputs.inventory.reserved)
    total_in_transit = to_fraction(inputs.inventory.total_in_transit)
    terms.update(on_hand=on_hand, reserved=reserved, total_in_transit=total_in_transit)
    if policy.r is not None:
        terms["review_period_days"] = policy.r
    z = None if policy.z is None else to_fraction(policy.z)
    if z is not None:
        terms["z"] = z

    # IP_contable needs a valid on_hand (V1-13, DT-053).
    if on_hand >= 0:
        terms["inventory_position_accounting"] = on_hand + total_in_transit - reserved
    if rules.has_overdue_lines(inputs.open_lines, as_of):
        flags.add(Flag.OVERDUE_ORDERS_EXCLUDED)

    weekly = None
    if inputs.forecast is not None:
        weekly = [to_fraction(q) for q in inputs.forecast.weekly_quantities]

    # --- L (V1-09, DT-050, A-1) and H (V1-03) --------------------------------------------------
    lead_time = None
    horizon = None
    if supplier is not None:
        terms.update(
            supplier_id=supplier.supplier_id,
            moq=to_fraction(supplier.moq),
            order_multiple=to_fraction(supplier.order_multiple),
        )
        if policy.n is not None and policy.n_min is not None:
            uncapped, source, count = rules.observed_lead_time(
                inputs.lead_time_observations,
                supplier.supplier_id,
                as_of,
                policy.n,
                policy.n_min,
                supplier.agreed_lead_time_days,
            )
            terms.update(
                uncapped_lead_time_days=uncapped,
                lead_time_source=source,
                lead_time_observation_count=count,
            )
            if source is LeadTimeSource.AGREED_FALLBACK:
                flags.add(Flag.LEAD_TIME_AGREED_FALLBACK)
            if policy.lt_max is not None:
                lead_time, capped = rules.cap_lead_time(uncapped, policy.lt_max)
                terms["lead_time_days"] = lead_time
                if capped:
                    flags.add(Flag.LEAD_TIME_CAPPED)
                if policy.r is not None:
                    horizon = rules.coverage_horizon(lead_time, policy.r)
                    terms["coverage_horizon_days"] = horizon

    if (
        lead_time is not None
        and weekly is not None
        and len(weekly) >= rules.weeks_required(lead_time)
    ):
        terms["demand_over_lead_time"] = rules.demand_over_horizon(weekly, lead_time)
        terms["demand_conversion_rule"] = rules.DEMAND_CONVERSION_RULE

    if horizon is None:
        return None

    # --- Reasons and magnitudes that need H ----------------------------------------------------
    if rules.validity_ends_within_horizon(inputs.product, as_of, horizon):  # case B (DT-P22)
        reasons.add(Reason.PRODUCT_OUT_OF_VALIDITY)

    effective, lines = rules.effective_in_transit(inputs.open_lines, as_of, horizon)
    terms.update(effective_in_transit=effective, effective_lines=lines)
    if total_in_transit > effective:
        flags.add(Flag.UNCOUNTED_TRANSIT)
    position = None
    if on_hand >= 0:
        position = on_hand + effective - reserved
        terms["inventory_position_decision"] = position

    ddh = None
    if weekly is not None:
        if len(weekly) < rules.weeks_required(horizon):
            reasons.add(Reason.FORECAST_TOO_SHORT)
        else:
            ddh = rules.demand_over_horizon(weekly, horizon)
            terms["demand_over_horizon"] = ddh
            terms["demand_conversion_rule"] = rules.DEMAND_CONVERSION_RULE
            if ddh == 0:
                flags.add(Flag.ZERO_FORECAST_DEMAND)

    consumption = [to_fraction(q) for q in inputs.consumption.quantities]
    count, s1, s2, a = rules.sigma_components(consumption, horizon)
    terms["sigma_window_count"] = count
    if count == 0:
        reasons.add(Reason.INSUFFICIENT_HISTORY)
        return None
    terms.update(s1=_component(s1), s2=_component(s2), a=_component(a))
    terms["sigma_h"] = Surd(Fraction(0), a, count).report()

    if z is None:
        return None
    b, d = rules.safety_stock_components(a, count, z)
    terms.update(b=_component(b), d=d)
    terms["safety_stock"] = Surd(Fraction(0), b, d).report()
    if ddh is None:
        return None
    terms["target_level"] = Surd(ddh, b, d).report()
    if position is None:
        return None
    p = ddh - position
    terms["p"] = p
    return Surd(p, b, d)


def _decide(x: Surd, terms: dict[str, Any], flags: set[Flag]) -> Outcome:
    """`V1-01` and `V1-06` on the exact ``x = P + √B/D`` (§16.6 point 6)."""
    if not rules.has_need(x):
        terms["raw_need"] = Fraction(0)
        return Outcome.NO_NEED
    raw_need = x.report()
    terms["raw_need"] = raw_need
    moq = terms["moq"]
    q_moq, q_final, moq_applied, rounding = rules.apply_supplier_constraints(
        x, moq, terms["order_multiple"]
    )
    terms["q_moq"] = raw_need if q_moq is None else q_moq
    terms["q_final"] = q_final
    if moq_applied:
        flags.add(Flag.MOQ_APPLIED)
    if rounding:
        flags.add(Flag.ORDER_MULTIPLE_ROUNDING)
    return Outcome.RECOMMEND
