"""Empirical interval of `DT-056` points 4 to 6: nearest-rank 10/90 quantiles of the historical
error of the same method at each horizon.

``confidence_level = 0.80`` is the nominal level: it is neither a guarantee nor a measured coverage;
calibration belongs to Phase 5. ``11`` errors per horizon is the operational minimum of this rule
(one observation left outside the interval in each tail), not a universal estimate.
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from .baselines import Predictor
from .contract import MIN_ERRORS_PER_HORIZON


def horizon_errors(weeks: Sequence[Fraction], predictor: Predictor, h: int) -> list[Fraction]:
    """``E_h``: ``Y_{t+h} − ŷ_{t,h}`` for every valid origin ``t`` with ``t + h ≤ n``.

    Each forecast uses only ``Y_1 … Y_t``; ``Y_{t+h}`` is still ``≤ as_of_date``.
    """
    errors = []
    for origin in range(1, len(weeks) - h + 1):
        forecast = predictor(weeks[:origin], h)
        if forecast is not None:
            errors.append(weeks[origin + h - 1] - forecast)
    return errors


def nearest_rank_bounds(errors: Sequence[Fraction]) -> tuple[Fraction, Fraction]:
    """``(q_lo, q_hi) = (e_(⌈m/10⌉), e_(⌈9m/10⌉))``, no interpolation. Requires ``m ≥ 11``."""
    m = len(errors)
    if m < MIN_ERRORS_PER_HORIZON:
        raise ValueError(f"{m} errors; the rule needs at least {MIN_ERRORS_PER_HORIZON}")
    ordered = sorted(errors)
    low_rank = (m + 9) // 10  # ⌈m/10⌉
    high_rank = (9 * m + 9) // 10  # ⌈9m/10⌉
    return ordered[low_rank - 1], ordered[high_rank - 1]


def interval(forecast: Fraction, q_lo: Fraction, q_hi: Fraction) -> tuple[Fraction, Fraction]:
    """``L = max(0, F + min(q_lo, 0))``, ``U = F + max(q_hi, 0)``: always ``0 ≤ L ≤ F ≤ U``."""
    lower = max(Fraction(0), forecast + min(q_lo, Fraction(0)))
    upper = forecast + max(q_hi, Fraction(0))
    return lower, upper
