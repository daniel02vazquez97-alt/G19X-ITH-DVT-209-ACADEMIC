"""The three V1 baselines (`DT-056` point 3) and their definitions (`DT-057`).

Each baseline is a function ``predict(history, h)``: the forecast of week ``t + h`` made at an origin
that knows only ``history = (Y_1 … Y_t)``, or ``None`` when that origin has too little history. The
same function gives the final forecast (origin ``n``) and the historical errors of the interval, so
both use exactly the same definition and nothing after the origin.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from fractions import Fraction
from types import MappingProxyType

from .contract import BaselineDefinition

SEASON_LENGTH_WEEKS = 52
WINDOW_WEEKS = 13

NAIVE = BaselineDefinition(name="baseline.naive", version="1.0.0", algorithm="NAIVE")
SEASONAL_NAIVE = BaselineDefinition(
    name="baseline.seasonal_naive",
    version="1.0.0",
    algorithm="SEASONAL_NAIVE",
    specific=(("season_length_weeks", SEASON_LENGTH_WEEKS),),
)
MOVING_AVERAGE = BaselineDefinition(
    name="baseline.moving_average",
    version="1.0.0",
    algorithm="MOVING_AVERAGE",
    specific=(("window_weeks", WINDOW_WEEKS),),
)

#: Every baseline U3 runs, in a fixed order.
BASELINES: tuple[BaselineDefinition, ...] = (NAIVE, SEASONAL_NAIVE, MOVING_AVERAGE)
#: Provisional V1 reference (`DT-056` point 8): an operational, reversible choice, not a ranking.
REFERENCE = MOVING_AVERAGE
#: Primary chain: the reference, then its fallback; seasonal naïve is never primary in V1.
PRIMARY_CHAIN: tuple[BaselineDefinition, ...] = (MOVING_AVERAGE, NAIVE)

Predictor = Callable[[Sequence[Fraction], int], Fraction | None]


def predict_naive(history: Sequence[Fraction], h: int) -> Fraction | None:
    """``F_h = Y_t`` for every ``h``."""
    if len(history) < 1:
        return None
    return history[-1]


def predict_seasonal_naive(history: Sequence[Fraction], h: int) -> Fraction | None:
    """``F_h = Y_{t+h−52}``: the same week one season (52 anchored weeks) earlier."""
    index = len(history) + h - SEASON_LENGTH_WEEKS  # 1-based week index
    if index < 1:
        return None
    return history[index - 1]


def predict_moving_average(history: Sequence[Fraction], h: int) -> Fraction | None:
    """``F_h = (Y_{t−12} + … + Y_t) / 13`` for every ``h``; the window is never shortened."""
    if len(history) < WINDOW_WEEKS:
        return None
    return sum(history[-WINDOW_WEEKS:], Fraction(0)) / WINDOW_WEEKS


PREDICTORS: Mapping[str, Predictor] = MappingProxyType(
    {
        NAIVE.name: predict_naive,
        SEASONAL_NAIVE.name: predict_seasonal_naive,
        MOVING_AVERAGE.name: predict_moving_average,
    }
)
