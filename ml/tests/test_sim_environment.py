"""F5b environment: one day by hand, a whole trajectory by hand, transit, holdout guards and isolation."""

from __future__ import annotations

import ast
import datetime as _dt
import unittest
from decimal import Decimal
from pathlib import Path

from app.supply_engine import OpenLine
from ml.cuts import HoldoutAccessError
from ml.data import on_hand_at, open_lines_at
from ml.simulation.environment import load_latent_demand, simulate_day
from ml.simulation.simulator import SIMULATED_ORDER_BASE, SimConfig, simulate_product
from ml.tests.fixtures import TempDataset
from ml.tests.sim_support import BRANCH, CUT, KEY, constant_forecaster, day, hand_config, hand_inputs

D = Decimal
ML_DIR = Path(__file__).resolve().parents[1]


class DayTest(unittest.TestCase):
    def test_one_day(self) -> None:
        out = simulate_day(D(5), D(3), D(10))
        self.assertEqual((out.consumption, out.lost, out.end_on_hand), (D(8), D(2), D(0)))
        out = simulate_day(D(50), D(0), D(10))
        self.assertEqual((out.consumption, out.lost, out.end_on_hand), (D(10), D(0), D(40)))
        with self.assertRaises(ValueError):
            simulate_day(D(-1), D(0), D(1))


class HandTrajectoryTest(unittest.TestCase):
    """One product, 21 days, ``L = 9`` (agreed fallback), forecast 70/week, ``R = 7`` → ``H = 16``.

    ``DDH = 70 + 70 + 2/7·70 = 160``; constant consumption → ``σ = 0`` → ``S = 160``.
    Day 0: IP = 50 + 30 (exogenous, day 2) = 80 → order 80, arrives day 9.
    Day 7: on_hand 10, transit 80 → IP 90 → order 70, arrives day 16.
    Day 8: demand 25 with 10 available → 15 lost. Day 14: on_hand 20, transit 70 → order 70 (day 23).
    """

    def setUp(self) -> None:
        self.ps = simulate_product(hand_inputs(), KEY, hand_config(), constant_forecaster(), keep_inputs=True)
        self.trace = self.ps.traces[BRANCH]

    def test_inventory_balance_and_lost_sales(self) -> None:
        expected = [40, 60, 50, 40, 30, 20, 10, 0, 70, 60, 50, 40, 30, 20, 10, 70, 60, 50, 40, 30, 20]
        self.assertEqual(self.trace.end_on_hand, [D(x) for x in expected])
        self.assertEqual(self.trace.lost, [D(0)] * 7 + [D(15)] + [D(0)] * 13)
        self.assertTrue(all(x >= 0 for x in self.trace.end_on_hand))
        for i in range(21):  # balance: start + received − consumption = end
            start = D(50) if i == 0 else self.trace.end_on_hand[i - 1]
            self.assertEqual(start + self.trace.received[i] - self.trace.consumption[i], self.trace.end_on_hand[i])
            self.assertEqual(self.ps.demand[i] - self.trace.consumption[i], self.trace.lost[i])

    def test_orders_arrive_after_the_engine_lead_time(self) -> None:
        orders = [(o.placed_on, o.quantity, o.lead_time_days, o.arrival_on) for o in self.trace.orders]
        self.assertEqual(orders, [(CUT, D(80), 9, day(9)), (day(7), D(70), 9, day(16)), (day(14), D(70), 9, day(23))])
        self.assertEqual(self.trace.received[1], D(30))  # exogenous line on day 2
        self.assertEqual(self.trace.received[8], D(80))
        self.assertEqual(self.trace.received[15], D(70))

    def test_transit_counts_in_the_next_decision(self) -> None:
        first, second = self.trace.inputs[0], self.trace.inputs[1]
        self.assertEqual(first.open_lines, (OpenLine(77, 1, 1, day(2), D(30)),))
        self.assertEqual(second.open_lines, (OpenLine(SIMULATED_ORDER_BASE + 1, 1, 1, day(9), D(80)),))
        self.assertEqual(second.inventory.total_in_transit, D(80))
        self.assertEqual(second.inventory.on_hand, D(10))
        self.assertEqual(second.consumption.quantities[-7:], (D(10),) * 7)


class HoldoutGuardTest(unittest.TestCase):
    def test_demand_movements_and_orders_after_the_limit(self) -> None:
        with TempDataset(latent=lambda p, d: 7) as path:
            demand = load_latent_demand(path, "SYNTHETIC")  # unparsable rows after the limit are discarded
            on_hand = on_hand_at(path, D_CUT)  # idem for the movements
            lines = open_lines_at(path, D_CUT)
            with self.assertRaises(HoldoutAccessError):
                demand.on((1, 1), _dt.date(2025, 9, 25))
            for loader in (on_hand_at, open_lines_at):
                with self.assertRaises(HoldoutAccessError):
                    loader(path, _dt.date(2025, 9, 25))
            self.assertEqual(demand.on((1, 1), _dt.date(2025, 9, 24)), D(7))
        self.assertGreater(on_hand[(1, 1)], 0)
        self.assertTrue(all(line.issued_on <= D_CUT for line in lines))
        with self.assertRaises(HoldoutAccessError):
            SimConfig(first_cut=CUT, period_end=_dt.date(2025, 9, 25))

    def test_latent_demand_only_with_synthetic_data(self) -> None:
        with TempDataset(latent=lambda p, d: 7) as path, self.assertRaises(ValueError):
            load_latent_demand(path, "REAL")


D_CUT = _dt.date(2024, 3, 27)


class IsolationTest(unittest.TestCase):
    """The latent demand only lives in the environment; the models never see it (AST)."""

    def _sources(self):
        for source in sorted(ML_DIR.rglob("*.py")):
            relative = source.relative_to(ML_DIR).as_posix()
            if relative.startswith("tests/"):
                continue
            yield relative, source.read_text(encoding="utf-8")

    def test_only_the_environment_uses_demand_csv(self) -> None:
        """As a code constant (docstrings aside): the environment reads it; F5a's loader only forbids it."""
        naming = {}
        for rel, text in self._sources():
            tree = ast.parse(text)
            docstrings = {
                id(node.body[0].value)
                for node in ast.walk(tree)
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and node.body
                and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)
            }
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and node.value == "demand.csv" and id(node) not in docstrings:
                    naming.setdefault(rel, 0)
                    naming[rel] += 1
        self.assertEqual(naming, {"data.py": 1, "simulation/environment.py": 1})
        from ml.data import FORBIDDEN_FILES

        self.assertIn("demand.csv", FORBIDDEN_FILES)

    def test_only_the_simulator_imports_the_environment(self) -> None:
        importers = []
        for rel, text in self._sources():
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith("environment"):
                    importers.append(rel)
                elif isinstance(node, ast.Import) and any(a.name.endswith("environment") for a in node.names):
                    importers.append(rel)
        self.assertEqual(importers, ["simulation/simulator.py"])
        for forbidden in ("simulation/forecasters.py", "simulation/engine_inputs.py", "models.py", "backtest.py"):
            self.assertNotIn(forbidden, importers)


if __name__ == "__main__":
    unittest.main()
