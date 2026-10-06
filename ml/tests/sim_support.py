"""Hand-built inputs for the F5b tests: one product, a few weeks, trajectories computed by hand."""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal

from app.supply_engine import SupplierRelation
from ml.data import DailyRow, Dataset, ExogenousLine, ProductRecord
from ml.simulation.environment import LatentDemand
from ml.simulation.simulator import SimConfig, SimulationInputs

CUT = _dt.date(2024, 3, 27)
ONE_DAY = _dt.timedelta(days=1)
KEY = (1, 1)
BRANCH = "baseline.naive"
#: Weekly forecast of the stub: 70 units (10 per day).
WEEKLY = Decimal(70)


def day(n: int) -> _dt.date:
    return CUT + ONE_DAY * n


def latent(n: int) -> Decimal:
    """Latent demand of day ``n`` after the cut: 10 per day, 25 on day 8."""
    return Decimal(25) if n == 8 else Decimal(10)


def hand_inputs(lead_time: int = 9, spike: bool = True) -> SimulationInputs:
    """70 observed days of 10 units, on_hand 50, one exogenous line of 30 expected on day 2."""
    start = CUT - ONE_DAY * 69
    rows = tuple(DailyRow(start + ONE_DAY * i, Decimal(10), False) for i in range(70))
    product = ProductRecord(1, True, start, None)
    relation = SupplierRelation(1, True, True, Decimal(0), Decimal(1), lead_time)
    dataset = Dataset("ds-hand", "SYNTHETIC", {1: product}, (1,), {KEY: rows}, {1: (relation,)}, ())
    demand = {KEY: {day(n): (latent(n) if spike else Decimal(10)) for n in range(1, 60)}}
    line = ExogenousLine(77, 1, 1, 1, 1, CUT - ONE_DAY * 5, day(2), Decimal(30), Decimal(0), ((day(2), Decimal(30)),))
    return SimulationInputs(dataset, LatentDemand(demand, "SYNTHETIC"), {KEY: Decimal(50)}, (line,), (), {1: Decimal(2)})


def hand_config(days: int = 21, branches: tuple[str, ...] = (BRANCH,)) -> SimConfig:
    return SimConfig(first_cut=CUT, period_end=day(days), branches=branches)


def constant_forecaster(weekly: Decimal = WEEKLY):
    def forecaster(model, history, config):
        return (weekly,) * 14

    return forecaster
