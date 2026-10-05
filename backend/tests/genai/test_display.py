"""``display`` of `DT-069`: 6 decimals ``ROUND_HALF_EVEN``, no trailing zeros, ``.``, never a float."""

from __future__ import annotations

import unittest

from app.genai.errors import ExplanationError
from app.genai.facts import display


class DisplayTest(unittest.TestCase):
    def test_integers_as_they_are(self) -> None:
        for value, expected in (("242", "242"), ("0", "0"), ("-0", "0"), ("2700", "2700"), ("-5", "-5"),
                                ("007", "7")):
            with self.subTest(value):
                self.assertEqual(display(value), expected)

    def test_exact_decimals(self) -> None:
        for value, expected in (("1.650000", "1.65"), ("2.500000", "2.5"), ("3.000000", "3"), ("1.65", "1.65"),
                                ("530.692308", "530.692308"), ("1000.000000", "1000"), ("0.0", "0")):
            with self.subTest(value):
                self.assertEqual(display(value), expected)

    def test_rationals_from_the_exact_value(self) -> None:
        # 265346154/109375 = 2426.021979428571…; 132673077/70000 = 1895.329671428571…; -5/2 = -2.5
        self.assertEqual(display("265346154/109375"), "2426.021979")
        self.assertEqual(display("132673077/70000"), "1895.329671")
        self.assertEqual(display("-5/2"), "-2.5")
        self.assertEqual(display("1/3"), "0.333333")
        self.assertEqual(display("2/3"), "0.666667")

    def test_half_even_at_the_sixth_decimal(self) -> None:
        self.assertEqual(display("0.0000005"), "0")         # tie → even (0)
        self.assertEqual(display("0.0000015"), "0.000002")  # tie → even (2)
        self.assertEqual(display("0.0000025"), "0.000002")  # tie → even (2)
        self.assertEqual(display("1/2000000"), "0")         # exact tie as a rational
        self.assertEqual(display("3/2000000"), "0.000002")
        self.assertEqual(display("-0.0000001"), "0")        # zero never carries a sign

    def test_approximate_decimal_of_28_digits(self) -> None:
        # Persisted by U4 as reported by U1; rounded once, from that Decimal.
        self.assertEqual(display("2623.500600092591729239380374"), "2623.5006")
        self.assertEqual(display("439.4786206640203006679518026"), "439.478621")
        self.assertEqual(display("78.02191620945438640224055247"), "78.021916")
        self.assertEqual(display("2.021916209454386402240552468"), "2.021916")
        self.assertEqual(display("1E-7"), "0")

    def test_no_float_and_no_garbage(self) -> None:
        for bad in (1.5, 2, None):
            with self.subTest(bad), self.assertRaises(ExplanationError):
                display(bad)  # type: ignore[arg-type]
        for bad in ("abc", "NaN", "Infinity", ""):
            with self.subTest(bad), self.assertRaises(ExplanationError):
                display(bad)

    def test_no_thousands_separator_and_point_as_decimal_separator(self) -> None:
        self.assertEqual(display("1234567.25"), "1234567.25")
        self.assertNotIn(",", display("1234567/3"))


if __name__ == "__main__":
    unittest.main()
