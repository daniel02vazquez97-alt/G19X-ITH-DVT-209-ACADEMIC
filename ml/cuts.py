"""Backtesting calendar of `DT-075` (ACEPTADA) and the holdout guard.

Week ``n`` ends on ``2025-12-31 − 7·(156 − n)`` (anchored as in U3, `DT-046`). The 17 development
cuts are the ends of weeks 64, 68, …, 128; each evaluates the 14 following weeks, the last one up to
week 142 (2025-09-24). Weeks 143–156 are the single-use holdout of gate G2: no F5a path may read them.
"""

from __future__ import annotations

import datetime as _dt

ANCHOR_END = _dt.date(2025, 12, 31)
TOTAL_WEEKS = 156
FIRST_CUT_WEEK = 64
LAST_CUT_WEEK = 128
CUT_STEP_WEEKS = 4
#: Evaluation horizon in weeks (`DT-075` point 2); equal to U3's ``HORIZON_WEEKS``.
HORIZON_WEEKS = 14
#: The holdout cut (`DT-075` point 4); its evaluation weeks start the day after.
HOLDOUT_CUT = _dt.date(2025, 9, 24)
#: Last date any F5a path may read (training or truth).
LAST_READABLE_DATE = HOLDOUT_CUT

_ONE_DAY = _dt.timedelta(days=1)


class HoldoutAccessError(RuntimeError):
    """A request would read data of the holdout (after ``LAST_READABLE_DATE``)."""


def week_end(n: int) -> _dt.date:
    """Last day of anchored week ``n`` (1 … 156)."""
    if not 1 <= n <= TOTAL_WEEKS:
        raise ValueError(f"week {n} is outside 1..{TOTAL_WEEKS}")
    return ANCHOR_END - _ONE_DAY * (7 * (TOTAL_WEEKS - n))


def development_cuts() -> tuple[_dt.date, ...]:
    """The 17 ``as_of`` dates of `DT-075` point 2, in increasing order."""
    return tuple(week_end(n) for n in range(FIRST_CUT_WEEK, LAST_CUT_WEEK + 1, CUT_STEP_WEEKS))


def evaluation_end(as_of: _dt.date) -> _dt.date:
    """Last day evaluated from ``as_of``: the end of week ``as_of + 14``."""
    return as_of + _ONE_DAY * (7 * HORIZON_WEEKS)


def check_readable(last_day: _dt.date) -> None:
    """Raise `HoldoutAccessError` if ``last_day`` is after ``LAST_READABLE_DATE``."""
    if last_day > LAST_READABLE_DATE:
        raise HoldoutAccessError(
            f"{last_day} is after {LAST_READABLE_DATE}: the holdout (DT-075 point 4) is reserved for G2"
        )


def check_cut(as_of: _dt.date) -> None:
    """A development cut is admissible only if its 14 evaluation weeks end before the holdout."""
    if as_of >= HOLDOUT_CUT:
        raise HoldoutAccessError(f"cut {as_of} is the holdout cut or later (DT-075 point 4)")
    check_readable(evaluation_end(as_of))
