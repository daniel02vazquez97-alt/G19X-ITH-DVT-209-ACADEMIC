"""Configuration contract for the synthetic dataset generator.

Phase 1 - Data, Component 1: ``DatasetConfig``.

Pipeline::

    dataset_config.yaml -> load_config() -> DatasetConfig -> validate()

``DatasetConfig`` is the single object every later generator component receives. It carries
only what is needed to produce reproducible synthetic data:

* technical parameters (seed, time window),
* structural parameters (catalogue size),
* scenario coverage (which generation axes the dataset must exercise — see ``Scenario``).

It deliberately carries **no business parameters**. Service level, safety stock, reorder
point, review period, target coverage, shortage or holding costs, MOQ and risk thresholds
are business decisions that are still undefined (``knowledge/business-rules.md`` section 3)
and belong to the supply engine, not to the data generator. Adding a default value here
would turn a pending business decision into an invented fact.

Scenarios are **coverage requirements**, not business rules, and they are not mutually
exclusive: one SKU may represent several at once. They are Level A generation axes, not the
full list of situations the dataset must contain — see ``Scenario`` and `DT-023`.

Only dependency: PyYAML, required to parse the configuration file. Validation uses the
standard library so that the generator stays independent from the API stack.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

import yaml

__all__ = [
    "ConfigError",
    "Scenario",
    "Period",
    "Scale",
    "DatasetConfig",
    "load_config",
    "DEFAULT_CONFIG_PATH",
]

DEFAULT_CONFIG_PATH = Path(__file__).with_name("dataset_config.yaml")


class ConfigError(ValueError):
    """Raised when the configuration is missing, malformed or invalid.

    Carries every problem found rather than only the first one, so a wrong configuration is
    corrected in a single pass instead of one error at a time.
    """

    def __init__(self, problems: list[str]) -> None:
        self.problems = list(problems)
        joined = "\n".join(f"  - {p}" for p in self.problems)
        super().__init__(f"Invalid dataset configuration:\n{joined}")


class Scenario(str, Enum):
    """Level A generation axes: behaviours the generator produces deliberately.

    This enumeration is the closed set of valid values: anything else in the configuration
    is rejected. Each member is a coverage requirement for the generated data, **not** a
    business parameter and **not** an inventory rule.

    **These are not the 26 situations of `knowledge/dataset-specification.md` §25**, and they
    are not meant to be (`DT-023`). Those 26 split across three levels:

    * **Level A — generation axes.** This enum. Behaviours a SKU or a product-supplier
      relationship can be assigned, which the generator controls through configuration.
    * **Level B — attributes and states.** Fields of the data model that must take varied
      values: ``ProductSupplier.moq``, ``order_multiple``, ``is_preferred``,
      ``Product.is_active``, ``PurchaseOrder.status``. They belong to the entities, not here.
    * **Level C — emergent properties.** Situations that arise from combining data and are
      checked by the dataset validator: censored demand, total-vs-effective transit, the
      MOQ/overstock conflict, an inactive product that keeps its history.

    Those 26 situations split 13 / 9 / 4 across the three levels. This enum holds **16**
    values: the 13 Level A situations plus three axes that are not rows of §25 —
    ``HIGH_ROTATION``, ``LOW_ROTATION`` and ``MULTIPLE_LEAD_TIMES`` — which other sections
    back (``MULTIPLE_LEAD_TIMES`` by §13 and §14; the two rotation axes by `docs/02` §8 and
    §10.4, an open discrepancy recorded as `DT-P12`). 26 counts situations of the
    specification and 16 counts members of this enum: the two numbers are not comparable.

    A Level C situation must not become a member of this enum. Labelling it in the generator
    would require fixing a business rule that is still pending — the effective-transit cut-off
    (`DT-P11`), the risk-classification thresholds (`BR-X03`), the discontinued-product rule
    (`BR-P10`), the censored-demand treatment (`DT-011`) — which §3.5, §27 and §37 of the
    specification forbid.
    """

    # Rotation
    HIGH_ROTATION = "HIGH_ROTATION"
    LOW_ROTATION = "LOW_ROTATION"
    # Demand shape
    STABLE_DEMAND = "STABLE_DEMAND"
    GROWING_DEMAND = "GROWING_DEMAND"
    DECLINING_DEMAND = "DECLINING_DEMAND"
    SEASONAL_DEMAND = "SEASONAL_DEMAND"
    INTERMITTENT_DEMAND = "INTERMITTENT_DEMAND"
    ERRATIC_DEMAND = "ERRATIC_DEMAND"
    # Inventory situations
    STOCKOUT = "STOCKOUT"
    OVERSTOCK = "OVERSTOCK"
    LOW_INVENTORY = "LOW_INVENTORY"
    # Supplier behaviour and replenishment
    RELIABLE_SUPPLIER = "RELIABLE_SUPPLIER"
    DELAYED_SUPPLIER = "DELAYED_SUPPLIER"
    PARTIAL_DELIVERY = "PARTIAL_DELIVERY"
    MULTIPLE_LEAD_TIMES = "MULTIPLE_LEAD_TIMES"
    IN_TRANSIT = "IN_TRANSIT"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


# Declaration order above is the canonical order used when normalising the configuration.
_SCENARIO_ORDER = {member: index for index, member in enumerate(Scenario)}

_REQUIRED_TOP_LEVEL_KEYS = ("seed", "period", "scale", "scenarios")
_REQUIRED_PERIOD_KEYS = ("start_date", "end_date")
_REQUIRED_SCALE_KEYS = (
    "product_count",
    "supplier_count",
    "category_count",
    "location_count",
)


@dataclass(frozen=True)
class Period:
    """Time window the synthetic history must span."""

    start_date: _dt.date
    end_date: _dt.date

    @property
    def days(self) -> int:
        """Length of the window in days."""
        return (self.end_date - self.start_date).days

    def to_dict(self) -> dict[str, str]:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }


@dataclass(frozen=True)
class Scale:
    """Size of the synthetic catalogue.

    These are generator settings, not measurements of the real business.
    """

    product_count: int
    supplier_count: int
    category_count: int
    location_count: int

    def to_dict(self) -> dict[str, int]:
        return {
            "product_count": self.product_count,
            "supplier_count": self.supplier_count,
            "category_count": self.category_count,
            "location_count": self.location_count,
        }


@dataclass(frozen=True)
class DatasetConfig:
    """Validated configuration handed to every generator component.

    Instances are frozen and normalised: ``required_scenarios`` is always a tuple in the
    canonical order of :class:`Scenario`, so two runs of the same configuration produce
    equal objects regardless of the order used in the YAML file.
    """

    seed: int
    period: Period
    scale: Scale
    # No default: an empty tuple is not a valid configuration (see _check_scenarios), so
    # allowing the field to be omitted would let an invalid object be constructed silently.
    required_scenarios: tuple[Scenario, ...]

    # -- construction ----------------------------------------------------------------

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "DatasetConfig":
        """Build a validated configuration from a plain mapping.

        Raises:
            ConfigError: if the mapping is missing keys, has unknown keys, or holds values
                that fail validation. All problems are reported together.
        """
        if not isinstance(raw, Mapping):
            raise ConfigError(
                [f"the configuration must be a mapping, got {type(raw).__name__}"]
            )

        problems: list[str] = []

        missing = [k for k in _REQUIRED_TOP_LEVEL_KEYS if k not in raw]
        if missing:
            problems.append(
                "missing required key(s): " + ", ".join(sorted(missing))
            )

        unknown = sorted(set(raw) - set(_REQUIRED_TOP_LEVEL_KEYS))
        if unknown:
            # A silently ignored typo in a key is a defect that surfaces much later, as a
            # dataset that quietly does not match its configuration.
            problems.append(
                "unknown key(s): "
                + ", ".join(unknown)
                + f" (allowed: {', '.join(_REQUIRED_TOP_LEVEL_KEYS)})"
            )

        seed = _parse_seed(raw.get("seed"), problems) if "seed" in raw else None
        period = _parse_period(raw.get("period"), problems) if "period" in raw else None
        scale = _parse_scale(raw.get("scale"), problems) if "scale" in raw else None
        scenarios = (
            _parse_scenarios(raw.get("scenarios"), problems)
            if "scenarios" in raw
            else None
        )

        # Invariants are checked on whatever parsed successfully, so a configuration with
        # several independent mistakes reports them all at once instead of one per run.
        if seed is not None:
            problems.extend(_check_seed(seed))
        if period is not None:
            problems.extend(_check_period(period))
        if scale is not None:
            problems.extend(_check_scale(scale))
        if scenarios is not None:
            problems.extend(_check_scenarios(scenarios))

        if problems:
            raise ConfigError(problems)

        # Every branch above either produced a value or appended a problem, so by this point
        # the four values are present; the assertions make that explicit for type checkers.
        assert seed is not None and period is not None
        assert scale is not None and scenarios is not None

        return cls(
            seed=seed,
            period=period,
            scale=scale,
            required_scenarios=scenarios,
        )

    # -- validation ------------------------------------------------------------------

    def validate(self) -> "DatasetConfig":
        """Check the invariants that survive parsing. Returns ``self`` for chaining.

        Raises:
            ConfigError: if any invariant is violated.
        """
        problems = (
            _check_seed(self.seed)
            + _check_period(self.period)
            + _check_scale(self.scale)
            + _check_scenarios(self.required_scenarios)
        )
        if problems:
            raise ConfigError(problems)
        return self

    # -- normalised representation ---------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Normalised, serialisable form of the configuration.

        Two configurations that mean the same thing produce the same dictionary, whatever
        order or date format the source file used. Later phases can store this alongside a
        generated dataset to record exactly how it was produced.
        """
        return {
            "seed": self.seed,
            "period": self.period.to_dict(),
            "scale": self.scale.to_dict(),
            "scenarios": {
                "required": [s.value for s in self.required_scenarios],
            },
        }


# ---------------------------------------------------------------------------------------
# Invariant checks
#
# One source of truth for the rules: used both while parsing a mapping and by
# DatasetConfig.validate() on an already-built object. Each returns a list of problems
# rather than raising, so several can be combined into a single report.
# ---------------------------------------------------------------------------------------


def _check_seed(seed: Any) -> list[str]:
    if isinstance(seed, bool) or not isinstance(seed, int):
        return [f"seed must be an integer, got {seed!r}"]
    if seed < 0:
        return [f"seed must be zero or positive, got {seed}"]
    return []


def _check_period(period: Period) -> list[str]:
    if period.start_date >= period.end_date:
        return [
            "period.start_date must be strictly earlier than period.end_date "
            f"(got start_date={period.start_date.isoformat()}, "
            f"end_date={period.end_date.isoformat()})"
        ]
    return []


def _check_scale(scale: Scale) -> list[str]:
    problems: list[str] = []
    for name in _REQUIRED_SCALE_KEYS:
        value = getattr(scale, name)
        if isinstance(value, bool) or not isinstance(value, int):
            problems.append(f"scale.{name} must be an integer, got {value!r}")
        elif value <= 0:
            problems.append(f"scale.{name} must be a positive integer, got {value}")
    return problems


def _check_scenarios(scenarios: tuple[Scenario, ...]) -> list[str]:
    problems: list[str] = []
    if not scenarios:
        problems.append("scenarios.required must list at least one scenario")
    invalid = [s for s in scenarios if not isinstance(s, Scenario)]
    if invalid:
        problems.append(
            "scenarios.required contains values that are not members of Scenario: "
            + ", ".join(repr(s) for s in invalid)
        )
    if invalid:
        # The two checks below assume genuine Scenario members; reporting them on top of
        # the type problem would only add noise.
        return problems

    seen: set[Scenario] = set()
    duplicates: list[str] = []
    for scenario in scenarios:
        if scenario in seen:
            duplicates.append(scenario.value)
        seen.add(scenario)
    if duplicates:
        problems.append(
            "scenarios.required contains duplicate(s): " + ", ".join(sorted(set(duplicates)))
        )

    # The docstring of DatasetConfig promises the tuple is in canonical order. Checking it
    # here keeps validate() and from_mapping() in agreement: an object whose to_dict() is
    # fed back to from_mapping() must survive the round trip.
    canonical = tuple(sorted(seen, key=_SCENARIO_ORDER.__getitem__))
    if not duplicates and scenarios != canonical:
        problems.append(
            "scenarios.required must be in the canonical order of Scenario "
            f"(expected {[s.value for s in canonical]}, "
            f"got {[s.value for s in scenarios]})"
        )
    return problems


# ---------------------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------------------


def _parse_seed(value: Any, problems: list[str]) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        problems.append(f"seed must be an integer, got {value!r}")
        return None
    return value


def _parse_date(value: Any, label: str, problems: list[str]) -> _dt.date | None:
    # PyYAML already turns an unquoted ISO date into datetime.date; both forms are accepted
    # so the file can quote its dates for readability without changing the meaning.
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str):
        try:
            return _dt.date.fromisoformat(value.strip())
        except ValueError:
            problems.append(f"{label} is not a valid ISO date (YYYY-MM-DD): {value!r}")
            return None
    problems.append(f"{label} must be an ISO date string (YYYY-MM-DD), got {value!r}")
    return None


def _parse_period(value: Any, problems: list[str]) -> Period | None:
    if not isinstance(value, Mapping):
        problems.append(f"period must be a mapping, got {type(value).__name__}")
        return None

    missing = [k for k in _REQUIRED_PERIOD_KEYS if k not in value]
    if missing:
        problems.append("period is missing key(s): " + ", ".join(sorted(missing)))

    unknown = sorted(set(value) - set(_REQUIRED_PERIOD_KEYS))
    if unknown:
        problems.append("period has unknown key(s): " + ", ".join(unknown))

    start = (
        _parse_date(value.get("start_date"), "period.start_date", problems)
        if "start_date" in value
        else None
    )
    end = (
        _parse_date(value.get("end_date"), "period.end_date", problems)
        if "end_date" in value
        else None
    )
    if start is None or end is None:
        return None
    return Period(start_date=start, end_date=end)


def _parse_scale(value: Any, problems: list[str]) -> Scale | None:
    if not isinstance(value, Mapping):
        problems.append(f"scale must be a mapping, got {type(value).__name__}")
        return None

    missing = [k for k in _REQUIRED_SCALE_KEYS if k not in value]
    if missing:
        problems.append("scale is missing key(s): " + ", ".join(sorted(missing)))

    unknown = sorted(set(value) - set(_REQUIRED_SCALE_KEYS))
    if unknown:
        problems.append("scale has unknown key(s): " + ", ".join(unknown))

    if missing:
        return None

    # Every key is inspected before returning: a scale with two wrong types must report two
    # problems, not just the first one. Returning early here would contradict ConfigError,
    # which promises to carry every problem found.
    counts: dict[str, int] = {}
    bad_types = False
    for name in _REQUIRED_SCALE_KEYS:
        raw_value = value[name]
        if isinstance(raw_value, bool) or not isinstance(raw_value, int):
            problems.append(f"scale.{name} must be an integer, got {raw_value!r}")
            bad_types = True
            continue
        counts[name] = raw_value

    if bad_types:
        return None
    return Scale(**counts)


def _parse_scenarios(value: Any, problems: list[str]) -> tuple[Scenario, ...] | None:
    if not isinstance(value, Mapping):
        problems.append(f"scenarios must be a mapping, got {type(value).__name__}")
        return None

    if "required" not in value:
        problems.append("scenarios is missing key: required")
        return None

    unknown_keys = sorted(set(value) - {"required"})
    if unknown_keys:
        problems.append("scenarios has unknown key(s): " + ", ".join(unknown_keys))

    raw_list = value["required"]
    if isinstance(raw_list, str) or not isinstance(raw_list, (list, tuple)):
        problems.append(
            f"scenarios.required must be a list of scenario names, got {raw_list!r}"
        )
        return None

    valid_names = {member.value for member in Scenario}
    parsed: list[Scenario] = []
    unknown_scenarios: list[Any] = []
    duplicates: list[str] = []

    for item in raw_list:
        if not isinstance(item, str) or item not in valid_names:
            unknown_scenarios.append(item)
            continue
        member = Scenario(item)
        if member in parsed:
            duplicates.append(item)
            continue
        parsed.append(member)

    if unknown_scenarios:
        problems.append(
            "scenarios.required contains unknown scenario(s): "
            + ", ".join(repr(s) for s in unknown_scenarios)
            + " (valid scenarios: "
            + ", ".join(sorted(valid_names))
            + ")"
        )
    if duplicates:
        problems.append(
            "scenarios.required contains duplicate(s): "
            + ", ".join(sorted(set(duplicates)))
        )

    if unknown_scenarios or duplicates:
        return None

    # Normalise to the canonical order so the object does not depend on file ordering.
    return tuple(sorted(parsed, key=_SCENARIO_ORDER.__getitem__))


# ---------------------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------------------


def load_config(path: str | Path | None = None) -> DatasetConfig:
    """Load, parse and validate the dataset configuration.

    Args:
        path: configuration file. Defaults to ``dataset_config.yaml`` next to this module.

    Returns:
        A validated, normalised :class:`DatasetConfig`.

    Raises:
        FileNotFoundError: if the file does not exist.
        ConfigError: if the file is not valid YAML, is empty, or fails validation.
    """
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        raise FileNotFoundError(f"Dataset configuration file not found: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError([f"{config_path} is not valid YAML: {exc}"]) from exc

    if raw is None:
        raise ConfigError([f"{config_path} is empty"])

    return DatasetConfig.from_mapping(raw)
