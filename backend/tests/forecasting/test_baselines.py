"""Weekly aggregation, the three baselines, the minimum histories and the primary chain (`DT-056`).

Every expected value is computed by hand in the test.
"""

from __future__ import annotations

import datetime as dt
import unittest
from decimal import Decimal
from fractions import Fraction

from app.forecasting import (
    MOVING_AVERAGE,
    NAIVE,
    SEASONAL_NAIVE,
    ConfidenceFlag,
    UnavailableReason,
    forecast,
    period_bounds,
)
from app.forecasting.weekly import weekly_totals

from ._builders import A, DAY, daily_request, weekly_request


def D(value: str) -> Decimal:
    return Decimal(value)


class WeeklyAggregationTest(unittest.TestCase):
    def test_exactly_seven_days_is_one_week(self) -> None:
        self.assertEqual(weekly_totals([Fraction(v) for v in [1, 2, 3, 4, 5, 6, 7]]), [28])

    def test_leftover_oldest_days_are_discarded(self) -> None:
        # 10 days: the 3 oldest (100, 200, 300) are discarded; the week is the last 7.
        daily = [Fraction(v) for v in [100, 200, 300, 1, 1, 1, 1, 1, 1, 1]]
        self.assertEqual(weekly_totals(daily), [7])

    def test_weeks_are_anchored_on_as_of_date(self) -> None:
        # 14 days: the value on A − 7 belongs to Y_1, the one on A − 6 to Y_2 = [A − 6, A].
        daily = [Fraction(0)] * 14
        daily[6] = Fraction(5)  # A − 7
        daily[7] = Fraction(9)  # A − 6
        self.assertEqual(weekly_totals(daily), [5, 9])

    def test_less_than_a_week_gives_no_week(self) -> None:
        self.assertEqual(weekly_totals([Fraction(1)] * 6), [])

    def test_periods_start_on_as_of_plus_one(self) -> None:
        self.assertEqual(period_bounds(A, 1), (A + DAY, A + DAY * 8))
        self.assertEqual(period_bounds(A, 2), (A + DAY * 8, A + DAY * 15))
        self.assertEqual(period_bounds(A, 14), (A + DAY * 92, A + DAY * 99))


class NaiveTest(unittest.TestCase):
    def test_hand_computed_naive(self) -> None:
        # Y_j = j − 1 (j = 1…25): F = Y_25 = 24; every error at h is Y_{t+h} − Y_t = h, so
        # q_lo = q_hi = h, L = F and U = F + h.
        result = forecast(weekly_request(list(range(25))))
        series = result.series_for(NAIVE.name)
        self.assertEqual(len(series.periods), 14)
        for h, period in enumerate(series.periods, start=1):
            self.assertEqual(period.period_start, A + DAY * (1 + 7 * (h - 1)))
            self.assertEqual(period.period_end, period.period_start + DAY * 7)
            self.assertEqual(period.predicted_quantity, D("24.000000"))
            self.assertEqual(period.lower_bound, D("24.000000"))
            self.assertEqual(period.upper_bound, Decimal(24 + h).quantize(D("0.000001")))

    def test_all_fourteen_points_are_the_last_week(self) -> None:
        weeks = [3, 0, 8] * 9  # 27 weeks, the last is 8
        series = forecast(weekly_request(weeks)).series_for(NAIVE.name)
        self.assertEqual({p.predicted_quantity for p in series.periods}, {D("8")})

    def test_last_week_zero_gives_zero_point_and_a_valid_interval(self) -> None:
        weeks = [5] * 24 + [0]
        series = forecast(weekly_request(weeks)).series_for(NAIVE.name)
        for period in series.periods:
            self.assertEqual(period.predicted_quantity, 0)
            self.assertEqual(period.lower_bound, 0)
            self.assertGreaterEqual(period.upper_bound, 0)


class SeasonalNaiveTest(unittest.TestCase):
    def test_hand_computed_seasonal_naive(self) -> None:
        # Y_j = j mod 52 (j = 1…63): F_h = Y_{63+h−52} = Y_{11+h} = 11 + h; every error is
        # Y_{t+h} − Y_{t+h−52} = 0, so L = F = U.
        weeks = [j % 52 for j in range(1, 64)]
        series = forecast(weekly_request(weeks)).series_for(SEASONAL_NAIVE.name)
        self.assertIsNotNone(series)
        for h, period in enumerate(series.periods, start=1):
            expected = Decimal(11 + h)
            self.assertEqual(
                (period.lower_bound, period.predicted_quantity, period.upper_bound),
                (expected, expected, expected),
            )

    def test_uses_weeks_n_minus_51_to_n_minus_38(self) -> None:
        weeks = [0] * 63
        weeks[63 - 51 - 1] = 7  # Y_{n−51}: the point of h = 1
        weeks[63 - 38 - 1] = 9  # Y_{n−38}: the point of h = 14
        series = forecast(weekly_request(weeks)).series_for(SEASONAL_NAIVE.name)
        self.assertEqual(series.periods[0].predicted_quantity, 7)
        self.assertEqual(series.periods[13].predicted_quantity, 9)
        self.assertEqual({p.predicted_quantity for p in series.periods[1:13]}, {0})

    def test_not_computed_without_enough_history(self) -> None:
        result = forecast(weekly_request([1] * 62))
        self.assertIsNone(result.series_for(SEASONAL_NAIVE.name))
        self.assertIn(
            (SEASONAL_NAIVE, UnavailableReason.INSUFFICIENT_HISTORY),
            [(u.definition, u.reason) for u in result.unavailable],
        )


class MovingAverageTest(unittest.TestCase):
    def test_hand_computed_moving_average(self) -> None:
        # Y_j = j (j = 1…37): F = (25 + … + 37) / 13 = 31; every error at h is
        # (t + h) − (t − 6) = h + 6, so L = F and U = 31 + h + 6.
        series = forecast(weekly_request(list(range(1, 38)))).series_for(MOVING_AVERAGE.name)
        for h, period in enumerate(series.periods, start=1):
            self.assertEqual(period.predicted_quantity, 31)
            self.assertEqual(period.lower_bound, 31)
            self.assertEqual(period.upper_bound, 37 + h)

    def test_window_is_the_last_thirteen_weeks_and_never_shortened(self) -> None:
        weeks = [1000] * 24 + [1] * 12 + [2]  # 37 weeks; the window holds twelve 1 and one 2
        series = forecast(weekly_request(weeks)).series_for(MOVING_AVERAGE.name)
        # 14/13 = 1.0769230769… → 1.076923 at six decimals.
        self.assertEqual({p.predicted_quantity for p in series.periods}, {D("1.076923")})
        self.assertIsNone(forecast(weekly_request([1] * 36)).series_for(MOVING_AVERAGE.name))


class MinimumHistoryAndFallbackTest(unittest.TestCase):
    def computed(self, weeks: int) -> list[str]:
        return [s.definition.name for s in forecast(weekly_request([2] * weeks)).series]

    def test_minimum_histories(self) -> None:
        self.assertEqual(self.computed(24), [])
        self.assertEqual(self.computed(25), [NAIVE.name])
        self.assertEqual(self.computed(36), [NAIVE.name])
        self.assertEqual(self.computed(37), [NAIVE.name, MOVING_AVERAGE.name])
        self.assertEqual(self.computed(62), [NAIVE.name, MOVING_AVERAGE.name])
        self.assertEqual(self.computed(63), [NAIVE.name, SEASONAL_NAIVE.name, MOVING_AVERAGE.name])

    def test_primary_chain(self) -> None:
        for weeks, primary, flag in (
            (63, MOVING_AVERAGE, ConfidenceFlag.STANDARD),
            (37, MOVING_AVERAGE, ConfidenceFlag.STANDARD),
            (36, NAIVE, ConfidenceFlag.INSUFFICIENT_HISTORY),
            (25, NAIVE, ConfidenceFlag.INSUFFICIENT_HISTORY),
        ):
            with self.subTest(weeks=weeks):
                result = forecast(weekly_request([2] * weeks))
                self.assertEqual(result.primary, primary)
                self.assertEqual(result.confidence_flag, flag)
                self.assertIsNone(result.no_forecast_reason)

    def test_no_forecast_below_twenty_five_weeks(self) -> None:
        for weeks in (0, 1, 24):
            with self.subTest(weeks=weeks):
                result = forecast(daily_request([1] * (7 * weeks + 3)))
                self.assertIsNone(result.primary)
                self.assertIsNone(result.confidence_flag)
                self.assertEqual(result.no_forecast_reason, UnavailableReason.INSUFFICIENT_HISTORY)
                self.assertEqual(result.series, ())
                self.assertEqual(len(result.unavailable), 3)

    def test_seasonal_naive_is_never_primary(self) -> None:
        result = forecast(weekly_request([j % 52 for j in range(1, 100)]))
        self.assertEqual(result.primary, MOVING_AVERAGE)
        self.assertIsNotNone(result.series_for(SEASONAL_NAIVE.name))

    def test_result_metadata(self) -> None:
        result = forecast(weekly_request([2] * 40, leftover=[9, 9]))
        self.assertEqual(result.history_weeks, 40)
        self.assertEqual(result.confidence_level, D("0.80"))
        self.assertEqual(result.method_used, "BASELINE")
        self.assertEqual(result.stockout_treatment, "NONE_RAW_CONSUMPTION_V1")
        self.assertEqual((result.product_id, result.location_id, result.as_of_date), (1, 1, A))


if __name__ == "__main__":
    unittest.main()
