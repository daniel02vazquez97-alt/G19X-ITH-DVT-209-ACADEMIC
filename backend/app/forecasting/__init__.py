"""U3 — `ForecastProvider` and the V1 baselines (`DT-046`, `DT-056`).

A pure library: standard library only, no database, no clock, no randomness, no ``float``. It
estimates weekly demand with an interval; it never decides purchases (RML-012).
"""

from .baselines import BASELINES, MOVING_AVERAGE, NAIVE, PRIMARY_CHAIN, REFERENCE, SEASONAL_NAIVE
from .contract import (
    CONFIDENCE_LEVEL,
    HORIZON_WEEKS,
    METHOD_USED,
    MIN_ERRORS_PER_HORIZON,
    QUANTIZATION_SCALE,
    STOCKOUT_TREATMENT,
    BaselineDefinition,
    ConfidenceFlag,
    ForecastPeriod,
    ForecastRequest,
    ForecastResult,
    ForecastSeries,
    UnavailableBaseline,
    UnavailableReason,
    build_request,
)
from .exact import InvalidForecastInputError
from .provider import LocalBaselineProvider, forecast, period_bounds

__all__ = [
    "BASELINES",
    "CONFIDENCE_LEVEL",
    "HORIZON_WEEKS",
    "METHOD_USED",
    "MIN_ERRORS_PER_HORIZON",
    "MOVING_AVERAGE",
    "NAIVE",
    "PRIMARY_CHAIN",
    "QUANTIZATION_SCALE",
    "REFERENCE",
    "SEASONAL_NAIVE",
    "STOCKOUT_TREATMENT",
    "BaselineDefinition",
    "ConfidenceFlag",
    "ForecastPeriod",
    "ForecastRequest",
    "ForecastResult",
    "ForecastSeries",
    "InvalidForecastInputError",
    "LocalBaselineProvider",
    "UnavailableBaseline",
    "UnavailableReason",
    "build_request",
    "forecast",
    "period_bounds",
]
