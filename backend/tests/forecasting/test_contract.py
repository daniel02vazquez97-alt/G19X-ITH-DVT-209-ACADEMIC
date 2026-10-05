"""Contract of `ForecastProvider` (`DT-046`): accepted types and every rejection."""

from __future__ import annotations

import dataclasses
import datetime as dt
import unittest
from decimal import Decimal
from fractions import Fraction

from app.forecasting import (
    MOVING_AVERAGE,
    NAIVE,
    SEASONAL_NAIVE,
    ForecastRequest,
    InvalidForecastInputError,
    build_request,
    forecast,
)

from ._builders import A, DAY, daily_request


class AcceptedQuantitiesTest(unittest.TestCase):
    def test_int_decimal_and_fraction_are_accepted(self) -> None:
        for value in (3, Decimal("2.5"), Fraction(7, 3)):
            with self.subTest(value=value):
                result = forecast(daily_request([value] * 7 * 25))
                self.assertEqual(result.primary, NAIVE)

    def test_stockout_flags_travel_but_do_not_change_the_result(self) -> None:
        daily = [i % 9 for i in range(7 * 40)]
        plain = forecast(daily_request(daily))
        flagged = forecast(daily_request(daily, flags=[i % 3 == 0 for i in range(len(daily))]))
        self.assertEqual(plain.series, flagged.series)

    def test_the_request_is_immutable(self) -> None:
        request = daily_request([1] * 7)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            request.as_of_date = A + DAY  # type: ignore[misc]


class RejectedInputTest(unittest.TestCase):
    def assertRejected(self, code: str, **changes: object) -> None:
        base = dict(
            product_id=1,
            location_id=1,
            as_of_date=A,
            history_start=A - DAY * 6,
            daily_consumption=(1,) * 7,
            daily_stockout_flags=(False,) * 7,
        )
        base.update(changes)
        with self.assertRaises(InvalidForecastInputError) as caught:
            ForecastRequest(**base)  # type: ignore[arg-type]
        self.assertEqual(caught.exception.code, code)

    def test_float_is_rejected(self) -> None:
        self.assertRejected("INVALID_TYPE", daily_consumption=(1,) * 6 + (1.0,))

    def test_bool_is_not_a_quantity(self) -> None:
        self.assertRejected("INVALID_TYPE", daily_consumption=(1,) * 6 + (True,))

    def test_nan_and_infinity_are_rejected(self) -> None:
        for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity"), Decimal("sNaN")):
            with self.subTest(value=value):
                self.assertRejected("NOT_FINITE", daily_consumption=(1,) * 6 + (value,))

    def test_negative_consumption_is_rejected(self) -> None:
        self.assertRejected("NEGATIVE_QUANTITY", daily_consumption=(1,) * 6 + (-1,))

    def test_history_beyond_as_of_date_is_rejected(self) -> None:
        self.assertRejected("FUTURE_DATE", daily_consumption=(1,) * 8, daily_stockout_flags=(False,) * 8)
        self.assertRejected("FUTURE_DATE", history_start=A + DAY)

    def test_history_that_does_not_reach_as_of_date_is_rejected(self) -> None:
        self.assertRejected("INCOMPLETE_HISTORY", daily_consumption=(1,) * 6, daily_stockout_flags=(False,) * 6)

    def test_lengths_must_match(self) -> None:
        self.assertRejected("LENGTH_MISMATCH", daily_stockout_flags=(False,) * 6)

    def test_flags_must_be_bool(self) -> None:
        self.assertRejected("INVALID_TYPE", daily_stockout_flags=(False,) * 6 + (0,))

    def test_containers_ids_and_dates_are_typed(self) -> None:
        self.assertRejected("INVALID_TYPE", daily_consumption=[1] * 7)
        self.assertRejected("INVALID_TYPE", product_id=True)
        self.assertRejected("INVALID_TYPE", as_of_date=dt.datetime(2025, 12, 31))


class BuildRequestTest(unittest.TestCase):
    def rows(self, days: int, end: dt.date = A) -> list[tuple[dt.date, object, bool]]:
        return [(end - DAY * i, i, False) for i in range(days)]

    def test_rows_in_any_order_become_a_contiguous_request(self) -> None:
        request = build_request(1, 1, A, self.rows(10))
        self.assertEqual(request.history_start, A - DAY * 9)
        self.assertEqual(request.daily_consumption, tuple(range(9, -1, -1)))

    def assertRejected(self, code: str, rows: list[tuple[dt.date, object, bool]]) -> None:
        with self.assertRaises(InvalidForecastInputError) as caught:
            build_request(1, 1, A, rows)
        self.assertEqual(caught.exception.code, code)

    def test_gap_is_rejected_not_imputed(self) -> None:
        rows = self.rows(10)
        del rows[4]
        self.assertRejected("GAP", rows)

    def test_future_row_is_rejected(self) -> None:
        self.assertRejected("FUTURE_DATE", self.rows(10) + [(A + DAY, 1, False)])

    def test_duplicate_day_is_rejected(self) -> None:
        self.assertRejected("DUPLICATE_DATE", self.rows(10) + [(A, 1, False)])

    def test_history_must_reach_as_of_date(self) -> None:
        self.assertRejected("INCOMPLETE_HISTORY", self.rows(10, end=A - DAY))
        self.assertRejected("INCOMPLETE_HISTORY", [])


class DefinitionsTest(unittest.TestCase):
    COMMON = {
        "horizon_weeks": 14,
        "history_weeks": "ANCHORED_AT_AS_OF_FULL_WEEKS",
        "interval": {
            "method": "EMPIRICAL_HORIZON_ERROR_QUANTILES",
            "confidence_level": "0.80",
            "quantile_rule": "NEAREST_RANK",
            "min_errors_per_horizon": 11,
            "lower_floor": "0",
        },
        "quantization": {"scale": 6, "rounding": "ROUND_HALF_EVEN"},
        "stockout_treatment": "NONE_RAW_CONSUMPTION_V1",
    }

    def test_the_three_versions_and_their_hyperparameters(self) -> None:
        self.assertEqual(
            [(d.name, d.version, d.algorithm) for d in (NAIVE, SEASONAL_NAIVE, MOVING_AVERAGE)],
            [
                ("baseline.naive", "1.0.0", "NAIVE"),
                ("baseline.seasonal_naive", "1.0.0", "SEASONAL_NAIVE"),
                ("baseline.moving_average", "1.0.0", "MOVING_AVERAGE"),
            ],
        )
        self.assertEqual(NAIVE.hyperparameters, self.COMMON)
        self.assertEqual(SEASONAL_NAIVE.hyperparameters, {**self.COMMON, "season_length_weeks": 52})
        self.assertEqual(MOVING_AVERAGE.hyperparameters, {**self.COMMON, "window_weeks": 13})

    def test_hyperparameters_cannot_be_mutated_through_the_definition(self) -> None:
        NAIVE.hyperparameters["horizon_weeks"] = 99
        NAIVE.hyperparameters["interval"]["confidence_level"] = "0.95"
        self.assertEqual(NAIVE.hyperparameters, self.COMMON)


if __name__ == "__main__":
    unittest.main()
