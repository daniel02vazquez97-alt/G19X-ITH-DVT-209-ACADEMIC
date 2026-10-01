"""Contract tests of the supply engine's public types (`DT-051`, `DT-052`, `docs/06` §16.5).

Run from ``backend/``::

    python3 -m unittest discover -s tests -t .

Scope: canonical order and values of every enumeration, ``ENGINE_VERSION``, the V1 parameter set,
immutability of the input and output types, and the shape of ``InvalidInputError``. The expected
lists are literals copied from `docs/06` §16.5 and §16.11.4, not read from the module.
"""

from __future__ import annotations

import dataclasses
import re
import unittest
from fractions import Fraction

from app.supply_engine import (
    ENGINE_VERSION,
    POLICY_SET_V1,
    V1_PROVISIONAL_PARAMETERS,
    Breakdown,
    EvaluationInput,
    EvaluationResult,
    Flag,
    InvalidInputError,
    LeadTimeSource,
    MethodUsed,
    Outcome,
    PolicyParameter,
    Product,
    Reason,
)

from . import builders as b


class EnumerationTest(unittest.TestCase):
    def test_outcomes(self) -> None:
        self.assertEqual([o.value for o in Outcome], ["RECOMMEND", "NO_NEED", "NOT_CALCULABLE"])

    def test_reasons_in_canonical_order(self) -> None:
        self.assertEqual(
            [r.value for r in Reason],
            [
                "PRODUCT_INACTIVE",
                "PRODUCT_OUT_OF_VALIDITY",
                "NO_ACTIVE_PREFERRED_SUPPLIER",
                "NEGATIVE_ON_HAND",
                "FORECAST_MISSING",
                "FORECAST_TOO_SHORT",
                "INSUFFICIENT_HISTORY",
                "MISSING_POLICY_PARAMETER",
            ],
        )

    def test_flags_in_canonical_order(self) -> None:
        self.assertEqual(
            [f.value for f in Flag],
            [
                "LEAD_TIME_AGREED_FALLBACK",
                "LEAD_TIME_CAPPED",
                "MOQ_APPLIED",
                "ORDER_MULTIPLE_ROUNDING",
                "UNCOUNTED_TRANSIT",
                "OVERDUE_ORDERS_EXCLUDED",
                "ZERO_FORECAST_DEMAND",
            ],
        )

    def test_policy_parameters_in_canonical_order(self) -> None:
        self.assertEqual([p.value for p in PolicyParameter], ["R", "z", "N", "N_MIN", "LT_MAX"])

    def test_lead_time_sources_and_methods(self) -> None:
        self.assertEqual([s.value for s in LeadTimeSource], ["OBSERVED", "AGREED_FALLBACK"])
        self.assertEqual(
            [m.value for m in MethodUsed], ["MODEL", "BASELINE", "INTERMITTENT_METHOD"]
        )

    def test_enumerations_are_strings(self) -> None:
        self.assertEqual(Reason.PRODUCT_OUT_OF_VALIDITY, "PRODUCT_OUT_OF_VALIDITY")
        self.assertIsInstance(Flag.MOQ_APPLIED, str)


class VersionAndPolicyTest(unittest.TestCase):
    def test_engine_version_is_the_constant_0_1_0(self) -> None:
        self.assertEqual(ENGINE_VERSION, "0.1.0")
        self.assertRegex(ENGINE_VERSION, r"^\d+\.\d+\.\d+$")

    def test_every_result_carries_the_engine_version(self) -> None:
        from app.supply_engine import evaluate

        self.assertEqual(evaluate(b.evaluation()).engine_version, "0.1.0")

    def test_v1_parameters(self) -> None:
        self.assertEqual(POLICY_SET_V1, "V1_PROVISIONAL")
        p = V1_PROVISIONAL_PARAMETERS
        self.assertEqual(
            (p.policy_set, p.r, p.z, p.n, p.n_min, p.lt_max),
            ("V1_PROVISIONAL", 7, Fraction(33, 20), 12, 3, 90),
        )
        self.assertIsInstance(p.z, Fraction)  # 33/20 exactly, never 1.65 as a float


class ImmutabilityTest(unittest.TestCase):
    def test_input_types_are_frozen(self) -> None:
        item = b.product()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            item.is_active = False  # type: ignore[misc]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            b.evaluation().as_of_date = b.day(1)  # type: ignore[misc]

    def test_output_types_are_frozen(self) -> None:
        from app.supply_engine import evaluate

        result = evaluate(b.evaluation())
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.outcome = Outcome.NO_NEED  # type: ignore[misc]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.breakdown.q_final = Fraction(0)  # type: ignore[misc]

    def test_input_block_order_is_canonical(self) -> None:
        self.assertEqual(
            [f.name for f in dataclasses.fields(EvaluationInput)],
            [
                "as_of_date",
                "product",
                "supplier_relations",
                "inventory",
                "open_lines",
                "lead_time_observations",
                "consumption",
                "forecast",
                "policy",
            ],
        )

    def test_product_fields(self) -> None:
        self.assertEqual(
            [f.name for f in dataclasses.fields(Product)],
            ["product_id", "location_id", "is_active", "valid_from", "valid_to"],
        )

    def test_result_fields(self) -> None:
        self.assertEqual(
            [f.name for f in dataclasses.fields(EvaluationResult)],
            [
                "outcome",
                "reasons",
                "missing_policy_parameters",
                "flags",
                "breakdown",
                "forecast_id",
                "policy_set",
                "engine_version",
            ],
        )

    def test_decision_terms_exist_in_the_breakdown(self) -> None:
        names = {f.name for f in dataclasses.fields(Breakdown)}
        for name in ("raw_need", "q_moq", "q_final", "s1", "s2", "a", "b", "d", "p"):
            with self.subTest(name=name):
                self.assertIn(name, names)


class InvalidInputErrorTest(unittest.TestCase):
    def test_is_a_value_error_with_a_field(self) -> None:
        error = InvalidInputError("inventory.reserved", "must be >= 0")
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.field, "inventory.reserved")
        self.assertEqual(error.message, "must be >= 0")
        self.assertEqual(str(error), "inventory.reserved: must be >= 0")

    def test_format_is_field_colon_message(self) -> None:
        self.assertTrue(re.fullmatch(r"[^:]+: .+", str(InvalidInputError("a.b", "c"))))


if __name__ == "__main__":
    unittest.main()
