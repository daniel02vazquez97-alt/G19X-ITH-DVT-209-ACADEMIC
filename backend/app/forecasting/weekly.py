"""Weekly aggregation of the daily history, anchored on ``as_of_date`` (`DT-056` point 1).

``n = ⌊(A − S + 1) / 7⌋`` complete weeks; week ``j`` (chronological, ``1 … n``) covers
``[A − 7(n − j) − 6, A − 7(n − j)]``, so ``Y_n`` is ``[A − 6, A]``. The ``(A − S + 1) mod 7`` oldest
days are discarded. No ISO or calendar weeks.
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction


def weekly_totals(daily: Sequence[Fraction]) -> list[Fraction]:
    """``Y_1 … Y_n`` from a contiguous daily series whose last day is ``as_of_date``."""
    weeks = len(daily) // 7
    leftover = len(daily) - 7 * weeks
    return [sum(daily[leftover + 7 * j : leftover + 7 * (j + 1)], Fraction(0)) for j in range(weeks)]
