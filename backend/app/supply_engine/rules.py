"""One function per V1 rule (`docs/06` §16.4, `DT-031`).

Pure functions over already validated values, converted to ``Fraction``. None of them reads a
segment attribute (`V1-11`), the clock or anything outside its arguments, and none of them adapts
the horizon: ``H = L + R`` is computed once and only read afterwards (`V1-03`, `DT-P22`).
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Sequence
from fractions import Fraction

from .contract import LeadTimeObservation, LeadTimeSource, OpenLine, Product, SupplierRelation
from .exact import Surd, ceil_fraction

_ONE_DAY = _dt.timedelta(days=1)

#: The only conversion rule between weekly forecast and days (`V1-04`, `DT-019`, `docs/06` §5.1).
DEMAND_CONVERSION_RULE = "V1-04"


# --- V1-10 -----------------------------------------------------------------------------------


def select_supplier(relations: Sequence[SupplierRelation]) -> SupplierRelation | None:
    """The active and preferred relation, or ``None`` (`V1-10`); validation guarantees at most one."""
    for relation in relations:
        if relation.is_active and relation.is_preferred:
            return relation
    return None


# --- V1-09, V1-09.1, V1-09.2, DT-050, A-1 -----------------------------------------------------


def observed_lead_time(
    observations: Sequence[LeadTimeObservation],
    supplier_id: int,
    as_of: _dt.date,
    window: int,
    minimum: int,
    agreed_lead_time_days: int,
) -> tuple[int, LeadTimeSource, int]:
    """``(L_source, source, n)`` of `V1-09` before the cap.

    Observations of the chosen supplier completed on or before ``as_of``, ordered by
    ``completed_on`` descending and, on ties, ``issued_on`` ascending (`DT-050`); the window is the
    first ``window`` of them (`V1-09.1`). With ``n ≥ minimum`` the result is ``ceil(median)`` and
    ``OBSERVED``; otherwise the agreed lead time and ``AGREED_FALLBACK``.
    """
    eligible = [o for o in observations if o.supplier_id == supplier_id and o.completed_on <= as_of]
    eligible.sort(key=lambda o: (-o.completed_on.toordinal(), o.issued_on.toordinal()))
    chosen = eligible[:window]
    count = len(chosen)
    if count >= minimum:
        days = sorted((o.completed_on - o.issued_on).days for o in chosen)
        middle = count // 2
        if count % 2:
            median = Fraction(days[middle])
        else:
            median = Fraction(days[middle - 1] + days[middle], 2)
        return ceil_fraction(median), LeadTimeSource.OBSERVED, count
    return agreed_lead_time_days, LeadTimeSource.AGREED_FALLBACK, count


def cap_lead_time(uncapped: int, maximum: int) -> tuple[int, bool]:
    """``(min(L_source, LT_MAX), capped)`` for any source (`V1-09.2`, aclaración A-1)."""
    if uncapped > maximum:
        return maximum, True
    return uncapped, False


# --- V1-03 -----------------------------------------------------------------------------------


def coverage_horizon(lead_time_days: int, review_period_days: int) -> int:
    """``H = L + R`` (`V1-03`). Never adapted afterwards, not even to ``valid_to`` (`DT-P22`)."""
    return lead_time_days + review_period_days


# --- V1-04, DT-048 ---------------------------------------------------------------------------


def weeks_required(days: int) -> int:
    """``K(days) = ⌈days / 7⌉``: forecast weeks needed to cover ``days`` (`DT-048`)."""
    weeks, rest = divmod(days, 7)
    return weeks + (1 if rest else 0)


def demand_over_horizon(weekly: Sequence[Fraction], days: int) -> Fraction:
    """``Σ F_1..F_q + (r/7)·F_{q+1}`` with ``q, r = divmod(days, 7)`` (`V1-04`).

    The only place of the system that converts between granularities (`docs/06` §5.1). Requires
    ``len(weekly) ≥ K(days)``; with ``r = 0`` week ``q + 1`` is not needed.
    """
    weeks, rest = divmod(days, 7)
    if len(weekly) < weeks_required(days):
        raise ValueError("the forecast does not cover the requested days")
    total = sum(weekly[:weeks], Fraction(0))
    if rest:
        total += Fraction(rest, 7) * weekly[weeks]
    return total


# --- V1-02 -----------------------------------------------------------------------------------


def effective_in_transit(
    lines: Sequence[OpenLine], as_of: _dt.date, horizon_days: int
) -> tuple[Fraction, tuple[OpenLine, ...]]:
    """Pending quantity of the lines with ``as_of < expected_on ≤ as_of + H`` (`V1-02`, `DT-P15`).

    Returns the total and the contributing lines ordered by ``(purchase_order_id, item_id)``.
    """
    end = as_of + _ONE_DAY * horizon_days
    included = tuple(
        sorted(
            (line for line in lines if as_of < line.expected_on <= end),
            key=lambda line: (line.purchase_order_id, line.item_id),
        )
    )
    total = sum((Fraction(line.quantity_pending) for line in included), Fraction(0))
    return total, included


def has_overdue_lines(lines: Sequence[OpenLine], as_of: _dt.date) -> bool:
    """Some open line has ``expected_on ≤ as_of``: it is excluded from the effective transit."""
    return any(line.expected_on <= as_of for line in lines)


# --- DT-049, DT-P22 --------------------------------------------------------------------------


def is_valid_on(product: Product, as_of: _dt.date) -> bool:
    """``valid_from ≤ as_of ∧ (valid_to is None ∨ as_of ≤ valid_to)``: case A is its negation."""
    if as_of < product.valid_from:
        return False
    return product.valid_to is None or as_of <= product.valid_to


def validity_ends_within_horizon(product: Product, as_of: _dt.date, horizon_days: int) -> bool:
    """Case B of ``PRODUCT_OUT_OF_VALIDITY``: ``valid_to ≠ None ∧ as_of ≤ valid_to < as_of + H``.

    It only reads ``H``; the horizon is never shortened to fit ``valid_to`` (`DT-P22`).
    """
    if product.valid_to is None:
        return False
    return as_of <= product.valid_to < as_of + _ONE_DAY * horizon_days


# --- V1-05 -----------------------------------------------------------------------------------


def sigma_components(
    quantities: Sequence[Fraction], horizon_days: int
) -> tuple[int, Fraction | None, Fraction | None, Fraction | None]:
    """``(n, S1, S2, A)`` over all windows of ``H`` consecutive days (`docs/06` §16.6 point 2).

    ``W_i`` is the consumption of window ``i``; ``S1 = Σ W_i``, ``S2 = Σ W_i²``, ``A = n·S2 − S1²``
    (population estimator). With ``n = 0`` the three components are ``None``.
    """
    count = max(0, len(quantities) - horizon_days + 1)
    if count == 0:
        return 0, None, None, None
    window = sum(quantities[:horizon_days], Fraction(0))
    s1 = window
    s2 = window * window
    for index in range(horizon_days, len(quantities)):
        window += quantities[index] - quantities[index - horizon_days]
        s1 += window
        s2 += window * window
    return count, s1, s2, count * s2 - s1 * s1


def safety_stock_components(a: Fraction, count: int, z: Fraction) -> tuple[Fraction, int]:
    """``(B, D)`` with ``SS = z·σ_H = √B / D``: ``B = z_num²·A``, ``D = z_den·n`` (§16.6 point 3).

    With ``z = 33/20`` this is ``B = 1089·A`` and ``D = 20·n``.
    """
    return z.numerator**2 * a, z.denominator * count


# --- V1-01, V1-06 ----------------------------------------------------------------------------


def has_need(x: Surd) -> bool:
    """``raw_need = max(0, x) > 0`` with ``x = DDH + SS − IP_decisión`` (`V1-01`), exactly."""
    return not x.le(Fraction(0))


def apply_supplier_constraints(
    x: Surd, moq: Fraction, multiple: Fraction
) -> tuple[Fraction | None, Fraction, bool, bool]:
    """`V1-06` for ``x > 0``: ``(Q_moq exact or None if irrational, Q_final, MOQ_APPLIED, ROUNDING)``.

    ``x ≤ MOQ`` → base ``MOQ`` and ``Q_final = ceil(MOQ/M)·M``; otherwise base ``x`` and
    ``Q_final = ceil(x/M)·M`` (§16.6 point 6). ``MOQ_APPLIED ⇔ MOQ > raw_need``;
    ``ORDER_MULTIPLE_ROUNDING ⇔ Q_final ≠ base``. No tolerance anywhere.
    """
    if x.le(moq):
        q_final = ceil_fraction(moq / multiple) * multiple
        return moq, q_final, not x.equals(moq), q_final != moq
    q_final = x.ceil_div(multiple) * multiple
    return x.exact(), q_final, False, not x.equals(q_final)
