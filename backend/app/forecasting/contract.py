"""Public contract of `ForecastProvider` (`DT-046`): request, result and baseline definitions.

Every type is a frozen dataclass. Quantities enter as ``int``, finite ``Decimal`` or ``Fraction``
(never ``float`` nor ``bool``) and leave as ``Decimal`` with at most six decimals (`DT-056` point 11).
The request is validated on construction, so an invalid request cannot exist.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction
from typing import Any

from .exact import InvalidForecastInputError, to_fraction

#: Weeks of every forecast (`DT-046`): ``⌈(LT_MAX_v1 + R_v1) / 7⌉ = 14``.
HORIZON_WEEKS = 14
#: Nominal level of the interval (`DT-056` point 5). Not a guarantee nor a measured coverage.
CONFIDENCE_LEVEL = Decimal("0.80")
#: Operational minimum of errors per horizon of the nearest-rank 10/90 rule (`DT-056` point 6).
MIN_ERRORS_PER_HORIZON = 11
#: Decimals of every quantity the provider returns (`DT-056` point 11).
QUANTIZATION_SCALE = 6
#: Provisional V1 treatment of stockout days (`DT-056` point 9); `DT-011` stays open.
STOCKOUT_TREATMENT = "NONE_RAW_CONSUMPTION_V1"
#: ``method_used`` of every baseline series (`docs/05` §19.3, RML-007).
METHOD_USED = "BASELINE"

Quantity = int | Decimal | Fraction

_ONE_DAY = _dt.timedelta(days=1)


class ConfidenceFlag(StrEnum):
    STANDARD = "STANDARD"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"


class UnavailableReason(StrEnum):
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"


def _common_hyperparameters() -> dict[str, Any]:
    return {
        "horizon_weeks": HORIZON_WEEKS,
        "history_weeks": "ANCHORED_AT_AS_OF_FULL_WEEKS",
        "interval": {
            "method": "EMPIRICAL_HORIZON_ERROR_QUANTILES",
            "confidence_level": str(CONFIDENCE_LEVEL),
            "quantile_rule": "NEAREST_RANK",
            "min_errors_per_horizon": MIN_ERRORS_PER_HORIZON,
            "lower_floor": "0",
        },
        "quantization": {"scale": QUANTIZATION_SCALE, "rounding": "ROUND_HALF_EVEN"},
        "stockout_treatment": STOCKOUT_TREATMENT,
    }


@dataclass(frozen=True, slots=True)
class BaselineDefinition:
    """Identity of a baseline version (`DT-057`): one row of ``model_versions``."""

    name: str
    version: str
    algorithm: str
    #: Parameters specific to the algorithm, as ``(key, value)`` pairs.
    specific: tuple[tuple[str, int], ...] = ()

    @property
    def hyperparameters(self) -> dict[str, Any]:
        """A fresh dict: the common block of `DT-056` plus the specific parameters."""
        result = _common_hyperparameters()
        result.update(dict(self.specific))
        return result


@dataclass(frozen=True, slots=True)
class ForecastRequest:
    """Daily consumption of one series up to ``as_of_date``, contiguous by construction.

    Day ``i`` of ``daily_consumption`` is ``history_start + i``; the last one must be ``as_of_date``.
    ``daily_stockout_flags`` travels with the request (`docs/05` §19.2) but V1 does not use it.
    """

    product_id: int
    location_id: int
    as_of_date: _dt.date
    history_start: _dt.date
    daily_consumption: tuple[Quantity, ...]
    daily_stockout_flags: tuple[bool, ...]

    def __post_init__(self) -> None:
        for name in ("product_id", "location_id"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise InvalidForecastInputError("INVALID_TYPE", name, "must be an int")
        for name in ("as_of_date", "history_start"):
            value = getattr(self, name)
            if isinstance(value, _dt.datetime) or not isinstance(value, _dt.date):
                raise InvalidForecastInputError("INVALID_TYPE", name, "must be a date")
        if not isinstance(self.daily_consumption, tuple):
            raise InvalidForecastInputError("INVALID_TYPE", "daily_consumption", "must be a tuple")
        if not isinstance(self.daily_stockout_flags, tuple):
            raise InvalidForecastInputError("INVALID_TYPE", "daily_stockout_flags", "must be a tuple")
        if self.history_start > self.as_of_date:
            raise InvalidForecastInputError(
                "FUTURE_DATE", "history_start", "history starts after as_of_date"
            )
        expected = (self.as_of_date - self.history_start).days + 1
        if len(self.daily_consumption) > expected:
            raise InvalidForecastInputError(
                "FUTURE_DATE", "daily_consumption", "history extends beyond as_of_date"
            )
        if len(self.daily_consumption) < expected:
            raise InvalidForecastInputError(
                "INCOMPLETE_HISTORY", "daily_consumption", "history must end on as_of_date"
            )
        if len(self.daily_stockout_flags) != len(self.daily_consumption):
            raise InvalidForecastInputError(
                "LENGTH_MISMATCH", "daily_stockout_flags", "one flag per day is required"
            )
        for index, quantity in enumerate(self.daily_consumption):
            value = to_fraction(quantity, f"daily_consumption[{index}]")
            if value < 0:
                raise InvalidForecastInputError(
                    "NEGATIVE_QUANTITY", f"daily_consumption[{index}]", "must be >= 0"
                )
        for index, flag in enumerate(self.daily_stockout_flags):
            if not isinstance(flag, bool):
                raise InvalidForecastInputError(
                    "INVALID_TYPE", f"daily_stockout_flags[{index}]", "must be a bool"
                )


def build_request(
    product_id: int,
    location_id: int,
    as_of_date: _dt.date,
    rows: Sequence[tuple[_dt.date, Quantity, bool]],
) -> ForecastRequest:
    """A request from dated rows ``(day, quantity, is_stockout_affected)`` in any order.

    Rejects a row after ``as_of_date`` (``FUTURE_DATE``), a repeated day (``DUPLICATE_DATE``), a gap
    (``GAP``) and a history that does not reach ``as_of_date`` (``INCOMPLETE_HISTORY``). Nothing is
    imputed.
    """
    if not rows:
        raise InvalidForecastInputError("INCOMPLETE_HISTORY", "rows", "no consumption up to as_of_date")
    ordered = sorted(rows, key=lambda row: row[0])
    for day, _quantity, _flag in ordered:
        if day > as_of_date:
            raise InvalidForecastInputError("FUTURE_DATE", "rows", f"{day} is after {as_of_date}")
    for previous, current in zip(ordered, ordered[1:]):
        if current[0] == previous[0]:
            raise InvalidForecastInputError("DUPLICATE_DATE", "rows", f"{current[0]} appears twice")
        if current[0] != previous[0] + _ONE_DAY:
            raise InvalidForecastInputError(
                "GAP", "rows", f"no consumption between {previous[0]} and {current[0]}"
            )
    if ordered[-1][0] != as_of_date:
        raise InvalidForecastInputError(
            "INCOMPLETE_HISTORY", "rows", f"history ends on {ordered[-1][0]}, not on {as_of_date}"
        )
    return ForecastRequest(
        product_id=product_id,
        location_id=location_id,
        as_of_date=as_of_date,
        history_start=ordered[0][0],
        daily_consumption=tuple(row[1] for row in ordered),
        daily_stockout_flags=tuple(row[2] for row in ordered),
    )


@dataclass(frozen=True, slots=True)
class ForecastPeriod:
    """Week ``h``: ``[period_start, period_end)``, with ``0 ≤ lower ≤ predicted ≤ upper``."""

    period_start: _dt.date
    period_end: _dt.date
    predicted_quantity: Decimal
    lower_bound: Decimal
    upper_bound: Decimal


@dataclass(frozen=True, slots=True)
class ForecastSeries:
    definition: BaselineDefinition
    periods: tuple[ForecastPeriod, ...]


@dataclass(frozen=True, slots=True)
class UnavailableBaseline:
    definition: BaselineDefinition
    reason: UnavailableReason


@dataclass(frozen=True, slots=True)
class ForecastResult:
    """Every computable series, the unavailable baselines and the primary series (`DT-056`).

    ``primary`` is ``None`` when no baseline is computable; then ``confidence_flag`` is ``None`` and
    ``no_forecast_reason`` says why.
    """

    product_id: int
    location_id: int
    as_of_date: _dt.date
    history_weeks: int
    series: tuple[ForecastSeries, ...]
    unavailable: tuple[UnavailableBaseline, ...]
    primary: BaselineDefinition | None
    confidence_flag: ConfidenceFlag | None
    no_forecast_reason: UnavailableReason | None
    confidence_level: Decimal = CONFIDENCE_LEVEL
    method_used: str = METHOD_USED
    stockout_treatment: str = STOCKOUT_TREATMENT

    def series_for(self, name: str) -> ForecastSeries | None:
        for series in self.series:
            if series.definition.name == name:
                return series
        return None
