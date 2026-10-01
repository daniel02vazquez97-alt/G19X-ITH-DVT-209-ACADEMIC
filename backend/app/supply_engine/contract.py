"""Public contract of the V1 supply engine (unit U1).

Normative source: `docs/06-motor-abastecimiento.md` §16 — inputs §16.3, output §16.5, exact
arithmetic §16.6 (B3) and the closed contract of §16.11 — with decisions `DT-045` and `DT-048` to
`DT-054`.

Everything here is an immutable value: frozen dataclasses, tuples and string enumerations. The
engine never mutates its input and never reads anything that is not in it: no clock, no
configuration, no database (`docs/06` §16.1).

Numbers at the input boundary are ``int``, finite ``Decimal`` or ``Fraction`` (`DT-051`); ``float``
is rejected. Every decision is taken on ``Fraction``; ``Decimal`` only appears in the output, for the
five values that §16.6 point 7 reports with 28 significant digits.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction
from typing import Union

#: Version of the engine's observable output (`DT-051`): PATCH changes no output, MINOR changes the
#: output of some valid input without breaking the contract, MAJOR breaks the contract or its types.
ENGINE_VERSION = "0.1.0"

#: The only policy set V1 knows (`DT-031`, `docs/06` §16.3).
POLICY_SET_V1 = "V1_PROVISIONAL"

#: Exact number accepted at the input boundary (`DT-051`).
Quantity = Union[int, Decimal, Fraction]

#: Reported value: exact (``Fraction``) or, only for the five fields of §16.6 point 7 when ``A`` is
#: not a perfect square, a ``Decimal`` with 28 significant digits.
Reported = Union[Fraction, Decimal]


class Outcome(StrEnum):
    """Result of one evaluation (`docs/06` §16.5)."""

    RECOMMEND = "RECOMMEND"
    NO_NEED = "NO_NEED"
    NOT_CALCULABLE = "NOT_CALCULABLE"


class Reason(StrEnum):
    """Why an evaluation is ``NOT_CALCULABLE``. Closed list, in canonical order (§16.5, `DT-051`).

    ``PRODUCT_OUT_OF_VALIDITY`` means the product is not valid during the whole period the
    evaluation requires, ``as_of_date`` to ``as_of_date + H`` (`DT-P22`).
    """

    PRODUCT_INACTIVE = "PRODUCT_INACTIVE"
    PRODUCT_OUT_OF_VALIDITY = "PRODUCT_OUT_OF_VALIDITY"
    NO_ACTIVE_PREFERRED_SUPPLIER = "NO_ACTIVE_PREFERRED_SUPPLIER"
    NEGATIVE_ON_HAND = "NEGATIVE_ON_HAND"
    FORECAST_MISSING = "FORECAST_MISSING"
    FORECAST_TOO_SHORT = "FORECAST_TOO_SHORT"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    MISSING_POLICY_PARAMETER = "MISSING_POLICY_PARAMETER"


class Flag(StrEnum):
    """Traceability flags, in canonical order (§16.5); conditions in §16.11.4."""

    LEAD_TIME_AGREED_FALLBACK = "LEAD_TIME_AGREED_FALLBACK"
    LEAD_TIME_CAPPED = "LEAD_TIME_CAPPED"
    MOQ_APPLIED = "MOQ_APPLIED"
    ORDER_MULTIPLE_ROUNDING = "ORDER_MULTIPLE_ROUNDING"
    UNCOUNTED_TRANSIT = "UNCOUNTED_TRANSIT"
    OVERDUE_ORDERS_EXCLUDED = "OVERDUE_ORDERS_EXCLUDED"
    ZERO_FORECAST_DEMAND = "ZERO_FORECAST_DEMAND"


class LeadTimeSource(StrEnum):
    """Where ``L`` comes from (`V1-09`)."""

    OBSERVED = "OBSERVED"
    AGREED_FALLBACK = "AGREED_FALLBACK"


class PolicyParameter(StrEnum):
    """Policy parameters, in the canonical order of ``missing_policy_parameters`` (`DT-051`)."""

    R = "R"
    Z = "z"
    N = "N"
    N_MIN = "N_MIN"
    LT_MAX = "LT_MAX"


class MethodUsed(StrEnum):
    """How the forecast was produced (`docs/05` §19.3, RML-007). The engine does not read it."""

    MODEL = "MODEL"
    BASELINE = "BASELINE"
    INTERMITTENT_METHOD = "INTERMITTENT_METHOD"


class InvalidInputError(ValueError):
    """The input violates the contract (`DT-052`, `docs/06` §16.11.5).

    The only exception of the contract. It is not an outcome: a valid input that cannot produce a
    recommendation returns ``NOT_CALCULABLE`` instead. ``field`` is the path in the input contract
    (``inventory.reserved``, ``open_lines[2].quantity_pending``); the message describes the broken
    rule and never contains the received value or any identifier.
    """

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


# --------------------------------------------------------------------------------------------
# Input (docs/06 §16.3). Field order is the canonical validation order (DT-052).
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Product:
    """The evaluated product. No ``abc_class`` nor ``rotation_class`` (`V1-11`, aclaración A-2)."""

    product_id: int
    location_id: int
    is_active: bool
    valid_from: _dt.date
    valid_to: _dt.date | None


@dataclass(frozen=True, slots=True)
class SupplierRelation:
    """One product-supplier relation. The engine receives all of them and selects (`V1-10`)."""

    supplier_id: int
    is_active: bool
    is_preferred: bool
    moq: Quantity
    order_multiple: Quantity
    agreed_lead_time_days: int


@dataclass(frozen=True, slots=True)
class Inventory:
    """Inventory at the close of ``as_of_date`` (`V1-02`, `V1-13`)."""

    on_hand: Quantity
    reserved: Quantity
    total_in_transit: Quantity


@dataclass(frozen=True, slots=True)
class OpenLine:
    """One open purchase-order line at the close of ``as_of_date`` (`V1-02`, `DT-012`)."""

    purchase_order_id: int
    item_id: int
    supplier_id: int
    expected_on: _dt.date
    quantity_pending: Quantity


@dataclass(frozen=True, slots=True)
class LeadTimeObservation:
    """One fully received line: issue date and date of its last receipt (`V1-09`)."""

    supplier_id: int
    issued_on: _dt.date
    completed_on: _dt.date


@dataclass(frozen=True, slots=True)
class ConsumptionSeries:
    """Dense daily series of satisfied demand: ``quantities[i]`` is day ``start_date + i`` (`DT-052`)."""

    start_date: _dt.date
    quantities: tuple[Quantity, ...]


@dataclass(frozen=True, slots=True)
class Forecast:
    """Weekly forecast anchored on ``horizon_start``: week ``k`` is
    ``[start_date + 7(k−1), start_date + 7k)`` (`docs/06` §16.2, `DT-048`)."""

    start_date: _dt.date
    weekly_quantities: tuple[Quantity, ...]
    forecast_id: int
    model_version: int
    method_used: MethodUsed


@dataclass(frozen=True, slots=True)
class PolicyParameters:
    """Policy set and its parameters; ``None`` means missing (``MISSING_POLICY_PARAMETER``).

    Contract names: ``r`` is ``R``, ``z`` is ``z``, ``n`` is ``N``, ``n_min`` is ``N_MIN`` and
    ``lt_max`` is ``LT_MAX`` (`docs/06` §16.3).
    """

    policy_set: str
    r: int | None
    z: Quantity | None
    n: int | None
    n_min: int | None
    lt_max: int | None


#: The V1 parameters of `DT-031`, exact (`z_v1 = 33/20`, `docs/06` §16.6 point 1).
V1_PROVISIONAL_PARAMETERS = PolicyParameters(
    policy_set=POLICY_SET_V1, r=7, z=Fraction(33, 20), n=12, n_min=3, lt_max=90
)


@dataclass(frozen=True, slots=True)
class EvaluationInput:
    """One evaluation: one product-location at one cut-off date (`docs/06` §16.1).

    The order of the fields is the canonical order of the input blocks (`DT-051`).
    """

    as_of_date: _dt.date
    product: Product
    supplier_relations: tuple[SupplierRelation, ...]
    inventory: Inventory
    open_lines: tuple[OpenLine, ...]
    lead_time_observations: tuple[LeadTimeObservation, ...]
    consumption: ConsumptionSeries
    forecast: Forecast | None
    policy: PolicyParameters


# --------------------------------------------------------------------------------------------
# Output (docs/06 §16.5, §16.11.4, §16.11.6)
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Breakdown:
    """Every term of `docs/06` §13 that could be computed validly; ``None`` otherwise (`DT-053`).

    Contract names: ``lead_time_days`` is ``L``; ``lead_time_observation_count`` is the ``n`` of
    `V1-09`; ``review_period_days`` is ``R``; ``coverage_horizon_days`` is ``H``;
    ``demand_over_lead_time`` is the demand over ``L`` (DDLT); ``demand_over_horizon`` is ``DDH``;
    ``sigma_window_count`` is the ``n`` of B3; ``sigma_h`` is ``σ_H``; ``safety_stock`` is ``SS``;
    ``target_level`` is ``S = DDH + SS``; ``inventory_position_decision`` is ``IP_decisión``;
    ``inventory_position_accounting`` is ``IP_contable``; ``order_multiple`` is ``M``;
    ``s1``, ``s2``, ``a``, ``b``, ``d`` and ``p`` are the exact B3 components ``S1``, ``S2``, ``A``,
    ``B``, ``D`` and ``P`` (§16.6).

    The decision terms ``raw_need``, ``q_moq`` and ``q_final`` exist only when ``reasons == ()``.
    """

    as_of_date: _dt.date
    horizon_start: _dt.date
    supplier_id: int | None = None
    lead_time_days: int | None = None
    lead_time_source: LeadTimeSource | None = None
    lead_time_observation_count: int | None = None
    uncapped_lead_time_days: int | None = None
    review_period_days: int | None = None
    coverage_horizon_days: int | None = None
    demand_conversion_rule: str | None = None
    demand_over_lead_time: Fraction | None = None
    demand_over_horizon: Fraction | None = None
    sigma_window_count: int | None = None
    sigma_h: Reported | None = None
    z: Fraction | None = None
    safety_stock: Reported | None = None
    target_level: Reported | None = None
    on_hand: Fraction | None = None
    reserved: Fraction | None = None
    total_in_transit: Fraction | None = None
    effective_in_transit: Fraction | None = None
    effective_lines: tuple[OpenLine, ...] | None = None
    inventory_position_decision: Fraction | None = None
    inventory_position_accounting: Fraction | None = None
    moq: Fraction | None = None
    order_multiple: Fraction | None = None
    raw_need: Reported | None = None
    q_moq: Reported | None = None
    q_final: Fraction | None = None
    s1: int | Fraction | None = None
    s2: int | Fraction | None = None
    a: int | Fraction | None = None
    b: int | Fraction | None = None
    d: int | None = None
    p: Fraction | None = None


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Output of one evaluation (`docs/06` §16.5)."""

    outcome: Outcome
    reasons: tuple[Reason, ...]
    missing_policy_parameters: tuple[PolicyParameter, ...]
    flags: tuple[Flag, ...]
    breakdown: Breakdown
    forecast_id: int | None
    policy_set: str
    engine_version: str
