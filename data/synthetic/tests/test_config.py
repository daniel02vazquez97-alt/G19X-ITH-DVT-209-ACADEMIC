"""Tests for Component 1: ``DatasetConfig``.

Run from the repository root::

    python3 -m unittest discover -s data/synthetic/tests -t .

Uses the standard library ``unittest`` so the generator needs no test dependency beyond
PyYAML (see `docs/13-testing.md`: no unnecessary dependencies, deterministic tests).

Scope: only the configuration contract. There is no dataset yet, so there is nothing else
to test.
"""

from __future__ import annotations

import datetime as _dt
import tempfile
import unittest
from pathlib import Path

import yaml

from data.synthetic.config.config import (
    DEFAULT_CONFIG_PATH,
    ConfigError,
    DatasetConfig,
    Scenario,
    load_config,
)

VALID_CONFIG: dict = {
    "seed": 20260913,
    "period": {"start_date": "2023-01-01", "end_date": "2026-01-01"},
    "scale": {
        "product_count": 100,
        "supplier_count": 10,
        "category_count": 10,
        "location_count": 1,
    },
    "scenarios": {"required": [s.value for s in Scenario]},
}


def config_without(*keys: str) -> dict:
    """Deep copy of VALID_CONFIG with the given top-level keys removed."""
    return {k: v for k, v in _deep_copy(VALID_CONFIG).items() if k not in keys}


def _deep_copy(value):
    if isinstance(value, dict):
        return {k: _deep_copy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_deep_copy(v) for v in value]
    return value


def write_yaml(directory: Path, payload, name: str = "config.yaml") -> Path:
    path = directory / name
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


class ValidConfigTests(unittest.TestCase):
    """A valid configuration loads correctly."""

    def test_valid_mapping_loads(self):
        config = DatasetConfig.from_mapping(_deep_copy(VALID_CONFIG))

        self.assertEqual(config.seed, 20260913)
        self.assertEqual(config.period.start_date, _dt.date(2023, 1, 1))
        self.assertEqual(config.period.end_date, _dt.date(2026, 1, 1))
        self.assertEqual(config.scale.product_count, 100)
        self.assertEqual(config.scale.supplier_count, 10)
        self.assertEqual(config.scale.category_count, 10)
        self.assertEqual(config.scale.location_count, 1)
        self.assertEqual(len(config.required_scenarios), 16)

    def test_shipped_config_file_loads(self):
        """The configuration committed to the repository is itself valid."""
        config = load_config(DEFAULT_CONFIG_PATH)

        self.assertEqual(config.seed, 20260913)
        self.assertEqual(config.period.start_date, _dt.date(2023, 1, 1))
        self.assertEqual(config.period.end_date, _dt.date(2026, 1, 1))
        self.assertEqual(config.scale.product_count, 100)
        self.assertEqual(config.scale.location_count, 1)
        self.assertEqual(set(config.required_scenarios), set(Scenario))

    def test_load_config_from_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_yaml(Path(tmp), _deep_copy(VALID_CONFIG))
            config = load_config(path)
        self.assertEqual(config.seed, 20260913)

    def test_period_days(self):
        # The expected value is a literal, not the same subtraction the code performs:
        # 2023 and 2025 have 365 days, 2024 has 366. 365 + 366 + 365 = 1096.
        config = DatasetConfig.from_mapping(_deep_copy(VALID_CONFIG))
        self.assertEqual(config.period.days, 1096)

    def test_config_is_frozen(self):
        config = DatasetConfig.from_mapping(_deep_copy(VALID_CONFIG))
        with self.assertRaises(Exception):
            config.seed = 1  # type: ignore[misc]

    def test_unquoted_dates_are_accepted(self):
        """PyYAML parses an unquoted ISO date as datetime.date; both forms must work."""
        raw = _deep_copy(VALID_CONFIG)
        raw["period"] = {
            "start_date": _dt.date(2023, 1, 1),
            "end_date": _dt.date(2026, 1, 1),
        }
        config = DatasetConfig.from_mapping(raw)
        self.assertEqual(config.period.start_date, _dt.date(2023, 1, 1))


class InvalidDateTests(unittest.TestCase):
    """The period must be a strictly increasing interval."""

    def test_start_equal_to_end_is_rejected(self):
        raw = _deep_copy(VALID_CONFIG)
        raw["period"]["end_date"] = raw["period"]["start_date"]
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertIn("strictly earlier", str(ctx.exception))

    def test_start_after_end_is_rejected(self):
        raw = _deep_copy(VALID_CONFIG)
        raw["period"] = {"start_date": "2026-01-01", "end_date": "2023-01-01"}
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertIn("strictly earlier", str(ctx.exception))

    def test_malformed_date_is_rejected(self):
        raw = _deep_copy(VALID_CONFIG)
        raw["period"]["start_date"] = "01/01/2023"
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertIn("period.start_date", str(ctx.exception))


class InvalidScaleTests(unittest.TestCase):
    """Structural counts must be positive integers."""

    SCALE_KEYS = (
        "product_count",
        "supplier_count",
        "category_count",
        "location_count",
    )

    def test_zero_is_rejected_for_every_count(self):
        for key in self.SCALE_KEYS:
            with self.subTest(key=key):
                raw = _deep_copy(VALID_CONFIG)
                raw["scale"][key] = 0
                with self.assertRaises(ConfigError) as ctx:
                    DatasetConfig.from_mapping(raw)
                self.assertIn(f"scale.{key}", str(ctx.exception))
                self.assertIn("positive integer", str(ctx.exception))

    def test_negative_is_rejected_for_every_count(self):
        for key in self.SCALE_KEYS:
            with self.subTest(key=key):
                raw = _deep_copy(VALID_CONFIG)
                raw["scale"][key] = -1
                with self.assertRaises(ConfigError) as ctx:
                    DatasetConfig.from_mapping(raw)
                self.assertIn(f"scale.{key}", str(ctx.exception))

    def test_non_integer_count_is_rejected(self):
        raw = _deep_copy(VALID_CONFIG)
        raw["scale"]["product_count"] = 10.5
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertIn("must be an integer", str(ctx.exception))

    def test_boolean_is_not_accepted_as_a_count(self):
        """In Python ``True == 1``; a boolean must not slip through as a count."""
        raw = _deep_copy(VALID_CONFIG)
        raw["scale"]["product_count"] = True
        with self.assertRaises(ConfigError):
            DatasetConfig.from_mapping(raw)

    def test_every_wrongly_typed_count_is_reported(self):
        """``ConfigError`` carries every problem found, not only the first one."""
        raw = _deep_copy(VALID_CONFIG)
        raw["scale"]["product_count"] = 10.5
        raw["scale"]["supplier_count"] = "ten"
        raw["scale"]["category_count"] = None
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        message = str(ctx.exception)
        for key in ("product_count", "supplier_count", "category_count"):
            with self.subTest(key=key):
                self.assertIn(f"scale.{key}", message)
        self.assertEqual(
            len([p for p in ctx.exception.problems if p.startswith("scale.")]), 3
        )


class UnknownScenarioTests(unittest.TestCase):
    """Only members of the Scenario enumeration are accepted."""

    def test_unknown_scenario_is_rejected(self):
        raw = _deep_copy(VALID_CONFIG)
        raw["scenarios"]["required"].append("NEGATIVE_LEAD_TIME")
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertIn("unknown scenario", str(ctx.exception))
        self.assertIn("NEGATIVE_LEAD_TIME", str(ctx.exception))

    def test_misspelled_scenario_is_rejected(self):
        raw = _deep_copy(VALID_CONFIG)
        raw["scenarios"]["required"] = ["HIGH_ROTATION", "STOCK_OUT"]
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertIn("STOCK_OUT", str(ctx.exception))

    def test_lowercase_scenario_is_rejected(self):
        raw = _deep_copy(VALID_CONFIG)
        raw["scenarios"]["required"] = ["high_rotation"]
        with self.assertRaises(ConfigError):
            DatasetConfig.from_mapping(raw)

    def test_empty_scenario_list_is_rejected(self):
        raw = _deep_copy(VALID_CONFIG)
        raw["scenarios"]["required"] = []
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertIn("at least one scenario", str(ctx.exception))

    def test_duplicate_scenario_is_rejected(self):
        raw = _deep_copy(VALID_CONFIG)
        raw["scenarios"]["required"] = ["HIGH_ROTATION", "HIGH_ROTATION"]
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertIn("duplicate", str(ctx.exception))


class ScenarioSetTests(unittest.TestCase):
    """The enumeration is a closed set of exactly sixteen Level A generation axes (`DT-023`)."""

    EXPECTED = (
        "HIGH_ROTATION",
        "LOW_ROTATION",
        "STABLE_DEMAND",
        "GROWING_DEMAND",
        "DECLINING_DEMAND",
        "SEASONAL_DEMAND",
        "INTERMITTENT_DEMAND",
        "ERRATIC_DEMAND",
        "STOCKOUT",
        "OVERSTOCK",
        "LOW_INVENTORY",
        "RELIABLE_SUPPLIER",
        "DELAYED_SUPPLIER",
        "PARTIAL_DELIVERY",
        "MULTIPLE_LEAD_TIMES",
        "IN_TRANSIT",
    )

    def test_enumeration_has_exactly_sixteen_members(self):
        self.assertEqual(len(Scenario), 16)

    def test_enumeration_contains_exactly_the_expected_values(self):
        self.assertEqual({s.value for s in Scenario}, set(self.EXPECTED))

    def test_the_fourteen_original_axes_are_preserved(self):
        """Adding two axes must not remove, rename or merge any of the original fourteen.

        The fourteen are written out here rather than derived from ``EXPECTED``: deriving
        them would make this test agree with the enumeration by construction, which is
        exactly what it is supposed to check independently.
        """
        original_fourteen = (
            "HIGH_ROTATION",
            "LOW_ROTATION",
            "STABLE_DEMAND",
            "GROWING_DEMAND",
            "DECLINING_DEMAND",
            "SEASONAL_DEMAND",
            "INTERMITTENT_DEMAND",
            "ERRATIC_DEMAND",
            "STOCKOUT",
            "OVERSTOCK",
            "RELIABLE_SUPPLIER",
            "DELAYED_SUPPLIER",
            "MULTIPLE_LEAD_TIMES",
            "IN_TRANSIT",
        )
        self.assertEqual(len(original_fourteen), 14)
        names = {s.name for s in Scenario}
        for value in original_fourteen:
            with self.subTest(scenario=value):
                self.assertIn(value, names)

    def test_the_addition_is_exactly_two_axes(self):
        """The enumeration grew from fourteen to sixteen: no third value slipped in."""
        added = {s.name for s in Scenario} - {
            "HIGH_ROTATION",
            "LOW_ROTATION",
            "STABLE_DEMAND",
            "GROWING_DEMAND",
            "DECLINING_DEMAND",
            "SEASONAL_DEMAND",
            "INTERMITTENT_DEMAND",
            "ERRATIC_DEMAND",
            "STOCKOUT",
            "OVERSTOCK",
            "RELIABLE_SUPPLIER",
            "DELAYED_SUPPLIER",
            "MULTIPLE_LEAD_TIMES",
            "IN_TRANSIT",
        }
        self.assertEqual(added, {"LOW_INVENTORY", "PARTIAL_DELIVERY"})

    def test_parsed_scenarios_are_enum_members_not_strings(self):
        """``Scenario`` is a ``str`` enum, so equality alone would also accept plain
        strings. The parsed values must be genuine members."""
        config = load_config(DEFAULT_CONFIG_PATH)
        for value in config.required_scenarios:
            with self.subTest(scenario=value):
                self.assertIsInstance(value, Scenario)

    def test_low_inventory_is_accepted(self):
        raw = _deep_copy(VALID_CONFIG)
        raw["scenarios"]["required"] = ["LOW_INVENTORY"]
        config = DatasetConfig.from_mapping(raw)
        self.assertEqual(config.required_scenarios, (Scenario.LOW_INVENTORY,))

    def test_partial_delivery_is_accepted(self):
        raw = _deep_copy(VALID_CONFIG)
        raw["scenarios"]["required"] = ["PARTIAL_DELIVERY"]
        config = DatasetConfig.from_mapping(raw)
        self.assertEqual(config.required_scenarios, (Scenario.PARTIAL_DELIVERY,))

    def test_both_new_axes_appear_after_loading_the_yaml_file(self):
        config = load_config(DEFAULT_CONFIG_PATH)
        self.assertIn(Scenario.LOW_INVENTORY, config.required_scenarios)
        self.assertIn(Scenario.PARTIAL_DELIVERY, config.required_scenarios)
        self.assertEqual(len(config.required_scenarios), 16)

    def test_new_axes_survive_normalisation_round_trip(self):
        config = load_config(DEFAULT_CONFIG_PATH)
        required = config.to_dict()["scenarios"]["required"]
        self.assertIn("LOW_INVENTORY", required)
        self.assertIn("PARTIAL_DELIVERY", required)
        self.assertEqual(config, DatasetConfig.from_mapping(config.to_dict()))

    def test_the_set_stays_closed_after_the_addition(self):
        """Adding two axes must not open the enumeration to arbitrary values."""
        for unknown in (
            "TRANSIT_EFFECTIVE_INSUFFICIENT",  # Level C — must not be an axis (DT-023)
            "CENSORED_DEMAND",                 # Level C
            "MOQ",                             # Level B — attribute of ProductSupplier
            "PREFERRED_SUPPLIER",              # Level B
            "LOW_INVENTORY_LEVEL",             # near-miss of a valid value
            "PARTIAL_DELIVERIES",              # near-miss of a valid value
        ):
            with self.subTest(scenario=unknown):
                raw = _deep_copy(VALID_CONFIG)
                raw["scenarios"]["required"] = ["HIGH_ROTATION", unknown]
                with self.assertRaises(ConfigError) as ctx:
                    DatasetConfig.from_mapping(raw)
                self.assertIn("unknown scenario", str(ctx.exception))
                self.assertIn(unknown, str(ctx.exception))

    def test_axes_combine_freely_in_a_coverage_list(self):
        """Scenarios are not mutually exclusive, and the two new axes are no exception.

        This only checks that `DatasetConfig` accepts such a list. Whether a single SKU may
        carry several axes at once is a property of the scenario assignment component
        (Component 7) and is not tested here.
        """
        for combination in (
            ["HIGH_ROTATION", "SEASONAL_DEMAND", "STOCKOUT", "DELAYED_SUPPLIER", "IN_TRANSIT"],
            [
                "HIGH_ROTATION",
                "SEASONAL_DEMAND",
                "LOW_INVENTORY",
                "DELAYED_SUPPLIER",
                "PARTIAL_DELIVERY",
                "IN_TRANSIT",
            ],
        ):
            with self.subTest(combination=combination):
                raw = _deep_copy(VALID_CONFIG)
                raw["scenarios"]["required"] = list(combination)
                config = DatasetConfig.from_mapping(raw)
                self.assertEqual(len(config.required_scenarios), len(combination))


class DirectConstructionTests(unittest.TestCase):
    """``validate()`` must enforce the same invariants as ``from_mapping()``.

    A `DatasetConfig` can be built directly, bypassing the parser. If `validate()` were
    weaker than the parser, an object could pass validation and still produce a `to_dict()`
    that `from_mapping()` rejects — the round trip promised by the class docstring.
    """

    def _config(self, scenarios):
        base = load_config(DEFAULT_CONFIG_PATH)
        return DatasetConfig(
            seed=base.seed,
            period=base.period,
            scale=base.scale,
            required_scenarios=scenarios,
        )

    def test_required_scenarios_has_no_default(self):
        """Omitting the field would build an object that `validate()` rejects."""
        base = load_config(DEFAULT_CONFIG_PATH)
        with self.assertRaises(TypeError):
            DatasetConfig(seed=base.seed, period=base.period, scale=base.scale)

    def test_validate_rejects_an_empty_scenario_tuple(self):
        with self.assertRaises(ConfigError) as ctx:
            self._config(()).validate()
        self.assertIn("at least one scenario", str(ctx.exception))

    def test_validate_rejects_duplicates(self):
        with self.assertRaises(ConfigError) as ctx:
            self._config((Scenario.STOCKOUT, Scenario.STOCKOUT)).validate()
        self.assertIn("duplicate", str(ctx.exception))

    def test_validate_rejects_a_non_canonical_order(self):
        with self.assertRaises(ConfigError) as ctx:
            self._config((Scenario.IN_TRANSIT, Scenario.HIGH_ROTATION)).validate()
        self.assertIn("canonical order", str(ctx.exception))

    def test_validate_accepts_the_canonical_order(self):
        config = self._config((Scenario.HIGH_ROTATION, Scenario.IN_TRANSIT))
        self.assertIs(config.validate(), config)

    def test_a_validated_object_round_trips_through_from_mapping(self):
        """Whatever `validate()` accepts, `from_mapping()` must accept too."""
        config = self._config(
            (Scenario.HIGH_ROTATION, Scenario.LOW_INVENTORY, Scenario.IN_TRANSIT)
        ).validate()
        self.assertEqual(DatasetConfig.from_mapping(config.to_dict()), config)


class MissingParameterTests(unittest.TestCase):
    """A missing mandatory parameter must fail with a clear message."""

    def test_each_missing_top_level_key_is_reported(self):
        for key in ("seed", "period", "scale", "scenarios"):
            with self.subTest(key=key):
                with self.assertRaises(ConfigError) as ctx:
                    DatasetConfig.from_mapping(config_without(key))
                message = str(ctx.exception)
                self.assertIn("missing required key", message)
                self.assertIn(key, message)

    def test_missing_period_key_is_reported(self):
        raw = _deep_copy(VALID_CONFIG)
        del raw["period"]["end_date"]
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertIn("period is missing key", str(ctx.exception))
        self.assertIn("end_date", str(ctx.exception))

    def test_missing_scale_key_is_reported(self):
        raw = _deep_copy(VALID_CONFIG)
        del raw["scale"]["supplier_count"]
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertIn("scale is missing key", str(ctx.exception))
        self.assertIn("supplier_count", str(ctx.exception))

    def test_missing_scenarios_required_is_reported(self):
        raw = _deep_copy(VALID_CONFIG)
        raw["scenarios"] = {}
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertIn("scenarios is missing key", str(ctx.exception))

    def test_all_problems_are_reported_together(self):
        """A wrong configuration is corrected in one pass, not one error at a time."""
        raw = config_without("seed")
        raw["scale"]["product_count"] = 0
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertGreaterEqual(len(ctx.exception.problems), 2)

    def test_unknown_top_level_key_is_rejected(self):
        """A typo in a key must not be silently ignored."""
        raw = _deep_copy(VALID_CONFIG)
        raw["service_level"] = 0.95
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertIn("unknown key", str(ctx.exception))
        self.assertIn("service_level", str(ctx.exception))

    def test_empty_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.yaml"
            path.write_text("", encoding="utf-8")
            with self.assertRaises(ConfigError) as ctx:
                load_config(path)
            self.assertIn("empty", str(ctx.exception))

    def test_missing_file_is_reported(self):
        with self.assertRaises(FileNotFoundError):
            load_config(Path("/nonexistent/dataset_config.yaml"))

    def test_invalid_yaml_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.yaml"
            path.write_text("seed: [unclosed\n", encoding="utf-8")
            with self.assertRaises(ConfigError) as ctx:
                load_config(path)
            self.assertIn("not valid YAML", str(ctx.exception))


class InvalidSeedTests(unittest.TestCase):
    """The seed must exist and be usable for reproducible generation."""

    def test_non_integer_seed_is_rejected(self):
        raw = _deep_copy(VALID_CONFIG)
        raw["seed"] = "20260913"
        with self.assertRaises(ConfigError) as ctx:
            DatasetConfig.from_mapping(raw)
        self.assertIn("seed must be an integer", str(ctx.exception))

    def test_negative_seed_is_rejected(self):
        config = DatasetConfig.from_mapping(_deep_copy(VALID_CONFIG))
        invalid = DatasetConfig(
            seed=-1,
            period=config.period,
            scale=config.scale,
            required_scenarios=config.required_scenarios,
        )
        with self.assertRaises(ConfigError) as ctx:
            invalid.validate()
        self.assertIn("zero or positive", str(ctx.exception))


class ReproducibilityTests(unittest.TestCase):
    """The same configuration must yield the same normalised object."""

    def test_two_loads_produce_equal_objects(self):
        first = DatasetConfig.from_mapping(_deep_copy(VALID_CONFIG))
        second = DatasetConfig.from_mapping(_deep_copy(VALID_CONFIG))
        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_two_loads_from_file_produce_equal_objects(self):
        first = load_config(DEFAULT_CONFIG_PATH)
        second = load_config(DEFAULT_CONFIG_PATH)
        self.assertEqual(first, second)

    def test_scenario_order_in_the_file_does_not_matter(self):
        raw = _deep_copy(VALID_CONFIG)
        reference = DatasetConfig.from_mapping(raw)

        shuffled = _deep_copy(VALID_CONFIG)
        shuffled["scenarios"]["required"] = list(
            reversed(shuffled["scenarios"]["required"])
        )
        other = DatasetConfig.from_mapping(shuffled)

        self.assertEqual(reference, other)
        self.assertEqual(reference.required_scenarios, other.required_scenarios)

    def test_date_format_does_not_change_the_object(self):
        quoted = DatasetConfig.from_mapping(_deep_copy(VALID_CONFIG))

        unquoted = _deep_copy(VALID_CONFIG)
        unquoted["period"] = {
            "start_date": _dt.date(2023, 1, 1),
            "end_date": _dt.date(2026, 1, 1),
        }
        self.assertEqual(quoted, DatasetConfig.from_mapping(unquoted))

    def test_normalised_dict_round_trips(self):
        config = load_config(DEFAULT_CONFIG_PATH)
        rebuilt = DatasetConfig.from_mapping(config.to_dict())
        self.assertEqual(config, rebuilt)


class NoBusinessParametersTests(unittest.TestCase):
    """The configuration contract must not carry business decisions.

    These parameters are pending business definitions (`knowledge/business-rules.md` §3) and
    belong to the supply engine. A default value here would turn a pending decision into an
    invented fact, which this test exists to prevent.
    """

    FORBIDDEN = (
        "service_level",
        "z_score",
        "safety_stock",
        "reorder_point",
        "review_period",
        "target_coverage",
        "shortage_cost",
        "holding_cost",
        "supplier_score",
        "risk_threshold",
        "moq",
        "order_multiple",
        "lead_time_days",
    )

    def test_config_object_exposes_no_business_parameters(self):
        config = load_config(DEFAULT_CONFIG_PATH)
        attributes = {a.lower() for a in dir(config) if not a.startswith("_")}
        for name in self.FORBIDDEN:
            with self.subTest(parameter=name):
                self.assertNotIn(name, attributes)

    def test_config_file_declares_no_business_parameters(self):
        text = DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")
        # Ignore comment lines: the file explains in prose why these are excluded.
        keys = "\n".join(
            line for line in text.splitlines() if not line.lstrip().startswith("#")
        ).lower()
        for name in self.FORBIDDEN:
            with self.subTest(parameter=name):
                self.assertNotIn(name, keys)


if __name__ == "__main__":
    unittest.main()
