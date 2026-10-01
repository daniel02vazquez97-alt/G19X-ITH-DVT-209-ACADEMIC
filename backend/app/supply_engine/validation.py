"""Input validation of the V1 supply engine (`DT-052`, `docs/06` §16.11.5).

Everything is validated before anything is computed, and only the **first** error, in canonical
order, is raised:

* Phase 1 — type, finiteness and sign: blocks in the order of `EvaluationInput`, fields in the order
  of `docs/06` §16.3, collections by index.
* Phase 2 — coherence, in this order: (a) ``valid_to ≥ valid_from``; (b) at most one active and
  preferred relation; (c) unique ``(purchase_order_id, item_id)``; (d) ``Σ quantity_pending =
  total_in_transit``; (e) ``completed_on ≥ issued_on``; (f) consumption coherence; (g)
  ``forecast.start_date = as_of_date + 1``; (h) ``policy_set`` and the V1 values.

``on_hand < 0`` is **not** invalid input: it is ``NOT_CALCULABLE`` with ``NEGATIVE_ON_HAND``
(`V1-13`). Messages never contain the received value nor any identifier.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from fractions import Fraction
from typing import Any

from .contract import (
    V1_PROVISIONAL_PARAMETERS,
    POLICY_SET_V1,
    ConsumptionSeries,
    EvaluationInput,
    Forecast,
    InvalidInputError,
    Inventory,
    LeadTimeObservation,
    MethodUsed,
    OpenLine,
    PolicyParameters,
    Product,
    SupplierRelation,
)

_ONE_DAY = _dt.timedelta(days=1)


def to_fraction(value: int | Decimal | Fraction) -> Fraction:
    """Lossless conversion of an already validated exact number."""
    return Fraction(value)


def validate(inputs: Any) -> None:
    """Raise `InvalidInputError` for the first contract violation; return ``None`` otherwise."""
    _phase_1(inputs)
    _phase_2(inputs)


# --------------------------------------------------------------------------------------------
# Phase 1 — type, finiteness and sign
# --------------------------------------------------------------------------------------------


def _type_name(value: Any) -> str:
    return type(value).__name__


def _require_instance(value: Any, kind: type, field: str) -> None:
    if not isinstance(value, kind):
        raise InvalidInputError(field, f"must be a {kind.__name__}, not {_type_name(value)}")


def _require_int(value: Any, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidInputError(field, f"must be an int, not {_type_name(value)}")


def _require_non_negative_int(value: Any, field: str) -> None:
    _require_int(value, field)
    if value < 0:
        raise InvalidInputError(field, "must be >= 0")


def _require_bool(value: Any, field: str) -> None:
    if not isinstance(value, bool):
        raise InvalidInputError(field, f"must be a bool, not {_type_name(value)}")


def _require_date(value: Any, field: str) -> None:
    if isinstance(value, _dt.datetime) or not isinstance(value, _dt.date):
        raise InvalidInputError(field, f"must be a datetime.date, not {_type_name(value)}")


def _require_optional_date(value: Any, field: str) -> None:
    if value is not None:
        _require_date(value, field)


def _require_quantity(value: Any, field: str) -> None:
    """Exact number: ``int``, finite ``Decimal`` or ``Fraction`` (`DT-051`)."""
    if isinstance(value, float):
        raise InvalidInputError(field, "float is not accepted; use int, Decimal or Fraction")
    if isinstance(value, bool):
        raise InvalidInputError(field, "bool is not accepted; use int, Decimal or Fraction")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise InvalidInputError(field, "must be finite")
        return
    if isinstance(value, (int, Fraction)):
        return
    raise InvalidInputError(field, f"must be an exact number (int, Decimal or Fraction), not {_type_name(value)}")


def _require_non_negative_quantity(value: Any, field: str) -> None:
    _require_quantity(value, field)
    if Fraction(value) < 0:
        raise InvalidInputError(field, "must be >= 0")


def _require_tuple(value: Any, field: str) -> None:
    if not isinstance(value, tuple):
        raise InvalidInputError(field, f"must be a tuple, not {_type_name(value)}")


def _phase_1(inputs: Any) -> None:
    _require_instance(inputs, EvaluationInput, "input")
    _require_date(inputs.as_of_date, "as_of_date")
    _check_product(inputs.product)
    _check_supplier_relations(inputs.supplier_relations)
    _check_inventory(inputs.inventory)
    _check_open_lines(inputs.open_lines)
    _check_observations(inputs.lead_time_observations)
    _check_consumption(inputs.consumption)
    _check_forecast(inputs.forecast)
    _check_policy(inputs.policy)


def _check_product(product: Any) -> None:
    _require_instance(product, Product, "product")
    _require_int(product.product_id, "product.product_id")
    _require_int(product.location_id, "product.location_id")
    _require_bool(product.is_active, "product.is_active")
    _require_date(product.valid_from, "product.valid_from")
    _require_optional_date(product.valid_to, "product.valid_to")


def _check_supplier_relations(relations: Any) -> None:
    _require_tuple(relations, "supplier_relations")
    for index, relation in enumerate(relations):
        path = f"supplier_relations[{index}]"
        _require_instance(relation, SupplierRelation, path)
        _require_int(relation.supplier_id, f"{path}.supplier_id")
        _require_bool(relation.is_active, f"{path}.is_active")
        _require_bool(relation.is_preferred, f"{path}.is_preferred")
        _require_non_negative_quantity(relation.moq, f"{path}.moq")
        _require_quantity(relation.order_multiple, f"{path}.order_multiple")
        if Fraction(relation.order_multiple) < 1:
            # Precondition M ≥ 1 of docs/06 §16.6 point 5.
            raise InvalidInputError(f"{path}.order_multiple", "must be >= 1")
        _require_non_negative_int(relation.agreed_lead_time_days, f"{path}.agreed_lead_time_days")


def _check_inventory(inventory: Any) -> None:
    _require_instance(inventory, Inventory, "inventory")
    # on_hand < 0 is valid input: NOT_CALCULABLE with NEGATIVE_ON_HAND (V1-13, DT-052).
    _require_quantity(inventory.on_hand, "inventory.on_hand")
    _require_non_negative_quantity(inventory.reserved, "inventory.reserved")
    _require_non_negative_quantity(inventory.total_in_transit, "inventory.total_in_transit")


def _check_open_lines(lines: Any) -> None:
    _require_tuple(lines, "open_lines")
    for index, line in enumerate(lines):
        path = f"open_lines[{index}]"
        _require_instance(line, OpenLine, path)
        _require_int(line.purchase_order_id, f"{path}.purchase_order_id")
        _require_int(line.item_id, f"{path}.item_id")
        _require_int(line.supplier_id, f"{path}.supplier_id")
        _require_date(line.expected_on, f"{path}.expected_on")
        _require_non_negative_quantity(line.quantity_pending, f"{path}.quantity_pending")


def _check_observations(observations: Any) -> None:
    _require_tuple(observations, "lead_time_observations")
    for index, observation in enumerate(observations):
        path = f"lead_time_observations[{index}]"
        _require_instance(observation, LeadTimeObservation, path)
        _require_int(observation.supplier_id, f"{path}.supplier_id")
        _require_date(observation.issued_on, f"{path}.issued_on")
        _require_date(observation.completed_on, f"{path}.completed_on")


def _check_consumption(consumption: Any) -> None:
    _require_instance(consumption, ConsumptionSeries, "consumption")
    _require_date(consumption.start_date, "consumption.start_date")
    _require_tuple(consumption.quantities, "consumption.quantities")
    for index, quantity in enumerate(consumption.quantities):
        _require_non_negative_quantity(quantity, f"consumption.quantities[{index}]")


def _check_forecast(forecast: Any) -> None:
    if forecast is None:
        return
    _require_instance(forecast, Forecast, "forecast")
    _require_date(forecast.start_date, "forecast.start_date")
    _require_tuple(forecast.weekly_quantities, "forecast.weekly_quantities")
    for index, quantity in enumerate(forecast.weekly_quantities):
        _require_non_negative_quantity(quantity, f"forecast.weekly_quantities[{index}]")
    _require_int(forecast.forecast_id, "forecast.forecast_id")
    _require_int(forecast.model_version, "forecast.model_version")
    _require_instance(forecast.method_used, MethodUsed, "forecast.method_used")


def _check_policy(policy: Any) -> None:
    _require_instance(policy, PolicyParameters, "policy")
    _require_instance(policy.policy_set, str, "policy.policy_set")
    for name in ("r", "n", "n_min", "lt_max"):
        value = getattr(policy, name)
        if value is not None:
            _require_int(value, f"policy.{name}")
    if policy.z is not None:
        _require_quantity(policy.z, "policy.z")


# --------------------------------------------------------------------------------------------
# Phase 2 — coherence, in the order (a) … (h) of DT-052
# --------------------------------------------------------------------------------------------


def _phase_2(inputs: EvaluationInput) -> None:
    as_of = inputs.as_of_date
    product = inputs.product

    # (a) valid_to ≥ valid_from.
    if product.valid_to is not None and product.valid_to < product.valid_from:
        raise InvalidInputError("product.valid_to", "must be on or after valid_from")

    # (b) at most one active and preferred relation (DT-024).
    preferred = [r for r in inputs.supplier_relations if r.is_active and r.is_preferred]
    if len(preferred) > 1:
        raise InvalidInputError("supplier_relations", "at most one relation may be active and preferred")

    # (c) unique (purchase_order_id, item_id).
    seen: set[tuple[int, int]] = set()
    for index, line in enumerate(inputs.open_lines):
        key = (line.purchase_order_id, line.item_id)
        if key in seen:
            raise InvalidInputError(f"open_lines[{index}]", "duplicates the (purchase_order_id, item_id) of an earlier line")
        seen.add(key)

    # (d) Σ quantity_pending = total_in_transit (docs/06 §4.1).
    pending = sum((to_fraction(line.quantity_pending) for line in inputs.open_lines), Fraction(0))
    if pending != to_fraction(inputs.inventory.total_in_transit):
        raise InvalidInputError("inventory.total_in_transit", "must equal the sum of open_lines.quantity_pending")

    # (e) completed_on ≥ issued_on (DT-031 §V1-09, question 6).
    for index, observation in enumerate(inputs.lead_time_observations):
        if observation.completed_on < observation.issued_on:
            raise InvalidInputError(f"lead_time_observations[{index}].completed_on", "must be on or after issued_on")

    # (f) consumption: dense series inside the validity, ending at min(as_of_date, valid_to).
    consumption = inputs.consumption
    if consumption.start_date < product.valid_from:
        raise InvalidInputError("consumption.start_date", "must be on or after product.valid_from")
    if consumption.quantities:
        expected_end = as_of if product.valid_to is None else min(as_of, product.valid_to)
        last_day = consumption.start_date + _ONE_DAY * (len(consumption.quantities) - 1)
        if last_day != expected_end:
            raise InvalidInputError("consumption.quantities", "must end on min(as_of_date, product.valid_to)")

    # (g) forecast anchored on horizon_start (DT-048).
    if inputs.forecast is not None and inputs.forecast.start_date != as_of + _ONE_DAY:
        raise InvalidInputError("forecast.start_date", "must equal as_of_date + 1 day")

    # (h) policy set and V1 values (DT-031; B3 fixes z = 33/20).
    policy = inputs.policy
    if policy.policy_set != POLICY_SET_V1:
        raise InvalidInputError("policy.policy_set", f"must be {POLICY_SET_V1}")
    for name in ("r", "z", "n", "n_min", "lt_max"):
        value = getattr(policy, name)
        if value is not None and to_fraction(value) != to_fraction(getattr(V1_PROVISIONAL_PARAMETERS, name)):
            raise InvalidInputError(f"policy.{name}", "must equal the V1_PROVISIONAL value")
