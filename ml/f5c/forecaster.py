"""Forecaster of the F5c simulator branches (`DT-093` points 9 and 11).

Branch names are ``model`` or ``model@strategy`` (`DT-081` strategy ``b`` or ``c``). For the four F5b models
without a strategy the forecast is exactly the F5b one (``ml.simulation.forecasters.point_forecast``), so those
branches reproduce F5b.

* Candidates re-optimise their parameters every ``refit_every`` weekly decisions (the history grows one week per
  decision) and update their state at every decision with the fixed parameters.
* A candidate that is not eligible yet (Holt-Winters before 104 weeks) or whose values cannot cross the `DT-074`
  boundary uses the points of the official baseline on the same branch history; the substitution is returned
  so that the simulator counts it.
* Strategy branches rebuild the weekly series from the branch daily history and its stockout flags (simulated
  lost sales count as stockout days), with the anchoring of the branch weeks.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from ..candidates import CANDIDATE_NAMES, CandidateConfig, contract_points, eligible, fit
from ..config import F5aConfig
from ..models import BoundaryError
from ..simulation.forecasters import WeeklyHistory, point_forecast
from .config import OFFICIAL_BASELINE, STRATEGY_AS_IS
from .points import model_points
from .strategies import strategy_weeks

STRATEGY_SEPARATOR = "@"
NOT_ELIGIBLE = "NOT_ELIGIBLE"
INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class BranchForecast:
    points: tuple[Decimal, ...] | None
    substitution: str | None = None


def split_branch(branch: str) -> tuple[str, str]:
    model, _, strategy = branch.partition(STRATEGY_SEPARATOR)
    return model, strategy or STRATEGY_AS_IS


def branch_name(model: str, strategy: str) -> str:
    return model if strategy == STRATEGY_AS_IS else f"{model}{STRATEGY_SEPARATOR}{strategy}"


class F5cForecaster:
    def __init__(self, candidates: CandidateConfig, refit_every: int = 4, impute_window_days: int = 56) -> None:
        if refit_every < 1:
            raise ValueError("refit_every must be at least 1")
        self.candidates = candidates
        self.refit_every = refit_every
        self.impute_window_days = impute_window_days

    def _weeks(self, history: WeeklyHistory, strategy: str) -> list[Fraction]:
        if strategy == STRATEGY_AS_IS:
            return list(history.weeks)
        end = history.offset + 7 * len(history.weeks)  # days of the anchored weeks (later days are not used)
        daily = [Fraction(q) for q in history.daily[:end]]
        return strategy_weeks(strategy, daily, list(history.flags[:end]), len(history.weeks), self.impute_window_days)

    def __call__(self, branch: str, history: WeeklyHistory, f5a: F5aConfig) -> BranchForecast | tuple | None:
        model, strategy = split_branch(branch)
        if model not in CANDIDATE_NAMES and strategy == STRATEGY_AS_IS:
            return point_forecast(model, history, f5a)  # F5b path, unchanged
        weeks = self._weeks(history, strategy)
        if model not in CANDIDATE_NAMES:
            points, _ = model_points(model, weeks, f5a, self.candidates)
            return BranchForecast(points)
        floats = [float(w) for w in weeks]
        if not eligible(model, floats, self.candidates):
            return self._substitute(weeks, f5a, NOT_ELIGIBLE)
        fits = history.__dict__.setdefault("f5c_fits", {})
        fitted = fits.get(branch)
        if fitted is None or len(history.weeks) - fitted[0] >= self.refit_every:
            fitted = (len(history.weeks), fit(model, floats, self.candidates).params)
            fits[branch] = fitted
        try:
            return BranchForecast(contract_points(model, floats, fitted[1]))
        except BoundaryError:
            return self._substitute(weeks, f5a, INVALID)

    def _substitute(self, weeks: list[Fraction], f5a: F5aConfig, reason: str) -> BranchForecast:
        points, _ = model_points(OFFICIAL_BASELINE, weeks, f5a, self.candidates)
        return BranchForecast(points, reason)
