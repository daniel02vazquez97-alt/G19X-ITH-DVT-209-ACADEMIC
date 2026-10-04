"""Consumption history of ``/products/{id}/history`` (`DT-067`, US-033, RF-009). Pure functions.

* Periods: ``daily``, ``weekly`` (ISO weeks, Monday to Sunday) or ``monthly`` (calendar months);
  ``period_end`` is exclusive. Every period that intersects ``[date_from, date_to]`` is returned.
* A day without a ``consumption`` row is *not observed* and never counts as zero. A period is complete if
  it lies entirely inside the range and every one of its days is observed.
* Statistics only over the ``n`` complete periods (``periods_used``): ``mean``, the **population** standard
  deviation ``√(Σ(qᵢ − mean)² / n)`` (no Bessel correction: with ``n = 1`` it is 0), ``cv = std_dev /
  mean`` (null when ``mean = 0``) and ``zero_periods``. With ``n = 0`` every statistic is null.
* Exact arithmetic (`Fraction`); the square root in `Decimal` with 28 significant digits; values reported
  with 6 decimals ``ROUND_HALF_EVEN``.

The source is ``consumption`` only, never ``demand``; no stockout correction (`DT-011`).
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from typing import Any

GRANULARITIES = ("daily", "weekly", "monthly")
DEFAULT_GRANULARITY = "weekly"
_ONE_DAY = _dt.timedelta(days=1)
_SIX = Decimal("0.000001")


@dataclass(frozen=True)
class DayRow:
    day: _dt.date
    quantity: Decimal
    stockout: bool


def _period_start(day: _dt.date, granularity: str) -> _dt.date:
    if granularity == "daily":
        return day
    if granularity == "weekly":
        return day - _dt.timedelta(days=day.weekday())  # ISO week: Monday
    return day.replace(day=1)


def _next_start(start: _dt.date, granularity: str) -> _dt.date:
    if granularity == "daily":
        return start + _ONE_DAY
    if granularity == "weekly":
        return start + _dt.timedelta(days=7)
    return (start.replace(day=28) + _dt.timedelta(days=4)).replace(day=1)


def report(value: Fraction | Decimal) -> Decimal:
    """6 decimals ``ROUND_HALF_EVEN``, from the exact value (or the 28-digit root)."""
    with localcontext() as context:
        context.prec = 80
        exact = value if isinstance(value, Decimal) else Decimal(value.numerator) / Decimal(value.denominator)
        return exact.quantize(_SIX, rounding=ROUND_HALF_EVEN)


def population_std(values: list[Fraction], mean: Fraction) -> Decimal:
    """``√(Σ(qᵢ − mean)² / n)`` with 28 significant digits; ``n`` is ``len(values)`` (population)."""
    variance = sum(((q - mean) ** 2 for q in values), Fraction(0)) / len(values)
    with localcontext() as context:
        context.prec = 28
        context.rounding = ROUND_HALF_EVEN
        return (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()


def statistics(quantities: list[Decimal]) -> dict[str, Any]:
    n = len(quantities)
    if n == 0:
        return {"periods_used": 0, "mean": None, "std_dev": None, "cv": None, "zero_periods": None}
    values = [Fraction(q) for q in quantities]
    mean = sum(values, Fraction(0)) / n
    std = population_std(values, mean)
    cv = None
    if mean != 0:
        with localcontext() as context:
            context.prec = 28
            cv = report(std / (Decimal(mean.numerator) / Decimal(mean.denominator)))
    return {
        "periods_used": n,
        "mean": report(mean),
        "std_dev": report(std),
        "cv": cv,
        "zero_periods": sum(1 for q in values if q == 0),
    }


def build_history(rows: Iterable[DayRow], date_from: _dt.date, date_to: _dt.date, granularity: str) -> dict[str, Any]:
    """Periods intersecting ``[date_from, date_to]`` (inclusive) and the statistics of the complete ones."""
    if granularity not in GRANULARITIES:
        raise ValueError(f"unknown granularity: {granularity}")
    if date_from > date_to:
        return {"periods": [], "statistics": statistics([])}
    by_day = {r.day: r for r in rows if date_from <= r.day <= date_to}
    periods = []
    complete_quantities = []
    start = _period_start(date_from, granularity)
    while start <= date_to:
        end = _next_start(start, granularity)
        days = (end - start).days
        inside = start >= date_from and end - _ONE_DAY <= date_to
        observed = [by_day[d] for d in (start + _ONE_DAY * i for i in range(days)) if d in by_day]
        quantity = sum((r.quantity for r in observed), Decimal(0))
        complete = inside and len(observed) == days
        periods.append(
            {
                "period_start": start,
                "period_end": end,
                "days": days,
                "days_observed": len(observed),
                "quantity": quantity,
                "stockout_days": sum(1 for r in observed if r.stockout),
                "complete": complete,
            }
        )
        if complete:
            complete_quantities.append(quantity)
        start = end
    return {"periods": periods, "statistics": statistics(complete_quantities)}
