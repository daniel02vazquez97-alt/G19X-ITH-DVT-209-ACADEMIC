"""F5c on the fixture dataset: parity with F5a/F5b, leakage, substitution, simulator branches, isolation, outputs."""

from __future__ import annotations

import ast
import dataclasses
import datetime as _dt
import hashlib
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from app.forecasting import MOVING_AVERAGE
from ml.__main__ import main
from ml.backtest import observations_of, run_backtest, run_series_cut
from ml.candidates import CANDIDATE_NAMES, HOLT_NAME, HOLT_WINTERS_NAME, TSB_NAME, CandidateConfig
from ml.config import F5aConfig
from ml.data import load_dataset
from ml.f5c import backtest as f5c_backtest
from ml.f5c.backtest import NOT_ELIGIBLE, OK, SUBSTITUTED, run_series_cut_f5c
from ml.f5c.config import F5cConfig
from ml.f5c.forecaster import F5cForecaster
from ml.f5c.report import COMPACT_MAX_BYTES, compact_json_text
from ml.f5c.results import level2, parity
from ml.f5c.run import run_f5c
from ml.models import MODEL_NAMES, BoundaryError
from ml.report import observations_csv, series_cuts_csv
from ml.simulation import simulator
from ml.simulation.forecasters import WeeklyHistory, point_forecast
from ml.simulation.report import build_results as f5b_results
from ml.simulation.report import detail_csvs as f5b_csvs
from ml.simulation.run import run_f5b
from ml.simulation.simulator import SimConfig, prepare_inputs, simulate_product
from ml.tests.fixtures import TempDataset
from ml.tests.test_leakage import ALTERED_ORDERS, altered_quantity, altered_stockout
from ml.tests.test_sim_simulator import latent
from ml.tests.test_types import _floats

ML_DIR = Path(__file__).resolve().parents[1]
EARLY = _dt.date(2024, 8, 14)
LATE = _dt.date(2025, 1, 29)  # 108 anchored weeks of history: Holt-Winters is eligible
SHORT = SimConfig(period_end=_dt.date(2024, 7, 10))
OFFICIAL = MOVING_AVERAGE.name


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Level1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with TempDataset() as path:
            cls.ds = load_dataset(path)

    def test_f5a_models_are_unchanged(self) -> None:
        config = F5cConfig()
        for as_of in (EARLY, LATE):
            for key in self.ds.series_keys():
                f = run_series_cut_f5c(self.ds, key, as_of, config)
                base = run_series_cut(self.ds, key, as_of, config.f5a)
                self.assertEqual({m: f.base.forecasts[m] for m in base.forecasts}, base.forecasts)
                mine = [o for o in observations_of(f.base, config.f5a) if o.model in MODEL_NAMES]
                self.assertEqual(mine, observations_of(base, config.f5a))

    def test_holt_winters_eligibility(self) -> None:
        early = run_series_cut_f5c(self.ds, (1, 1), EARLY, F5cConfig())
        late = run_series_cut_f5c(self.ds, (1, 1), LATE, F5cConfig())
        self.assertEqual(early.candidate_status[HOLT_WINTERS_NAME], NOT_ELIGIBLE)
        self.assertEqual(late.candidate_status[HOLT_WINTERS_NAME], OK)
        self.assertFalse(early.seasonal)

    def test_post_cut_changes_do_not_change_the_training_side(self) -> None:
        with TempDataset(quantity=altered_quantity, stockout=altered_stockout, orders=ALTERED_ORDERS) as b:
            altered = load_dataset(b)
        for key in self.ds.series_keys():
            a, b = run_series_cut_f5c(self.ds, key, EARLY, F5cConfig()), run_series_cut_f5c(altered, key, EARLY, F5cConfig())
            self.assertEqual(a.base.forecasts, b.base.forecasts, key)
            self.assertEqual((a.candidate_status, a.seasonal_acf, a.stockout_share),
                             (b.candidate_status, b.seasonal_acf, b.stockout_share), key)

    def test_invalid_candidate_is_replaced_by_the_official_baseline_and_counted(self) -> None:
        real = f5c_backtest.candidate_forecast

        def failing(name, weeks, config):
            if name == HOLT_NAME:
                raise BoundaryError("negative forecast")
            return real(name, weeks, config)

        with mock.patch.object(f5c_backtest, "candidate_forecast", failing):
            f = run_series_cut_f5c(self.ds, (1, 1), EARLY, F5cConfig())
        self.assertEqual(f.candidate_status[HOLT_NAME], SUBSTITUTED)
        self.assertEqual(f.base.forecasts[HOLT_NAME].points, f.base.forecasts[OFFICIAL].points)
        self.assertEqual(f.candidate_status[TSB_NAME], OK)

    def test_candidate_output_is_decimal(self) -> None:
        f = run_series_cut_f5c(self.ds, (1, 1), LATE, F5cConfig())
        for name in CANDIDATE_NAMES:
            fc = f.base.forecasts[name]
            self.assertFalse(list(_floats(fc.points + fc.lowers + fc.uppers)), name)


class SimulatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TempDataset(latent=latent, on_hand_at_first_cut=60)
        cls.path = cls._tmp.__enter__()
        cls.inputs = prepare_inputs(cls.path, SHORT)
        cls.forecaster = F5cForecaster(CandidateConfig())

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.__exit__(None, None, None)

    def _sim(self, branches, forecaster=None):
        config = dataclasses.replace(SHORT, branches=branches)
        return simulate_product(self.inputs, (1, 1), config, forecaster or self.forecaster)

    def test_f5b_branches_are_identical_through_the_f5c_forecaster(self) -> None:
        mine, theirs = self._sim(MODEL_NAMES), self._sim(MODEL_NAMES, point_forecast)
        for branch in MODEL_NAMES:
            a, b = mine.traces[branch], theirs.traces[branch]
            self.assertEqual((a.lost, a.end_on_hand, a.orders, a.decisions), (b.lost, b.end_on_hand, b.orders, b.decisions))

    def test_not_eligible_holt_winters_uses_the_official_baseline_and_is_counted(self) -> None:
        ps = self._sim((OFFICIAL, HOLT_WINTERS_NAME))
        hw, ma = ps.traces[HOLT_WINTERS_NAME], ps.traces[OFFICIAL]
        self.assertTrue(all(d.substitution == "NOT_ELIGIBLE" for d in hw.decisions))
        self.assertEqual((hw.lost, hw.end_on_hand), (ma.lost, ma.end_on_hand))
        self.assertTrue(all(d.substitution is None for d in ma.decisions))

    def test_candidates_refit_every_four_decisions(self) -> None:
        from ml.f5c import forecaster as module

        calls = []
        real = module.fit

        def counting(name, weeks, config):
            calls.append(len(weeks))
            return real(name, weeks, config)

        with mock.patch.object(module, "fit", counting):
            ps = self._sim((TSB_NAME,), F5cForecaster(CandidateConfig(), refit_every=4))
        decisions = len(ps.traces[TSB_NAME].decisions)
        self.assertEqual(len(calls), -(-decisions // 4))
        self.assertTrue(all(b - a == 4 for a, b in zip(calls, calls[1:])))

    def test_no_float_crosses_into_u1_with_candidates_and_strategies(self) -> None:
        real = simulator.evaluate

        def guarded(engine_input):
            found = list(_floats(engine_input))
            if found:
                raise AssertionError(f"float in the U1 input: {found[:3]}")
            return real(engine_input)

        with mock.patch.object(simulator, "evaluate", guarded):
            self._sim(CANDIDATE_NAMES + ("baseline.moving_average@b", "ml.ses@c", "ml.tsb@c"))

    def test_strategies_equal_as_is_without_stockouts(self) -> None:
        daily = [Decimal(5 + i % 3) for i in range(7 * 40)]
        history = WeeklyHistory(daily)
        history.daily, history.flags, history.offset = daily, [False] * len(daily), 0
        for model in (OFFICIAL, "ml.ses", TSB_NAME):
            plain = self.forecaster(model, history, F5aConfig())
            plain = getattr(plain, "points", plain)
            for strategy in ("b", "c"):
                self.assertEqual(self.forecaster(f"{model}@{strategy}", history, F5aConfig()).points, plain, (model, strategy))


class IsolationTest(unittest.TestCase):
    FORECASTING = ("candidates.py", "f5c/points.py", "f5c/forecaster.py", "f5c/strategies.py", "f5c/backtest.py",
                   "f5c/study.py", "f5c/criteria.py", "f5c/intervals.py", "f5c/config.py")

    def test_models_never_see_the_latent_demand(self) -> None:
        for rel in self.FORECASTING:
            tree = ast.parse((ML_DIR / rel).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertFalse(node.module.endswith(("environment", "simulator")), (rel, node.module))
                if isinstance(node, ast.Constant) and node.value == "demand.csv":
                    self.fail(f"{rel} names demand.csv")


class PipelineTest(unittest.TestCase):
    """End to end on the fixture: parity of the F5a/F5b files, reproducibility and outputs."""

    def test_parity_reproducibility_and_outputs(self) -> None:
        with TempDataset(latent=latent, on_hand_at_first_cut=60) as path, tempfile.TemporaryDirectory() as tmp:
            run = run_f5c(path, sim_config=SHORT)
            # F5a and F5b computed by their own code on the same data: the hashes they would record.
            ds = load_dataset(path)
            f5a = run_backtest(ds, F5aConfig())
            inputs, sim, level1 = run_f5b(path, SHORT)
            csvs = f5b_csvs(sim, f5b_results(inputs, sim, level1))
            reports = Path(tmp)
            (reports / "fase5-f5a-backtest-sintetico.json").write_text(json.dumps({"files": {
                "f5a-observations.csv": _sha(observations_csv(f5a)), "f5a-series-cuts.csv": _sha(series_cuts_csv(f5a))}}))
            (reports / "fase5-f5b-nivel2-sintetico.json").write_text(json.dumps({"files": {n: _sha(t) for n, t in csvs.items()}}))
            result = parity(run, level2(run), reports)
            self.assertEqual({n: p["equal"] for n, p in result.items()}, {n: True for n in result})
            self.assertEqual(len(result), 5)
            two = run_f5c(path, sim_config=SHORT, workers=2)
            self.assertEqual([o for o in run.level1.observations], [o for o in two.level1.observations])
            self.assertEqual(run.top, two.top)
            for a, b in zip(run.simulation.products, two.simulation.products):
                self.assertEqual({k: (t.lost, t.decisions) for k, t in a.traces.items()},
                                 {k: (t.lost, t.decisions) for k, t in b.traces.items()})

    def test_cli_is_deterministic_and_compact(self) -> None:
        with TempDataset(latent=latent, on_hand_at_first_cut=60) as path, tempfile.TemporaryDirectory() as tmp:
            out, report = Path(tmp) / "out", Path(tmp) / "f5c.md"
            args = ["candidates", "--data", str(path), "--out", str(out), "--report", str(report),
                    "--generated-on", "2026-10-06", "--period-end", "2024-07-10"]
            self.assertEqual(main(args), 0)
            first = report.with_suffix(".json").read_bytes()
            self.assertEqual(main(args), 0)
            self.assertEqual(report.with_suffix(".json").read_bytes(), first)
            self.assertLess(len(first), COMPACT_MAX_BYTES)
            text = report.read_text(encoding="utf-8")
            self.assertIn("SYNTHETIC", text)
            self.assertIn("No recomienda ni promueve ningún modelo", text)
            summary = json.loads((out / "f5c-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["results"]["level2"]["engine_versions"], ["0.1.0"])
            self.assertEqual(compact_json_text(summary).encode("utf-8"), first)


if __name__ == "__main__":
    unittest.main()
