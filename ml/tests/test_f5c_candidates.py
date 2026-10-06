"""F5c candidates (`DT-092`): Holt, Holt-Winters, Croston, SBA and TSB by hand, properties and the `DT-074` boundary."""

from __future__ import annotations

import math
import unittest
from decimal import Decimal
from unittest import mock

from ml.candidates import (
    CANDIDATE_NAMES,
    CROSTON_NAME,
    HOLT_NAME,
    HOLT_WINTERS_NAME,
    SBA_NAME,
    TSB_NAME,
    CandidateConfig,
    _croston,
    _holt,
    _holt_winters,
    _tsb,
    candidate_forecast,
    contract_points,
    fit,
    raw_points,
)
from ml.models import BoundaryError

CONFIG = CandidateConfig()


class HandComputedTest(unittest.TestCase):
    def test_holt_by_hand(self) -> None:
        # State after week 2: level 12, trend 2. Week 3: f = 14, e = −1; level = 0.5·13 + 0.5·14 = 13.5;
        # trend = 0.1·(13.5 − 12) + 0.9·2 = 1.95.
        run = _holt([10.0, 12.0, 13.0], 0.5, 0.1)
        self.assertEqual(run.squared, [1.0])
        self.assertAlmostEqual(run.forecast(3, 1), 15.45, places=12)
        self.assertAlmostEqual(run.forecast(3, 4), 13.5 + 4 * 1.95, places=12)
        self.assertEqual(run.first_origin, 2)

    def test_croston_and_sba_by_hand(self) -> None:
        # First demand in week 3: size 6, interval 3 → 2. Weeks 4, 5: errors −2, −2. Week 6: demand 3, error 1;
        # size 6 + 0.5(3 − 6) = 4.5, interval 3 + 0.5((6 − 3) − 3) = 3 → 1.5.
        y = [0.0, 0.0, 6.0, 0.0, 0.0, 3.0]
        run = _croston(y, 0.5, 1.0)
        self.assertEqual(run.squared, [4.0, 4.0, 1.0])
        self.assertAlmostEqual(run.forecast(6, 1), 1.5, places=12)
        sba = _croston(y, 0.5, 0.75)
        self.assertAlmostEqual(sba.forecast(3, 1), 1.5, places=12)
        self.assertAlmostEqual(sba.forecast(6, 7), 1.125, places=12)  # flat over the horizon

    def test_tsb_by_hand(self) -> None:
        # Size 6, probability 1/3 → 2. Week 4: e = −2, p = 1/6 → 1. Week 5: e = −1, p = 1/12 → 0.5.
        # Week 6: e = 2.5; size 4.5; p = 1/12 + 0.5(1 − 1/12) = 13/24 → 2.4375.
        run = _tsb([0.0, 0.0, 6.0, 0.0, 0.0, 3.0], 0.5, 0.5)
        self.assertEqual(run.squared, [4.0, 1.0, 6.25])
        self.assertAlmostEqual(run.forecast(6, 1), 2.4375, places=12)

    def test_holt_winters_recovers_trend_and_season(self) -> None:
        y = [100.0 + 0.5 * t + (30.0 if t % 52 == 10 else 0.0) for t in range(130)]
        chosen = fit(HOLT_WINTERS_NAME, y, CONFIG)
        self.assertLess(chosen.sse, 1e-9)
        points = raw_points(HOLT_WINTERS_NAME, y, chosen.params)
        for h, value in enumerate(points, start=1):
            t = 129 + h
            self.assertAlmostEqual(value, 100.0 + 0.5 * t + (30.0 if t % 52 == 10 else 0.0), places=6)

    def test_holt_winters_needs_two_seasons(self) -> None:
        with self.assertRaises(ValueError):
            _holt_winters([1.0] * 103, 0.1, 0.1, 0.1)
        self.assertIsNone(candidate_forecast(HOLT_WINTERS_NAME, [5.0] * 103, CONFIG))
        self.assertIsNotNone(candidate_forecast(HOLT_WINTERS_NAME, [5.0] * 104, CONFIG))


class PropertiesTest(unittest.TestCase):
    def test_constant_series(self) -> None:
        for name in CANDIDATE_NAMES:
            fc = candidate_forecast(name, [7.0] * 110, CONFIG)
            self.assertIsNotNone(fc, name)
            # SBA is biased on purpose by 1 − α/2 (it corrects Croston for intermittent demand).
            expected = 7.0 * (1 - fit(name, [7.0] * 110, CONFIG).params[0] / 2) if name == SBA_NAME else 7.0
            self.assertTrue(all(abs(float(p) - expected) < 1e-6 for p in fc.points), name)
            self.assertTrue(all(lo <= p <= hi for lo, p, hi in zip(fc.lowers, fc.points, fc.uppers)), name)
            self.assertEqual(fit(name, [7.0] * 110, CONFIG).params, CONFIG.grid(name)[0], name)  # ties → first

    def test_all_zero_series_forecasts_zero(self) -> None:
        for name in (CROSTON_NAME, SBA_NAME, TSB_NAME):
            fc = candidate_forecast(name, [0.0] * 30, CONFIG)
            self.assertEqual(set(fc.points) | set(fc.lowers) | set(fc.uppers), {Decimal("0.000000")}, name)

    def test_empty_and_short_series_are_not_eligible(self) -> None:
        for name in CANDIDATE_NAMES:
            self.assertIsNone(candidate_forecast(name, [], CONFIG), name)
            self.assertIsNone(candidate_forecast(name, [3.0] * 24, CONFIG), name)

    def test_intermittent_methods_are_non_negative(self) -> None:
        y = [0.0, 4.0, 0.0, 0.0, 9.0, 0.0, 1.0] * 6
        for name in (CROSTON_NAME, SBA_NAME, TSB_NAME):
            fc = candidate_forecast(name, y, CONFIG)
            self.assertTrue(all(v >= 0 for v in fc.points + fc.lowers), name)

    def test_negative_forecast_cannot_cross_the_boundary(self) -> None:
        y = [float(200 - 8 * t) for t in range(25)]  # steep decline: Holt goes below zero within 14 weeks
        with self.assertRaises(BoundaryError):
            candidate_forecast(HOLT_NAME, y, CONFIG)
        with self.assertRaises(BoundaryError):
            contract_points(HOLT_NAME, y, fit(HOLT_NAME, y, CONFIG).params)

    def test_tiny_negative_rounds_to_zero_and_is_valid(self) -> None:
        # −1e−9 becomes 0.000000 after the DT-074 conversion: valid, not a failure; −0.5 is a failure.
        with mock.patch("ml.candidates.raw_points", return_value=[-1e-9] * 14):
            self.assertEqual(contract_points(HOLT_NAME, [1.0] * 30, (0.1, 0.01)), (Decimal(0),) * 14)
        with mock.patch("ml.candidates.raw_points", return_value=[-0.5] * 14):
            with self.assertRaises(BoundaryError):
                contract_points(HOLT_NAME, [1.0] * 30, (0.1, 0.01))
        with mock.patch("ml.candidates.raw_points", return_value=[math.nan] * 14):
            with self.assertRaises(BoundaryError):
                contract_points(HOLT_NAME, [1.0] * 30, (0.1, 0.01))

    def test_grids_are_small_and_exact(self) -> None:
        for name in CANDIDATE_NAMES:
            grid = CONFIG.grid(name)
            self.assertLessEqual(len(grid), 48, name)
            self.assertEqual(grid, sorted(grid), name)


if __name__ == "__main__":
    unittest.main()
