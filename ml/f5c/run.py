"""Orchestration of an F5c run: Level 1 of the 17 cuts, the `DT-011` study and the Level 2 simulation.

Order (`DT-092`): (1) Level 1 of every model; (2) the two best candidates by Level 1 (MASE at ``L + R`` relative to
the official baseline, `DT-093` point 1); (3) the `DT-011` study of the official baseline, SES and those candidates;
(4) the closed-loop simulation of F5b with every model as a branch plus the strategy branches (b) and (c) of the
studied models. Units of work are a cut (Levels 1 and the study) and a product (Level 2): they run in worker
processes and are collected in a fixed order, so the outputs do not depend on the number of workers.

Optional resumable cache (``cache_dir`` under ``ml/out/``, ignored by Git) keyed by a fingerprint of the
configuration, the dataset and the source of ``ml/``; with a ``time_budget`` the run stops cleanly
(`IncompleteRun`) and the next call continues. Nothing after 2025-09-24 is read.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path

from ..candidates import CANDIDATE_NAMES
from ..cuts import development_cuts
from ..data import SeriesKey
from ..simulation.run import IncompleteRun, _load, _store, run_fingerprint
from ..simulation.simulator import (
    ProductSimulation,
    SimConfig,
    SimulationInputs,
    SimulationResult,
    eligible_keys,
    prepare_inputs,
    simulate_product,
)
from .backtest import ALL_MODELS, F5cLevel1, run_cut
from .config import STRATEGY_EXCLUDE, STRATEGY_IMPUTE, F5cConfig
from .criteria import relative_level1
from .forecaster import F5cForecaster, branch_name
from .study import StudyCut, study_series_cut, studied_models

_ONE_DAY = _dt.timedelta(days=1)
_WORKER: dict = {}

__all__ = ["F5cRun", "IncompleteRun", "run_f5c", "top_candidates", "sim_branches"]


@dataclass
class F5cRun:
    config: F5cConfig
    sim_config: SimConfig
    inputs: SimulationInputs
    level1: F5cLevel1
    top: tuple[str, ...]
    study: list[StudyCut]
    simulation: SimulationResult
    #: Cadence sensitivity (`DT-093` point 9): per product, Level 2 windows of the branches re-optimised every decision.
    cadence: list[dict] = field(default_factory=list)


def top_candidates(level1: F5cLevel1, n: int) -> tuple[str, ...]:
    ranked = []
    for name in CANDIDATE_NAMES:
        ratio = relative_level1(level1.observations, name)
        if ratio is not None:
            ranked.append((ratio, CANDIDATE_NAMES.index(name), name))
    return tuple(name for _r, _i, name in sorted(ranked)[:n])


def sim_branches(top: tuple[str, ...]) -> tuple[str, ...]:
    extra = tuple(branch_name(m, s) for m in studied_models(top) for s in (STRATEGY_EXCLUDE, STRATEGY_IMPUTE))
    return ALL_MODELS + extra


def _latent_total(demand):
    def total(key: SeriesKey, first: _dt.date, last: _dt.date) -> Decimal:
        out, day = Decimal(0), first
        while day <= last:
            out += demand.on(key, day)
            day += _ONE_DAY
        return out

    return total


# --- workers ---------------------------------------------------------------------------------------------


def _init(directory: str, config: F5cConfig, sim_config: SimConfig) -> None:
    _WORKER["inputs"] = prepare_inputs(directory, sim_config)
    _WORKER["config"] = config
    _WORKER["sim_config"] = sim_config
    _WORKER["forecaster"] = F5cForecaster(config.candidates, config.sim_refit_every, config.impute_window_days)


def _level1_cut(as_of: _dt.date):
    return run_cut(_WORKER["inputs"].dataset, as_of, _WORKER["config"])


def _study_cut(args):
    series_cuts, models = args
    inputs, config = _WORKER["inputs"], _WORKER["config"]
    total = _latent_total(inputs.demand)
    return [s for f in series_cuts if (s := study_series_cut(inputs.dataset, f, models, config, total)) is not None]


#: Branches of the cadence sensitivity: the official baseline and the candidates that re-optimise every decision.
CADENCE_BRANCHES: tuple[str, ...] = ("baseline.moving_average", "ml.holt", "ml.croston", "ml.tsb")
PERIOD_FULL = "FULL"
PERIOD_NO_WARMUP = "NO_WARMUP"


def periods(sim_config: SimConfig) -> dict[str, tuple[_dt.date, _dt.date]]:
    return {
        PERIOD_FULL: (sim_config.first_cut + _ONE_DAY, sim_config.period_end),
        PERIOD_NO_WARMUP: (sim_config.first_cut + _ONE_DAY * (7 * sim_config.warmup_weeks + 1), sim_config.period_end),
    }


def _cadence(key: SeriesKey) -> dict:
    """One product of the cadence sensitivity: candidates re-optimised at every weekly decision (refit every 1)."""
    from ..simulation.level2 import window_metrics

    inputs, config = _WORKER["inputs"], _WORKER["config"]
    sim_config = replace(_WORKER["sim_config"], branches=CADENCE_BRANCHES)
    forecaster = F5cForecaster(config.candidates, 1, config.impute_window_days)
    ps = simulate_product(inputs, key, sim_config, forecaster)
    cost = inputs.unit_costs.get(key[0])
    out: dict = {"key": key, "windows": {}, "substitutions": {}}
    for period, (first, last) in periods(sim_config).items():
        if first <= last:
            out["windows"][period] = {b: window_metrics(ps, b, first, last, cost) for b in CADENCE_BRANCHES}
    for b in CADENCE_BRANCHES:
        out["substitutions"][b] = sum(1 for d in ps.traces[b].decisions if d.substitution)
    return out


def _simulate(args) -> ProductSimulation:
    key, branches = args
    sim_config = replace(_WORKER["sim_config"], branches=branches)
    return simulate_product(_WORKER["inputs"], key, sim_config, _WORKER["forecaster"])


def _fingerprint(config: F5cConfig, sim_config: SimConfig, dataset_version: str) -> str:
    digest = hashlib.sha256(run_fingerprint(sim_config, dataset_version).encode("utf-8"))
    digest.update(json.dumps(config.describe(), sort_keys=True, default=str).encode("utf-8"))
    return digest.hexdigest()[:16]


def run_f5c(
    directory: Path | str,
    config: F5cConfig | None = None,
    sim_config: SimConfig | None = None,
    workers: int = 1,
    products: list[int] | None = None,
    cache_dir: Path | None = None,
    time_budget: float | None = None,
    reuse_cache: Path | None = None,
) -> F5cRun:
    """``reuse_cache`` uses that cache folder as is, without the fingerprint check: only valid when the code that
    produced it and the current computation code are the same (the report records the option)."""
    started = time.monotonic()
    config = config or F5cConfig()
    sim_config = sim_config or SimConfig()
    directory = str(directory)
    _init(directory, config, sim_config)
    inputs = _WORKER["inputs"]
    cache = None
    if reuse_cache is not None:
        cache = Path(reuse_cache)
        if not cache.is_dir():
            raise FileNotFoundError(f"{cache} is not a cache folder")
    elif cache_dir is not None:
        cache = Path(cache_dir) / _fingerprint(config, sim_config, inputs.dataset.dataset_version)
        cache.mkdir(parents=True, exist_ok=True)

    def over_budget() -> bool:
        return time_budget is not None and time.monotonic() - started > time_budget

    def stage(name: str, units: list, fn, label) -> list:
        """Run ``fn`` on each unit, reusing cached results; results in unit order."""
        results: dict[int, object] = {}
        missing = []
        for i, unit in enumerate(units):
            path = cache / f"{name}-{label(unit)}.pkl" if cache is not None else None
            if path is not None and path.exists():
                results[i] = _load(path)
            else:
                missing.append(i)

        def keep(i: int, value: object) -> None:
            results[i] = value
            if cache is not None:
                _store(cache / f"{name}-{label(units[i])}.pkl", value)

        if missing and workers > 1:
            with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(directory, config, sim_config)) as pool:
                pending = list(missing)
                while pending:
                    if over_budget():
                        raise IncompleteRun(f"{name}: {len(results)} of {len(units)} done; run again to continue")
                    batch, pending = pending[: workers * 2], pending[workers * 2 :]
                    for i, value in zip(batch, pool.map(fn, [units[i] for i in batch])):
                        keep(i, value)
        else:
            for i in missing:
                if over_budget():
                    raise IncompleteRun(f"{name}: {len(results)} of {len(units)} done; run again to continue")
                keep(i, fn(units[i]))
        return [results[i] for i in range(len(units))]

    cuts = development_cuts()
    level1_parts = stage("level1", list(cuts), _level1_cut, lambda c: c.isoformat())
    level1 = F5cLevel1(cuts, [f for scs, _ in level1_parts for f in scs], [o for _, obs in level1_parts for o in obs])
    top = top_candidates(level1, config.study_top_candidates)
    models = studied_models(top)
    by_cut = [[f for f in level1.series_cuts if f.base.as_of == c] for c in cuts]
    study_parts = stage("study", [(scs, models) for scs in by_cut], _study_cut, lambda u: u[0][0].base.as_of.isoformat())
    study = [s for part in study_parts for s in part]
    branches = sim_branches(top)
    keys, excluded = eligible_keys(inputs.dataset, sim_config)
    if products is not None:
        wanted = set(products)
        keys = [k for k in keys if k[0] in wanted]
        excluded = [e for e in excluded if e["product_id"] in wanted]
    sims = stage("sim", [(k, branches) for k in keys], _simulate, lambda u: f"{u[0][0]}-{u[0][1]}")
    cadence = stage("cadence", list(keys), _cadence, lambda k: f"{k[0]}-{k[1]}")
    final_sim = replace(sim_config, branches=branches)
    return F5cRun(config, final_sim, inputs, level1, top, study, SimulationResult(final_sim, sims, excluded), cadence)
