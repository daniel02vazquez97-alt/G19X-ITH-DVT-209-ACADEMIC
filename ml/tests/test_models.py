"""Baselines equal to calling U3 directly; SES by hand; the `DT-074` boundary."""

from __future__ import annotations

import datetime as _dt
import math
import unittest
from decimal import ROUND_HALF_EVEN, Decimal

from app.forecasting import build_request, forecast
from ml.backtest import run_series_cut
from ml.config import F5aConfig
from ml.data import load_dataset
from ml.models import SES_NAME, BoundaryError, _nearest_rank, fit_ses, ses_forecast, to_contract
from ml.tests.fixtures import TempDataset

CUT = _dt.date(2024, 3, 27)


class BaselinesTest(unittest.TestCase):
    def test_baselines_equal_u3_called_directly(self) -> None:
        with TempDataset() as path:
            ds = load_dataset(path)
        for key in [(1, 1), (2, 1), (3, 1)]:
            sc = run_series_cut(ds, key, CUT, F5aConfig())
            rows = [(r.day, r.quantity, r.stockout) for r in ds.history(key, CUT)]
            direct = forecast(build_request(key[0], key[1], CUT, rows))
            self.assertEqual(
                {s.definition.name for s in direct.series} | {SES_NAME},
                set(sc.forecasts),
                key,
            )
            for series in direct.series:
                mine = sc.forecasts[series.definition.name]
                self.assertEqual(mine.points, tuple(p.predicted_quantity for p in series.periods))
                self.assertEqual(mine.lowers, tuple(p.lower_bound for p in series.periods))
                self.assertEqual(mine.uppers, tuple(p.upper_bound for p in series.periods))


class SesTest(unittest.TestCase):
    def test_three_points_by_hand(self) -> None:
        # Y = 10, 20, 10. level_1 = 10; e_2 = 10; level_2 = 10 + 10α; e_3 = −10α → SSE = 100 + 100α².
        fit = fit_ses([10.0, 20.0, 10.0], F5aConfig())
        self.assertEqual(fit.alpha, 0.05)
        self.assertAlmostEqual(fit.sse, 100.25, places=12)
        self.assertAlmostEqual(fit.levels[1], 10.5, places=12)
        self.assertAlmostEqual(fit.levels[2], 10.475, places=12)

    def test_trend_by_hand(self) -> None:
        # Y = 0, 10, 20, 30: SSE(α) = 100 + (20 − 10α)² + (30 − 30α + 10α²)², decreasing → α = 0.95.
        fit = fit_ses([0.0, 10.0, 20.0, 30.0], F5aConfig())
        a = 0.95
        self.assertEqual(fit.alpha, a)
        self.assertAlmostEqual(fit.sse, 100 + (20 - 10 * a) ** 2 + (30 - 30 * a + 10 * a * a) ** 2, places=9)

    def test_ties_keep_the_smallest_alpha(self) -> None:
        self.assertEqual(fit_ses([7.0] * 30, F5aConfig()).alpha, 0.05)

    def test_grid(self) -> None:
        grid = F5aConfig().ses_alpha_grid
        self.assertEqual(len(grid), 19)
        self.assertEqual(grid[0], 0.05)
        self.assertEqual(grid[-1], 0.95)
        self.assertTrue(all(math.isclose(b - a, 0.05) for a, b in zip(grid, grid[1:])))

    def test_deterministic(self) -> None:
        weeks = [float((i * 37) % 11 + (i % 3)) for i in range(60)]
        first, second = ses_forecast(weeks, F5aConfig()), ses_forecast(weeks, F5aConfig())
        self.assertEqual(first, second)
        assert first is not None
        self.assertEqual(len(set(first.points)), 1)  # flat forecast
        for lo, p, hi in zip(first.lowers, first.points, first.uppers):
            self.assertTrue(Decimal(0) <= lo <= p <= hi)
            self.assertIsInstance(p, Decimal)
            self.assertLessEqual(-p.as_tuple().exponent, 6)

    def test_interval_uses_nearest_rank_of_one_step_errors(self) -> None:
        weeks = [float(10 + (i % 4)) for i in range(25)]
        fc = ses_forecast(weeks, F5aConfig())
        assert fc is not None
        fit = fit_ses(weeks, F5aConfig())
        errors = [weeks[t] - fit.levels[t - 1] for t in range(1, 25)]  # h = 1, origins 1..24
        q_lo, q_hi = _nearest_rank(errors)
        point = fit.levels[-1]
        self.assertEqual(fc.lowers[0], to_contract(max(0.0, point + min(q_lo, 0.0))))
        self.assertEqual(fc.uppers[0], to_contract(point + max(q_hi, 0.0)))

    def test_nearest_rank_ranks(self) -> None:
        errors = [float(i) for i in range(1, 12)]  # m = 11 → e_(2), e_(10)
        self.assertEqual(_nearest_rank(errors), (2.0, 10.0))

    def test_minimum_history(self) -> None:
        self.assertIsNone(ses_forecast([5.0] * 24, F5aConfig()))
        self.assertIsNotNone(ses_forecast([5.0] * 25, F5aConfig()))


class BoundaryTest(unittest.TestCase):
    def test_exact_binary_conversion_not_text(self) -> None:
        # 2.5e-06 is stored slightly above the tie: exact conversion rounds up, text would round to even.
        self.assertEqual(to_contract(2.5e-06), Decimal("0.000003"))
        self.assertEqual(Decimal("2.5e-06").quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN), Decimal("0.000002"))
        self.assertEqual(to_contract(0.1), Decimal("0.100000"))

    def test_non_finite_and_violations_are_not_corrected(self) -> None:
        for bad in (math.nan, math.inf, -math.inf):
            with self.assertRaises(BoundaryError):
                to_contract(bad)
        with self.assertRaises(BoundaryError):
            ses_forecast([-5.0] * 30, F5aConfig())  # negative point: a failure, never clipped


if __name__ == "__main__":
    unittest.main()
