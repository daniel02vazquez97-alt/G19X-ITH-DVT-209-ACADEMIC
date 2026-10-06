"""F5b Level 2 metrics and the informative cross of `DT-078`, computed by hand."""

from __future__ import annotations

import datetime as _dt
import unittest
from decimal import Decimal

from ml.metrics import Observation
from ml.simulation.level2 import (
    identical_series_cut_ordering,
    pooled,
    relative_inventory,
    series_cut_agreement,
    spearman,
    window_metrics,
)
from ml.simulation.simulator import BranchTrace, ProductSimulation, SimulatedOrder

D = Decimal
START = _dt.date(2024, 3, 28)


def product(lost_a: list[int], lost_b: list[int], inv_a: list[int], inv_b: list[int]) -> ProductSimulation:
    n = len(lost_a)
    demand = [D(10)] * n
    traces = {}
    for name, lost, inv in (("a", lost_a, inv_a), ("b", lost_b, inv_b)):
        t = BranchTrace()
        t.lost = [D(x) for x in lost]
        t.consumption = [D(10 - x) for x in lost]
        t.end_on_hand = [D(x) for x in inv]
        t.received = [D(0)] * n
        t.orders = [SimulatedOrder(name, 1, START + _dt.timedelta(days=2), D(30), 5, START + _dt.timedelta(days=7))]
        traces[name] = t
    return ProductSimulation((1, 1), START, demand, D(0), (), traces)


class WindowTest(unittest.TestCase):
    def test_metrics_by_hand(self) -> None:
        lost = [0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5]
        ps = product(lost, [0] * 14, [5] * 14, [20] * 14)
        w = window_metrics(ps, "a", START, START + _dt.timedelta(days=13), D(2))
        self.assertEqual((w.days, w.demand, w.consumption, w.lost, w.stockout_days), (14, D(140), D(132), D(8), 2))
        self.assertEqual((w.cycles, w.cycles_without_stockout), (2, 0))
        d = w.as_dict()
        self.assertAlmostEqual(d["fill_rate"], 132 / 140)
        self.assertAlmostEqual(d["stockout_rate"], 2 / 14)
        self.assertEqual(d["avg_inventory"], 5.0)
        self.assertEqual(d["avg_inventory_value"], 10.0)
        self.assertAlmostEqual(d["rotation"], 132 / 5)
        self.assertEqual((d["units_ordered"], d["orders"]), ("30", 1))
        b = window_metrics(ps, "b", START, START + _dt.timedelta(days=6), None)
        self.assertEqual((b.cycles, b.cycles_without_stockout, b.as_dict()["avg_inventory_value"]), (1, 1, None))
        with self.assertRaises(ValueError):
            window_metrics(ps, "a", START, START + _dt.timedelta(days=20), None)

    def test_pooled_and_relative_inventory(self) -> None:
        ps = product([0] * 7, [2] + [0] * 6, [10] * 7, [20] * 7)
        wa, wb = (window_metrics(ps, x, START, START + _dt.timedelta(days=6), None) for x in ("a", "b"))
        agg = {"a": pooled([wa, wa]), "b": pooled([wb])}
        self.assertEqual(agg["a"]["avg_inventory"], 20.0)
        self.assertEqual(agg["a"]["units_short"], "0")
        self.assertEqual(agg["b"]["units_short"], "2")
        self.assertEqual(relative_inventory(agg, "b"), {"a": 1.0, "b": 1.0})


def obs(model: str, forecast: float, actual: float, as_of: str = "2024-03-27", product: int = 1) -> Observation:
    return Observation(as_of, product, 1, model, "LR", 14, "SMOOTH", forecast, actual, None, None, 2.0, 4.0, False)


class CrossTest(unittest.TestCase):
    def test_spearman_by_hand(self) -> None:
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [40, 30, 20, 10]), -1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [1, 3, 2, 4]), 0.8)
        self.assertAlmostEqual(spearman([1, 1, 2, 3], [1, 2, 3, 4]), 0.9486832980505138)  # average ranks
        self.assertIsNone(spearman([1, 1, 1], [1, 2, 3]))

    def test_series_cut_agreement_by_hand(self) -> None:
        # Series 1: L1 prefers a (|e| 1 < 3); L2 prefers a (0 < 4 units short), a has less inventory → agree + inv.
        # Series 2: L1 prefers a; L2 prefers b → disagree. Series 3: L2 tie → not counted.
        ps1 = product([0] * 14, [4] + [0] * 13, [5] * 14, [9] * 14)
        ps2 = product([6] + [0] * 13, [0] * 14, [5] * 14, [9] * 14)
        ps3 = product([0] * 14, [0] * 14, [5] * 14, [9] * 14)
        windows = {}
        for pid, ps in ((1, ps1), (2, ps2), (3, ps3)):
            for model in ("a", "b"):
                windows[("2024-03-27", pid, 1, model)] = window_metrics(ps, model, START, START + _dt.timedelta(days=13), None)
        observations = [obs(m, f, 10.0, product=p) for p in (1, 2, 3) for m, f in (("a", 11.0), ("b", 13.0))]
        result = series_cut_agreement(observations, windows, ("a", "b"))
        cell = result["LR"]["mase"]
        self.assertEqual((cell["pairs_compared"], cell["pairs_tied"]), (2, 1))
        self.assertEqual(cell["agreement"], 0.5)
        self.assertEqual(cell["agreement_with_inventory"], 0.5)
        self.assertEqual(cell["agreements_meeting_inventory"], 1.0)
        self.assertEqual(result["LR"]["wape"], cell)  # same ordering per series-cut
        self.assertTrue(identical_series_cut_ordering(observations))


if __name__ == "__main__":
    unittest.main()
