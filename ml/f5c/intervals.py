"""US-055 in F5c (`DT-082`, `DT-093` point 6): coverage of the current interval and of a calibrated variant.

* **Current interval:** the nearest-rank 10/90 interval of each model (U3 for the baselines, the same rule for SES
  and the candidates), nominal level 0.80 (`DT-056` D-03).
* **Calibrated variant** (PROPUESTA): per model and horizon, a widening factor ``k`` applied around the point,
  ``[max(0, p − k(p − lower)), p + k(upper − p)]``. For each late cut ``t`` the factor is fitted on the cuts whose
  14 evaluation weeks end on or before ``t`` (`DT-082` point 2: only errors known at ``t``) and is then applied to
  the weeks of ``t``. Calibration cuts and measured cuts never coincide.
* **Rule of `DT-093` point 6:** an interval is calibrated at a horizon if its coverage on the late cuts lies in
  ``[0.75, 0.85]``. It decides the label of the band only, never a promotion.

Coverage is measured weekly (h = 1 … 14) against the observed consumption of complete weeks; the view without
stockout weeks is reported too, because the observed consumption is censored.
"""

from __future__ import annotations

import bisect
import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from app.forecasting import HORIZON_WEEKS

from ..backtest import ALL_SEGMENTS, VIEW_ALL, VIEW_NO_STOCKOUT
from ..cuts import evaluation_end
from .backtest import F5cLevel1

_NEVER = math.inf


@dataclass(frozen=True, slots=True)
class WeekRecord:
    cut: int  # index of the cut
    model: str
    h: int
    segment: str
    needed_k: float  # smallest widening factor that covers the actual (inf if none)
    stockout: bool


def needed_widening(point: float, lower: float, upper: float, actual: float) -> float:
    """Smallest ``k ≥ 0`` with ``actual`` inside the widened interval (lower clipping at 0 never helps)."""
    if actual == point:
        return 0.0
    if actual > point:
        return (actual - point) / (upper - point) if upper > point else _NEVER
    return (point - actual) / (point - lower) if point > lower else _NEVER


def records(level1: F5cLevel1) -> list[WeekRecord]:
    index = {cut: i for i, cut in enumerate(level1.cuts)}
    out = []
    for f in level1.series_cuts:
        segment = f.base.segment or ""
        for model, h, point, lower, upper, actual, stockout in f.weekly:
            out.append(WeekRecord(index[f.base.as_of], model, h, segment, needed_widening(point, lower, upper, actual), stockout))
    return out


def coverage_at(sorted_needed: Sequence[float], k: float) -> float | None:
    if not sorted_needed:
        return None
    return bisect.bisect_right(sorted_needed, k) / len(sorted_needed)


def fit_widening(needed: Sequence[float], grid: Sequence[float], nominal: float) -> float | None:
    """Grid factor with coverage closest to ``nominal``; ties → the smaller factor."""
    ordered = sorted(needed)
    if not ordered:
        return None
    best, best_gap = None, None
    for k in grid:
        gap = abs(coverage_at(ordered, k) - nominal)
        if best_gap is None or gap < best_gap:
            best, best_gap = k, gap
    return best


def _share(flags: Sequence[bool]) -> float | None:
    return sum(1 for f in flags if f) / len(flags) if flags else None


def coverage_study(level1: F5cLevel1, grid: Sequence[float], nominal: float, late_cut_index: int, low: float, high: float) -> dict:
    """Coverage per model × horizon × view × segment: current (all cuts and late cuts) and calibrated (late cuts)."""
    recs = records(level1)
    cuts = level1.cuts
    late = list(range(late_cut_index, len(cuts)))
    calibration_cuts = {t: [c for c in range(len(cuts)) if evaluation_end(cuts[c]) <= cuts[t]] for t in late}
    grouped: dict[tuple[str, int, int], list[WeekRecord]] = defaultdict(list)
    for r in recs:
        grouped[(r.model, r.h, r.cut)].append(r)
    models = sorted({r.model for r in recs})
    result: dict = {"late_cuts": [cuts[t].isoformat() for t in late],
                    "calibration_cuts": {cuts[t].isoformat(): [cuts[c].isoformat() for c in calibration_cuts[t]] for t in late},
                    "models": {}}
    for model in models:
        per_view: dict = {}
        for view in (VIEW_ALL, VIEW_NO_STOCKOUT):
            keep = (lambda r: True) if view == VIEW_ALL else (lambda r: not r.stockout)
            horizons: dict = {}
            for h in range(1, HORIZON_WEEKS + 1):
                cur_all: dict[str, list[bool]] = defaultdict(list)
                cur_late: dict[str, list[bool]] = defaultdict(list)
                cal_late: dict[str, list[bool]] = defaultdict(list)
                factors = []
                for c in range(len(cuts)):
                    for r in grouped.get((model, h, c), ()):
                        if keep(r):
                            for seg in (ALL_SEGMENTS, r.segment):
                                cur_all[seg].append(r.needed_k <= 1.0)
                for t in late:
                    needed = [r.needed_k for c in calibration_cuts[t] for r in grouped.get((model, h, c), ()) if keep(r)]
                    k = fit_widening(needed, grid, nominal)
                    if k is not None:
                        factors.append(k)
                    for r in grouped.get((model, h, t), ()):
                        if not keep(r):
                            continue
                        for seg in (ALL_SEGMENTS, r.segment):
                            cur_late[seg].append(r.needed_k <= 1.0)
                            if k is not None:
                                cal_late[seg].append(r.needed_k <= k)
                horizons[h] = {
                    seg: {
                        "current_all_cuts": _share(cur_all[seg]),
                        "current_late_cuts": _share(cur_late[seg]),
                        "calibrated_late_cuts": _share(cal_late[seg]),
                        "n_late": len(cur_late[seg]),
                    }
                    for seg in sorted(cur_all)
                }
                horizons[h][ALL_SEGMENTS]["mean_factor"] = math.fsum(factors) / len(factors) if factors else None
            per_view[view] = horizons
        all_view = per_view[VIEW_ALL]

        def within(key: str) -> int:
            return sum(1 for h in all_view if all_view[h].get(ALL_SEGMENTS, {}).get(key) is not None
                       and low <= all_view[h][ALL_SEGMENTS][key] <= high)

        per_view["horizons_within_band"] = {
            "current_late_cuts": within("current_late_cuts"),
            "calibrated_late_cuts": within("calibrated_late_cuts"),
            "of": len(all_view),
        }
        result["models"][model] = per_view
    return result
