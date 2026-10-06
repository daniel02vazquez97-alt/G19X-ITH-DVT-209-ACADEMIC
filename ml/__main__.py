"""Command line of F5a, non-interactive. From the repository root::

    PYTHONPATH=backend python -m ml backtest --data data/synthetic/output \\
        --out ml/out --report docs/reports/fase5-f5a-backtest-sintetico.md

Reads the dataset read-only, writes only to ``--out`` and ``--report`` and exits non-zero on error.
Each run also evaluates the other population rule (`DT-087`) for the comparison of the report.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import shlex
import sys
import time
from pathlib import Path

from .backtest import comparison_tables, cut_summaries, run_backtest
from .backtest import discontinued_profile
from .config import ALTERNATIVE_POPULATION, POPULATION_AS_OF_VALIDITY, POPULATION_U3_SNAPSHOT, F5aConfig
from .data import load_dataset
from .report import (
    SUMMARY_FILE,
    build_summary,
    compact_json_text,
    render_markdown,
    rule_comparison,
    run_metadata,
    write_outputs,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ml", description="F5a: backtesting, Level 1 and segmentation (SYNTHETIC)")
    sub = parser.add_subparsers(dest="command", required=True)
    bt = sub.add_parser("backtest", help="run the 17 development cuts of DT-075")
    bt.add_argument("--data", required=True, type=Path, help="published dataset directory")
    bt.add_argument("--out", default=Path("ml/out"), type=Path, help="output directory (detail CSVs and JSON, not versioned)")
    bt.add_argument(
        "--report", type=Path, help="also write the Markdown report and its compact JSON (same name, .json); details stay in --out"
    )
    bt.add_argument(
        "--generated-on", type=_dt.date.fromisoformat, help="report date (YYYY-MM-DD); default: today. Metadata only"
    )
    bt.add_argument(
        "--population", choices=(POPULATION_AS_OF_VALIDITY, POPULATION_U3_SNAPSHOT), default=POPULATION_AS_OF_VALIDITY
    )
    raw = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(raw)

    started = time.monotonic()
    config = F5aConfig(population_rule=args.population)
    dataset = load_dataset(args.data)
    generated_on = args.generated_on or _dt.date.today()
    command = "PYTHONPATH=backend python -m ml " + shlex.join(raw)
    metadata = run_metadata(dataset.dataset_version, dataset.data_origin, generated_on, command)
    result = run_backtest(dataset, config)
    tables = comparison_tables(result, config)
    per_cut = cut_summaries(result)
    other = F5aConfig(population_rule=ALTERNATIVE_POPULATION[config.population_rule])
    other_result = run_backtest(dataset, other)
    comparison = rule_comparison(
        {
            config.population_rule: (tables, per_cut),
            other.population_rule: (comparison_tables(other_result, other), cut_summaries(other_result)),
        }
    )
    discontinued = discontinued_profile(dataset, result, config)
    summary, obs_csv, sc_csv = build_summary(result, config, tables, per_cut, metadata, comparison, discontinued)
    write_outputs(args.out, summary, obs_csv, sc_csv)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        # Rendered from the written JSON, so the report can be regenerated from ml/out alone.
        written = json.loads((args.out / SUMMARY_FILE).read_text(encoding="utf-8"))
        args.report.write_text(render_markdown(written), encoding="utf-8", newline="\n")
        args.report.with_suffix(".json").write_text(compact_json_text(written), encoding="utf-8", newline="\n")
    print(f"F5a backtest: {len(result.cuts)} cuts, {len(result.observations)} observations, "
          f"results_sha256={summary['results_sha256']} ({time.monotonic() - started:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
