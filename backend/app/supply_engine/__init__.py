"""V1 supply engine (unit U1): a pure, deterministic library (`docs/06` §16).

One entry point, `evaluate`, per product-location and explicit cut-off date. Standard library only;
no database, HTTP, LLM, clock, randomness or global configuration (`docs/03` §16.4).
"""

from .contract import (
    ENGINE_VERSION,
    POLICY_SET_V1,
    V1_PROVISIONAL_PARAMETERS,
    Breakdown,
    ConsumptionSeries,
    EvaluationInput,
    EvaluationResult,
    Flag,
    Forecast,
    InvalidInputError,
    Inventory,
    LeadTimeObservation,
    LeadTimeSource,
    MethodUsed,
    OpenLine,
    Outcome,
    PolicyParameter,
    PolicyParameters,
    Product,
    Reason,
    SupplierRelation,
)
from .engine import evaluate

__all__ = [
    "ENGINE_VERSION",
    "POLICY_SET_V1",
    "V1_PROVISIONAL_PARAMETERS",
    "Breakdown",
    "ConsumptionSeries",
    "EvaluationInput",
    "EvaluationResult",
    "Flag",
    "Forecast",
    "InvalidInputError",
    "Inventory",
    "LeadTimeObservation",
    "LeadTimeSource",
    "MethodUsed",
    "OpenLine",
    "Outcome",
    "PolicyParameter",
    "PolicyParameters",
    "Product",
    "Reason",
    "SupplierRelation",
    "evaluate",
]
