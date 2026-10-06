"""Candidate models of F5c (`DT-092`): Holt, additive Holt-Winters, Croston, SBA and TSB.

``float`` lives only inside this module and the other ``ml`` modules (`DT-074`); every value that leaves for a
comparison or for U1 crosses the boundary of `ml.models` (``Decimal(x)`` exact → 6 decimals ``ROUND_HALF_EVEN``,
no correction). Values that cannot cross (non-finite, negative, interval contract violated) raise
`BoundaryError`; the caller replaces the series by the official baseline and counts it (`DT-093`).

Fitting (`DT-093` point 9, provisional and configurable): small grids, minimum one-step squared error inside the
training window, ties kept by the first (smallest) parameter combination of the grid, scanned in increasing order.
Sums of ``float`` use ``math.fsum`` so that results do not depend on the Python version. The interval is the
nearest-rank 10/90 rule of `DT-056` on the in-sample errors at each horizon with the fitted parameters, as the
SES of F5a. Initialisations and grids are provisional choices of this module, recorded in every report:

* **Holt** (additive trend): state after week 2 ``level = Y_2``, ``trend = Y_2 − Y_1``; one-step errors from week 3.
* **Holt-Winters** (additive, period 52): needs at least two seasons (104 weeks, `DT-093` point 10). Initial trend
  ``(A_2 − A_1) / 52`` with ``A_k`` the mean of season ``k``; initial level ``A_1 − 26.5·trend``; initial seasonal
  indices the mean detrended deviation of the first two seasons, centred to sum zero. Recursion from week 1.
* **Croston** / **SBA**: size and interval smoothed with the same ``α`` from the first non-zero week (size = that
  demand, interval = its week index); SBA multiplies the Croston forecast by ``1 − α/2``.
* **TSB**: size smoothed with ``α`` on demand weeks, demand probability smoothed with ``β`` every week; initial
  probability ``1 / (index of the first non-zero week)``.
* A series without any non-zero week forecasts zero for the intermittent methods.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import product
from typing import Any

from app.forecasting import HORIZON_WEEKS, MIN_ERRORS_PER_HORIZON

from .models import BoundaryError, ModelForecast, _checked_period, _nearest_rank, to_contract

HOLT_NAME = "ml.holt"
HOLT_WINTERS_NAME = "ml.holt_winters"
CROSTON_NAME = "ml.croston"
SBA_NAME = "ml.sba"
TSB_NAME = "ml.tsb"
CANDIDATE_NAMES: tuple[str, ...] = (HOLT_NAME, HOLT_WINTERS_NAME, CROSTON_NAME, SBA_NAME, TSB_NAME)
INTERMITTENT_NAMES = frozenset({CROSTON_NAME, SBA_NAME, TSB_NAME})
CANDIDATE_VERSION = "0.1.0-provisional"
SEASON_WEEKS = 52


def _grid(*hundredths: int) -> tuple[float, ...]:
    """Grid values built from integers (k / 100), so that the grid is exact and reproducible."""
    return tuple(k / 100 for k in hundredths)


@dataclass(frozen=True)
class CandidateConfig:
    """Grids and minimum histories of the candidates (`DT-093` point 9: provisional, configurable)."""

    holt_alpha: tuple[float, ...] = field(default_factory=lambda: _grid(10, 20, 30, 40, 50, 60, 70, 80, 90))
    holt_beta: tuple[float, ...] = field(default_factory=lambda: _grid(1, 5, 10, 20, 30))
    hw_alpha: tuple[float, ...] = field(default_factory=lambda: _grid(10, 20, 30, 50))
    hw_beta: tuple[float, ...] = field(default_factory=lambda: _grid(1, 5, 10))
    hw_gamma: tuple[float, ...] = field(default_factory=lambda: _grid(5, 10, 20, 30))
    croston_alpha: tuple[float, ...] = field(default_factory=lambda: _grid(5, 10, 20, 30))
    tsb_alpha: tuple[float, ...] = field(default_factory=lambda: _grid(5, 10, 20, 30))
    tsb_beta: tuple[float, ...] = field(default_factory=lambda: _grid(5, 10, 20, 30))
    #: Same minimum as SES and the naïve baseline: 11 errors at h = 14 need 25 weeks (provisional).
    min_history_weeks: int = 25
    #: Two complete seasons (`DT-093` point 10, decision of the responsable).
    hw_min_history_weeks: int = 104

    def grid(self, name: str) -> list[tuple[float, ...]]:
        grids = {
            HOLT_NAME: (self.holt_alpha, self.holt_beta),
            HOLT_WINTERS_NAME: (self.hw_alpha, self.hw_beta, self.hw_gamma),
            CROSTON_NAME: (self.croston_alpha,),
            SBA_NAME: (self.croston_alpha,),
            TSB_NAME: (self.tsb_alpha, self.tsb_beta),
        }[name]
        return list(product(*grids))

    def min_weeks(self, name: str) -> int:
        return self.hw_min_history_weeks if name == HOLT_WINTERS_NAME else self.min_history_weeks

    def describe(self) -> dict[str, Any]:
        def fmt(values: tuple[float, ...]) -> list[str]:
            return [f"{v:.2f}" for v in values]

        return {
            "label": "PROPUESTA (provisional)",
            "selection": "minimum one-step SSE inside the training window; ties → first (smallest) grid combination",
            "interval": "nearest-rank 10/90 of DT-056 on in-sample errors per horizon (fitted parameters)",
            "holt": {"alpha": fmt(self.holt_alpha), "beta": fmt(self.holt_beta), "init": "level=Y2, trend=Y2−Y1"},
            "holt_winters": {
                "alpha": fmt(self.hw_alpha), "beta": fmt(self.hw_beta), "gamma": fmt(self.hw_gamma),
                "period": SEASON_WEEKS, "init": "two first seasons (trend, level, centred indices)",
            },
            "croston_sba": {"alpha": fmt(self.croston_alpha), "sba_factor": "1 − α/2"},
            "tsb": {"alpha": fmt(self.tsb_alpha), "beta": fmt(self.tsb_beta), "init": "p = 1 / index of first demand"},
            "min_history_weeks": self.min_history_weeks,
            "hw_min_history_weeks": self.hw_min_history_weeks,
        }


# --- Filters: one pass with fixed parameters -------------------------------------------------------------
# Each filter returns the one-step squared errors and ``paths(t, h)``: the h-step forecast from origin ``t``
# (1-based: after observing Y_1 … Y_t) for the origins where the model has a state.


@dataclass
class _Run:
    squared: list[float]
    first_origin: int
    forecast: Any  # (t, h) -> float

    @property
    def sse(self) -> float:
        return math.fsum(self.squared)


def _holt(y: Sequence[float], alpha: float, beta: float) -> _Run:
    if len(y) < 2:
        raise ValueError("Holt needs two weeks")
    levels = [0.0, y[0], y[1]]  # index = week (1-based); index 1 unused by forecasts
    trends = [0.0, 0.0, y[1] - y[0]]
    squared = []
    for t in range(3, len(y) + 1):
        f = levels[t - 1] + trends[t - 1]
        e = y[t - 1] - f
        squared.append(e * e)
        level = alpha * y[t - 1] + (1 - alpha) * f
        trends.append(beta * (level - levels[t - 1]) + (1 - beta) * trends[t - 1])
        levels.append(level)
    return _Run(squared, 2, lambda t, h: levels[t] + h * trends[t])


def _holt_winters(y: Sequence[float], alpha: float, beta: float, gamma: float) -> _Run:
    m = SEASON_WEEKS
    if len(y) < 2 * m:
        raise ValueError("Holt-Winters needs two seasons")
    a1 = math.fsum(y[:m]) / m
    a2 = math.fsum(y[m : 2 * m]) / m
    trend = (a2 - a1) / m
    level = a1 - (m + 1) / 2 * trend
    raw = [((y[i] - (level + (i + 1) * trend)) + (y[i + m] - (level + (i + 1 + m) * trend))) / 2 for i in range(m)]
    centre = math.fsum(raw) / m
    # seasonal[t + m - 1] holds s_t for t = 1 - m … n (index 0 is s_{1-m}).
    seasonal = [r - centre for r in raw]
    levels, trends = [level], [trend]  # index = week (0 = initial state)
    squared = []
    for t in range(1, len(y) + 1):
        s_old = seasonal[t - 1]  # s_{t-m}
        f = levels[t - 1] + trends[t - 1] + s_old
        e = y[t - 1] - f
        squared.append(e * e)
        lv = alpha * (y[t - 1] - s_old) + (1 - alpha) * (levels[t - 1] + trends[t - 1])
        trends.append(beta * (lv - levels[t - 1]) + (1 - beta) * trends[t - 1])
        levels.append(lv)
        seasonal.append(gamma * (y[t - 1] - lv) + (1 - gamma) * s_old)
    return _Run(squared, 1, lambda t, h: levels[t] + h * trends[t] + seasonal[t + h - 1])


def _first_demand(y: Sequence[float]) -> int | None:
    for i, v in enumerate(y):
        if v > 0:
            return i + 1
    return None


def _croston(y: Sequence[float], alpha: float, factor: float) -> _Run:
    t0 = _first_demand(y)
    if t0 is None:
        return _Run([v * v for v in y], 1, lambda t, h: 0.0)
    size, interval, last = y[t0 - 1], float(t0), t0
    forecasts = {t0: factor * size / interval}
    squared = []
    for t in range(t0 + 1, len(y) + 1):
        e = y[t - 1] - forecasts[t - 1]
        squared.append(e * e)
        if y[t - 1] > 0:
            size += alpha * (y[t - 1] - size)
            interval += alpha * ((t - last) - interval)
            last = t
        forecasts[t] = factor * size / interval
    return _Run(squared, t0, lambda t, h: forecasts[t])


def _tsb(y: Sequence[float], alpha: float, beta: float) -> _Run:
    t0 = _first_demand(y)
    if t0 is None:
        return _Run([v * v for v in y], 1, lambda t, h: 0.0)
    size, prob = y[t0 - 1], 1.0 / t0
    forecasts = {t0: prob * size}
    squared = []
    for t in range(t0 + 1, len(y) + 1):
        e = y[t - 1] - forecasts[t - 1]
        squared.append(e * e)
        if y[t - 1] > 0:
            size += alpha * (y[t - 1] - size)
            prob += beta * (1.0 - prob)
        else:
            prob += beta * (0.0 - prob)
        forecasts[t] = prob * size
    return _Run(squared, t0, lambda t, h: forecasts[t])


def _filter(name: str, y: Sequence[float], params: tuple[float, ...]) -> _Run:
    if name == HOLT_NAME:
        return _holt(y, *params)
    if name == HOLT_WINTERS_NAME:
        return _holt_winters(y, *params)
    if name == CROSTON_NAME:
        return _croston(y, params[0], 1.0)
    if name == SBA_NAME:
        return _croston(y, params[0], 1.0 - params[0] / 2)
    if name == TSB_NAME:
        return _tsb(y, *params)
    raise ValueError(f"unknown candidate {name}")


# --- Fitting, points and intervals -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CandidateFit:
    name: str
    params: tuple[float, ...]
    sse: float


def eligible(name: str, weeks: Sequence[float], config: CandidateConfig) -> bool:
    return len(weeks) >= config.min_weeks(name)


def fit(name: str, weeks: Sequence[float], config: CandidateConfig) -> CandidateFit:
    """Grid combination with the minimum one-step SSE; ties keep the first combination (`DT-093` point 9)."""
    best: CandidateFit | None = None
    for params in config.grid(name):
        sse = _filter(name, weeks, params).sse
        if best is None or sse < best.sse:
            best = CandidateFit(name, params, sse)
    assert best is not None
    return best


def raw_points(name: str, weeks: Sequence[float], params: tuple[float, ...]) -> list[float]:
    """The 14 weekly ``float`` points from the last week with fixed parameters (state updated to the last week)."""
    run = _filter(name, weeks, params)
    n = len(weeks)
    return [run.forecast(n, h) for h in range(1, HORIZON_WEEKS + 1)]


def contract_points(name: str, weeks: Sequence[float], params: tuple[float, ...]) -> tuple:
    """The 14 points through the `DT-074` boundary; negative or non-finite values raise `BoundaryError`."""
    out = []
    for value in raw_points(name, weeks, params):
        p = to_contract(value)
        if p < 0:
            raise BoundaryError(f"negative forecast {p}")
        out.append(p)
    return tuple(out)


def candidate_forecast(name: str, weeks: Sequence[float], config: CandidateConfig) -> ModelForecast | None:
    """14 periods with the nearest-rank interval, or ``None`` if not eligible (history or errors per horizon).

    Raises `BoundaryError` if a value cannot cross the `DT-074` boundary (the caller falls back and counts).
    """
    if not eligible(name, weeks, config):
        return None
    chosen = fit(name, weeks, config)
    run = _filter(name, weeks, chosen.params)
    n = len(weeks)
    points, lowers, uppers = [], [], []
    for h in range(1, HORIZON_WEEKS + 1):
        errors = [weeks[t + h - 1] - run.forecast(t, h) for t in range(run.first_origin, n - h + 1)]
        if len(errors) < MIN_ERRORS_PER_HORIZON:
            return None
        point = run.forecast(n, h)
        # The contract is checked after the conversion (DT-074 point 3): −1e−9 becomes 0.000000 and is valid.
        q_lo, q_hi = _nearest_rank(errors)
        p, lo, hi = _checked_period(point, max(0.0, point + min(q_lo, 0.0)), point + max(q_hi, 0.0))
        points.append(p)
        lowers.append(lo)
        uppers.append(hi)
    return ModelForecast(name, tuple(points), tuple(lowers), tuple(uppers), alpha=chosen.params[0])
