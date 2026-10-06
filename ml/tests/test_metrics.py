"""Level 1 metrics computed by hand, zero denominators and the two stockout views."""

from __future__ import annotations

import datetime as _dt
import math
import unittest

from ml.backtest import ALL_SEGMENTS, H1, VIEW_ALL, VIEW_NO_STOCKOUT, BacktestResult, comparison_tables
from ml.config import F5aConfig
from ml.metrics import Observation, aggregate, dispersion, horizon_scale, naive_scale
from ml.models import MODEL_NAMES


def obs(forecast, actual, *, scale=2.0, stockout=False, lower=None, upper=None, model="m", product=1, as_of="2024-03-27"):
    return Observation(as_of, product, 1, model, H1, 7, "SMOOTH", forecast, actual, lower, upper, scale, scale * scale, stockout)


class AggregateTest(unittest.TestCase):
    def test_by_hand(self) -> None:
        sample = [
            obs(12.0, 10.0, lower=9.0, upper=13.0),  # e = +2, covered
            obs(5.0, 8.0, scale=3.0, lower=9.0, upper=12.0),  # e = −3, not covered
            obs(4.0, 0.0, scale=0.0),  # e = +4, zero scale, zero actual, no interval
        ]
        m = aggregate(sample)
        self.assertEqual(m["n"], 3)
        self.assertAlmostEqual(m["mae"], 3.0)
        self.assertAlmostEqual(m["rmse"], math.sqrt((4 + 9 + 16) / 3))
        self.assertAlmostEqual(m["mase"], (2 / 2 + 3 / 3) / 2)  # the zero-scale series is excluded
        self.assertAlmostEqual(m["rmsse"], (2 / 2 + 3 / 3) / 2)
        self.assertEqual(m["n_zero_scale"], 1)
        self.assertAlmostEqual(m["wape"], 9 / 18)
        self.assertAlmostEqual(m["bias"], (2 - 3 + 4) / 3)
        self.assertAlmostEqual(m["bias_rel"], 3 / 18)
        self.assertAlmostEqual(m["coverage"], 0.5)
        self.assertEqual(m["n_interval"], 2)
        self.assertAlmostEqual(m["mape"], (2 / 10 + 3 / 8) / 2)  # zero actual excluded and counted
        self.assertEqual(m["n_zero_actual"], 1)

    def test_zero_total_actual(self) -> None:
        m = aggregate([obs(1.0, 0.0), obs(0.0, 0.0)])
        self.assertIsNone(m["wape"])
        self.assertIsNone(m["bias_rel"])
        self.assertIsNone(m["mape"])
        self.assertEqual(aggregate([])["n"], 0)

    def test_scales(self) -> None:
        s_abs, s_sq = naive_scale([10.0, 12.0, 9.0, 9.0])  # diffs 2, −3, 0
        self.assertAlmostEqual(s_abs, 5 / 3)
        self.assertAlmostEqual(s_sq, 13 / 3)
        self.assertEqual(naive_scale([5.0, 5.0, 5.0]), (0.0, 0.0))
        self.assertEqual(horizon_scale(2.0, 4.0, 7, F5aConfig().lr_scale_policy), (2.0, 4.0))
        self.assertEqual(horizon_scale(2.0, 4.0, 21, F5aConfig().lr_scale_policy), (6.0, 36.0))

    def test_dispersion(self) -> None:
        d = dispersion([1.0, None, 3.0])
        self.assertEqual((d["mean"], d["sd"], d["min"], d["max"], d["n_cuts"]), (2.0, 1.0, 1.0, 3.0, 2))
        self.assertEqual(dispersion([None])["n_cuts"], 0)


class ViewsTest(unittest.TestCase):
    def test_all_weeks_and_weeks_without_stockout(self) -> None:
        observations = []
        for model in MODEL_NAMES:
            observations.append(obs(10.0, 10.0, model=model, product=1))
            observations.append(obs(10.0, 4.0, model=model, product=2, stockout=True))  # censored truth
        result = BacktestResult((_dt.date(2024, 3, 27),), [], observations)
        tables = comparison_tables(result, F5aConfig())
        for model in MODEL_NAMES:
            all_weeks = tables[H1][VIEW_ALL][ALL_SEGMENTS][model]
            clean = tables[H1][VIEW_NO_STOCKOUT][ALL_SEGMENTS][model]
            self.assertEqual(all_weeks["n_observations"], 2)
            self.assertEqual(clean["n_observations"], 1)
            self.assertAlmostEqual(all_weeks["across_cuts"]["mae"]["mean"], 3.0)
            self.assertAlmostEqual(clean["across_cuts"]["mae"]["mean"], 0.0)

    def test_only_the_common_set_is_compared(self) -> None:
        observations = [obs(10.0, 9.0, model=m, product=1) for m in MODEL_NAMES]
        observations.append(obs(50.0, 9.0, model=MODEL_NAMES[0], product=2))  # only one model: not common
        tables = comparison_tables(BacktestResult((_dt.date(2024, 3, 27),), [], observations), F5aConfig())
        self.assertEqual(tables[H1][VIEW_ALL][ALL_SEGMENTS][MODEL_NAMES[0]]["n_observations"], 1)


if __name__ == "__main__":
    unittest.main()
