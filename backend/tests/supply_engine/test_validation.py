"""Input validation (`DT-052`, `docs/06` §16.11.5).

Run from ``backend/``::

    python3 -m unittest discover -s tests -t .

Scope: one test per rule of phase 1 (type, finiteness, sign) and phase 2 (a)–(h); the first error in
canonical order is the only one raised; messages carry neither values nor identifiers; ``on_hand <
0`` is not invalid input (`V1-13`).
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import unittest
from decimal import Decimal
from fractions import Fraction

from app.supply_engine import InvalidInputError, Inventory, Outcome, Reason, evaluate

from . import builders as b


class _Base(unittest.TestCase):
    def assertInvalid(self, inputs: object, field: str) -> InvalidInputError:
        with self.assertRaises(InvalidInputError) as caught:
            evaluate(inputs)  # type: ignore[arg-type]
        self.assertEqual(caught.exception.field, field)
        return caught.exception


class PhaseOneTypesTest(_Base):
    def test_float_is_rejected_everywhere_a_quantity_is_expected(self) -> None:
        cases = {
            "inventory.on_hand": b.evaluation(inventory=Inventory(1.5, 0, 30)),
            "inventory.reserved": b.evaluation(inventory=Inventory(17, 0.0, 30)),
            "supplier_relations[0].moq": b.evaluation(supplier_relations=(b.relation(moq=2.5),)),
            "open_lines[1].quantity_pending": b.evaluation(
                open_lines=(b.line(1, b.day(10), 10), b.line(2, b.day(46), 20.0))
            ),
            "consumption.quantities[3]": b.evaluation(consumption=b.consumption([5, 5, 5, 5.0])),
            "forecast.weekly_quantities[0]": b.evaluation(forecast=b.forecast([40.0, 40, 40, 40])),
            "policy.z": b.evaluation(policy=b.v1_policy(z=1.65)),
        }
        for field, inputs in cases.items():
            with self.subTest(field=field):
                error = self.assertInvalid(inputs, field)
                self.assertIn("float is not accepted", error.message)

    def test_nan_and_infinity_are_rejected(self) -> None:
        for bad in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity"), Decimal("sNaN")):
            with self.subTest(value=str(bad)):
                self.assertInvalid(b.evaluation(inventory=Inventory(bad, 0, 30)), "inventory.on_hand")

    def test_bool_and_str_are_not_quantities(self) -> None:
        self.assertInvalid(b.evaluation(inventory=Inventory(True, 0, 30)), "inventory.on_hand")
        self.assertInvalid(b.evaluation(inventory=Inventory("17", 0, 30)), "inventory.on_hand")

    def test_exact_numbers_are_accepted(self) -> None:
        for value in (17, Decimal("17.0"), Fraction(34, 2)):
            with self.subTest(value=value):
                evaluate(b.evaluation(inventory=Inventory(value, 0, 30)))

    def test_datetime_is_not_a_date(self) -> None:
        self.assertInvalid(b.evaluation(as_of_date=dt.datetime(2025, 12, 31)), "as_of_date")

    def test_strict_bool_and_int(self) -> None:
        self.assertInvalid(b.evaluation(product=b.product(is_active=1)), "product.is_active")
        self.assertInvalid(b.evaluation(product=b.product(product_id=True)), "product.product_id")
        self.assertInvalid(b.evaluation(product=b.product(product_id="101")), "product.product_id")

    def test_collections_must_be_tuples(self) -> None:
        self.assertInvalid(b.evaluation(supplier_relations=[b.relation()]), "supplier_relations")
        self.assertInvalid(b.evaluation(open_lines=list(b.evaluation().open_lines)), "open_lines")

    def test_blocks_must_have_their_type(self) -> None:
        self.assertInvalid("not an input", "input")
        self.assertInvalid(b.evaluation(product=None), "product")
        self.assertInvalid(b.evaluation(forecast="weekly"), "forecast")

    def test_forecast_metadata_types(self) -> None:
        bad_method = dataclasses.replace(b.forecast([40] * 4), method_used="BASELINE")
        self.assertInvalid(b.evaluation(forecast=bad_method), "forecast.method_used")
        bad_version = dataclasses.replace(b.forecast([40] * 4), model_version="v3")
        self.assertInvalid(b.evaluation(forecast=bad_version), "forecast.model_version")


class PhaseOneSignTest(_Base):
    def test_negative_quantities_are_invalid(self) -> None:
        cases = {
            "inventory.reserved": b.evaluation(inventory=Inventory(17, -1, 30)),
            "inventory.total_in_transit": b.evaluation(inventory=Inventory(17, 0, -30)),
            "supplier_relations[0].moq": b.evaluation(supplier_relations=(b.relation(moq=-1),)),
            "open_lines[0].quantity_pending": b.evaluation(
                open_lines=(b.line(1, b.day(10), -10), b.line(2, b.day(46), 40))
            ),
            "consumption.quantities[0]": b.evaluation(consumption=b.consumption([-1, 5])),
            "forecast.weekly_quantities[2]": b.evaluation(forecast=b.forecast([40, 40, -1, 40])),
            "supplier_relations[0].agreed_lead_time_days": b.evaluation(
                supplier_relations=(b.relation(agreed_lead_time_days=-1),)
            ),
        }
        for field, inputs in cases.items():
            with self.subTest(field=field):
                self.assertEqual(self.assertInvalid(inputs, field).message, "must be >= 0")

    def test_order_multiple_below_one_is_invalid(self) -> None:
        """Precondition ``M ≥ 1`` of `docs/06` §16.6 point 5."""
        for value in (0, Fraction(1, 2), Decimal("0.99")):
            with self.subTest(value=value):
                self.assertInvalid(
                    b.evaluation(supplier_relations=(b.relation(order_multiple=value),)),
                    "supplier_relations[0].order_multiple",
                )
        evaluate(b.evaluation(supplier_relations=(b.relation(order_multiple=Fraction(5, 2)),)))

    def test_negative_on_hand_is_not_invalid_input(self) -> None:
        """`V1-13`, `DT-052`: NOT_CALCULABLE with NEGATIVE_ON_HAND, never an exception."""
        result = evaluate(b.evaluation(inventory=Inventory(-3, 0, 30)))
        self.assertEqual(result.outcome, Outcome.NOT_CALCULABLE)
        self.assertEqual(result.reasons, (Reason.NEGATIVE_ON_HAND,))


class PhaseTwoTest(_Base):
    def test_a_valid_to_before_valid_from(self) -> None:
        self.assertInvalid(
            b.evaluation(product=b.product(valid_to=dt.date(2022, 12, 31))), "product.valid_to"
        )

    def test_b_two_active_preferred_relations(self) -> None:
        relations = (b.relation(supplier_id=1), b.relation(supplier_id=2))
        self.assertInvalid(b.evaluation(supplier_relations=relations), "supplier_relations")
        allowed = (b.relation(supplier_id=1), b.relation(supplier_id=2, is_active=False))
        evaluate(b.evaluation(supplier_relations=allowed))

    def test_c_duplicate_line(self) -> None:
        lines = (b.line(1, b.day(10), 10), b.line(1, b.day(46), 20))
        self.assertInvalid(b.evaluation(open_lines=lines), "open_lines[1]")

    def test_d_total_in_transit_must_match_the_lines(self) -> None:
        self.assertInvalid(
            b.evaluation(inventory=Inventory(17, 0, 50)), "inventory.total_in_transit"
        )

    def test_e_completed_before_issued(self) -> None:
        bad = (b.observation(b.day(-5), b.day(-6)),)
        self.assertInvalid(
            b.evaluation(lead_time_observations=bad), "lead_time_observations[0].completed_on"
        )

    def test_f_consumption_coherence(self) -> None:
        before_validity = b.consumption([5] * 10, end=dt.date(2023, 1, 5))
        self.assertInvalid(b.evaluation(consumption=before_validity), "consumption.start_date")
        ends_early = b.consumption([5] * 10, end=b.day(-1))
        self.assertInvalid(b.evaluation(consumption=ends_early), "consumption.quantities")
        ends_late = b.consumption([5] * 10, end=b.day(1))
        self.assertInvalid(b.evaluation(consumption=ends_late), "consumption.quantities")

    def test_f_series_ends_at_valid_to_when_it_is_earlier(self) -> None:
        valid_to = dt.date(2025, 4, 2)
        inputs = b.evaluation(
            product=b.product(valid_to=valid_to), consumption=b.consumption([5] * 30, end=valid_to)
        )
        self.assertEqual(evaluate(inputs).outcome, Outcome.NOT_CALCULABLE)

    def test_g_forecast_must_be_anchored(self) -> None:
        shifted = b.forecast([40] * 4, start=b.day(2))
        self.assertInvalid(b.evaluation(forecast=shifted), "forecast.start_date")

    def test_h_policy_set_and_values(self) -> None:
        self.assertInvalid(b.evaluation(policy=b.v1_policy(policy_set="OTHER")), "policy.policy_set")
        for name, value in (("r", 0), ("r", 8), ("z", Fraction(2)), ("n", 10), ("n_min", 2), ("lt_max", 60)):
            with self.subTest(name=name, value=value):
                self.assertInvalid(b.evaluation(policy=b.v1_policy(**{name: value})), f"policy.{name}")
        evaluate(b.evaluation(policy=b.v1_policy(z=Decimal("1.65"))))


class OrderAndMessagesTest(_Base):
    def test_only_the_first_error_is_raised(self) -> None:
        # Phase 1 beats phase 2; earlier blocks beat later ones; (a) beats (d).
        inputs = b.evaluation(
            product=b.product(valid_to=dt.date(2022, 1, 1)),
            inventory=Inventory(17, -1, 50),
        )
        self.assertInvalid(inputs, "inventory.reserved")
        inputs = b.evaluation(
            product=b.product(valid_to=dt.date(2022, 1, 1)), inventory=Inventory(17, 0, 50)
        )
        self.assertInvalid(inputs, "product.valid_to")
        lines = (b.line(1, b.day(10), Fraction(-1)), b.line(2, b.day(10), Fraction(-2)))
        self.assertInvalid(b.evaluation(open_lines=lines), "open_lines[0].quantity_pending")

    def test_messages_contain_no_value_and_no_identifier(self) -> None:
        secret = Decimal("-98765.4321")
        error = self.assertInvalid(b.evaluation(inventory=Inventory(17, secret, 30)), "inventory.reserved")
        self.assertNotIn("98765", str(error))
        lines = (b.line(424242, b.day(10), 10), b.line(424242, b.day(46), 20))
        error = self.assertInvalid(b.evaluation(open_lines=lines), "open_lines[1]")
        self.assertNotIn("424242", str(error))
        self.assertTrue(str(error).startswith("open_lines[1]: "))


if __name__ == "__main__":
    unittest.main()
