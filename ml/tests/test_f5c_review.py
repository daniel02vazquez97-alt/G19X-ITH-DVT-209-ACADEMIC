"""F5c review adjustments: SES in the criteria table, criteria per DT-011 strategy, sensitivities and cache reuse."""

from __future__ import annotations

import datetime as _dt
import tempfile
import unittest
from pathlib import Path

from ml.backtest import LR
from ml.f5c.config import Criteria
from ml.f5c.criteria import CUMPLE, NO_CUMPLE, NOT_EVALUATED, level1_rows, level2_rows, verdict
from ml.f5c.results import CRITERIA_MODELS, build_results, level2
from ml.f5c.run import CADENCE_BRANCHES, run_f5c
from ml.metrics import Observation
from ml.models import SES_NAME
from ml.simulation.simulator import SimConfig
from ml.tests.fixtures import TempDataset
from ml.tests.test_sim_simulator import latent

SHORT = SimConfig(period_end=_dt.date(2024, 7, 10))
MA = "baseline.moving_average"


def _obs(cut: int, product: int, model: str, error: float) -> Observation:
    as_of = (_dt.date(2024, 3, 27) + _dt.timedelta(days=28 * cut)).isoformat()
    return Observation(as_of, product, 1, model, LR, 21, "SMOOTH", 10.0 + error, 10.0, None, None, 1.0, 1.0, False)


def _aggregates(branches: dict[str, tuple[int, float, float]]) -> dict:
    block = {b: {"units_short": str(u), "fill_rate": f, "avg_inventory": i} for b, (u, f, i) in branches.items()}
    return {"FULL": {"segments": {"ALL": {"branches": block}}}}


class CriteriaReferenceTest(unittest.TestCase):
    def test_reference_is_the_baseline_under_the_same_strategy(self) -> None:
        obs = []
        for c in range(6):
            for p in range(12):
                obs += [_obs(c, p, MA, 3.0), _obs(c, p, f"{MA}@b", 1.0), _obs(c, p, "ml.x@b", 2.0)]
        against_a = level1_rows(obs, "ml.x@b", Criteria(), MA)
        against_b = level1_rows(obs, "ml.x@b", Criteria(), f"{MA}@b")
        self.assertEqual(against_a[0]["status"], CUMPLE)
        self.assertEqual(against_b[0]["status"], NO_CUMPLE)

    def test_level2_rows_with_reference_and_missing_branch(self) -> None:
        agg = _aggregates({f"{MA}@b": (100, 0.99, 50.0), "ml.x@b": (101, 0.989, 52.0)})
        rows = level2_rows(agg, "ml.x@b", Criteria(), "FULL", f"{MA}@b")
        self.assertEqual([r["status"] for r in rows], [CUMPLE, CUMPLE, CUMPLE])
        self.assertEqual(level2_rows(agg, "ml.y@b", Criteria(), "FULL", f"{MA}@b")[0]["status"], NOT_EVALUATED)

    def test_verdict_ignores_informative_rows_and_reports_open_ones(self) -> None:
        rows = [{"criterion": "a", "status": CUMPLE}, {"criterion": "b", "status": NO_CUMPLE, "informative": True}]
        self.assertTrue(verdict(rows)["meets_all"])
        rows.append({"criterion": "c", "status": NOT_EVALUATED})
        self.assertEqual(verdict(rows), {"meets_all": False, "failing": [], "not_conclusive_or_not_evaluated": ["c"]})


class ReviewPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TempDataset(latent=latent, on_hand_at_first_cut=60)
        cls.path = cls._tmp.__enter__()
        cls._cache = tempfile.TemporaryDirectory()
        cls.f5c = run_f5c(cls.path, sim_config=SHORT, cache_dir=Path(cls._cache.name))
        cls.results = build_results(cls.f5c, None)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.__exit__(None, None, None)
        cls._cache.cleanup()

    def test_ses_is_in_the_criteria_table(self) -> None:
        self.assertEqual(tuple(self.results["criteria"]), CRITERIA_MODELS)
        self.assertEqual(CRITERIA_MODELS[0], SES_NAME)
        for entry in self.results["criteria"].values():
            self.assertIn("meets_all", entry["verdict"])

    def test_strategy_tables_cover_every_studied_model_and_strategy(self) -> None:
        tables = self.results["strategy_criteria"]
        self.assertEqual(sorted(tables), ["a", "b", "c"])
        for table in tables.values():
            self.assertNotIn(MA, table)
            self.assertIn(SES_NAME, table)

    def test_cadence_sensitivity_keeps_the_same_baseline(self) -> None:
        cadence = self.results["cadence_sensitivity"]
        self.assertTrue(cadence["baseline_identical_to_main_run"])
        self.assertEqual(cadence["branches"], list(CADENCE_BRANCHES))
        self.assertEqual(len(cadence["sha256"]), 64)

    def test_segment_sensitivity_thresholds(self) -> None:
        self.assertEqual(sorted(self.results["segment_sensitivity"]), ["11", "9"])

    def test_reused_cache_gives_the_same_results(self) -> None:
        cache = next(Path(self._cache.name).iterdir())
        again = run_f5c(self.path, sim_config=SHORT, reuse_cache=cache)
        self.assertEqual(again.level1.observations, self.f5c.level1.observations)
        self.assertEqual(level2(again)["aggregates"], level2(self.f5c)["aggregates"])
        with self.assertRaises(FileNotFoundError):
            run_f5c(self.path, sim_config=SHORT, reuse_cache=Path(self._cache.name) / "missing")


if __name__ == "__main__":
    unittest.main()
