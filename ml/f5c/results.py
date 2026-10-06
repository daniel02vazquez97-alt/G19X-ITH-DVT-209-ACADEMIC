"""Aggregates of an F5c run (Level 1, `DT-011` study, US-055, Level 2, cross, criteria and F5a/F5b parity).

Everything here is deterministic and labelled SYNTHETIC by the report. Nothing recommends a model (`DT-084`).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

from app.forecasting import REFERENCE

from ..backtest import ALL_SEGMENTS, HORIZONS, VIEW_NO_STOCKOUT, VIEWS, BacktestResult
from ..candidates import CANDIDATE_NAMES, HOLT_WINTERS_NAME
from ..cuts import development_cuts
from ..metrics import Observation, aggregate
from ..models import MODEL_NAMES
from ..report import observations_csv, series_cuts_csv
from ..segmentation import SEGMENTS
from ..simulation.level2 import (
    WindowMetrics,
    model_level_spearman,
    pooled,
    relative_inventory,
    series_cut_agreement,
    window_metrics,
)
from ..simulation.report import ORDERS_FILE as F5B_ORDERS, DECISIONS_FILE as F5B_DECISIONS, WINDOWS_FILE as F5B_WINDOWS
from ..simulation.report import detail_csvs as f5b_detail_csvs
from ..simulation.simulator import ProductSimulation, SimulationResult
from .backtest import ALL_MODELS, NOT_ELIGIBLE, OK, SUBSTITUTED
from .config import OFFICIAL_BASELINE, STRATEGIES
from .criteria import level1_rows, level2_rows, pairwise_per_cut
from .forecaster import split_branch
from .intervals import coverage_study
from .run import F5cRun
from .study import studied_models

PERIOD_FULL = "FULL"
PERIOD_NO_WARMUP = "NO_WARMUP"
_ONE_DAY = _dt.timedelta(days=1)
_WINDOW_DAYS = 98
STUDY_METRICS = ("mase", "rmsse", "wape", "bias_rel")
L1_METRICS = ("mase", "rmsse", "wape", "bias_rel", "coverage")


def _mean(values) -> float | None:
    present = [v for v in values if v is not None]
    return math.fsum(present) / len(present) if present else None


# --- Level 1 ---------------------------------------------------------------------------------------------


def level1_summary(run: F5cRun) -> dict:
    """Each model against the official baseline on their pairwise common set (mean of per-cut metrics)."""
    obs = run.level1.observations
    out: dict = {}
    for model in ALL_MODELS:
        block: dict = {}
        for horizon in HORIZONS:
            for view in VIEWS:
                per_cut = pairwise_per_cut(obs, model, OFFICIAL_BASELINE, horizon, view)
                segments = sorted({s for c in per_cut.values() for s in c})
                entry = {}
                for segment in segments:
                    rows = [c[segment] for c in per_cut.values() if segment in c]
                    entry[segment] = {
                        "cuts": len(rows),
                        "mean_series": math.fsum(r["n"] for r in rows) / len(rows) if rows else 0.0,
                        "model": {m: _mean(r["model"][m] for r in rows) for m in L1_METRICS},
                        "official_baseline": {m: _mean(r["reference"][m] for r in rows) for m in L1_METRICS},
                    }
                block.setdefault(horizon, {})[view] = entry
        out[model] = block
    return out


def eligibility(run: F5cRun) -> dict:
    per_cut: dict = {}
    for f in run.level1.series_cuts:
        cut = f.base.as_of.isoformat()
        entry = per_cut.setdefault(cut, {"population": 0, "seasonal": 0, "status": defaultdict(Counter)})
        if not f.base.in_population or f.base.exclusion_reason is not None:
            continue
        entry["population"] += 1
        entry["seasonal"] += int(f.seasonal)
        for name, status in f.candidate_status.items():
            entry["status"][name][status] += 1
    out = {}
    for cut, e in sorted(per_cut.items()):
        out[cut] = {
            "population": e["population"],
            "seasonal": e["seasonal"],
            "candidates": {n: {s: e["status"][n].get(s, 0) for s in (OK, NOT_ELIGIBLE, SUBSTITUTED)} for n in CANDIDATE_NAMES},
        }
    totals = {n: {s: sum(v["candidates"][n][s] for v in out.values()) for s in (OK, NOT_ELIGIBLE, SUBSTITUTED)}
              for n in CANDIDATE_NAMES}
    return {"per_cut": out, "totals": totals}


# --- DT-011 study ----------------------------------------------------------------------------------------


def study_summary(run: F5cRun) -> dict:
    extreme = sorted({(s.key[0], s.key[1]) for s in run.study if s.extreme})
    excluded = {(s.as_of, s.key) for s in run.study if s.extreme}
    substitutions: Counter = Counter()
    by_group: dict[tuple, dict[tuple, dict[str, Observation]]] = defaultdict(lambda: defaultdict(dict))
    for s in run.study:
        substitutions.update(s.substitutions)
        if (s.as_of, s.key) in excluded:
            continue
        for kind, obs in s.observations.items():
            for o in obs:
                model, strategy = split_branch(o.model)
                by_group[(kind, model, o.horizon)][(o.as_of, o.product_id, o.location_id)][strategy] = o
    out: dict = {}
    for (kind, model, horizon), keyed in sorted(by_group.items()):
        complete = {k: v for k, v in keyed.items() if all(s in v for s in STRATEGIES)}
        for view in VIEWS:
            per_cut: dict[str, dict[str, list[Observation]]] = defaultdict(lambda: defaultdict(list))
            for (cut, _p, _l), per_strategy in complete.items():
                for strategy, o in per_strategy.items():
                    if view == VIEW_NO_STOCKOUT and o.stockout:
                        continue
                    per_cut[cut][strategy].append(o)
            entry = {}
            for strategy in STRATEGIES:
                aggs = [aggregate(per_cut[c][strategy]) for c in sorted(per_cut) if per_cut[c][strategy]]
                entry[strategy] = {m: _mean(a[m] for a in aggs) for m in STUDY_METRICS}
                entry[strategy]["cuts"] = len(aggs)
                entry[strategy]["n"] = sum(a["n"] for a in aggs)
            out.setdefault(kind, {}).setdefault(model, {}).setdefault(horizon, {})[view] = entry
    return {
        "models": list(studied_models(run.top)),
        "extreme_series": [{"product_id": p, "location_id": l} for p, l in extreme],
        "extreme_series_cuts": len(excluded),
        "substitutions": dict(sorted(substitutions.items())),
        "metrics": out,
    }


# --- Level 2 ---------------------------------------------------------------------------------------------


def _segments_at_first_cut(run: F5cRun) -> dict[tuple[int, int], str]:
    first = run.sim_config.first_cut
    return {f.base.key: f.base.segment or "" for f in run.level1.series_cuts if f.base.as_of == first}


def level2(run: F5cRun) -> dict:
    result, config = run.simulation, run.sim_config
    segments = _segments_at_first_cut(run)
    branches = config.branches
    cuts = [c for c in development_cuts() if c >= config.first_cut and c + _ONE_DAY * _WINDOW_DAYS <= config.period_end]
    windows: dict[tuple[str, int, int, str], WindowMetrics] = {}
    for ps in result.products:
        cost = run.inputs.unit_costs.get(ps.key[0])
        for cut in cuts:
            for branch in branches:
                windows[(cut.isoformat(), ps.key[0], ps.key[1], branch)] = window_metrics(
                    ps, branch, cut + _ONE_DAY, cut + _ONE_DAY * _WINDOW_DAYS, cost
                )
    periods = {
        PERIOD_FULL: (config.first_cut + _ONE_DAY, config.period_end),
        PERIOD_NO_WARMUP: (config.first_cut + _ONE_DAY * (7 * config.warmup_weeks + 1), config.period_end),
    }
    aggregates: dict = {}
    for period, (first, last) in periods.items():
        if first > last:
            continue
        per_branch: dict[str, dict[str, list[WindowMetrics]]] = defaultdict(lambda: defaultdict(list))
        for ps in result.products:
            cost = run.inputs.unit_costs.get(ps.key[0])
            segment = segments.get(ps.key, "")
            for branch in branches:
                w = window_metrics(ps, branch, first, last, cost)
                per_branch[branch][ALL_SEGMENTS].append(w)
                per_branch[branch][segment].append(w)
        block: dict = {"first": first.isoformat(), "last": last.isoformat(), "segments": {}}
        for segment in (ALL_SEGMENTS,) + SEGMENTS:
            by_branch = {b: pooled(per_branch[b][segment]) for b in branches if per_branch[b].get(segment)}
            if by_branch:
                block["segments"][segment] = {
                    "branches": by_branch,
                    "avg_inventory_relative_to_reference": relative_inventory(by_branch, REFERENCE.name),
                }
        aggregates[period] = block
    across_cuts: dict = {}
    for branch in branches:
        per_cut = defaultdict(list)
        for (cut, _p, _l, b), w in windows.items():
            if b == branch:
                per_cut[cut].append(w)
        values = [float(pooled(per_cut[c])["units_short"]) for c in sorted(per_cut)]
        across_cuts[branch] = {
            "units_short_per_window": {
                "mean": statistics.fmean(values) if values else None,
                "sd": statistics.pstdev(values) if len(values) > 1 else 0.0,
                "min": min(values) if values else None,
                "max": max(values) if values else None,
            }
        }
    decisions: dict = {}
    engine_versions = set()
    for branch in branches:
        outcomes, substitutions = Counter(), Counter()
        for ps in result.products:
            for d in ps.traces[branch].decisions:
                outcomes[d.outcome] += 1
                engine_versions.add(d.engine_version)
                if d.substitution:
                    substitutions[d.substitution] += 1
        decisions[branch] = {"outcomes": dict(sorted(outcomes.items())), "substitutions": dict(sorted(substitutions.items()))}
    simulated = {ps.key for ps in result.products}
    observations = [o for o in run.level1.observations if (o.product_id, o.location_id) in simulated]
    cut_labels = [c.isoformat() for c in cuts]
    without_hw = tuple(m for m in ALL_MODELS if m != HOLT_WINTERS_NAME)
    cross = {
        "inventory_tolerances": [0.0, 0.05],
        "series_cut_agreement": {
            "0": series_cut_agreement(observations, windows, ALL_MODELS, 0.0),
            "0.05": series_cut_agreement(observations, windows, ALL_MODELS, 0.05),
        },
        "model_level_spearman": {
            "without_holt_winters": model_level_spearman(observations, windows, without_hw, cut_labels),
            "all_models": model_level_spearman(observations, windows, ALL_MODELS, cut_labels),
        },
    }
    return {
        "windows": windows,
        "cuts": cut_labels,
        "branches": list(branches),
        "aggregates": aggregates,
        "across_cuts": across_cuts,
        "decisions": decisions,
        "engine_versions": sorted(engine_versions),
        "cross": cross,
        "simulated": len(simulated),
        "excluded": result.excluded,
    }


# --- Criteria table --------------------------------------------------------------------------------------


def criteria_table(run: F5cRun, l2: dict) -> dict:
    crit = run.config.criteria
    out = {}
    for name in CANDIDATE_NAMES:
        rows = level1_rows(run.level1.observations, name, crit)
        rows += level2_rows(l2["aggregates"], name, crit, PERIOD_FULL)
        rows += [dict(r, informative=True) for r in level2_rows(l2["aggregates"], name, crit, PERIOD_NO_WARMUP)]
        out[name] = rows
    return out


# --- Parity with F5a and F5b -----------------------------------------------------------------------------


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parity(run: F5cRun, l2: dict, reports_dir: Path | None) -> dict:
    """Recompute the F5a and F5b detail files from the F5c run (their four models only) and compare the hashes."""
    f5a_obs = [o for o in run.level1.observations if o.model in MODEL_NAMES]
    f5a_result = BacktestResult(run.level1.cuts, [f.base for f in run.level1.series_cuts], f5a_obs)
    mine = {"f5a-observations.csv": _sha(observations_csv(f5a_result)), "f5a-series-cuts.csv": _sha(series_cuts_csv(f5a_result))}
    sim = run.simulation
    f5b_config = replace(run.sim_config, branches=MODEL_NAMES)
    products = [
        ProductSimulation(ps.key, ps.start, ps.demand, ps.initial_on_hand, ps.exogenous,
                          {b: ps.traces[b] for b in MODEL_NAMES})
        for ps in sim.products
    ]
    windows = {k: v for k, v in l2["windows"].items() if k[3] in MODEL_NAMES}
    csvs = f5b_detail_csvs(SimulationResult(f5b_config, products, sim.excluded), {"windows": windows})
    mine.update({name: _sha(text) for name, text in csvs.items()})
    recorded: dict = {}
    if reports_dir is not None:
        for report, names in (("fase5-f5a-backtest-sintetico.json", ("f5a-observations.csv", "f5a-series-cuts.csv")),
                              ("fase5-f5b-nivel2-sintetico.json", (F5B_WINDOWS, F5B_ORDERS, F5B_DECISIONS))):
            path = reports_dir / report
            if path.exists():
                files = json.loads(path.read_text(encoding="utf-8")).get("files", {})
                for name in names:
                    recorded[name] = files.get(name)
    return {
        name: {"f5c": sha, "recorded": recorded.get(name), "equal": recorded.get(name) == sha if recorded.get(name) else None}
        for name, sha in mine.items()
    }


def build_results(run: F5cRun, reports_dir: Path | None) -> dict:
    l2 = level2(run)
    crit = run.config.criteria
    return {
        "top_candidates": list(run.top),
        "eligibility": eligibility(run),
        "level1": level1_summary(run),
        "study": study_summary(run),
        "us055": coverage_study(run.level1, run.config.widening_grid, crit.nominal_level, run.config.late_cut_index,
                                crit.coverage_low, crit.coverage_high),
        "level2": l2,
        "criteria": criteria_table(run, l2),
        "parity": parity(run, l2, reports_dir),
    }
