"""Nearest-rank quantiles, interval bounds and quantization (`DT-056` points 4 to 6 and 11)."""

from __future__ import annotations

import unittest
from decimal import Decimal
from fractions import Fraction

from app.forecasting import MOVING_AVERAGE, NAIVE, forecast
from app.forecasting.exact import quantize
from app.forecasting.interval import horizon_errors, interval, nearest_rank_bounds
from app.forecasting.baselines import predict_moving_average, predict_naive, predict_seasonal_naive

from ._builders import weekly_request

F = Fraction


class NearestRankTest(unittest.TestCase):
    def test_m_eleven_gives_second_and_tenth(self) -> None:
        errors = [F(v) for v in (7, -3, 11, 0, 5, -8, 2, 9, -1, 4, 6)]  # sorted: -8 -3 -1 0 2 4 5 6 7 9 11
        self.assertEqual(nearest_rank_bounds(errors), (F(-3), F(9)))

    def test_other_sizes(self) -> None:
        for m, low, high in ((12, 2, 11), (20, 2, 18), (21, 3, 19), (100, 10, 90)):
            with self.subTest(m=m):
                errors = [F(i) for i in range(1, m + 1)]
                self.assertEqual(nearest_rank_bounds(errors), (F(low), F(high)))

    def test_fewer_than_eleven_errors_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            nearest_rank_bounds([F(1)] * 10)


class BoundsTest(unittest.TestCase):
    def test_all_errors_negative(self) -> None:
        self.assertEqual(interval(F(10), F(-4), F(-1)), (F(6), F(10)))

    def test_all_errors_positive(self) -> None:
        self.assertEqual(interval(F(10), F(2), F(5)), (F(10), F(15)))

    def test_all_errors_zero(self) -> None:
        self.assertEqual(interval(F(10), F(0), F(0)), (F(10), F(10)))

    def test_asymmetric_errors(self) -> None:
        self.assertEqual(interval(F(10), F(-1), F(7)), (F(9), F(17)))

    def test_lower_bound_is_floored_at_zero(self) -> None:
        self.assertEqual(interval(F(3), F(-8), F(2)), (F(0), F(5)))
        self.assertEqual(interval(F(0), F(-2), F(4)), (F(0), F(4)))


class HorizonErrorsTest(unittest.TestCase):
    WEEKS = [F(j) for j in range(1, 71)]

    def test_counts_per_baseline(self) -> None:
        n = len(self.WEEKS)
        for h in (1, 7, 14):
            with self.subTest(h=h):
                self.assertEqual(len(horizon_errors(self.WEEKS, predict_naive, h)), n - h)
                self.assertEqual(len(horizon_errors(self.WEEKS, predict_moving_average, h)), n - h - 12)
                self.assertEqual(len(horizon_errors(self.WEEKS, predict_seasonal_naive, h)), n - 52)

    def test_errors_use_only_the_origin_history(self) -> None:
        # Naïve on Y_j = j: every error at h is exactly h.
        self.assertEqual(set(horizon_errors(self.WEEKS, predict_naive, 5)), {F(5)})


class QuantizeTest(unittest.TestCase):
    def test_half_even_without_float(self) -> None:
        self.assertEqual(quantize(F(5, 10**7), 6), Decimal("0.000000"))
        self.assertEqual(quantize(F(15, 10**7), 6), Decimal("0.000002"))
        self.assertEqual(quantize(F(25, 10**7), 6), Decimal("0.000002"))
        self.assertEqual(quantize(F(2, 3), 6), Decimal("0.666667"))
        self.assertEqual(quantize(F(14, 13), 6), Decimal("1.076923"))
        self.assertEqual(quantize(F(215), 6), Decimal("215.000000"))
        self.assertEqual(quantize(F(215), 6).as_tuple().exponent, -6)


class IntervalInvariantTest(unittest.TestCase):
    SERIES = {
        "intermittent": [0, 0, 0, 12, 0, 0, 0, 0, 30, 0, 0, 0, 0, 0, 7] * 5,
        "zero": [0] * 70,
        "constant": [6] * 70,
        "growing": list(range(70)),
        "erratic": [(j * 37) % 23 for j in range(70)],
    }

    def test_bounds_are_ordered_non_negative_and_six_decimals(self) -> None:
        for name, weeks in self.SERIES.items():
            result = forecast(weekly_request(weeks))
            self.assertEqual(len(result.series), 3, name)
            for series in result.series:
                for period in series.periods:
                    with self.subTest(series=name, baseline=series.definition.name):
                        self.assertTrue(0 <= period.lower_bound <= period.predicted_quantity <= period.upper_bound)
                        for value in (period.lower_bound, period.predicted_quantity, period.upper_bound):
                            self.assertIsInstance(value, Decimal)
                            self.assertEqual(value.as_tuple().exponent, -6)

    def test_zero_series_gives_zero_interval(self) -> None:
        for series in forecast(weekly_request(self.SERIES["zero"])).series:
            for period in series.periods:
                self.assertEqual((period.lower_bound, period.predicted_quantity, period.upper_bound), (0, 0, 0))

    def test_constant_series_gives_a_degenerate_interval(self) -> None:
        series = forecast(weekly_request(self.SERIES["constant"])).series_for(MOVING_AVERAGE.name)
        self.assertEqual({(p.lower_bound, p.upper_bound) for p in series.periods}, {(Decimal(6), Decimal(6))})

    def test_interval_widens_with_the_horizon_for_a_trend(self) -> None:
        series = forecast(weekly_request(self.SERIES["growing"])).series_for(NAIVE.name)
        uppers = [p.upper_bound for p in series.periods]
        self.assertEqual(uppers, sorted(uppers))
        self.assertLess(uppers[0], uppers[-1])


if __name__ == "__main__":
    unittest.main()
