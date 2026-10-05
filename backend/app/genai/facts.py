"""``facts[]`` and their ``display`` (`DT-068` point 5, `DT-069` points 1–3; `docs/09` §14.5).

Only values persisted in ``calculation_inputs.breakdown`` are read: nothing is recalculated.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext
from fractions import Fraction
from typing import Any

from .errors import ExplanationError
from .types import DAYS, NOT_CALCULABLE, QUANTITY, RECOMMEND, Fact

#: Closed vocabulary, in its canonical order, with the unit of each fact.
VOCABULARY: tuple[tuple[str, str], ...] = (
    ("q_final", QUANTITY),
    ("raw_need", QUANTITY),
    ("safety_stock", QUANTITY),
    ("target_level", QUANTITY),
    ("lead_time_days", DAYS),
    ("uncapped_lead_time_days", DAYS),
    ("review_period_days", DAYS),
    ("coverage_horizon_days", DAYS),
    ("demand_over_horizon", QUANTITY),
    ("inventory_position_decision", QUANTITY),
    ("inventory_position_accounting", QUANTITY),
    ("total_in_transit", QUANTITY),
    ("effective_in_transit", QUANTITY),
    ("moq", QUANTITY),
    ("order_multiple", QUANTITY),
    ("q_moq", QUANTITY),
    ("on_hand", QUANTITY),
    ("reserved", QUANTITY),
)
UNIT_OF = dict(VOCABULARY)

#: Facts of RECOMMEND and NO_NEED whenever their value is not null.
ALWAYS = frozenset({"safety_stock", "target_level", "demand_over_horizon", "inventory_position_decision",
                    "effective_in_transit", "on_hand", "reserved", "lead_time_days", "review_period_days",
                    "coverage_horizon_days"})
#: Facts only of RECOMMEND.
RECOMMEND_ONLY = frozenset({"q_final", "raw_need"})
#: Facts that exist only with a flag, and the outcomes where that flag's sentence exists.
CONDITIONAL: tuple[tuple[str, frozenset[str], tuple[str, ...]], ...] = (
    ("LEAD_TIME_CAPPED", frozenset({"uncapped_lead_time_days"}), ("RECOMMEND", "NO_NEED")),
    ("UNCOUNTED_TRANSIT", frozenset({"total_in_transit", "inventory_position_accounting"}), ("RECOMMEND", "NO_NEED")),
    ("MOQ_APPLIED", frozenset({"moq"}), ("RECOMMEND",)),
    ("ORDER_MULTIPLE_ROUNDING", frozenset({"order_multiple", "q_moq"}), ("RECOMMEND",)),
)

_INTEGER = re.compile(r"-?\d+")
_RATIONAL = re.compile(r"-?\d+/\d+")
_QUANTUM = Decimal("0.000001")


def _plain(value: Decimal) -> str:
    """Fixed-point text without trailing zeros; ``0`` never carries a sign."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "0") else text


def display(value: str) -> str:
    """`DT-069`: integers as they are; anything else to 6 decimals ``ROUND_HALF_EVEN`` from the exact
    value (``p/q`` and exact decimals) or from the persisted ``Decimal`` (approximate terms), without
    trailing zeros, ``.`` as separator, no thousands separator and never a ``float``."""
    if not isinstance(value, str):
        raise ExplanationError(f"a persisted figure must be text, not {type(value).__name__}")
    text = value.strip()
    if _INTEGER.fullmatch(text):
        return _plain(Decimal(int(text)))
    if _RATIONAL.fullmatch(text):
        exact = Fraction(text)
        scaled = round(exact * 1_000_000)  # round() of a Fraction is round-half-even, exact
        return _plain(Decimal(scaled).scaleb(-6))
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ExplanationError("a persisted figure is not a number") from exc
    if not number.is_finite():
        raise ExplanationError("a persisted figure is not finite")
    with localcontext() as context:
        context.prec = 200
        return _plain(number.quantize(_QUANTUM, rounding=ROUND_HALF_EVEN))


def fact_keys(outcome: str, flags: tuple[str, ...]) -> frozenset[str]:
    """The keys the template of ``outcome`` may use with these ``flags`` (`docs/09` §14.5, table)."""
    if outcome == NOT_CALCULABLE:
        return frozenset()
    keys = set(ALWAYS)
    if outcome == RECOMMEND:
        keys |= RECOMMEND_ONLY
    for flag, flag_keys, outcomes in CONDITIONAL:
        if flag in flags and outcome in outcomes:
            keys |= flag_keys
    return frozenset(keys)


def build_facts(outcome: str, flags: tuple[str, ...], breakdown: Mapping[str, Any]) -> tuple[Fact, ...]:
    """The facts of the outcome, in the vocabulary order; a null persisted value gives no fact."""
    keys = fact_keys(outcome, flags)
    facts = []
    for key, unit in VOCABULARY:
        if key not in keys:
            continue
        value = breakdown.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            raise ExplanationError(f"breakdown.{key} must be persisted text")
        facts.append(Fact(key=key, value=value, display=display(value), unit=unit))
    return tuple(facts)
