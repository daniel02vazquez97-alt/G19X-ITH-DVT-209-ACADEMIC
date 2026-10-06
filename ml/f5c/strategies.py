"""Training data under the strategies of `DT-081` (`DT-093` point 8, ACEPTADA, provisional).

* (a) consumption as is (the current rule, `DT-056` D-10);
* (b) the stockout days are excluded: each anchored week becomes ``Σ observed × 7 / days_observed`` and a week
  without any observed day is omitted;
* (c) each stockout day is imputed with the mean consumption of the non-stockout days of the previous 8 weeks
  (56 days, original values only); without such days the consumption is kept as is.

Only the training side changes; the truth is never an imputed value (`DT-076` point 2). Everything uses the rows
up to the decision date only and stays exact (``Fraction``).
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from .config import STRATEGY_AS_IS, STRATEGY_EXCLUDE, STRATEGY_IMPUTE


def imputed_daily(quantities: Sequence[Fraction], flags: Sequence[bool], window_days: int = 56) -> list[Fraction]:
    """Strategy (c) on a contiguous daily series (index order = day order)."""
    out = []
    for i, (q, stockout) in enumerate(zip(quantities, flags)):
        if not stockout:
            out.append(q)
            continue
        donors = [quantities[j] for j in range(max(0, i - window_days), i) if not flags[j]]
        out.append(sum(donors, Fraction(0)) / len(donors) if donors else q)
    return out


def anchored_weeks(values: Sequence, weeks: int) -> list[Sequence]:
    """The last ``7 · weeks`` days split into weeks (oldest leftover days dropped, as U3 ``weekly_totals``)."""
    start = len(values) - 7 * weeks
    if start < 0:
        raise ValueError("not enough days for the requested weeks")
    return [values[start + 7 * j : start + 7 * (j + 1)] for j in range(weeks)]


def strategy_weeks(
    strategy: str,
    quantities: Sequence[Fraction],
    flags: Sequence[bool],
    weeks: int | None = None,
    window_days: int = 56,
) -> list[Fraction]:
    """Weekly training series under ``strategy``; ``weeks`` defaults to every complete week anchored on the last day."""
    if len(quantities) != len(flags):
        raise ValueError("quantities and flags must have the same length")
    n = len(quantities) // 7 if weeks is None else weeks
    if strategy == STRATEGY_AS_IS:
        return [sum(w, Fraction(0)) for w in anchored_weeks(list(quantities), n)]
    if strategy == STRATEGY_IMPUTE:
        daily = imputed_daily(quantities, flags, window_days)
        return [sum(w, Fraction(0)) for w in anchored_weeks(daily, n)]
    if strategy == STRATEGY_EXCLUDE:
        out = []
        for qs, fs in zip(anchored_weeks(list(quantities), n), anchored_weeks(list(flags), n)):
            observed = [q for q, f in zip(qs, fs) if not f]
            if observed:
                out.append(sum(observed, Fraction(0)) * 7 / len(observed))
        return out
    raise ValueError(f"unknown strategy {strategy}")


def stockout_share(flags: Sequence[bool]) -> float:
    return sum(1 for f in flags if f) / len(flags) if flags else 0.0
