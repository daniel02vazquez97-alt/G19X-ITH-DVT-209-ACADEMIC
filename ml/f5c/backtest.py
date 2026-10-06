"""F5c Level 1 (`DT-092`): the 17 cuts of `DT-075` for the baselines, SES and the five candidates.

Per series-cut the F5a computation runs unchanged (`ml.backtest.run_series_cut`: population, U3 baselines, SES,
segment, ``L + R`` and observed truth), so the four F5a models give exactly the F5a observations. On the same
training weeks this module adds:

* the five candidates (`ml.candidates`). A candidate that is not eligible (history, errors per horizon) has no
  forecast; one whose values cannot cross the `DT-074` boundary is **replaced by the official baseline** of that
  series-cut and counted (`DT-093`);
* the seasonality flag of `DT-093` point 7 and the stockout share of the training days;
* weekly records ``(model, h, point, lower, upper, actual, stockout)`` for every week of the 14 evaluated whose
  7 days are observed: the input of the coverage study of US-055.

Only data ``≤ as_of`` enters the training side; the truth is the observed consumption (`DT-076` point 2).
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Sequence
from dataclasses import dataclass, field
from fractions import Fraction

from app.forecasting import HORIZON_WEEKS
from app.forecasting.weekly import weekly_totals

from ..backtest import SeriesCut, observations_of, run_series_cut
from ..candidates import CANDIDATE_NAMES, BoundaryError, candidate_forecast
from ..cuts import check_cut, development_cuts
from ..data import Dataset, SeriesKey
from ..metrics import Observation
from ..models import MODEL_NAMES, ModelForecast
from ..segmentation import seasonality
from .config import OFFICIAL_BASELINE, F5cConfig
from .strategies import stockout_share

#: Every model of F5c in reporting order: the three U3 baselines, SES and the five candidates.
ALL_MODELS: tuple[str, ...] = MODEL_NAMES + CANDIDATE_NAMES
OK = "OK"
NOT_ELIGIBLE = "NOT_ELIGIBLE"
SUBSTITUTED = "SUBSTITUTED"
_ONE_DAY = _dt.timedelta(days=1)


@dataclass
class F5cSeriesCut:
    base: SeriesCut
    seasonal_acf: float | None = None
    seasonal: bool = False
    stockout_share: float = 0.0
    candidate_status: dict[str, str] = field(default_factory=dict)
    substitution_reasons: dict[str, str] = field(default_factory=dict)
    #: ``(model, h, point, lower, upper, actual, stockout)`` for the observed weeks of the 14 evaluated.
    weekly: list[tuple] = field(default_factory=list)


@dataclass
class F5cLevel1:
    cuts: tuple[_dt.date, ...]
    series_cuts: list[F5cSeriesCut]
    observations: list[Observation]


def _weekly_truth(ds: Dataset, key: SeriesKey, as_of: _dt.date, h: int) -> tuple[float, bool] | None:
    rows = ds.window(key, as_of + _ONE_DAY * (7 * (h - 1) + 1), as_of + _ONE_DAY * (7 * h))
    if rows is None:
        return None
    return float(sum((Fraction(r.quantity) for r in rows), Fraction(0))), any(r.stockout for r in rows)


def run_series_cut_f5c(ds: Dataset, key: SeriesKey, as_of: _dt.date, config: F5cConfig) -> F5cSeriesCut:
    sc = run_series_cut(ds, key, as_of, config.f5a)
    out = F5cSeriesCut(sc)
    if not sc.in_population or sc.exclusion_reason is not None:
        return out
    rows = ds.history(key, as_of)
    weeks = [float(w) for w in weekly_totals([Fraction(r.quantity) for r in rows])]
    out.seasonal_acf, out.seasonal = seasonality(weeks, config.seasonal_min_weeks, config.seasonal_lag, config.seasonal_z)
    out.stockout_share = stockout_share([r.stockout for r in rows])
    official = sc.forecasts.get(OFFICIAL_BASELINE)
    for name in CANDIDATE_NAMES:
        try:
            fc = candidate_forecast(name, weeks, config.candidates)
        except BoundaryError as exc:
            if official is None:
                out.candidate_status[name] = NOT_ELIGIBLE
                continue
            fc = ModelForecast(name, official.points, official.lowers, official.uppers)
            out.candidate_status[name] = SUBSTITUTED
            out.substitution_reasons[name] = str(exc)
        else:
            if fc is None:
                out.candidate_status[name] = NOT_ELIGIBLE
                continue
            out.candidate_status[name] = OK
        sc.forecasts[name] = fc
    for h in range(1, HORIZON_WEEKS + 1):
        truth = _weekly_truth(ds, key, as_of, h)
        if truth is None:
            continue
        for name, fc in sc.forecasts.items():
            out.weekly.append(
                (name, h, float(fc.points[h - 1]), float(fc.lowers[h - 1]), float(fc.uppers[h - 1]), truth[0], truth[1])
            )
    return out


def run_cut(ds: Dataset, as_of: _dt.date, config: F5cConfig) -> tuple[list[F5cSeriesCut], list[Observation]]:
    """Every series of one cut (unit of the resumable cache)."""
    check_cut(as_of)
    series_cuts, observations = [], []
    for key in ds.series_keys():
        f = run_series_cut_f5c(ds, key, as_of, config)
        series_cuts.append(f)
        observations.extend(observations_of(f.base, config.f5a))
    return series_cuts, observations


def run_level1(ds: Dataset, config: F5cConfig, cuts: Sequence[_dt.date] | None = None) -> F5cLevel1:
    chosen = tuple(cuts) if cuts is not None else development_cuts()
    for as_of in chosen:
        check_cut(as_of)  # before any read: the holdout is never touched
    series_cuts, observations = [], []
    for as_of in chosen:
        scs, obs = run_cut(ds, as_of, config)
        series_cuts.extend(scs)
        observations.extend(obs)
    return F5cLevel1(chosen, series_cuts, observations)
