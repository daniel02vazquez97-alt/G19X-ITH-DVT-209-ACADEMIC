"""Consumption history statistics (`DT-067`), with cases computed by hand. Pure, no database."""

from __future__ import annotations

import datetime as dt
import statistics as stdlib_statistics
import unittest
from decimal import Decimal

from _api_support import BACKEND_DIR  # noqa: F401 — path setup

from app.api.history import DayRow, build_history, population_std, statistics
from fractions import Fraction

D = dt.date


def days(start: dt.date, quantities: list[int], stockout: set[int] = frozenset()) -> list[DayRow]:
    return [DayRow(start + dt.timedelta(days=i), Decimal(q), i in stockout) for i, q in enumerate(quantities)]


class StatisticsTest(unittest.TestCase):
    def test_population_not_sample_standard_deviation(self) -> None:
        values = [Decimal(v) for v in (2, 4, 4, 4, 5, 5, 7, 9)]
        result = statistics(values)
        # Hand computation: mean 5, Σ(q − 5)² = 32, population variance 32/8 = 4 → σ = 2 exactly.
        self.assertEqual(result["std_dev"], Decimal("2.000000"))
        sample = stdlib_statistics.stdev([float(v) for v in values])  # 2.138…: must NOT be used
        self.assertNotEqual(result["std_dev"], Decimal(f"{sample:.6f}"))
        self.assertEqual(result["mean"], Decimal("5.000000"))
        self.assertEqual(result["cv"], Decimal("0.400000"))
        self.assertEqual((result["periods_used"], result["zero_periods"]), (8, 0))

    def test_irrational_root_is_rounded_half_even_to_six_decimals(self) -> None:
        # [1, 2]: mean 1.5, variance 0.25 → σ 0.5; [0, 1, 2]: variance 2/3 → σ = 0.816496580927726…
        self.assertEqual(statistics([Decimal(1), Decimal(2)])["std_dev"], Decimal("0.500000"))
        result = statistics([Decimal(0), Decimal(1), Decimal(2)])
        self.assertEqual(result["std_dev"], Decimal("0.816497"))
        self.assertEqual(result["cv"], Decimal("0.816497"))  # σ / 1
        self.assertEqual(result["zero_periods"], 1)

    def test_n_equals_one_gives_zero(self) -> None:
        result = statistics([Decimal(7)])
        self.assertEqual((result["periods_used"], result["std_dev"], result["mean"], result["cv"]),
                         (1, Decimal("0.000000"), Decimal("7.000000"), Decimal("0.000000")))

    def test_n_equals_zero_gives_nulls(self) -> None:
        self.assertEqual(statistics([]), {"periods_used": 0, "mean": None, "std_dev": None, "cv": None,
                                          "zero_periods": None})

    def test_mean_zero_gives_null_cv(self) -> None:
        result = statistics([Decimal(0), Decimal(0)])
        self.assertEqual((result["mean"], result["std_dev"], result["cv"], result["zero_periods"]),
                         (Decimal("0.000000"), Decimal("0.000000"), None, 2))

    def test_population_std_helper(self) -> None:
        self.assertEqual(population_std([Fraction(1), Fraction(3)], Fraction(2)), Decimal(1))


class PeriodsTest(unittest.TestCase):
    def test_weekly_iso_weeks_with_partial_edges(self) -> None:
        # 2025-12-03 is a Wednesday; 2025-12-21 a Sunday. Weeks: [12-01,12-08) partial, [12-08,12-15),
        # [12-15,12-22) complete.
        rows = days(D(2025, 12, 3), [1] * 19, stockout={6})  # 12-03 … 12-21; 12-09 stockout
        result = build_history(rows, D(2025, 12, 3), D(2025, 12, 21), "weekly")
        periods = result["periods"]
        self.assertEqual([(p["period_start"], p["period_end"]) for p in periods],
                         [(D(2025, 12, 1), D(2025, 12, 8)), (D(2025, 12, 8), D(2025, 12, 15)), (D(2025, 12, 15), D(2025, 12, 22))])
        self.assertEqual([p["days"] for p in periods], [7, 7, 7])
        self.assertEqual([p["days_observed"] for p in periods], [5, 7, 7])
        self.assertEqual([p["quantity"] for p in periods], [5, 7, 7])
        self.assertEqual([p["stockout_days"] for p in periods], [0, 1, 0])
        self.assertEqual([p["complete"] for p in periods], [False, True, True])
        self.assertEqual(result["statistics"]["periods_used"], 2)
        self.assertEqual(result["statistics"]["std_dev"], Decimal("0.000000"))

    def test_monthly_calendar_months(self) -> None:
        rows = days(D(2024, 1, 1), [1] * 60)  # 2024-01-01 … 2024-02-29 (leap year)
        result = build_history(rows, D(2024, 1, 1), D(2024, 3, 10), "monthly")
        periods = result["periods"]
        self.assertEqual([(p["period_start"], p["period_end"], p["days"]) for p in periods],
                         [(D(2024, 1, 1), D(2024, 2, 1), 31), (D(2024, 2, 1), D(2024, 3, 1), 29), (D(2024, 3, 1), D(2024, 4, 1), 31)])
        self.assertEqual([p["complete"] for p in periods], [True, True, False])
        self.assertEqual([p["quantity"] for p in periods], [31, 29, 0])
        stats = result["statistics"]
        # Complete months: 31 and 29 → mean 30, σ = 1 (population).
        self.assertEqual((stats["mean"], stats["std_dev"]), (Decimal("30.000000"), Decimal("1.000000")))
        # Exactly the statistics of DT-067: no others.
        self.assertEqual(set(stats), {"periods_used", "mean", "std_dev", "cv", "zero_periods"})

    def test_daily_and_missing_days_are_not_zero(self) -> None:
        rows = days(D(2025, 1, 1), [3, 0, 5])
        del rows[1]  # 2025-01-02 has no row: not observed, not zero
        result = build_history(rows, D(2025, 1, 1), D(2025, 1, 3), "daily")
        self.assertEqual([p["complete"] for p in result["periods"]], [True, False, True])
        self.assertEqual([p["days_observed"] for p in result["periods"]], [1, 0, 1])
        stats = result["statistics"]
        self.assertEqual((stats["periods_used"], stats["zero_periods"], stats["mean"]), (2, 0, Decimal("4.000000")))

    def test_observed_zero_counts_as_zero_period(self) -> None:
        result = build_history(days(D(2025, 1, 1), [0, 2]), D(2025, 1, 1), D(2025, 1, 2), "daily")
        self.assertEqual(result["statistics"]["zero_periods"], 1)

    def test_empty_range(self) -> None:
        result = build_history([], D(2025, 1, 3), D(2025, 1, 2), "weekly")
        self.assertEqual(result["periods"], [])
        self.assertEqual(result["statistics"]["periods_used"], 0)

    def test_unknown_granularity(self) -> None:
        with self.assertRaises(ValueError):
            build_history([], D(2025, 1, 1), D(2025, 1, 2), "yearly")


if __name__ == "__main__":
    unittest.main()
