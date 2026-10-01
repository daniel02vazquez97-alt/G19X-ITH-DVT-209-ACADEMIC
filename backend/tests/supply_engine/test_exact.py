"""Exact arithmetic of strategy B3 (`docs/06` §16.6, `DT-P14`).

Run from ``backend/``::

    python3 -m unittest discover -s tests -t .

Scope: point 4 (sign before squaring), point 5 (exact ``ceil`` bracketed with ``isqrt``), point 7
(28 significant digits, correctly rounded from the exact value) and the guarantee that decisions
never use an approximation. The oracle is independent: ``Decimal`` square roots at 120 digits in a
local context, compared on seeded pseudo-random cases (no unseeded randomness, `docs/13` §11).
"""

from __future__ import annotations

import math
import random
import unittest
from decimal import Decimal, localcontext
from fractions import Fraction

from app.supply_engine.exact import Surd, ceil_fraction, rational_sqrt

SEED = 20261001


def _oracle(u: Fraction, b: Fraction, d: int) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 120
        root = (Decimal(b.numerator) / Decimal(b.denominator)).sqrt()
        return Decimal(u.numerator) / Decimal(u.denominator) + root / d


def _oracle_28(u: Fraction, b: Fraction, d: int) -> Decimal:
    value = _oracle(u, b, d)
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = "ROUND_HALF_EVEN"
        return +value


class RationalSqrtTest(unittest.TestCase):
    def test_perfect_squares(self) -> None:
        cases = [(Fraction(0), Fraction(0)), (Fraction(4), Fraction(2)), (Fraction(9, 4), Fraction(3, 2))]
        for value, root in cases:
            with self.subTest(value=value):
                self.assertEqual(rational_sqrt(value), root)

    def test_irrational(self) -> None:
        for value in (Fraction(2), Fraction(3, 4), Fraction(1, 2), Fraction(1089 * 2)):
            with self.subTest(value=value):
                self.assertIsNone(rational_sqrt(value))

    def test_ceil_fraction(self) -> None:
        self.assertEqual(ceil_fraction(Fraction(14, 7)), 2)
        self.assertEqual(ceil_fraction(Fraction(15, 7)), 3)
        self.assertEqual(ceil_fraction(Fraction(-1, 2)), 0)


class ComparisonTest(unittest.TestCase):
    """§16.6 point 4."""

    def test_negative_rest_is_false_without_squaring(self) -> None:
        # x = 5 + 0 > 4. Squaring a negative rest would claim 0 ≤ (1·(4−5))² = 1, i.e. x ≤ 4.
        self.assertFalse(Surd(Fraction(5), Fraction(0), 1).le(Fraction(4)))
        self.assertFalse(Surd(Fraction(5), Fraction(2), 20).le(Fraction(4)))

    def test_equality_is_possible_only_with_a_rational_root(self) -> None:
        x = Surd(Fraction(1), Fraction(4), 2)  # 1 + 2/2 = 2
        self.assertTrue(x.le(Fraction(2)))
        self.assertTrue(x.equals(Fraction(2)))
        self.assertFalse(x.le(Fraction(1999, 1000)))
        self.assertFalse(Surd(Fraction(0), Fraction(2), 1).equals(Fraction(14142, 10000)))

    def test_square_root_of_two_just_above_and_below(self) -> None:
        root_two = Surd(Fraction(0), Fraction(2), 1)  # 1.41421356237309504880…
        self.assertTrue(root_two.le(Fraction(14142135623730951, 10**16)))
        self.assertFalse(root_two.le(Fraction(14142135623730950, 10**16)))

    def test_against_the_oracle(self) -> None:
        rng = random.Random(SEED)
        for _ in range(3000):
            u = Fraction(rng.randint(-500, 500), rng.randint(1, 7))
            b = Fraction(1089 * rng.randint(0, 10**6))
            d = 20 * rng.randint(1, 60)
            bound = Fraction(rng.randint(-200, 800), rng.randint(1, 7))
            x = Surd(u, b, d)
            if x.exact() is None:
                expected = _oracle(u, b, d) <= Decimal(bound.numerator) / Decimal(bound.denominator)
            else:
                expected = x.exact() <= bound
            self.assertEqual(x.le(bound), expected, (u, b, d, bound))


class CeilTest(unittest.TestCase):
    """§16.6 point 5."""

    def test_rational_path_is_exact(self) -> None:
        # (1·14)/7 = 2 exactly: ceil is 2, never 3 (the Decimal-28 trap that led to B3).
        self.assertEqual(Surd(Fraction(1, 7) * 14, Fraction(0), 20).ceil_div(Fraction(1)), 2)
        self.assertEqual(Surd(Fraction(18), Fraction(0), 20).ceil_div(Fraction(10)), 2)

    def test_k_and_k_plus_one(self) -> None:
        root_two = Surd(Fraction(0), Fraction(2), 1)
        self.assertEqual(root_two.ceil_div(Fraction(2)), 1)  # √2 ≤ 2
        self.assertEqual(Surd(Fraction(0), Fraction(2), 20).ceil_div(Fraction(1)), 1)
        # y = 1 + 1/20·⌊√8⌋ = 1.1; k = ceil(1.1/1) = 2; x = 1 + √8/20 ≈ 1.1414 ≤ 2 → 2.
        self.assertEqual(Surd(Fraction(1), Fraction(8), 20).ceil_div(Fraction(1)), 2)
        # x = 0.95 + √2/20 ≈ 1.0207 > 1, while y = 0.95 + 1/20 = 1 → k = 1 fails → 2.
        self.assertEqual(Surd(Fraction(95, 100), Fraction(2), 20).ceil_div(Fraction(1)), 2)

    def test_against_the_oracle(self) -> None:
        rng = random.Random(SEED + 1)
        for _ in range(3000):
            u = Fraction(rng.randint(-100, 900), rng.randint(1, 7))
            b = Fraction(1089 * rng.randint(0, 10**6))
            d = 20 * rng.randint(1, 60)
            divisor = Fraction(rng.randint(1, 50))
            x = Surd(u, b, d)
            if not x.le(Fraction(0)):
                exact = x.exact()
                if exact is None:
                    with localcontext() as ctx:
                        ctx.prec = 120
                        expected = math.ceil(_oracle(u, b, d) / Decimal(divisor.numerator))
                else:
                    expected = ceil_fraction(exact / divisor)
                self.assertEqual(x.ceil_div(divisor), expected, (u, b, d, divisor))


class ReportTest(unittest.TestCase):
    """§16.6 point 7: exact when rational; else 28 significant digits from the exact value."""

    def test_rational_values_are_reported_exactly(self) -> None:
        self.assertEqual(Surd(Fraction(680, 7), Fraction(0), 20).report(), Fraction(680, 7))
        self.assertEqual(Surd(Fraction(1), Fraction(9), 3).report(), Fraction(2))
        self.assertIsInstance(Surd(Fraction(0), Fraction(4), 1).report(), Fraction)

    def test_square_root_of_two(self) -> None:
        value = Surd(Fraction(0), Fraction(2), 1).report()
        self.assertIsInstance(value, Decimal)
        self.assertEqual(value, Decimal("1.414213562373095048801688724"))
        self.assertEqual(len(value.as_tuple().digits), 28)

    def test_small_values_keep_28_significant_digits(self) -> None:
        value = Surd(Fraction(0), Fraction(2, 10**40), 1).report()
        self.assertEqual(value, Decimal("1.414213562373095048801688724E-20"))
        self.assertEqual(len(value.as_tuple().digits), 28)

    def test_rounding_that_carries_into_a_new_digit(self) -> None:
        # 10 − 10⁻³⁰ + √2·10⁻³¹ ≈ 9.99999999999999999999999999999986 → 10.00…0 (28 digits).
        value = Surd(Fraction(10) - Fraction(1, 10**30), Fraction(2, 10**62), 1).report()
        self.assertEqual(value, Decimal("10.00000000000000000000000000"))
        self.assertEqual(len(value.as_tuple().digits), 28)

    def test_against_the_oracle(self) -> None:
        rng = random.Random(SEED + 2)
        for _ in range(2000):
            u = Fraction(rng.randint(0, 900), rng.randint(1, 7))
            b = Fraction(1089 * rng.randint(1, 10**6), rng.randint(1, 3))
            d = 20 * rng.randint(1, 60)
            x = Surd(u, b, d)
            if x.exact() is None:
                reported = x.report()
                self.assertEqual(reported, _oracle_28(u, b, d), (u, b, d))
                self.assertEqual(len(reported.as_tuple().digits), 28)


if __name__ == "__main__":
    unittest.main()
