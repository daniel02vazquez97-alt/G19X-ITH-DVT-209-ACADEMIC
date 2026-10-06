"""Models evaluated by F5a: the three U3 baselines, invoked as they are, and a provisional SES.

* Baselines: ``app.forecasting.build_request`` + ``app.forecasting.forecast``; nothing is
  reimplemented and their exact ``Decimal`` output is used as is (`DT-056`).
* Simple exponential smoothing (`DT-076` point 7, PROPUESTA): ``float`` inside this module only.
  Its output crosses the `DT-074` boundary (``Decimal(x)`` exact → 6 decimals ``ROUND_HALF_EVEN``,
  no correction) before any comparison or any call into U1.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal

from app.forecasting import (
    BASELINES,
    HORIZON_WEEKS,
    MIN_ERRORS_PER_HORIZON,
    QUANTIZATION_SCALE,
    ForecastRequest,
    ForecastResult,
    forecast,
)

from .config import SES_INIT_FIRST_OBSERVATION, F5aConfig

SES_NAME = "ml.ses"
SES_VERSION = "0.1.0-provisional"
#: Reporting order: the three U3 baselines (U3 order) and SES.
MODEL_NAMES: tuple[str, ...] = tuple(d.name for d in BASELINES) + (SES_NAME,)

_QUANTUM = Decimal(1).scaleb(-QUANTIZATION_SCALE)
_CONTEXT = Context(prec=60)


class BoundaryError(ValueError):
    """A model value cannot cross the `DT-074` boundary (non-finite or contract violation)."""


@dataclass(frozen=True, slots=True)
class ModelForecast:
    """14 weekly periods of one model at one cut, already in contract form (``Decimal``)."""

    model: str
    points: tuple[Decimal, ...]
    lowers: tuple[Decimal, ...]
    uppers: tuple[Decimal, ...]
    alpha: float | None = None


@dataclass(frozen=True, slots=True)
class SesFit:
    alpha: float
    sse: float
    #: ``levels[t]`` is the level after observing ``Y_1 … Y_{t+1}`` (0-based).
    levels: tuple[float, ...]


# --- Baselines -----------------------------------------------------------------------------------


def baseline_forecasts(request: ForecastRequest) -> tuple[ForecastResult, dict[str, ModelForecast]]:
    """Call U3 and expose each computable baseline series; unavailable ones are simply absent."""
    result = forecast(request)
    out = {}
    for series in result.series:
        out[series.definition.name] = ModelForecast(
            model=series.definition.name,
            points=tuple(p.predicted_quantity for p in series.periods),
            lowers=tuple(p.lower_bound for p in series.periods),
            uppers=tuple(p.upper_bound for p in series.periods),
        )
    return result, out


# --- DT-074 boundary -------------------------------------------------------------------------------


def to_contract(value: float) -> Decimal:
    """``float`` → ``Decimal(x)`` (exact binary value) → 6 decimals ``ROUND_HALF_EVEN``."""
    if not isinstance(value, float) or not math.isfinite(value):
        raise BoundaryError(f"{value!r} is not a finite float")
    return Decimal(value).quantize(_QUANTUM, rounding=ROUND_HALF_EVEN, context=_CONTEXT)


def _checked_period(point: float, lower: float, upper: float) -> tuple[Decimal, Decimal, Decimal]:
    p, lo, hi = to_contract(point), to_contract(lower), to_contract(upper)
    if not (Decimal(0) <= lo <= p <= hi):
        raise BoundaryError(f"contract violated: 0 ≤ {lo} ≤ {p} ≤ {hi}")
    return p, lo, hi


# --- Simple exponential smoothing (PROPUESTA) -----------------------------------------------------


def _levels(weeks: Sequence[float], alpha: float) -> tuple[list[float], float]:
    """Levels after each week and the one-step SSE; ``level_1 = Y_1`` (provisional initialisation)."""
    level = weeks[0]
    levels = [level]
    sse = 0.0
    for y in weeks[1:]:
        error = y - level
        sse += error * error
        level = level + alpha * error
        levels.append(level)
    return levels, sse


def fit_ses(weeks: Sequence[float], config: F5aConfig) -> SesFit:
    """``alpha`` of the grid with the minimum one-step SSE inside the training window.

    Ties keep the first (smallest) ``alpha``: the grid is scanned in increasing order with ``<``.
    """
    if config.ses_initial_level != SES_INIT_FIRST_OBSERVATION:
        raise ValueError(f"unknown SES initialisation {config.ses_initial_level}")
    if not weeks:
        raise ValueError("SES needs at least one week")
    best: SesFit | None = None
    for alpha in config.ses_alpha_grid:
        levels, sse = _levels(weeks, alpha)
        if best is None or sse < best.sse:
            best = SesFit(alpha=alpha, sse=sse, levels=tuple(levels))
    assert best is not None
    return best


def _nearest_rank(errors: Sequence[float]) -> tuple[float, float]:
    """Same rule as U3 (`DT-056` point 4): ``e_(⌈m/10⌉)`` and ``e_(⌈9m/10⌉)``, no interpolation."""
    m = len(errors)
    ordered = sorted(errors)
    return ordered[(m + 9) // 10 - 1], ordered[(9 * m + 9) // 10 - 1]


def ses_forecast(weeks: Sequence[float], config: F5aConfig) -> ModelForecast | None:
    """Flat SES forecast over the 14 weeks with the nearest-rank interval, or ``None``.

    ``None`` when the history is shorter than ``ses_min_history_weeks`` or some horizon has fewer
    than 11 errors. Raises `BoundaryError` if a value cannot cross the `DT-074` boundary.
    """
    n = len(weeks)
    if n < config.ses_min_history_weeks:
        return None
    fit = fit_ses(weeks, config)
    point = fit.levels[-1]
    points, lowers, uppers = [], [], []
    for h in range(1, HORIZON_WEEKS + 1):
        # Origin t (1-based) forecasts Y_{t+h} with level_t; only weeks ≤ as_of are used.
        errors = [weeks[t + h - 1] - fit.levels[t - 1] for t in range(1, n - h + 1)]
        if len(errors) < MIN_ERRORS_PER_HORIZON:
            return None
        q_lo, q_hi = _nearest_rank(errors)
        lower = max(0.0, point + min(q_lo, 0.0))
        upper = point + max(q_hi, 0.0)
        p, lo, hi = _checked_period(point, lower, upper)
        points.append(p)
        lowers.append(lo)
        uppers.append(hi)
    return ModelForecast(SES_NAME, tuple(points), tuple(lowers), tuple(uppers), alpha=fit.alpha)

