"""Exact arithmetic of the forecasting package: no ``float`` anywhere (`DT-056` point 11).

Quantities become ``Fraction`` without loss; results leave as ``Decimal`` quantized once, by integer
arithmetic, to six decimals with ``ROUND_HALF_EVEN``.
"""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction


class InvalidForecastInputError(ValueError):
    """The request violates the contract. ``code`` is a stable reason, ``field`` the offending part."""

    def __init__(self, code: str, field: str, message: str) -> None:
        super().__init__(f"{code}: {field}: {message}")
        self.code = code
        self.field = field
        self.message = message


def to_fraction(value: object, field: str) -> Fraction:
    """``int``, finite ``Decimal`` or ``Fraction`` → ``Fraction``; anything else is rejected."""
    if isinstance(value, bool):
        raise InvalidForecastInputError("INVALID_TYPE", field, "a bool is not a quantity")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, Fraction):
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise InvalidForecastInputError("NOT_FINITE", field, "NaN and infinity are rejected")
        return Fraction(value)
    raise InvalidForecastInputError(
        "INVALID_TYPE", field, f"{type(value).__name__} is not a quantity (int, Decimal or Fraction)"
    )


def quantize(value: Fraction, scale: int) -> Decimal:
    """The multiple of ``10**-scale`` nearest to ``value``; ties to the even multiple."""
    factor = 10**scale
    quotient, remainder = divmod(value.numerator * factor, value.denominator)
    twice = 2 * remainder
    if twice > value.denominator or (twice == value.denominator and quotient % 2):
        quotient += 1
    return Decimal(f"{quotient}e-{scale}")
