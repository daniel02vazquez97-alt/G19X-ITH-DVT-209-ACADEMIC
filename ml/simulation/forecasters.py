"""Weekly point forecast of each branch on its own (simulated) history.

U1 only reads the 14 weekly points, so each branch computes only its own points:

* the three baselines with the U3 predictors (``app.forecasting.baselines.PREDICTORS``) and the U3
  quantization (6 decimals, ``ROUND_HALF_EVEN``), available from the minimum history of `DT-056` point 7
  (25, 37 and 63 weeks); a test checks parity with ``app.forecasting.forecast``;
* the provisional SES of F5a (`DT-076` point 7) through the `DT-074` boundary.

The weekly totals are anchored on the decision date exactly as ``weekly_totals`` of U3 does: the history
starts with the weeks of the observed consumption and grows by one week at every weekly decision.
This module never sees the latent demand (`ml.simulation.environment`).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from fractions import Fraction

from app.forecasting import HORIZON_WEEKS, MOVING_AVERAGE, NAIVE, QUANTIZATION_SCALE, SEASONAL_NAIVE
from app.forecasting.baselines import PREDICTORS
from app.forecasting.exact import quantize
from app.forecasting.weekly import weekly_totals

from ..config import F5aConfig
from ..models import SES_NAME, fit_ses, to_contract

#: Minimum complete weeks for the 14 periods of each baseline (`DT-056` point 7).
MIN_HISTORY_WEEKS = {NAIVE.name: 25, MOVING_AVERAGE.name: 37, SEASONAL_NAIVE.name: 63}


class WeeklyHistory:
    """Anchored weekly totals of one branch: exact for the baselines, ``float`` copies for SES only."""

    def __init__(self, daily: Sequence[Decimal]) -> None:
        self.weeks: list[Fraction] = weekly_totals([Fraction(q) for q in daily])
        self.floats: list[float] = [float(w) for w in self.weeks]

    def append_week(self, days: Sequence[Decimal]) -> None:
        if len(days) != 7:
            raise ValueError("a week has 7 days")
        total = sum((Fraction(q) for q in days), Fraction(0))
        self.weeks.append(total)
        self.floats.append(float(total))


def point_forecast(model: str, history: WeeklyHistory, config: F5aConfig) -> tuple[Decimal, ...] | None:
    """The 14 weekly points of ``model`` (contract ``Decimal``), or ``None`` if the history is too short."""
    if model == SES_NAME:
        if len(history.floats) < config.ses_min_history_weeks:
            return None
        level = to_contract(fit_ses(history.floats, config).levels[-1])
        if level < 0:
            return None
        return (level,) * HORIZON_WEEKS
    if len(history.weeks) < MIN_HISTORY_WEEKS[model]:
        return None
    predictor = PREDICTORS[model]
    points = []
    for h in range(1, HORIZON_WEEKS + 1):
        value = predictor(history.weeks, h)
        if value is None:
            return None
        points.append(quantize(value, QUANTIZATION_SCALE))
    return tuple(points)
