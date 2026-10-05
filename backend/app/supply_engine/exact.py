"""Exact evaluation of `docs/06` §16.6 (strategy B3, `DT-P14`).

Every value that depends on ``σ_H`` has the form ``u + √b / d``, with ``u`` and ``b`` rational,
``b ≥ 0`` and ``d`` a positive integer:

* ``σ_H = √A / n``            → ``Surd(0, A, n)``
* ``SS  = √B / D``            → ``Surd(0, B, D)``    with ``B = 1089·A`` and ``D = 20·n``
* ``S   = DDH + √B / D``      → ``Surd(DDH, B, D)``
* ``x   = P + √B / D``        → ``Surd(P, B, D)``    with ``P = DDH − IP``

Decisions —comparisons and ``ceil``— are exact, with no tolerance and no decimal context: the sign is
checked before squaring (point 4) and ``ceil`` is bracketed with ``isqrt`` (point 5). ``Decimal``
appears only in ``Surd.report``, the representation rule of point 7 (28 significant digits,
correctly rounded from the exact value, ``ROUND_HALF_EVEN``), and never enters a decision.

With integer consumption, ``A``, ``B`` and ``D`` are integers exactly as §16.6 states. The algorithm
is written over rationals so that it stays exact for any exact input: ``isqrt`` is applied to
``⌊b⌋``, which keeps ``s ≤ √b < s + 1``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

#: Significant digits of a reported irrational value (§16.6 point 7).
REPORT_DIGITS = 28


def rational_sqrt(value: Fraction) -> Fraction | None:
    """Exact square root of a non-negative rational, or ``None`` if it is irrational."""
    if value < 0:
        raise ValueError("square root of a negative number")
    num_root = math.isqrt(value.numerator)
    den_root = math.isqrt(value.denominator)
    if num_root * num_root == value.numerator and den_root * den_root == value.denominator:
        return Fraction(num_root, den_root)
    return None


def ceil_fraction(value: Fraction) -> int:
    """Exact ceiling of a rational."""
    return -((-value.numerator) // value.denominator)


@dataclass(frozen=True, slots=True)
class Surd:
    """The real number ``u + √b / d``, held exactly."""

    u: Fraction
    b: Fraction
    d: int

    def __post_init__(self) -> None:
        if self.b < 0:
            raise ValueError("b must be non-negative")
        if self.d <= 0:
            raise ValueError("d must be positive")

    def exact(self) -> Fraction | None:
        """The value as a rational, or ``None`` when ``√b`` is irrational."""
        root = rational_sqrt(self.b)
        if root is None:
            return None
        return self.u + root / self.d

    def le(self, bound: Fraction) -> bool:
        """``u + √b/d ≤ bound``, exactly (§16.6 point 4).

        ``R = bound − u``; if ``R < 0`` the answer is false without squaring, because
        ``√b / d ≥ 0 > R``. Otherwise both sides are non-negative and ``√b/d ≤ R ⇔ b ≤ (d·R)²``.
        """
        rest = bound - self.u
        if rest < 0:
            return False
        return self.b <= (self.d * rest) ** 2

    def equals(self, value: Fraction) -> bool:
        """``u + √b/d == value``; only possible when ``√b`` is rational."""
        exact = self.exact()
        return exact is not None and exact == value

    def ceil_div(self, divisor: Fraction) -> int:
        """``ceil((u + √b/d) / divisor)``, exactly (§16.6 point 5); requires ``d·divisor > 1``."""
        if divisor <= 0:
            raise ValueError("divisor must be positive")
        exact = self.exact()
        if exact is not None:
            return ceil_fraction(exact / divisor)
        if self.d * divisor <= 1:
            raise ValueError("d·divisor must exceed 1 for the bracketing to be exact")
        root_floor = math.isqrt(self.b.numerator // self.b.denominator)
        lower = self.u + Fraction(root_floor, self.d)  # lower < x < lower + 1/d
        k = ceil_fraction(lower / divisor)
        return k if self.le(k * divisor) else k + 1

    def report(self) -> Fraction | Decimal:
        """Representation of §16.6 point 7: exact if rational, else 28 significant digits.

        The decimal is obtained directly from the exact value, never from another rounded value.
        """
        exact = self.exact()
        if exact is not None:
            return exact
        return _correctly_rounded(self)


def _floor_scaled(value: Surd, scale: Fraction) -> int:
    """``⌊scale · value⌋`` for ``scale > 0`` and irrational ``value``, with integers only.

    ``scale·value = U + √T`` with ``U = scale·u`` and ``T = (scale/d)²·b``. Writing ``U = un/ud`` and
    ``T = tn/td``, ``scale·value = (un·td + √(ud²·tn·td)) / (ud·td)``; the square root is irrational,
    so its floor is ``isqrt`` and no integer lies strictly between the floor and the value.
    """
    big_u = scale * value.u
    big_t = (scale / value.d) ** 2 * value.b
    un, ud = big_u.numerator, big_u.denominator
    tn, td = big_t.numerator, big_t.denominator
    numerator_floor = un * td + math.isqrt(ud * ud * tn * td)
    return numerator_floor // (ud * td)


def _correctly_rounded(value: Surd) -> Decimal:
    """Positive irrational ``value`` correctly rounded to ``REPORT_DIGITS`` significant digits.

    An irrational number is never a tie, so ``ROUND_HALF_EVEN`` reduces to rounding to nearest:
    with ``m = value·10^k`` in ``[10^27, 10^28)``, the result is ``⌊m + ½⌋ = (⌊2m⌋ + 1) // 2``.
    """
    # Decimal exponent: 10^e ≤ value < 10^(e+1).
    integer_part = _floor_scaled(value, Fraction(1))
    if integer_part < 0:
        raise ValueError("only positive values are reported")
    if integer_part >= 1:
        exponent = len(str(integer_part)) - 1
    else:
        shift = 1
        while True:
            scaled = _floor_scaled(value, Fraction(10**shift))
            if scaled >= 1:
                exponent = len(str(scaled)) - 1 - shift
                break
            shift += 1
    power = REPORT_DIGITS - 1 - exponent
    scale = Fraction(2 * 10**power) if power >= 0 else Fraction(2, 10 ** (-power))
    rounded = (_floor_scaled(value, scale) + 1) // 2
    if rounded == 10**REPORT_DIGITS:
        rounded = 10 ** (REPORT_DIGITS - 1)
        power -= 1
    digits = tuple(int(ch) for ch in str(rounded))
    return Decimal((0, digits, -power))
