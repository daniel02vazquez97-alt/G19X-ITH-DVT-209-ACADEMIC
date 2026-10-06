"""F5b closed loop on the fixture dataset: branches, exogenous events, as-of, sensitivity, types, reproducibility."""

from __future__ import annotations

import dataclasses
import datetime as _dt
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from ml.__main__ import main
from ml.simulation import simulator
from ml.simulation.report import build_results, build_summary, detail_csvs
from ml.simulation.run import IncompleteRun, run_f5b
from ml.simulation.simulator import (
    NO_ACTIVE_PREFERRED_SUPPLIER,
    SimConfig,
    eligible_keys,
    prepare_inputs,
    run_simulation,
    simulate_product,
)
from ml.tests.fixtures import TempDataset
from ml.tests.sim_support import BRANCH, KEY, constant_forecaster, hand_config, hand_inputs
from ml.tests.test_types import _floats

CUT = _dt.date(2024, 3, 27)
SHORT = SimConfig(first_cut=CUT, period_end=CUT + _dt.timedelta(days=42))


def latent(product: int, day: _dt.date) -> int:
    index = (day - _dt.date(2023, 1, 1)).days
    return 12 + (index % 7) + (8 if index % 23 == 0 else 0) if product != 2 else (6 if (index // 7) % 3 == 0 else 0)


class FixtureSimulationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TempDataset(latent=latent, on_hand_at_first_cut=60)
        cls.path = cls._tmp.__enter__()
        cls.inputs = prepare_inputs(cls.path, SHORT)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.__exit__(None, None, None)

    def test_population_with_l_plus_r_only(self) -> None:
        keys, excluded = eligible_keys(self.inputs.dataset, SHORT)
        self.assertEqual(keys, [(1, 1), (2, 1), (3, 1)])
        self.assertEqual(excluded, [{"product_id": 4, "location_id": 1, "reason": NO_ACTIVE_PREFERRED_SUPPLIER}])
        result = run_simulation(self.inputs, SHORT)
        self.assertEqual([ps.key for ps in result.products], keys)  # product 4 is listed, not simulated

    def test_same_environment_and_engine_version_different_histories(self) -> None:
        ps = simulate_product(self.inputs, (1, 1), SHORT)
        traces = list(ps.traces.values())
        versions = {d.engine_version for t in traces for d in t.decisions}
        self.assertEqual(len(versions), 1)
        self.assertEqual(len({len(t.decisions) for t in traces}), 1)
        exogenous = []
        for trace in traces:  # received = exogenous events (identical in every branch) + own orders
            own: dict = {}
            for o in trace.orders:
                own[o.arrival_on] = own.get(o.arrival_on, Decimal(0)) + o.quantity
            exogenous.append([r - own.get(CUT + _dt.timedelta(days=i + 1), Decimal(0)) for i, r in enumerate(trace.received)])
        self.assertTrue(all(e == exogenous[0] for e in exogenous))
        self.assertGreater(sum(exogenous[0]), 0)
        self.assertGreater(len({tuple(t.end_on_hand) for t in traces}), 1)  # closed loop: histories diverge

    def test_altering_the_future_does_not_change_earlier_decisions(self) -> None:
        base = simulate_product(self.inputs, (1, 1), SHORT, keep_inputs=True)
        later = CUT + _dt.timedelta(days=10)
        altered_rows = {
            key: {d: (q * 5 if d > later else q) for d, q in rows.items()} for key, rows in self.inputs.demand._rows.items()
        }
        demand = simulator.LatentDemand(altered_rows, "SYNTHETIC")
        altered = simulate_product(dataclasses.replace(self.inputs, demand=demand), (1, 1), SHORT, keep_inputs=True)
        for branch, trace in base.traces.items():
            other = altered.traces[branch]
            early = [i for i, d in enumerate(trace.decisions) if d.day <= later]
            self.assertEqual([trace.inputs[i] for i in early], [other.inputs[i] for i in early])
            self.assertEqual([o for o in trace.orders if o.placed_on <= later], [o for o in other.orders if o.placed_on <= later])
            self.assertNotEqual(trace.lost + trace.end_on_hand, other.lost + other.end_on_hand)

    def test_no_float_crosses_into_u1(self) -> None:
        calls = []
        real = simulator.evaluate

        def guarded(engine_input):
            found = list(_floats(engine_input))
            if found:
                raise AssertionError(f"float in the U1 input: {found[:3]}")
            calls.append(engine_input)
            return real(engine_input)

        with mock.patch.object(simulator, "evaluate", guarded):
            ps = simulate_product(self.inputs, (1, 1), SHORT)
        self.assertTrue(calls)
        for trace in ps.traces.values():
            self.assertTrue(all(isinstance(x, Decimal) for x in trace.end_on_hand + trace.lost + trace.consumption))

    def test_reproducible_and_independent_of_workers(self) -> None:
        def fingerprint(workers: int) -> str:
            inputs, result, level1 = run_f5b(self.path, SHORT, workers=workers)
            results = build_results(inputs, result, level1)
            return build_summary(SHORT, results, detail_csvs(result, results), {"fixed": True})["results_sha256"]

        first = fingerprint(1)
        self.assertEqual(first, fingerprint(1))
        self.assertEqual(first, fingerprint(2))

    def test_resumable_cache_gives_the_same_result(self) -> None:
        def fingerprint(inputs, result, level1) -> str:
            results = build_results(inputs, result, level1)
            return build_summary(SHORT, results, detail_csvs(result, results), {"fixed": True})["results_sha256"]

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(IncompleteRun):
                run_f5b(self.path, SHORT, cache_dir=Path(tmp), time_budget=0)
            resumed = run_f5b(self.path, SHORT, cache_dir=Path(tmp))
            again = run_f5b(self.path, SHORT, cache_dir=Path(tmp))  # everything from the cache
            cache = next(Path(tmp).iterdir())
            self.assertEqual(len(list(cache.glob("product-*.pkl"))), 3)
        self.assertEqual(fingerprint(*resumed), fingerprint(*run_f5b(self.path, SHORT)))
        self.assertEqual(fingerprint(*again), fingerprint(*resumed))


class SensitivityTest(unittest.TestCase):
    """`docs/13` §6.1: equal forecasts give equal results; a forecast biased down gives more units short."""

    def test_equality_of_conditions(self) -> None:
        config = hand_config(days=42, branches=(BRANCH, "baseline.moving_average"))
        ps = simulate_product(hand_inputs(spike=False), KEY, config, constant_forecaster())
        a, b = ps.traces.values()
        self.assertEqual((a.end_on_hand, a.lost, a.orders and [(o.placed_on, o.quantity) for o in a.orders]),
                         (b.end_on_hand, b.lost, [(o.placed_on, o.quantity) for o in b.orders]))

    def test_forecast_biased_down_produces_more_units_short(self) -> None:
        config = hand_config(days=42)
        unbiased = simulate_product(hand_inputs(spike=False), KEY, config, constant_forecaster(Decimal(70)))
        biased = simulate_product(hand_inputs(spike=False), KEY, config, constant_forecaster(Decimal(35)))
        self.assertGreater(sum(biased.traces[BRANCH].lost), sum(unbiased.traces[BRANCH].lost))
        self.assertEqual(sum(unbiased.traces[BRANCH].lost), 0)


class CliTest(unittest.TestCase):
    def test_cli_outputs_and_compact_json(self) -> None:
        with TempDataset(latent=latent, on_hand_at_first_cut=60) as path, tempfile.TemporaryDirectory() as tmp:
            out, report = Path(tmp) / "out", Path(tmp) / "f5b.md"
            args = ["simulate", "--data", str(path), "--out", str(out), "--report", str(report),
                    "--generated-on", "2026-10-05", "--period-end", "2024-07-10"]
            self.assertEqual(main(args), 0)
            first = report.with_suffix(".json").read_bytes()
            self.assertEqual(main(args), 0)
            self.assertEqual(report.with_suffix(".json").read_bytes(), first)
            self.assertLess(len(first), 50_000)
            text = report.read_text(encoding="utf-8")
            self.assertIn("SYNTHETIC", text)
            self.assertIn("no mide la variabilidad del proveedor", text)
            summary = json.loads((out / "f5b-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["results"]["engine_versions"], ["0.1.0"])
            compact = json.loads(first)
            self.assertNotIn("per_cut", json.dumps(compact["results"]["cross"]["model_level_spearman"]))


if __name__ == "__main__":
    unittest.main()
