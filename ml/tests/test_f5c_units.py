"""F5c units by hand: strategies of `DT-081`, seasonality, coverage and calibration of US-055, criteria table."""

from __future__ import annotations

import datetime as _dt
import math
import unittest
from fractions import Fraction

from ml.backtest import LR
from ml.cuts import development_cuts, evaluation_end
from ml.f5c.config import STRATEGY_AS_IS, STRATEGY_EXCLUDE, STRATEGY_IMPUTE, Criteria
from ml.f5c.criteria import CUMPLE, NO_CONCLUYENTE, NO_CUMPLE, level1_rows, pairwise_per_cut
from ml.f5c.intervals import coverage_at, fit_widening, needed_widening
from ml.f5c.strategies import imputed_daily, strategy_weeks
from ml.metrics import Observation
from ml.segmentation import lag_autocorrelation, seasonality

F = Fraction


class StrategiesTest(unittest.TestCase):
    imputed_daily = staticmethod(imputed_daily)
    strategy_weeks = staticmethod(strategy_weeks)

    def test_exclude_scales_by_observed_days_and_omits_empty_weeks(self) -> None:
        q = [F(10)] * 7 + [F(10), F(0), F(10), F(10), F(10), F(10), F(10)] + [F(3)] * 7
        f = [False] * 7 + [False, True, False, False, False, False, False] + [True] * 7
        # Week 2: 60 over 6 observed days × 7 = 70; week 3 has no observed day → omitted.
        self.assertEqual(self.strategy_weeks(STRATEGY_EXCLUDE, q, f), [F(70), F(70)])

    def test_impute_uses_the_mean_of_previous_non_stockout_days_only(self) -> None:
        q = [F(4), F(8), F(0), F(100)]
        f = [False, False, True, False]
        self.assertEqual(self.imputed_daily(q, f, 56), [F(4), F(8), F(6), F(100)])  # day 4 (later) never used

    def test_impute_without_donors_keeps_the_consumption(self) -> None:
        q = [F(2), F(1), F(5)]
        f = [True, True, False]
        self.assertEqual(self.imputed_daily(q, f, 56), [F(2), F(1), F(5)])
        # Donors only within the window: day 3's window of 1 day contains a stockout day only.
        self.assertEqual(self.imputed_daily([F(9), F(0), F(0)], [False, True, True], 1), [F(9), F(9), F(0)])

    def test_anchoring_drops_the_oldest_leftover_days(self) -> None:
        q = [F(100)] * 3 + [F(1)] * 14
        self.assertEqual(self.strategy_weeks(STRATEGY_AS_IS, q, [False] * 17), [F(7), F(7)])
        self.assertEqual(self.strategy_weeks(STRATEGY_IMPUTE, q, [False] * 17), [F(7), F(7)])

    def test_strategies_only_change_with_stockouts(self) -> None:
        q = [F(i % 5) for i in range(70)]
        weeks = {s: self.strategy_weeks(s, q, [False] * 70) for s in (STRATEGY_AS_IS, STRATEGY_EXCLUDE, STRATEGY_IMPUTE)}
        self.assertEqual(weeks[STRATEGY_AS_IS], weeks[STRATEGY_EXCLUDE])
        self.assertEqual(weeks[STRATEGY_AS_IS], weeks[STRATEGY_IMPUTE])


class SeasonalityTest(unittest.TestCase):
    def test_seasonal_needs_104_weeks_and_a_significant_lag_52(self) -> None:
        seasonal = [10.0 + (20.0 if t % 52 in (0, 1, 2) else 0.0) for t in range(110)]
        acf, flag = seasonality(seasonal)
        self.assertTrue(flag)
        self.assertGreater(acf, 1.96 / math.sqrt(110))
        self.assertEqual(seasonality(seasonal[:103]), (None, False))
        self.assertFalse(seasonality([float(t % 7) for t in range(110)])[1])
        self.assertIsNone(lag_autocorrelation([5.0] * 60, 52))

    def test_autocorrelation_by_hand(self) -> None:
        # y = 1, 2, 3, 4: mean 2.5; deviations −1.5, −0.5, 0.5, 1.5; lag 1: (0.75 − 0.25 + 0.75) / 5 = 0.25.
        self.assertAlmostEqual(lag_autocorrelation([1.0, 2.0, 3.0, 4.0], 1), 0.25, places=12)


class IntervalsTest(unittest.TestCase):
    def test_needed_widening_by_hand(self) -> None:
        self.assertEqual(needed_widening(10, 6, 14, 12), 0.5)
        self.assertEqual(needed_widening(10, 6, 14, 18), 2.0)
        self.assertEqual(needed_widening(10, 6, 14, 4), 1.5)
        self.assertEqual(needed_widening(10, 10, 14, 9), math.inf)
        self.assertEqual(needed_widening(10, 6, 14, 10), 0.0)

    def test_coverage_by_hand(self) -> None:
        needed = sorted([0.5, 0.9, 1.0, 1.2, math.inf])
        self.assertEqual(coverage_at(needed, 1.0), 3 / 5)
        self.assertEqual(coverage_at(needed, 1.2), 4 / 5)
        self.assertIsNone(coverage_at([], 1.0))

    def test_widening_fit_and_ties(self) -> None:
        needed = [0.5, 0.9, 1.0, 1.2, 1.4, 1.6, 2.0, 2.5, 3.5, math.inf]
        grid = tuple(k / 20 for k in range(10, 61))
        # 0.80 is reached first at k = 2.5 (8 of 10); any k in [2.5, 3.45] ties → the smaller.
        self.assertEqual(fit_widening(needed, grid, 0.80), 2.5)

    def test_calibration_cuts_end_before_the_measured_cut(self) -> None:
        cuts = development_cuts()
        for t in range(8, len(cuts)):
            calib = [c for c in range(len(cuts)) if evaluation_end(cuts[c]) <= cuts[t]]
            self.assertTrue(calib)
            self.assertNotIn(t, calib)
            self.assertTrue(all(evaluation_end(cuts[c]) <= cuts[t] for c in calib))


def _obs(cut: int, product: int, model: str, error: float, segment: str = "SMOOTH") -> Observation:
    """An L + R observation with actual 10 and scale 1, so that its scaled error equals ``error``."""
    as_of = (_dt.date(2024, 3, 27) + _dt.timedelta(days=28 * cut)).isoformat()
    return Observation(as_of, product, 1, model, LR, 21, segment, 10.0 + error, 10.0, None, None, 1.0, 1.0, False)


class CriteriaTest(unittest.TestCase):
    def _rows(self, n_cuts: int, better_in: int, products: int = 10) -> list[dict]:
        obs = []
        for c in range(n_cuts):
            for p in range(products):
                obs.append(_obs(c, p, "baseline.moving_average", 2.0))
                obs.append(_obs(c, p, "ml.x", 1.0 if c < better_in else 3.0))
        return level1_rows(obs, "ml.x", Criteria())

    def test_cuts_rule_rounds_up_and_needs_five(self) -> None:
        rows = self._rows(7, 5)  # ⌈2/3 · 7⌉ = 5
        self.assertEqual(rows[1]["value"]["needed"], 5)
        self.assertEqual(rows[1]["status"], CUMPLE)
        self.assertEqual(self._rows(7, 4)[1]["status"], NO_CUMPLE)
        four = self._rows(4, 4)
        self.assertTrue(all(r["status"] == NO_CONCLUYENTE for r in four))

    def test_segment_blocks_only_with_ten_products(self) -> None:
        obs = []
        for c in range(6):
            for p in range(20):
                segment = "INTERMITTENT" if p < 9 else "SMOOTH"
                obs.append(_obs(c, p, "baseline.moving_average", 2.0, segment))
                obs.append(_obs(c, p, "ml.x", 4.0 if segment == "INTERMITTENT" else 1.0, segment))
        rows = level1_rows(obs, "ml.x", Criteria())
        self.assertEqual(rows[2]["status"], CUMPLE)  # 9 intermittent series: reported, does not block
        blocks = {item["segment"]: item["blocks"] for item in rows[2]["value"]}
        self.assertEqual(blocks, {"INTERMITTENT": False, "SMOOTH": True})

    def test_pairwise_set_only_keeps_series_with_both_models(self) -> None:
        obs = [_obs(0, 1, "baseline.moving_average", 2.0), _obs(0, 1, "ml.x", 1.0), _obs(0, 2, "baseline.moving_average", 2.0)]
        per_cut = pairwise_per_cut(obs, "ml.x", "baseline.moving_average", LR)
        self.assertEqual(next(iter(per_cut.values()))["ALL"]["n"], 1)


if __name__ == "__main__":
    unittest.main()
