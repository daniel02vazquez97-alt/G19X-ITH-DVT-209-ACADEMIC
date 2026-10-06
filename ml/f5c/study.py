"""The `DT-011` study of F5c, Level 1 (`DT-081`, `DT-093` point 8).

For each studied model (official baseline, SES and the best candidates by Level 1) and each strategy (a), (b)
and (c), the 14 points are recomputed from the transformed training weeks of the cut; nothing else changes. The
truth is never imputed (`DT-076` point 2):

* **observed consumption** over week 1 and over ``L + R`` — the F5a truth, with its no-stockout view;
* **latent demand** over the same days — evaluation-only, SYNTHETIC only (`DT-034`, `DT-081` point 4). It is read
  from the simulation inputs; neither the models nor the strategies ever receive it.

The MASE/RMSSE scale is the F5a one (observed training weeks), identical for the three strategies. Series with
more than half of their training days in stockout are reported apart and left out of the comparison. A candidate
that cannot cross the `DT-074` boundary is replaced by the official baseline under the same strategy and counted.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction

from ..backtest import H1
from ..candidates import CANDIDATE_NAMES
from ..data import Dataset
from ..metrics import Observation, horizon_scale
from ..models import SES_NAME, BoundaryError
from ..protection import demand_over
from .backtest import F5cSeriesCut
from .config import OFFICIAL_BASELINE, STRATEGIES, F5cConfig
from .forecaster import branch_name
from .points import model_points
from .strategies import strategy_weeks

TRUTH_OBSERVED = "OBSERVED"
TRUTH_LATENT = "LATENT"
_ONE_DAY = _dt.timedelta(days=1)

LatentTotal = Callable[[tuple[int, int], _dt.date, _dt.date], Decimal]


@dataclass
class StudyCut:
    as_of: str
    key: tuple[int, int]
    extreme: bool
    stockout_share: float
    substitutions: dict[str, int] = field(default_factory=dict)
    observations: dict[str, list[Observation]] = field(default_factory=dict)  # truth kind → observations


def study_series_cut(
    ds: Dataset, f: F5cSeriesCut, models: Sequence[str], config: F5cConfig, latent_total: LatentTotal | None
) -> StudyCut | None:
    sc = f.base
    if not sc.in_population or sc.exclusion_reason is not None:
        return None
    rows = ds.history(sc.key, sc.as_of)
    quantities = [Fraction(r.quantity) for r in rows]
    flags = [r.stockout for r in rows]
    out = StudyCut(sc.as_of.isoformat(), sc.key, f.stockout_share > config.extreme_stockout_share, f.stockout_share)
    truths: dict[str, dict[str, tuple[float, bool, int]]] = {TRUTH_OBSERVED: {}, TRUTH_LATENT: {}}
    for horizon, truth in sc.truth.items():
        days = 7 if horizon == H1 else sc.protection.coverage_days  # type: ignore[union-attr]
        truths[TRUTH_OBSERVED][horizon] = (truth.value, truth.stockout, days)
        if latent_total is not None:
            value = latent_total(sc.key, sc.as_of + _ONE_DAY, sc.as_of + _ONE_DAY * days)
            truths[TRUTH_LATENT][horizon] = (float(value), truth.stockout, days)
    for strategy in STRATEGIES:
        weeks = strategy_weeks(strategy, quantities, flags, None, config.impute_window_days)
        official, _ = model_points(OFFICIAL_BASELINE, weeks, config.f5a, config.candidates)
        for model in models:
            label = branch_name(model, strategy)
            try:
                points, _ = model_points(model, weeks, config.f5a, config.candidates)
            except BoundaryError:
                points = official
                out.substitutions[label] = out.substitutions.get(label, 0) + 1
            if points is None:
                continue
            for kind, by_horizon in truths.items():
                for horizon, (actual, stockout, days) in by_horizon.items():
                    point = float(points[0]) if horizon == H1 else float(demand_over(points, days))
                    scale_abs, scale_sq = horizon_scale(sc.scale_abs, sc.scale_sq, days, config.f5a.lr_scale_policy)
                    out.observations.setdefault(kind, []).append(
                        Observation(
                            as_of=out.as_of, product_id=sc.key[0], location_id=sc.key[1], model=label, horizon=horizon,
                            days=days, segment=sc.segment or "", forecast=point, actual=actual, lower=None, upper=None,
                            scale_abs=scale_abs, scale_sq=scale_sq, stockout=stockout,
                        )
                    )
    return out


def studied_models(top_candidates: Sequence[str]) -> tuple[str, ...]:
    """Official baseline, SES and the chosen candidates, in a fixed order."""
    chosen = tuple(c for c in CANDIDATE_NAMES if c in set(top_candidates))
    return (OFFICIAL_BASELINE, SES_NAME) + chosen
