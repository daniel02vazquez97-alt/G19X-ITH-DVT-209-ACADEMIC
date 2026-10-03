"""`ForecastProvider` V1: three local baselines, empirical intervals and the primary chain.

Pure and deterministic (`DT-046`): no database, no clock, no randomness, no ``float``. The caller
(``app.runs``) builds the request and persists the result.
"""

from __future__ import annotations

import datetime as _dt
from fractions import Fraction

from .baselines import BASELINES, PREDICTORS, PRIMARY_CHAIN, REFERENCE
from .contract import (
    HORIZON_WEEKS,
    MIN_ERRORS_PER_HORIZON,
    QUANTIZATION_SCALE,
    BaselineDefinition,
    ConfidenceFlag,
    ForecastPeriod,
    ForecastRequest,
    ForecastResult,
    ForecastSeries,
    UnavailableBaseline,
    UnavailableReason,
)
from .exact import quantize, to_fraction
from .interval import horizon_errors, interval, nearest_rank_bounds
from .weekly import weekly_totals

_ONE_DAY = _dt.timedelta(days=1)


def period_bounds(as_of_date: _dt.date, h: int) -> tuple[_dt.date, _dt.date]:
    """Week ``h`` of the horizon: ``[A + 1 + 7(h − 1), A + 1 + 7h)`` (`DT-046`, `DT-048`)."""
    start = as_of_date + _ONE_DAY * (1 + 7 * (h - 1))
    return start, start + _ONE_DAY * 7


def _series(definition: BaselineDefinition, weeks: list[Fraction], as_of: _dt.date) -> ForecastSeries | None:
    """The 14 periods of one baseline, or ``None`` if any horizon lacks point or ``m ≥ 11`` errors."""
    predictor = PREDICTORS[definition.name]
    periods = []
    for h in range(1, HORIZON_WEEKS + 1):
        point = predictor(weeks, h)
        errors = horizon_errors(weeks, predictor, h)
        if point is None or len(errors) < MIN_ERRORS_PER_HORIZON:
            return None
        q_lo, q_hi = nearest_rank_bounds(errors)
        lower, upper = interval(point, q_lo, q_hi)
        start, end = period_bounds(as_of, h)
        period = ForecastPeriod(
            period_start=start,
            period_end=end,
            predicted_quantity=quantize(point, QUANTIZATION_SCALE),
            lower_bound=quantize(lower, QUANTIZATION_SCALE),
            upper_bound=quantize(upper, QUANTIZATION_SCALE),
        )
        _check_period(period)
        periods.append(period)
    return ForecastSeries(definition=definition, periods=tuple(periods))


def _check_period(period: ForecastPeriod) -> None:
    """Output invariants (`docs/04` §3.14): never returned broken."""
    if not (0 <= period.lower_bound <= period.predicted_quantity <= period.upper_bound):
        raise AssertionError(f"interval invariant violated: {period}")
    for value in (period.lower_bound, period.predicted_quantity, period.upper_bound):
        if -value.as_tuple().exponent > QUANTIZATION_SCALE:
            raise AssertionError(f"more than {QUANTIZATION_SCALE} decimals: {value}")


def forecast(request: ForecastRequest) -> ForecastResult:
    """Run the three baselines on ``request`` and choose the primary series (`DT-056` point 8)."""
    daily = [to_fraction(q, "daily_consumption") for q in request.daily_consumption]
    weeks = weekly_totals(daily)
    computed: dict[str, ForecastSeries] = {}
    unavailable = []
    for definition in BASELINES:
        series = _series(definition, weeks, request.as_of_date)
        if series is None:
            unavailable.append(UnavailableBaseline(definition, UnavailableReason.INSUFFICIENT_HISTORY))
        else:
            computed[definition.name] = series

    primary = next((d for d in PRIMARY_CHAIN if d.name in computed), None)
    if primary is None:
        flag = None
        reason = UnavailableReason.INSUFFICIENT_HISTORY
    else:
        flag = ConfidenceFlag.STANDARD if primary == REFERENCE else ConfidenceFlag.INSUFFICIENT_HISTORY
        reason = None
    return ForecastResult(
        product_id=request.product_id,
        location_id=request.location_id,
        as_of_date=request.as_of_date,
        history_weeks=len(weeks),
        series=tuple(computed[d.name] for d in BASELINES if d.name in computed),
        unavailable=tuple(unavailable),
        primary=primary,
        confidence_flag=flag,
        no_forecast_reason=reason,
    )


class LocalBaselineProvider:
    """The local implementation of the `ForecastProvider` port (`docs/03` §16.5)."""

    def forecast(self, request: ForecastRequest) -> ForecastResult:
        return forecast(request)
