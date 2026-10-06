"""Orchestration of an F5b run: the simulation of every product and the F5a Level 1 needed by the cross.

Products are independent, so they can run in worker processes (``workers``); results are collected in key
order, so the outputs are identical for any number of workers. The F5a backtest (population of `DT-087`)
runs alongside to provide the Level 1 values of the `DT-078` cross.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ..backtest import BacktestResult, run_backtest
from ..config import F5aConfig
from ..data import SeriesKey
from .simulator import SimConfig, SimulationInputs, SimulationResult, eligible_keys, prepare_inputs, simulate_product

_WORKER: dict = {}


def _init_worker(directory: str, config: SimConfig) -> None:
    _WORKER["inputs"] = prepare_inputs(directory, config)
    _WORKER["config"] = config


def _simulate(key: SeriesKey):
    return simulate_product(_WORKER["inputs"], key, _WORKER["config"])


def _level1(directory: str, f5a: F5aConfig) -> BacktestResult:
    return run_backtest(_WORKER["inputs"].dataset, f5a)


def run_f5b(
    directory: Path | str, config: SimConfig, workers: int = 1, products: list[int] | None = None
) -> tuple[SimulationInputs, SimulationResult, BacktestResult]:
    """Simulation of the eligible products and the F5a backtest of the same dataset."""
    directory = str(directory)
    inputs = prepare_inputs(directory, config)
    keys, excluded = eligible_keys(inputs.dataset, config)
    if products is not None:
        wanted = set(products)
        keys = [k for k in keys if k[0] in wanted]
        excluded = [e for e in excluded if e["product_id"] in wanted]
    if workers <= 1:
        simulated = [simulate_product(inputs, key, config) for key in keys]
        level1 = run_backtest(inputs.dataset, config.f5a)
    else:
        with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(directory, config)) as pool:
            level1_future = pool.submit(_level1, directory, config.f5a)
            simulated = list(pool.map(_simulate, keys))
            level1 = level1_future.result()
    return inputs, SimulationResult(config, simulated, excluded), level1
