"""Command line of F5a and F5b, non-interactive. From the repository root::

    PYTHONPATH=backend python -m ml backtest --data data/synthetic/output \\
        --out ml/out --report docs/reports/fase5-f5a-backtest-sintetico.md
    PYTHONPATH=backend python -m ml simulate --data data/synthetic/output \\
        --out ml/out --report docs/reports/fase5-f5b-nivel2-sintetico.md

Reads the dataset read-only, writes only to ``--out`` and ``--report`` and exits non-zero on error.
``backtest`` also evaluates the other population rule (`DT-087`) for the comparison of the report;
``simulate`` runs the Level 2 simulation of `DT-080` / `DT-088` and the F5a Level 1 of its cross.
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
from .simulation.simulator import OPEN_LINES_ACTUAL_RECEIPTS, OPEN_LINES_EXPECTED_ON
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
    parser = argparse.ArgumentParser(prog="python -m ml", description="F5a, F5b and F5c of Phase 5 (SYNTHETIC)")
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
    sim = sub.add_parser("simulate", help="F5b: closed-loop Level 2 simulation of the four baselines (DT-088)")
    sim.add_argument("--data", required=True, type=Path, help="published dataset directory (SYNTHETIC)")
    sim.add_argument("--out", default=Path("ml/out"), type=Path, help="output directory (detail CSVs and JSON, not versioned)")
    sim.add_argument("--report", type=Path, help="also write the Markdown report and its compact JSON (same name, .json)")
    sim.add_argument("--generated-on", type=_dt.date.fromisoformat, help="report date (YYYY-MM-DD); default: today")
    sim.add_argument("--workers", type=int, default=1, help="worker processes (results do not depend on it)")
    sim.add_argument(
        "--open-lines", choices=(OPEN_LINES_EXPECTED_ON, OPEN_LINES_ACTUAL_RECEIPTS), default=OPEN_LINES_EXPECTED_ON,
        help="arrival of the real lines open at the first cut (DT-080 point 7 by default)",
    )
    sim.add_argument(
        "--period-end", type=_dt.date.fromisoformat, default=None, help="end of the simulated period (default and maximum: 2025-09-24)"
    )
    sim.add_argument("--cache-dir", type=Path, help="resumable cache of finished products (e.g. ml/out/f5b-cache)")
    sim.add_argument("--time-budget", type=float, help="seconds; stop cleanly and resume on the next call (needs --cache-dir)")
    sim.add_argument("--products", type=lambda s: [int(x) for x in s.split(",")], help="restrict to these product ids")
    cand = sub.add_parser("candidates", help="F5c: candidate models, DT-011 study and US-055 intervals (DT-092)")
    cand.add_argument("--data", required=True, type=Path, help="published dataset directory (SYNTHETIC)")
    cand.add_argument("--out", default=Path("ml/out"), type=Path, help="output directory (detail CSVs and JSON, not versioned)")
    cand.add_argument("--report", type=Path, help="also write the Markdown report and its compact JSON (same name, .json)")
    cand.add_argument("--generated-on", type=_dt.date.fromisoformat, help="report date (YYYY-MM-DD); default: today")
    cand.add_argument("--workers", type=int, default=1, help="worker processes (results do not depend on it)")
    cand.add_argument("--cache-dir", type=Path, help="resumable cache (e.g. ml/out/f5c-cache)")
    cand.add_argument("--time-budget", type=float, help="seconds; stop cleanly and resume on the next call (needs --cache-dir)")
    cand.add_argument(
        "--reuse-cache", type=Path,
        help="use this cache folder as is, without the fingerprint check (only when the computation code did not change)",
    )
    cand.add_argument("--products", type=lambda s: [int(x) for x in s.split(",")], help="restrict the simulation to these product ids")
    cand.add_argument(
        "--period-end", type=_dt.date.fromisoformat, default=None, help="end of the simulated period (default and maximum: 2025-09-24)"
    )
    raw = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(raw)
    command = "PYTHONPATH=backend python -m ml " + shlex.join(raw)
    if args.command == "simulate":
        return _simulate(args, command)
    if args.command == "candidates":
        return _candidates(args, command)
    return _backtest(args, command)


def _simulate(args: argparse.Namespace, command: str) -> int:
    from .simulation import report as sim_report
    from .simulation.run import IncompleteRun, run_f5b
    from .simulation.simulator import SimConfig

    started = time.monotonic()
    config = SimConfig(open_lines_rule=args.open_lines)
    if args.period_end is not None:
        config = SimConfig(open_lines_rule=args.open_lines, period_end=args.period_end)
    try:
        inputs, result, level1 = run_f5b(
            args.data, config, workers=args.workers, products=args.products, cache_dir=args.cache_dir,
            time_budget=args.time_budget,
        )
    except IncompleteRun as exc:
        print(f"F5b simulate: incomplete ({exc}) after {time.monotonic() - started:.1f}s")
        return 3
    metadata = run_metadata(
        inputs.dataset.dataset_version, inputs.dataset.data_origin, args.generated_on or _dt.date.today(), command
    )
    results = sim_report.build_results(inputs, result, level1)
    csvs = sim_report.detail_csvs(result, results)
    summary = sim_report.build_summary(config, results, csvs, metadata)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, text in csvs.items():
        (args.out / name).write_text(text, encoding="utf-8", newline="\n")
    text = json.dumps(summary, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n"
    (args.out / sim_report.SUMMARY_FILE).write_text(text, encoding="utf-8", newline="\n")
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        written = json.loads(text)
        args.report.write_text(sim_report.render_markdown(written), encoding="utf-8", newline="\n")
        args.report.with_suffix(".json").write_text(sim_report.compact_json_text(written), encoding="utf-8", newline="\n")
    print(f"F5b simulate: {len(result.products)} series, {len(result.excluded)} excluded, "
          f"results_sha256={summary['results_sha256']} ({time.monotonic() - started:.1f}s)")
    return 0


def _candidates(args: argparse.Namespace, command: str) -> int:
    from .f5c import report as f5c_report
    from .f5c.results import build_results
    from .f5c.run import IncompleteRun, run_f5c
    from .simulation.simulator import SimConfig

    started = time.monotonic()
    sim_config = SimConfig() if args.period_end is None else SimConfig(period_end=args.period_end)
    try:
        run = run_f5c(args.data, sim_config=sim_config, workers=args.workers, products=args.products,
                      cache_dir=args.cache_dir, time_budget=args.time_budget, reuse_cache=args.reuse_cache)
    except IncompleteRun as exc:
        print(f"F5c candidates: incomplete ({exc}) after {time.monotonic() - started:.1f}s")
        return 3
    metadata = run_metadata(
        run.inputs.dataset.dataset_version, run.inputs.dataset.data_origin, args.generated_on or _dt.date.today(), command
    )
    reports_dir = args.report.parent if args.report is not None else Path("docs/reports")
    results = build_results(run, reports_dir)
    csvs = f5c_report.detail_csvs(run, results)
    summary = f5c_report.build_summary(run, results, csvs, metadata)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, text in csvs.items():
        (args.out / name).write_text(text, encoding="utf-8", newline="\n")
    text = json.dumps(summary, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n"
    (args.out / f5c_report.SUMMARY_FILE).write_text(text, encoding="utf-8", newline="\n")
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        written = json.loads(text)
        args.report.write_text(f5c_report.render_markdown(written), encoding="utf-8", newline="\n")
        args.report.with_suffix(".json").write_text(f5c_report.compact_json_text(written), encoding="utf-8", newline="\n")
    print(f"F5c candidates: {len(run.level1.cuts)} cuts, top {', '.join(run.top)}, {len(run.simulation.products)} series simulated, "
          f"results_sha256={summary['results_sha256']} ({time.monotonic() - started:.1f}s)")
    return 0


def _backtest(args: argparse.Namespace, command: str) -> int:
    started = time.monotonic()
    config = F5aConfig(population_rule=args.population)
    dataset = load_dataset(args.data)
    generated_on = args.generated_on or _dt.date.today()
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
