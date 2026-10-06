"""Weekly point forecasts shared by the `DT-011` study (Level 1) and the F5c simulator branches (Level 2).

* Baselines: the U3 predictors through ``ml.simulation.forecasters.point_forecast`` (exact, quantized as U3).
* SES: the provisional SES of F5a through the same function.
* Candidates: ``ml.candidates`` with fixed or freshly fitted parameters, through the `DT-074` boundary.

Every function takes a weekly training series (already transformed by a `DT-081` strategy if any) and returns
14 contract ``Decimal`` points, or ``None`` if the model is not eligible on that history.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from fractions import Fraction

from ..candidates import CANDIDATE_NAMES, CandidateConfig, contract_points, eligible, fit
from ..config import F5aConfig
from ..simulation.forecasters import WeeklyHistory, point_forecast


def weekly_history(weeks: Sequence[Fraction]) -> WeeklyHistory:
    history = WeeklyHistory([])
    history.weeks = list(weeks)
    history.floats = [float(w) for w in weeks]
    return history


def model_points(
    model: str,
    weeks: Sequence[Fraction],
    f5a: F5aConfig,
    candidates: CandidateConfig,
    params: tuple[float, ...] | None = None,
) -> tuple[tuple[Decimal, ...] | None, tuple[float, ...] | None]:
    """``(points, params)``: the 14 points of ``model`` and, for a candidate, the parameters used.

    A candidate is fitted when ``params`` is ``None``. Raises `ml.models.BoundaryError` when a candidate value
    cannot cross the `DT-074` boundary (the caller substitutes the official baseline and counts it).
    """
    if model not in CANDIDATE_NAMES:
        return point_forecast(model, weekly_history(weeks), f5a), None
    floats = [float(w) for w in weeks]
    if not eligible(model, floats, candidates):
        return None, None
    chosen = params if params is not None else fit(model, floats, candidates).params
    return contract_points(model, floats, chosen), chosen
