"""Level 2 metrics of `docs/05` §9.4 and `DT-080` point 9 / OD-S3 / OD-S4, and the informative cross of `DT-078`.

Per branch × product × window (the 14-week window of each F5a cut, or a reporting period):

* ``demand``, ``consumption`` and ``lost`` (units short) in units, exact sums;
* ``stockout_days`` (days with lost sales > 0) and the stockout rate (stockout days ÷ days);
* fill rate = consumption ÷ demand (``None`` without demand);
* cycle service level = 7-day review cycles without any lost sale ÷ cycles;
* average inventory = mean of the end-of-day ``on_hand`` (units) and its value at the preferred ``unit_cost``;
* rotation = consumption ÷ average inventory; ``units_ordered`` and ``orders`` placed in the window.

No costs (`BR-X04`), no absolute excess threshold (OD-S4) and no «urgent orders» (every simulated order uses the
lead time of the engine). Sums are exact; ratios are ``float`` for reporting only (`DT-074`).
"""

from __future__ import annotations

import datetime as _dt
import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from itertools import combinations

from ..backtest import HORIZONS, common_keys
from ..metrics import Observation, aggregate
from .simulator import ProductSimulation

_ONE_DAY = _dt.timedelta(days=1)
L1_METRICS = ("mase", "rmsse", "wape")


@dataclass(frozen=True, slots=True)
class WindowMetrics:
    days: int
    demand: Decimal
    consumption: Decimal
    lost: Decimal
    stockout_days: int
    cycles: int
    cycles_without_stockout: int
    inventory_sum: Decimal  # Σ end-of-day on_hand over the window
    unit_cost: Decimal | None
    units_ordered: Decimal
    orders: int

    @property
    def avg_inventory(self) -> Fraction:
        return Fraction(self.inventory_sum) / self.days

    def as_dict(self) -> dict:
        avg = self.avg_inventory
        return {
            "days": self.days,
            "demand": str(self.demand),
            "consumption": str(self.consumption),
            "units_short": str(self.lost),
            "stockout_days": self.stockout_days,
            "stockout_rate": self.stockout_days / self.days,
            "fill_rate": float(Fraction(self.consumption) / Fraction(self.demand)) if self.demand > 0 else None,
            "cycle_service_level": self.cycles_without_stockout / self.cycles if self.cycles else None,
            "avg_inventory": float(avg),
            "avg_inventory_value": float(avg * Fraction(self.unit_cost)) if self.unit_cost is not None else None,
            "rotation": float(Fraction(self.consumption) / avg) if avg > 0 else None,
            "units_ordered": str(self.units_ordered),
            "orders": self.orders,
        }


def window_metrics(
    ps: ProductSimulation, branch: str, first: _dt.date, last: _dt.date, unit_cost: Decimal | None, cycle_days: int = 7
) -> WindowMetrics:
    """Metrics of ``[first, last]`` (inclusive) for one branch; cycles start on ``first``."""
    start = (first - ps.start).days
    end = (last - ps.start).days + 1
    if start < 0 or end > len(ps.demand) or end <= start:
        raise ValueError(f"window {first}..{last} is outside the simulated period")
    trace = ps.traces[branch]
    lost = trace.lost[start:end]
    cycles = (end - start) // cycle_days
    ok = sum(1 for c in range(cycles) if not any(x > 0 for x in lost[c * cycle_days : (c + 1) * cycle_days]))
    placed = [o for o in trace.orders if first <= o.placed_on <= last]
    return WindowMetrics(
        days=end - start,
        demand=sum(ps.demand[start:end], Decimal(0)),
        consumption=sum(trace.consumption[start:end], Decimal(0)),
        lost=sum(lost, Decimal(0)),
        stockout_days=sum(1 for x in lost if x > 0),
        cycles=cycles,
        cycles_without_stockout=ok,
        inventory_sum=sum(trace.end_on_hand[start:end], Decimal(0)),
        unit_cost=unit_cost,
        units_ordered=sum((o.quantity for o in placed), Decimal(0)),
        orders=len(placed),
    )


def pooled(windows: Iterable[WindowMetrics]) -> dict:
    """Aggregate of several product windows: sums, pooled rates and total average inventory."""
    ws = list(windows)
    if not ws:
        return {"n_series": 0}
    demand = sum((w.demand for w in ws), Decimal(0))
    consumption = sum((w.consumption for w in ws), Decimal(0))
    lost = sum((w.lost for w in ws), Decimal(0))
    days = sum(w.days for w in ws)
    cycles = sum(w.cycles for w in ws)
    avg_inventory = sum((w.avg_inventory for w in ws), Fraction(0))
    value = [w.avg_inventory * Fraction(w.unit_cost) for w in ws if w.unit_cost is not None]
    return {
        "n_series": len(ws),
        "demand": str(demand),
        "consumption": str(consumption),
        "units_short": str(lost),
        "stockout_days": sum(w.stockout_days for w in ws),
        "stockout_rate": sum(w.stockout_days for w in ws) / days,
        "fill_rate": float(Fraction(consumption) / Fraction(demand)) if demand > 0 else None,
        "cycle_service_level": sum(w.cycles_without_stockout for w in ws) / cycles if cycles else None,
        "avg_inventory": float(avg_inventory),
        "avg_inventory_value": float(sum(value, Fraction(0))) if value else None,
        "rotation": float(Fraction(consumption) / avg_inventory) if avg_inventory > 0 else None,
        "units_ordered": str(sum((w.units_ordered for w in ws), Decimal(0))),
        "orders": sum(w.orders for w in ws),
    }


def relative_inventory(aggregates: dict[str, dict], reference: str) -> dict[str, float | None]:
    """Average inventory of each branch ÷ that of the reference branch (OD-S4: informative, no threshold)."""
    base = aggregates.get(reference, {}).get("avg_inventory")
    return {b: (a["avg_inventory"] / base if base else None) for b, a in aggregates.items() if "avg_inventory" in a}


# --- DT-078: informative cross between Level 1 and Level 2 ------------------------------------------------


def l1_value(o: Observation, metric: str) -> float | None:
    """Series-cut value of a candidate metric (MASE, RMSSE, WAPE = |e| / Y for one series)."""
    if metric == "mase":
        return o.scaled_abs
    if metric == "rmsse":
        return o.scaled_rms
    if metric == "wape":
        return abs(o.error) / o.actual if o.actual > 0 else None
    raise ValueError(metric)


def _sign(x: float | Fraction | Decimal) -> int:
    return (x > 0) - (x < 0)


def series_cut_agreement(
    observations: Sequence[Observation],
    windows: dict[tuple[str, int, int, str], WindowMetrics],
    models: Sequence[str],
    inventory_tolerance: float = 0.0,
) -> dict:
    """Pairwise agreement between each L1 candidate and the units short of L2, per horizon (`DT-078` point 5).

    For each pair of models and each (series, cut) with both values: the L1 preference (lower metric) and the
    L2 preference (fewer units short in the 14 weeks after the cut). Ties on either side are not counted.
    ``agreement_with_inventory`` (over the compared pairs) also requires the preferred model's average inventory to be at most
    ``(1 + tolerance)`` times the other's (OD-S4; the tolerance is OPEN until G1, provisional default 0);
    ``agreements_meeting_inventory`` is the same count over the agreements.
    """
    by_key: dict[tuple[str, int, int, str], dict[str, Observation]] = defaultdict(dict)
    for o in observations:
        by_key[(o.as_of, o.product_id, o.location_id, o.horizon)][o.model] = o
    out: dict = {}
    for horizon in HORIZONS:
        for metric in L1_METRICS:
            compared = ties = agree = agree_inv = 0
            for (cut, pid, loc, h), per_model in sorted(by_key.items()):
                if h != horizon:
                    continue
                for a, b in combinations(models, 2):
                    if a not in per_model or b not in per_model:
                        continue
                    wa, wb = windows.get((cut, pid, loc, a)), windows.get((cut, pid, loc, b))
                    va, vb = l1_value(per_model[a], metric), l1_value(per_model[b], metric)
                    if wa is None or wb is None or va is None or vb is None:
                        continue
                    p1, p2 = _sign(va - vb), _sign(wa.lost - wb.lost)
                    if p1 == 0 or p2 == 0:
                        ties += 1
                        continue
                    compared += 1
                    if p1 == p2:
                        agree += 1
                        best, other = (wa, wb) if p2 < 0 else (wb, wa)
                        if best.avg_inventory <= other.avg_inventory * Fraction(1 + inventory_tolerance):
                            agree_inv += 1
            out.setdefault(horizon, {})[metric] = {
                "pairs_compared": compared,
                "pairs_tied": ties,
                "agreement": agree / compared if compared else None,
                "agreement_with_inventory": agree_inv / compared if compared else None,
                "agreements_meeting_inventory": agree_inv / agree if agree else None,
            }
    return out


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Spearman's rho with average ranks for ties; ``None`` if a ranking is constant."""

    def ranks(values: Sequence[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        r = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def model_level_spearman(
    observations: Sequence[Observation],
    windows: dict[tuple[str, int, int, str], WindowMetrics],
    models: Sequence[str],
    cuts: Sequence[str],
) -> dict:
    """Per cut and horizon: Spearman between each L1 aggregate of the models and their total units short.

    The series set of each cut is the F5a comparison set (every model eligible, truth observed) restricted to
    the simulated products, so both levels see the same series.
    """
    common = common_keys(observations)
    grouped: dict[tuple[str, str, str], list[Observation]] = defaultdict(list)
    for o in observations:
        grouped[(o.as_of, o.horizon, o.model)].append(o)
    out: dict = {}
    for horizon in HORIZONS:
        for metric in L1_METRICS:
            per_cut = {}
            for cut in cuts:
                keys = {(c, p, loc) for c, p, loc, h in common if c == cut and h == horizon}
                keys = {k for k in keys if all((k[0], k[1], k[2], m) in windows for m in models)}
                if not keys:
                    continue
                l1, l2 = [], []
                for m in models:
                    obs = [o for o in grouped[(cut, horizon, m)] if (o.as_of, o.product_id, o.location_id) in keys]
                    l1.append(aggregate(obs)[metric])
                    l2.append(float(sum((windows[(k[0], k[1], k[2], m)].lost for k in keys), Decimal(0))))
                if any(v is None for v in l1):
                    continue
                per_cut[cut] = spearman(l1, l2)
            values = [v for v in per_cut.values() if v is not None]
            out.setdefault(horizon, {})[metric] = {
                "per_cut": per_cut,
                "mean": sum(values) / len(values) if values else None,
                "min": min(values) if values else None,
                "max": max(values) if values else None,
                "n_cuts": len(values),
            }
    return out


def identical_series_cut_ordering(observations: Sequence[Observation]) -> bool:
    """True if MASE, RMSSE and WAPE order the models identically in every series-cut (same |e| ordering)."""
    by_key: dict[tuple, list[Observation]] = defaultdict(list)
    for o in observations:
        by_key[(o.as_of, o.product_id, o.location_id, o.horizon)].append(o)
    for group in by_key.values():
        for a, b in combinations(group, 2):
            signs = set()
            for metric in L1_METRICS:
                va, vb = l1_value(a, metric), l1_value(b, metric)
                if va is not None and vb is not None:
                    signs.add(_sign(va - vb))
            if len(signs) > 1:
                return False
    return True

