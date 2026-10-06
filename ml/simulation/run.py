"""Orchestration of an F5b run: the simulation of every product and the F5a Level 1 needed by the cross.

Products are independent, so they can run in worker processes (``workers``); results are collected in key
order, so the outputs are identical for any number of workers. The F5a backtest (population of `DT-087`)
runs alongside to provide the Level 1 values of the `DT-078` cross.

Optional resumable cache (``cache_dir``, under ``ml/out/``, ignored by Git): each finished product and the F5a
result are stored with ``pickle`` in a folder named after a fingerprint of the configuration, the dataset and
the source code of ``ml/``, so a stale cache is never reused. With a ``time_budget`` the run stops cleanly
when the budget is spent (``IncompleteRun``) and the next call continues; the final outputs do not depend on
how the work was split.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import time
from concurrent.futures import ProcessPoolExecutor, TimeoutError, as_completed
from pathlib import Path

from ..backtest import BacktestResult, run_backtest
from ..config import F5aConfig
from ..data import SeriesKey
from .simulator import (
    ProductSimulation,
    SimConfig,
    SimulationInputs,
    SimulationResult,
    eligible_keys,
    prepare_inputs,
    simulate_product,
)

_WORKER: dict = {}
_ML_DIR = Path(__file__).resolve().parents[1]


class IncompleteRun(RuntimeError):
    """The time budget was spent; the cache keeps the finished work and the next call continues."""


def _init_worker(directory: str, config: SimConfig) -> None:
    _WORKER["inputs"] = prepare_inputs(directory, config)
    _WORKER["config"] = config


def _simulate(key: SeriesKey) -> ProductSimulation:
    return simulate_product(_WORKER["inputs"], key, _WORKER["config"])


def _level1(f5a: F5aConfig) -> BacktestResult:
    return run_backtest(_WORKER["inputs"].dataset, f5a)


def run_fingerprint(config: SimConfig, dataset_version: str) -> str:
    """Configuration, dataset and every source file of ``ml/`` (tests excluded)."""
    digest = hashlib.sha256(json.dumps(config.describe(), sort_keys=True, default=str).encode("utf-8"))
    digest.update(dataset_version.encode("utf-8"))
    for source in sorted(_ML_DIR.rglob("*.py")):
        if "tests" not in source.relative_to(_ML_DIR).parts:
            digest.update(source.relative_to(_ML_DIR).as_posix().encode("utf-8"))
            digest.update(source.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()[:16]


def _load(path: Path):
    with path.open("rb") as handle:
        return pickle.load(handle)


def _store(path: Path, value: object) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as handle:
        pickle.dump(value, handle, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(path)


def run_f5b(
    directory: Path | str,
    config: SimConfig,
    workers: int = 1,
    products: list[int] | None = None,
    cache_dir: Path | None = None,
    time_budget: float | None = None,
) -> tuple[SimulationInputs, SimulationResult, BacktestResult]:
    """Simulation of the eligible products and the F5a backtest of the same dataset."""
    started = time.monotonic()
    directory = str(directory)
    inputs = prepare_inputs(directory, config)
    keys, excluded = eligible_keys(inputs.dataset, config)
    if products is not None:
        wanted = set(products)
        keys = [k for k in keys if k[0] in wanted]
        excluded = [e for e in excluded if e["product_id"] in wanted]
    cache = None
    if cache_dir is not None:
        cache = Path(cache_dir) / run_fingerprint(config, inputs.dataset.dataset_version)
        cache.mkdir(parents=True, exist_ok=True)

    def cached(name: str) -> Path | None:
        return None if cache is None else cache / name

    done: dict[SeriesKey, ProductSimulation] = {}
    for key in keys:
        path = cached(f"product-{key[0]}-{key[1]}.pkl")
        if path is not None and path.exists():
            done[key] = _load(path)
    level1_path = cached("level1.pkl")
    level1 = _load(level1_path) if level1_path is not None and level1_path.exists() else None
    missing = [k for k in keys if k not in done]

    def over_budget() -> bool:
        return time_budget is not None and time.monotonic() - started > time_budget

    if workers <= 1:
        for key in missing:
            if over_budget():
                raise IncompleteRun(f"{len(done)} of {len(keys)} products simulated; run again to continue")
            done[key] = simulate_product(inputs, key, config)
            if cache is not None:
                _store(cache / f"product-{key[0]}-{key[1]}.pkl", done[key])
        if level1 is None:
            level1 = run_backtest(inputs.dataset, config.f5a)
    else:
        with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(directory, config)) as pool:
            futures: dict = {}
            if level1 is None:
                futures[pool.submit(_level1, config.f5a)] = None
            for key in missing:
                futures[pool.submit(_simulate, key)] = key
            remaining = None if time_budget is None else max(time_budget - (time.monotonic() - started), 0)
            try:
                for future in as_completed(futures, timeout=remaining):
                    key = futures[future]
                    if key is None:
                        level1 = future.result()
                        if level1_path is not None:
                            _store(level1_path, level1)
                    else:
                        done[key] = future.result()
                        if cache is not None:
                            _store(cache / f"product-{key[0]}-{key[1]}.pkl", done[key])
            except TimeoutError:
                for future in futures:
                    future.cancel()
                raise IncompleteRun(f"{len(done)} of {len(keys)} products simulated; run again to continue") from None
    if cache is not None and level1_path is not None and not level1_path.exists():
        _store(level1_path, level1)
    assert level1 is not None
    return inputs, SimulationResult(config, [done[k] for k in keys], excluded), level1
