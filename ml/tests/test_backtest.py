"""Per-model eligibility, common set, population rules, reproducibility and the report."""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from ml.__main__ import main
from ml.backtest import H1, HORIZONS, LR, VIEWS, comparison_tables, common_keys, cut_summaries, run_backtest
from ml.metrics import METRICS
from ml.segmentation import SEGMENTS
from ml.config import POPULATION_AS_OF_VALIDITY, POPULATION_U3_SNAPSHOT, F5aConfig
from ml.data import load_dataset
from ml.models import MODEL_NAMES
from ml.report import (
    COMPACT_MAX_BYTES,
    OBSERVATIONS_FILE,
    SERIES_CUTS_FILE,
    SUMMARY_FILE,
    build_summary,
    compact_json_text,
    render_markdown,
)
from ml.tests.fixtures import TempDataset

EARLY = _dt.date(2024, 3, 27)  # product 3 has 43 weeks: seasonal naïve (63) not eligible; product 4 still valid
LATER = _dt.date(2024, 8, 14)  # product 3 has 63 weeks: eligible
SEASONAL = "baseline.seasonal_naive"


class EligibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        with TempDataset() as path:
            self.ds = load_dataset(path)

    def test_per_model_eligibility_and_common_set(self) -> None:
        result = run_backtest(self.ds, F5aConfig(), [EARLY, LATER])  # default population: validity (DT-087)
        early, later = cut_summaries(result)
        self.assertEqual(early["eligible_by_model"][SEASONAL], 3)  # 1, 2 and 4; not 3
        self.assertEqual(early["eligible_by_model"]["baseline.naive"], 4)
        self.assertEqual(later["eligible_by_model"][SEASONAL], 3)  # 1, 2 and 3; 4 is out of validity
        common = common_keys(result.observations)
        self.assertNotIn((EARLY.isoformat(), 3, 1, H1), common)
        self.assertIn((LATER.isoformat(), 3, 1, H1), common)
        self.assertEqual(early["common_set"][H1], 3)
        self.assertEqual(later["common_set"][H1], 3)
        # Product 4 has no active preferred supplier: listed, out of L + R, inside h = 1.
        self.assertEqual(early["no_preferred_supplier"], [4])
        self.assertEqual(early["common_set"][LR], 2)
        self.assertEqual(early["snapshot_inactive_in_population"]["n"], 1)
        # The early cut of product 3 is reported for the other models but never compared.
        self.assertTrue(any(o.product_id == 3 and o.as_of == EARLY.isoformat() for o in result.observations))
        tables = comparison_tables(result, F5aConfig())
        for model in MODEL_NAMES:
            per_cut = tables[H1]["ALL_WEEKS"]["ALL"][model]["per_cut"]
            self.assertEqual(per_cut[EARLY.isoformat()]["n"], 3)
            self.assertEqual(per_cut[LATER.isoformat()]["n"], 3)

    def test_population_rules(self) -> None:
        snapshot = run_backtest(self.ds, F5aConfig(population_rule=POPULATION_U3_SNAPSHOT), [EARLY])
        as_of = run_backtest(self.ds, F5aConfig(), [EARLY, LATER])
        self.assertEqual(F5aConfig().population_rule, POPULATION_AS_OF_VALIDITY)
        self.assertEqual(cut_summaries(snapshot)[0]["population"], 3)  # inactive snapshot: product 4 out
        s_early, s_later = cut_summaries(as_of)
        self.assertEqual(s_early["population"], 4)  # valid on 2024-03-27
        self.assertEqual(s_later["population"], 3)  # valid_to 2024-06-30
        # Its H1 truth exists at the early cut; L + R does not (no active supplier, U1 would stop).
        self.assertIn((EARLY.isoformat(), 4, 1, H1), common_keys(as_of.observations))
        self.assertNotIn((EARLY.isoformat(), 4, 1, LR), common_keys(as_of.observations))


class ReproducibilityTest(unittest.TestCase):
    def test_same_inputs_same_hash(self) -> None:
        digests = []
        with TempDataset() as path:
            for _ in range(2):
                ds = load_dataset(path)
                config = F5aConfig()
                result = run_backtest(ds, config, [EARLY, LATER])
                summary, obs_csv, sc_csv = build_summary(
                    result, config, comparison_tables(result, config), cut_summaries(result), {"fixed": True}
                )
                digests.append((summary["results_sha256"], hashlib.sha256(obs_csv.encode()).hexdigest(), sc_csv))
        self.assertEqual(digests[0], digests[1])

    def test_cli_writes_deterministic_outputs_and_a_synthetic_report(self) -> None:
        with TempDataset() as path, tempfile.TemporaryDirectory() as tmp:
            out, report = Path(tmp) / "out", Path(tmp) / "reports" / "f5a.md"
            fixed = ["--generated-on", "2026-10-05"]  # no test reads the system clock (docs/13 §14)
            self.assertEqual(main(["backtest", "--data", str(path), "--out", str(out), "--report", str(report), *fixed]), 0)
            first = {n: (out / n).read_bytes() for n in (OBSERVATIONS_FILE, SERIES_CUTS_FILE)}
            summary = json.loads((out / SUMMARY_FILE).read_text(encoding="utf-8"))
            compact = report.with_suffix(".json")
            first_compact = compact.read_bytes()
            self.assertEqual(main(["backtest", "--data", str(path), "--out", str(out), "--report", str(report), *fixed]), 0)
            second = {n: (out / n).read_bytes() for n in (OBSERVATIONS_FILE, SERIES_CUTS_FILE)}
            self.assertEqual(first, second)
            self.assertEqual(compact.read_bytes(), first_compact)  # deterministic
            self.assertEqual(summary["label"], "SYNTHETIC")
            self.assertEqual(len(summary["protocol"]["cuts"]), 17)
            self.assertEqual(summary["metadata"]["generated_on"], "2026-10-05")
            for key in ("dataset_version", "engine_version_u1", "git_commit", "python_version"):
                self.assertIn(key, summary["metadata"])
            text = report.read_text(encoding="utf-8")
            self.assertIn("SYNTHETIC", text)
            self.assertIn("PROPUESTA", text)
            self.assertLess(len(first_compact), COMPACT_MAX_BYTES)
            compact_data = json.loads(first_compact)
            self.assertNotIn("cuts", compact_data)  # no per-cut tables in the versioned JSON
            self.assertNotIn("population_by_cut", compact_data["population_comparison"])
            self.assertEqual(compact_data["results_sha256"], summary["results_sha256"])
            for key in ("dataset_version", "engine_version_u1", "git_commit", "python_version", "seeds", "command", "generated_on"):
                self.assertIn(key, compact_data["metadata"])
            self.assertEqual(compact_data["config"]["population_rule"], "AS_OF_VALIDITY")
            self.assertEqual(compact_data["aggregates_stats_order"], ["mean", "sd", "min", "max", "n_cuts"])
            self.assertEqual(len(compact_data["aggregates"]["H1"]["ALL_WEEKS"]["ALL"]["ml.ses"]["metrics"]["mase"]), 5)
            self.assertEqual(render_markdown(summary), text)
            self.assertIn("## 6. Comparación de reglas de población", text)
            self.assertIn("--generated-on 2026-10-05", summary["metadata"]["command"])
            self.assertEqual(summary["population_comparison"]["rules"], ["AS_OF_VALIDITY", "U3_SNAPSHOT"])
            self.assertEqual([d["product_id"] for d in summary["discontinued"]], [4])


class CompactJsonSizeTest(unittest.TestCase):
    def test_worst_case_catalogue_stays_under_the_budget(self) -> None:
        """Every horizon × view × segment × model filled: the versioned JSON stays under 100 KB."""
        stats = {"mean": 0.123456789012, "sd": 0.0123456789, "min": 0.0012345678, "max": 1.23456789, "n_cuts": 17}
        entry = {"n_observations": 1700, "across_cuts": {m: dict(stats) for m in METRICS}, "per_cut": {"x": {}}}
        tables = {
            h: {v: {s: {m: entry for m in MODEL_NAMES} for s in ("ALL",) + SEGMENTS} for v in VIEWS} for h in HORIZONS
        }
        summary = {
            "label": "SYNTHETIC",
            "unit": "F5a (DT-086)",
            "metadata": {"command": "x" * 300},
            "protocol": {},
            "config": F5aConfig().describe(),
            "results_sha256": "0" * 64,
            "files": {},
            "tables": tables,
            "population_comparison": None,
            "discontinued": [],
        }
        first, second = compact_json_text(summary), compact_json_text(summary)
        self.assertEqual(first, second)
        self.assertLess(len(first.encode("utf-8")), COMPACT_MAX_BYTES)
        self.assertNotIn("per_cut", first)


if __name__ == "__main__":
    unittest.main()
