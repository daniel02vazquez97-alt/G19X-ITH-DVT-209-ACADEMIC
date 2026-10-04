"""Representation, ``input_sha256`` and ``config_sha256`` of U4 (`DT-059`, `DT-062`), without PostgreSQL."""

from __future__ import annotations

import ast
import dataclasses
import datetime as dt
import hashlib
import json
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import app.runs.recommendation_config as config_module
from app.runs.config import canonical_json
from app.runs.config import config_sha256 as u3_config_sha256
from app.runs.recommendation_config import (
    INPUT_RULES_VERSION,
    breakdown_document,
    config_sha256,
    exact_text,
    input_document,
    input_sha256,
    lock_key,
    numeric_value,
    policy_snapshot,
    run_configuration,
)
from app.runs.recommendation_inputs import build_evaluation_input
from app.supply_engine import ENGINE_VERSION, V1_PROVISIONAL_PARAMETERS, Breakdown

from ._u4_fixtures import A, consumption, forecast, inventory, line, observations, product, relation

MODEL = {"name": "baseline.moving_average", "version": "1.0.0"}


def sample(**overrides: object):
    arguments = {
        "as_of_date": A,
        "product": product(),
        "relations": [relation(9, preferred=False), relation(7)],
        "inventory": inventory("10", "5"),
        "order_lines": observations() + [line(50, 51, status="ISSUED", received="5", ordered="10")],
        "consumption": consumption(60),
        "forecast_rows": forecast("12.500000"),
    }
    arguments.update(overrides)
    return build_evaluation_input(**arguments)


class ExactTextTest(unittest.TestCase):
    def test_integers_finite_and_repeating_rationals(self) -> None:
        self.assertEqual(exact_text(12), "12")
        self.assertEqual(exact_text(Fraction(33, 20)), "1.65")
        self.assertEqual(exact_text(Fraction(270, 7)), "270/7")
        self.assertEqual(exact_text(Fraction(-1, 3)), "-1/3")
        self.assertEqual(exact_text(Fraction(10, 1)), "10")
        self.assertEqual(exact_text(Fraction(0)), "0")

    def test_equal_decimals_have_one_text(self) -> None:
        self.assertEqual(exact_text(Decimal("12.500000")), "12.5")
        self.assertEqual(exact_text(Decimal("1E+2")), "100")
        self.assertEqual(exact_text(Decimal("-0.000")), "0")

    def test_float_and_bool_are_rejected(self) -> None:
        for value in (1.5, True):
            with self.subTest(value), self.assertRaises(TypeError):
                exact_text(value)


class NumericValueTest(unittest.TestCase):
    def test_exact_when_representable(self) -> None:
        self.assertEqual(numeric_value(7), Decimal(7))
        self.assertEqual(str(numeric_value(Fraction(33, 20))), "1.65")
        self.assertEqual(str(numeric_value(Fraction(1, 1024))), "0.0009765625")
        self.assertIsNone(numeric_value(None))

    def test_repeating_rationals_get_28_significant_digits_half_even(self) -> None:
        # Hand computed: 270/7 = 38.571428 571428 571428 571428 57|14… → 28 digits, next digit 1.
        self.assertEqual(str(numeric_value(Fraction(270, 7))), "38.57142857142857142857142857")
        # 2/3 = 0.666…: 28 significant digits, last one rounded up.
        self.assertEqual(str(numeric_value(Fraction(2, 3))), "0.6666666666666666666666666667")
        # Half-even on an exact tie at the 29th digit is impossible for a repeating rational; check
        # that rounding starts from the exact value: 1/3 · 10^-30.
        self.assertEqual(str(numeric_value(Fraction(1, 3 * 10**30))), "3.333333333333333333333333333E-31")

    def test_u1_decimals_are_never_rounded_again(self) -> None:
        approximate = Decimal("1.234567890123456789012345679")
        self.assertIs(numeric_value(approximate), approximate)

    def test_float_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            numeric_value(0.5)


class PolicySnapshotTest(unittest.TestCase):
    def test_exact_snapshot_of_u1_policy(self) -> None:
        self.assertEqual(
            policy_snapshot(),
            {"policy_set": "V1_PROVISIONAL", "R": 7, "z": "1.65", "N": 12, "N_MIN": 3, "LT_MAX": 90},
        )
        self.assertEqual(policy_snapshot(), policy_snapshot(V1_PROVISIONAL_PARAMETERS))
        self.assertNotIn("float", json.dumps(policy_snapshot()))

    def test_u4_does_not_redefine_the_policy(self) -> None:
        # No second copy of the policy in code: no policy-set literal, no policy number, no Fraction(…).
        tree = ast.parse(Path(config_module.__file__).read_text(encoding="utf-8"))
        constants = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)}
        self.assertFalse({"V1_PROVISIONAL", "POLICY_SET_V1", "POLICY_SET_V1_PROVISIONAL"} & constants)
        self.assertFalse({7, 12, 3, 90, 33, 20} & {c for c in constants if type(c) is int})
        calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertNotIn("PolicyParameters", calls)


class BreakdownDocumentTest(unittest.TestCase):
    def test_every_field_and_the_approximate_terms(self) -> None:
        breakdown = Breakdown(
            as_of_date=A,
            horizon_start=A + dt.timedelta(days=1),
            demand_over_horizon=Fraction(270, 7),
            sigma_h=Decimal("3.162277660168379332007603569"),
            b=1089 * 10,
            d=20,
        )
        document, approximate = breakdown_document(breakdown)
        self.assertEqual(list(document), [f.name for f in dataclasses.fields(Breakdown)])
        self.assertEqual(document["demand_over_horizon"], "270/7")
        self.assertEqual(document["sigma_h"], "3.162277660168379332007603569")
        self.assertEqual(document["b"], "10890")
        self.assertIsNone(document["q_final"])
        self.assertEqual(approximate, ["sigma_h"])


class InputShaTest(unittest.TestCase):
    def test_deterministic_and_documented(self) -> None:
        built = sample()
        expected = hashlib.sha256(canonical_json(input_document(built, MODEL)).encode("utf-8")).hexdigest()
        self.assertEqual(input_sha256(built, MODEL), expected)
        self.assertEqual(input_sha256(sample(), MODEL), expected)

    def test_independent_of_input_order(self) -> None:
        reordered = sample(
            relations=[relation(7), relation(9, preferred=False)],
            order_lines=list(reversed(observations() + [line(50, 51, status="ISSUED", received="5", ordered="10")])),
            consumption=list(reversed(consumption(60))),
            forecast_rows=list(reversed(forecast("12.500000"))),
        )
        self.assertEqual(input_sha256(reordered, MODEL), input_sha256(sample(), MODEL))

    def test_technical_ids_are_normalized_to_the_model_identity(self) -> None:
        other_ids = sample(forecast_rows=forecast("12.5", start_id=9001, model=42))
        self.assertEqual(input_sha256(other_ids, MODEL), input_sha256(sample(), MODEL))
        document = input_document(sample(), MODEL)
        self.assertEqual(document["forecast"]["model"], MODEL)
        self.assertNotIn("forecast_id", json.dumps(document))
        self.assertNotIn("model_version", json.dumps(document))
        self.assertNotIn("generated_at", json.dumps(document))

    def test_changes_with_any_semantic_input(self) -> None:
        base = input_sha256(sample(), MODEL)
        changed = {
            "inventory": sample(inventory=inventory("11", "5")),
            "forecast": sample(forecast_rows=forecast("12.6")),
            "consumption": sample(consumption=consumption(61)),
            "relation": sample(relations=[relation(7, lead=21)]),
            "product": sample(product=product(active=False)),
        }
        for name, built in changed.items():
            with self.subTest(name):
                self.assertNotEqual(input_sha256(built, MODEL), base)
        self.assertNotEqual(input_sha256(sample(), {"name": "baseline.naive", "version": "1.0.0"}), base)

    def test_without_forecast_and_model_required_with_one(self) -> None:
        self.assertIsNone(input_document(sample(forecast_rows=[]), None)["forecast"])
        with self.assertRaises(ValueError):
            input_document(sample(), None)


class RunConfigurationTest(unittest.TestCase):
    def test_contents(self) -> None:
        configuration = run_configuration()
        self.assertEqual(configuration["run_type"], "RECOMMENDATION")
        self.assertEqual(configuration["engine_version"], ENGINE_VERSION)
        self.assertEqual(configuration["policy"]["policy_set"], "V1_PROVISIONAL")
        self.assertEqual(configuration["forecast_config_sha256"], u3_config_sha256())
        self.assertEqual(configuration["forecast_selection"], "SAME_AS_OF_SAME_LOAD_CURRENT_FORECAST_CONFIG")
        self.assertEqual(configuration["catalog_policy"], "ALL_PRODUCT_LOCATIONS")
        self.assertEqual(configuration["input_rules_version"], INPUT_RULES_VERSION)
        self.assertEqual(configuration["representation"], {"significant_digits": 28, "rounding": "ROUND_HALF_EVEN"})
        text = canonical_json(configuration)
        for forbidden in ("generated_at", "timestamp", "status"):
            self.assertNotIn(forbidden, text)

    def test_sha_is_deterministic_and_sensitive(self) -> None:
        base = config_sha256()
        self.assertEqual(base, config_sha256(run_configuration()))
        variants = {
            "engine": run_configuration(engine_version="0.2.0"),
            "policy": run_configuration(policy=dataclasses.replace(V1_PROVISIONAL_PARAMETERS, r=14)),
            "forecast": run_configuration(forecast_config="0" * 64),
            "rules": run_configuration(input_rules_version="1.0.1"),
        }
        for name, configuration in variants.items():
            with self.subTest(name):
                self.assertNotEqual(config_sha256(configuration), base)

    def test_lock_key_is_a_signed_64_bit_identity(self) -> None:
        key = lock_key(A, 1, config_sha256())
        self.assertTrue(-(2**63) <= key < 2**63)
        self.assertEqual(key, lock_key(A, 1, config_sha256()))
        self.assertNotEqual(key, lock_key(A, 2, config_sha256()))

    def test_engine_version_is_not_hardcoded(self) -> None:
        tree = ast.parse(Path(config_module.__file__).read_text(encoding="utf-8"))
        strings = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertNotIn(ENGINE_VERSION, strings)


if __name__ == "__main__":
    unittest.main()
