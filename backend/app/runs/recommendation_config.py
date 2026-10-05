"""Identity and representation of a recommendation execution (U4, `DT-059`, `DT-062`).

Standard library only (plus the public constants of U1 and U3), so it is tested without PostgreSQL:

* `exact_text` / `numeric_value` — the representation of `docs/06` §16.13.3: exact whenever possible,
  ``"p/q"`` for repeating rationals in JSON, 28 significant digits ``ROUND_HALF_EVEN`` from the exact
  value for ``numeric`` columns; never ``float``.
* `policy_snapshot` — U1's ``V1_PROVISIONAL_PARAMETERS`` as persisted; U4 never redefines them.
* `input_document` / `input_sha256` — the canonical, normalized JSON of an `EvaluationInput`.
* `run_configuration` / `config_sha256` / `lock_key` — the logical identity of an execution.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from enum import Enum
from fractions import Fraction
from typing import Any

from app.supply_engine import ENGINE_VERSION, V1_PROVISIONAL_PARAMETERS, Breakdown, EvaluationInput, PolicyParameters

from .config import canonical_json
from .config import config_sha256 as forecast_config_sha256

RUN_TYPE = "RECOMMENDATION"
#: Version of the reading rules of `docs/06` §16.13.2; a change that alters any input bumps it.
INPUT_RULES_VERSION = "1.0.0"
#: Population of `DT-059`/US-046: every product × location, without prior filtering.
CATALOG_POLICY = "ALL_PRODUCT_LOCATIONS"
#: Forecast selection of `DT-061`.
FORECAST_SELECTION = "SAME_AS_OF_SAME_LOAD_CURRENT_FORECAST_CONFIG"
SIGNIFICANT_DIGITS = 28
ROUNDING = "ROUND_HALF_EVEN"

__all__ = [
    "CATALOG_POLICY",
    "FORECAST_SELECTION",
    "INPUT_RULES_VERSION",
    "ROUNDING",
    "RUN_TYPE",
    "SIGNIFICANT_DIGITS",
    "breakdown_document",
    "config_sha256",
    "exact_text",
    "forecast_config_sha256",
    "input_document",
    "input_sha256",
    "lock_key",
    "numeric_value",
    "policy_snapshot",
    "run_configuration",
]


# --------------------------------------------------------------------------------------------
# Numbers
# --------------------------------------------------------------------------------------------


def _finite_decimal(value: Fraction) -> Decimal | None:
    """The exact decimal of ``value`` if its expansion is finite (denominator 2^a·5^b), else ``None``."""
    den = value.denominator
    twos = fives = 0
    while den % 2 == 0:
        den //= 2
        twos += 1
    while den % 5 == 0:
        den //= 5
        fives += 1
    if den != 1:
        return None
    scale = max(twos, fives)
    digits = value.numerator * 10**scale // value.denominator  # exact: the division has no remainder
    return Decimal(digits).scaleb(-scale)


def _plain(value: Decimal) -> str:
    """Exact decimal text without exponent and without trailing zeros (``"12.5"``, ``"0"``, ``"-3"``)."""
    text = format(value.normalize(), "f")
    return "0" if text in ("-0", "0") else text


def exact_text(value: int | Fraction | Decimal) -> str:
    """JSON text of an EXACT number: ``int`` and finite rationals as decimals, others as ``"p/q"``.

    A ``Decimal`` here is an exact input (``numeric`` from the database), normalized so that equal
    values have one text. Approximate values reported by U1 never go through this function.
    """
    if isinstance(value, bool) or not isinstance(value, (int, Fraction, Decimal)):
        raise TypeError(f"not an exact number: {type(value).__name__}")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("not a finite number")
        return _plain(value)
    finite = _finite_decimal(value)
    if finite is not None:
        return _plain(finite)
    return f"{value.numerator}/{value.denominator}"


def numeric_value(value: int | Fraction | Decimal | None) -> Decimal | None:
    """Value for a ``numeric`` column (`docs/06` §16.13.3).

    ``int`` and finite rationals: exact. A repeating rational: 28 significant digits ``ROUND_HALF_EVEN``,
    correctly rounded from the exact value (one decimal division in a 28-digit context). A ``Decimal``
    reported by U1 (already 28 significant digits from its exact value): as is, never re-rounded.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("bool is not a number")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if not isinstance(value, Fraction):
        raise TypeError(f"not an exact number: {type(value).__name__}")
    finite = _finite_decimal(value)
    if finite is not None:
        return finite
    with localcontext() as context:
        context.prec = SIGNIFICANT_DIGITS
        context.rounding = ROUND_HALF_EVEN
        return Decimal(value.numerator) / Decimal(value.denominator)


# --------------------------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------------------------


def _value(value: Any) -> Any:
    """Canonical JSON value of an exact input or output term."""
    if isinstance(value, Enum):
        return str(value.value)
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, (int, Fraction, Decimal)):
        return exact_text(value)
    if dataclasses.is_dataclass(value):
        return {f.name: _value(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, (tuple, list)):
        return [_value(v) for v in value]
    raise TypeError(f"cannot represent {type(value).__name__}")


def policy_snapshot(policy: PolicyParameters = V1_PROVISIONAL_PARAMETERS) -> dict[str, Any]:
    """The policy as persisted: ``{"policy_set": "V1_PROVISIONAL", "R": 7, "z": "1.65", …}`` (`DT-062`)."""
    return {
        "policy_set": policy.policy_set,
        "R": policy.r,
        "z": None if policy.z is None else exact_text(policy.z),
        "N": policy.n,
        "N_MIN": policy.n_min,
        "LT_MAX": policy.lt_max,
    }


def breakdown_document(breakdown: Breakdown) -> tuple[dict[str, Any], list[str]]:
    """Every field of U1's breakdown, with its name, and the names of the approximate terms.

    In U1's output a ``Decimal`` means approximate (28 significant digits, `DT-051`): it is kept as U1
    reported it and listed in ``approximate_terms``; the B3 components ``s1``, ``s2``, ``a``, ``b``,
    ``d`` and ``p`` stay exact, so ``x = P + √B/D`` can be rebuilt.
    """
    document: dict[str, Any] = {}
    approximate: list[str] = []
    for field in dataclasses.fields(breakdown):
        value = getattr(breakdown, field.name)
        if isinstance(value, Decimal):
            document[field.name] = str(value)
            approximate.append(field.name)
        else:
            document[field.name] = _value(value)
    return document, approximate


def input_document(inputs: EvaluationInput, model: dict[str, str] | None) -> dict[str, Any]:
    """Canonical, normalized JSON document of an `EvaluationInput` used for persistence (`DT-059`).

    Collections in canonical order, whatever the input order. Dataset identifiers (product, supplier,
    order, line) are kept. The technical ids generated by U3, ``forecast_id`` and ``model_version``, are
    replaced by the semantic identity of the model ``{name, version}``. No ``generated_at`` and no
    execution ids.
    """
    forecast = inputs.forecast
    if forecast is not None and model is None:
        raise ValueError("a forecast needs the semantic identity of its model")
    return {
        "as_of_date": inputs.as_of_date.isoformat(),
        "product": _value(inputs.product),
        "supplier_relations": [_value(r) for r in sorted(inputs.supplier_relations, key=lambda r: r.supplier_id)],
        "inventory": _value(inputs.inventory),
        "open_lines": [
            _value(line) for line in sorted(inputs.open_lines, key=lambda line: (line.purchase_order_id, line.item_id))
        ],
        "lead_time_observations": [
            [exact_text(o.supplier_id), o.issued_on.isoformat(), o.completed_on.isoformat()]
            for o in sorted(inputs.lead_time_observations, key=lambda o: (o.supplier_id, o.issued_on, o.completed_on))
        ],
        "consumption": _value(inputs.consumption),
        "forecast": None
        if forecast is None
        else {
            "start_date": forecast.start_date.isoformat(),
            "weekly_quantities": [exact_text(q) for q in forecast.weekly_quantities],
            "model": {"name": model["name"], "version": model["version"]},
            "method_used": str(forecast.method_used.value),
        },
        "policy": policy_snapshot(inputs.policy),
    }


def input_sha256(inputs: EvaluationInput, model: dict[str, str] | None) -> str:
    """SHA-256 of `input_document`: verifies the semantic inputs; it does not rebuild them by itself."""
    return hashlib.sha256(canonical_json(input_document(inputs, model)).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------------
# Execution identity
# --------------------------------------------------------------------------------------------


def run_configuration(
    *,
    engine_version: str = ENGINE_VERSION,
    policy: PolicyParameters = V1_PROVISIONAL_PARAMETERS,
    forecast_config: str | None = None,
    input_rules_version: str = INPUT_RULES_VERSION,
) -> dict[str, Any]:
    """Everything that determines the output of a recommendation execution (`DT-062` point 3)."""
    return {
        "run_type": RUN_TYPE,
        "engine_version": engine_version,
        "policy": policy_snapshot(policy),
        "forecast_config_sha256": forecast_config_sha256() if forecast_config is None else forecast_config,
        "forecast_selection": FORECAST_SELECTION,
        "catalog_policy": CATALOG_POLICY,
        "input_rules_version": input_rules_version,
        "representation": {"significant_digits": SIGNIFICANT_DIGITS, "rounding": ROUNDING},
    }


def config_sha256(configuration: dict[str, Any] | None = None) -> str:
    text = canonical_json(run_configuration() if configuration is None else configuration)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def lock_key(as_of_date: _dt.date, data_load_id: int, sha256: str) -> int:
    """Advisory-lock key of one logical recommendation execution (signed 64-bit)."""
    identity = canonical_json([RUN_TYPE, as_of_date.isoformat(), data_load_id, sha256])
    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)
