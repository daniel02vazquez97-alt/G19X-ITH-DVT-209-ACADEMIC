"""Environment of the Level 2 simulation: the latent demand and the physics of one day.

This is the **only** module of ``ml/`` that reads ``demand.csv`` (latent demand, `DT-034`): it is the truth
of the simulation, used only with SYNTHETIC data (`DT-080` point 8, OD-S3). The forecasters and the engine
never receive it; an AST test enforces it.

Day order of `DT-038` (`DT-080` point 6): receipts of the day, latent demand, simulated consumption
``= min(available, demand)``, lost sales ``= demand − consumption`` (no backorders). The inventory is never
negative. Everything is exact ``Decimal``.
"""

from __future__ import annotations

import csv
import datetime as _dt
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ..cuts import LAST_READABLE_DATE, check_readable
from ..data import SeriesKey

#: The only file of the latent demand. No other module of ``ml/`` may name it.
LATENT_DEMAND_FILE = "demand.csv"

_ZERO = Decimal(0)


class LatentDemand:
    """Latent demand per series and day, up to the readable limit. Days without a row have no demand."""

    def __init__(self, rows: dict[SeriesKey, dict[_dt.date, Decimal]], data_origin: str) -> None:
        self._rows = rows
        self.data_origin = data_origin

    def on(self, key: SeriesKey, day: _dt.date) -> Decimal:
        check_readable(day)
        return self._rows.get(key, {}).get(day, _ZERO)


def load_latent_demand(directory: Path | str, data_origin: str) -> LatentDemand:
    """Read ``demand.csv`` discarding every row after ``LAST_READABLE_DATE`` (holdout, `DT-075`)."""
    if data_origin != "SYNTHETIC":
        raise ValueError("the latent demand is only usable with SYNTHETIC data (DT-080 point 8, OD-S3)")
    rows: dict[SeriesKey, dict[_dt.date, Decimal]] = defaultdict(dict)
    with (Path(directory) / LATENT_DEMAND_FILE).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            day = _dt.date.fromisoformat(row["occurred_on"])
            if day > LAST_READABLE_DATE:
                continue  # holdout: discarded on parse, never kept
            key = (int(row["product_id"]), int(row["location_id"]))
            if day in rows[key]:
                raise ValueError(f"demand {key}: duplicate day {day}")
            rows[key][day] = Decimal(row["quantity"])
    return LatentDemand(dict(rows), data_origin)


@dataclass(frozen=True, slots=True)
class DayOutcome:
    received: Decimal
    demand: Decimal
    consumption: Decimal
    lost: Decimal
    end_on_hand: Decimal


def simulate_day(start_on_hand: Decimal, received: Decimal, demand: Decimal) -> DayOutcome:
    """One simulated day: receipts, then demand; consumption is capped by the available stock."""
    if start_on_hand < 0 or received < 0 or demand < 0:
        raise ValueError("on_hand, receipts and demand must be non-negative")
    available = start_on_hand + received
    consumption = min(available, demand)
    lost = demand - consumption
    return DayOutcome(received, demand, consumption, lost, available - consumption)
