"""F5a backtesting (`DT-075`) of the U3 baselines and the provisional SES, with Level 1 (`DT-076`).

Per cut and series:

1. population of the cut (`DT-075` point 6, rule in `ml.config`);
2. training data: only rows ``≤ as_of`` (`Dataset.history`); the U3 request is built with
   ``app.forecasting.build_request`` and the baselines run through ``app.forecasting.forecast``;
3. segment, naïve scale and SES from the same training weeks (anchored as in U3);
4. ``L + R`` with the U1 rules and the forecast over it with ``demand_over_horizon``;
5. truth: observed consumption of week 1 and of the ``L + R`` days, read separately and only if
   every day is observed; never ``demand.csv``, never an imputed value.

Nothing is persisted outside the output directory; ``model_versions`` is never written (`DT-084`).
"""

from __future__ import annotations

import datetime as _dt
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from fractions import Fraction

from app.forecasting import InvalidForecastInputError, build_request
from app.forecasting.weekly import weekly_totals
from app.supply_engine import LeadTimeSource

from .config import POPULATION_AS_OF_VALIDITY, POPULATION_U3_SNAPSHOT, F5aConfig
from .cuts import ANCHOR_END, LAST_READABLE_DATE, TOTAL_WEEKS, check_cut, development_cuts, evaluation_end
from .data import Dataset, SeriesKey
from .metrics import METRICS, Observation, aggregate, dispersion, horizon_scale, naive_scale
from .models import MODEL_NAMES, SES_NAME, BoundaryError, ModelForecast, baseline_forecasts, ses_forecast
from .protection import ProtectionHorizon, demand_over, protection_horizon
from .segmentation import SEGMENTS, SegmentFeatures, classify, features

H1 = "H1"
LR = "LR"
HORIZONS = (H1, LR)
VIEW_ALL = "ALL_WEEKS"
VIEW_NO_STOCKOUT = "NO_STOCKOUT"
VIEWS = (VIEW_ALL, VIEW_NO_STOCKOUT)
ALL_SEGMENTS = "ALL"

INACTIVE_OR_OUT_OF_VALIDITY = "INACTIVE_OR_OUT_OF_VALIDITY"
INVALID_HISTORY = "INVALID_HISTORY"
_ONE_DAY = _dt.timedelta(days=1)


@dataclass(frozen=True, slots=True)
class Truth:
    value: float
    stockout: bool


@dataclass
class SeriesCut:
    """Everything F5a knows about one series at one cut (training side and truth)."""

    as_of: _dt.date
    key: SeriesKey
    in_population: bool
    exclusion_reason: str | None = None
    segment: str | None = None
    feats: SegmentFeatures | None = None
    scale_abs: float = 0.0
    scale_sq: float = 0.0
    protection: ProtectionHorizon | None = None
    forecasts: dict[str, ModelForecast] = field(default_factory=dict)
    ses_failure: str | None = None
    truth: dict[str, Truth] = field(default_factory=dict)
    #: ``products.is_active`` as published (a snapshot of the dataset end); reported, never used by DT-087.
    snapshot_active: bool = True


@dataclass
class BacktestResult:
    cuts: tuple[_dt.date, ...]
    series_cuts: list[SeriesCut]
    observations: list[Observation]


def in_population(ds: Dataset, key: SeriesKey, as_of: _dt.date, rule: str) -> bool:
    product = ds.products[key[0]]
    if rule == POPULATION_U3_SNAPSHOT:
        return product.is_active and product.valid_on(as_of)
    if rule == POPULATION_AS_OF_VALIDITY:
        return product.valid_on(as_of)
    raise ValueError(f"unknown population rule {rule}")


def _truth(ds: Dataset, key: SeriesKey, as_of: _dt.date, days: int) -> Truth | None:
    rows = ds.window(key, as_of + _ONE_DAY, as_of + _ONE_DAY * days)
    if rows is None:
        return None
    return Truth(float(sum((Fraction(r.quantity) for r in rows), Fraction(0))), any(r.stockout for r in rows))


def run_series_cut(ds: Dataset, key: SeriesKey, as_of: _dt.date, config: F5aConfig) -> SeriesCut:
    """Training-side computation and truth of one series at one cut."""
    product_id, location_id = key
    active = ds.products[product_id].is_active
    if not in_population(ds, key, as_of, config.population_rule):
        empty = SegmentFeatures(0, 0, 0.0, None, None)
        return SeriesCut(
            as_of, key, False, INACTIVE_OR_OUT_OF_VALIDITY, segment=classify(empty, False, config), snapshot_active=active
        )
    rows = ds.history(key, as_of)
    try:
        request = build_request(product_id, location_id, as_of, [(r.day, r.quantity, r.stockout) for r in rows])
    except InvalidForecastInputError as exc:
        return SeriesCut(as_of, key, True, f"{INVALID_HISTORY}:{exc.code}", snapshot_active=active)
    _, forecasts = baseline_forecasts(request)
    weeks = [float(w) for w in weekly_totals([Fraction(q) for q in request.daily_consumption])]
    feats = features(weeks)
    sc = SeriesCut(as_of, key, True, segment=classify(feats, True, config), feats=feats, snapshot_active=active)
    sc.scale_abs, sc.scale_sq = naive_scale(weeks)
    try:
        ses = ses_forecast(weeks, config)
    except BoundaryError as exc:
        ses, sc.ses_failure = None, f"BOUNDARY:{exc}"
    if ses is not None:
        forecasts[SES_NAME] = ses
    sc.forecasts = {name: forecasts[name] for name in MODEL_NAMES if name in forecasts}
    sc.protection = protection_horizon(ds.relations.get(product_id, ()), ds.lead_time_observations, as_of, config.policy)
    truth_h1 = _truth(ds, key, as_of, 7)
    if truth_h1 is not None:
        sc.truth[H1] = truth_h1
    if sc.protection is not None:
        truth_lr = _truth(ds, key, as_of, sc.protection.coverage_days)
        if truth_lr is not None:
            sc.truth[LR] = truth_lr
    return sc


def observations_of(sc: SeriesCut, config: F5aConfig) -> list[Observation]:
    """Level 1 observations of one series-cut: one per model and horizon with truth."""
    out = []
    for name, fc in sc.forecasts.items():
        for horizon in HORIZONS:
            truth = sc.truth.get(horizon)
            if truth is None:
                continue
            if horizon == H1:
                days, point = 7, float(fc.points[0])
                lower, upper = float(fc.lowers[0]), float(fc.uppers[0])
            else:
                assert sc.protection is not None
                days = sc.protection.coverage_days
                point, lower, upper = float(demand_over(fc.points, days)), None, None
            scale_abs, scale_sq = horizon_scale(sc.scale_abs, sc.scale_sq, days, config.lr_scale_policy)
            out.append(
                Observation(
                    as_of=sc.as_of.isoformat(),
                    product_id=sc.key[0],
                    location_id=sc.key[1],
                    model=name,
                    horizon=horizon,
                    days=days,
                    segment=sc.segment or "",
                    forecast=point,
                    actual=truth.value,
                    lower=lower,
                    upper=upper,
                    scale_abs=scale_abs,
                    scale_sq=scale_sq,
                    stockout=truth.stockout,
                )
            )
    return out


def run_backtest(ds: Dataset, config: F5aConfig, cuts: Sequence[_dt.date] | None = None) -> BacktestResult:
    chosen = tuple(cuts) if cuts is not None else development_cuts()
    for as_of in chosen:
        check_cut(as_of)  # before any read: the holdout is never touched
    series_cuts, observations = [], []
    for as_of in chosen:
        for key in ds.series_keys():
            sc = run_series_cut(ds, key, as_of, config)
            series_cuts.append(sc)
            observations.extend(observations_of(sc, config))
    return BacktestResult(chosen, series_cuts, observations)


# --- Summaries --------------------------------------------------------------------------------------


def common_keys(
    observations: Sequence[Observation], models: Sequence[str] = MODEL_NAMES
) -> set[tuple[str, int, int, str]]:
    """(cut, product, location, horizon) where every model of ``models`` has an observation: the comparison set."""
    present_by_key: dict[tuple[str, int, int, str], set[str]] = defaultdict(set)
    wanted = set(models)
    for o in observations:
        if o.model in wanted:
            present_by_key[(o.as_of, o.product_id, o.location_id, o.horizon)].add(o.model)
    return {k for k, present in present_by_key.items() if present == wanted}


def comparison_tables(result: BacktestResult, config: F5aConfig) -> dict:
    """Per horizon × view × segment × model: per-cut metrics and their dispersion across cuts.

    Only the common set (every model eligible and truth observed) enters the comparison.
    """
    common = common_keys(result.observations)
    grouped: dict[tuple[str, str, str, str, str], list[Observation]] = defaultdict(list)
    for o in result.observations:
        if (o.as_of, o.product_id, o.location_id, o.horizon) not in common:
            continue
        views = (VIEW_ALL,) if o.stockout else VIEWS
        for view in views:
            for segment in (ALL_SEGMENTS, o.segment):
                grouped[(o.horizon, view, segment, o.model, o.as_of)].append(o)
    cut_labels = [c.isoformat() for c in result.cuts]
    tables: dict = {}
    segments = (ALL_SEGMENTS,) + SEGMENTS
    for horizon in HORIZONS:
        for view in VIEWS:
            for segment in segments:
                for model in MODEL_NAMES:
                    per_cut = {
                        c: aggregate(grouped.get((horizon, view, segment, model, c), []), config.zero_scale_policy)
                        for c in cut_labels
                    }
                    if not any(v["n"] for v in per_cut.values()):
                        continue
                    metrics = {m: dispersion(per_cut[c][m] for c in cut_labels) for m in METRICS}
                    tables.setdefault(horizon, {}).setdefault(view, {}).setdefault(segment, {})[model] = {
                        "per_cut": per_cut,
                        "across_cuts": metrics,
                        "n_observations": sum(v["n"] for v in per_cut.values()),
                    }
    return tables


def cut_summaries(result: BacktestResult) -> list[dict]:
    """Population, exclusions, eligibility per model, segments and L+R per cut."""
    by_cut: dict[_dt.date, list[SeriesCut]] = defaultdict(list)
    for sc in result.series_cuts:
        by_cut[sc.as_of].append(sc)
    common = common_keys(result.observations)
    out = []
    for as_of in result.cuts:
        scs = by_cut[as_of]
        population = [sc for sc in scs if sc.in_population]
        forecastable = [sc for sc in population if sc.exclusion_reason is None]
        lr_days = sorted(sc.protection.coverage_days for sc in forecastable if sc.protection is not None)
        excluded_ids: dict[str, list[int]] = defaultdict(list)
        for sc in scs:
            if sc.exclusion_reason:
                excluded_ids[sc.exclusion_reason].append(sc.key[0])
        inactive = [sc for sc in population if not sc.snapshot_active]
        out.append(
            {
                "as_of": as_of.isoformat(),
                "evaluation_end": evaluation_end(as_of).isoformat(),
                "candidates": len(scs),
                "population": len(population),
                "excluded": dict(sorted(Counter(sc.exclusion_reason for sc in scs if sc.exclusion_reason).items())),
                "excluded_ids": {reason: sorted(ids) for reason, ids in sorted(excluded_ids.items())},
                "snapshot_inactive_in_population": {
                    "n": len(inactive),
                    "segments": dict(sorted(Counter(sc.segment for sc in inactive if sc.segment).items())),
                },
                # Without an active preferred supplier U1 stops before H: out of L + R, inside h = 1. The supplier
                # is_active flag has no history and is neither inferred nor rebuilt (DT-087).
                "no_preferred_supplier": sorted(sc.key[0] for sc in forecastable if sc.protection is None),
                "eligible_by_model": {m: sum(1 for sc in forecastable if m in sc.forecasts) for m in MODEL_NAMES},
                "ses_boundary_failures": sum(1 for sc in forecastable if sc.ses_failure),
                "segments": dict(sorted(Counter(sc.segment for sc in scs if sc.segment).items())),
                "common_set": {h: sum(1 for k in common if k[0] == as_of.isoformat() and k[3] == h) for h in HORIZONS},
                "truth_missing": {h: sum(1 for sc in forecastable if h not in sc.truth) for h in HORIZONS},
                "stockout_targets": {
                    h: sum(1 for sc in forecastable if h in sc.truth and sc.truth[h].stockout) for h in HORIZONS
                },
                "lr_days": {"min": lr_days[0], "max": lr_days[-1], "n": len(lr_days)} if lr_days else None,
                "lead_time_fallback": sum(
                    1 for sc in forecastable if sc.protection and sc.protection.lead_time_source is not LeadTimeSource.OBSERVED
                ),
            }
        )
    return out


def discontinued_profile(ds: Dataset, result: BacktestResult, config: F5aConfig) -> list[dict]:
    """Products with a ``valid_to`` inside the readable period: last segment while valid and a re-count.

    The re-count places the observed weeks on the 156-week anchored calendar and counts the weeks after
    ``valid_to`` as zero demand. It reads nothing after ``valid_to`` (a master-data date, before the
    holdout): it only shows how a whole-period measurement would classify a discontinued series.
    """
    out = []
    for product_id, product in ds.products.items():
        if product.valid_to is None or product.valid_to > LAST_READABLE_DATE:
            continue
        last = [sc for sc in result.series_cuts if sc.key[0] == product_id and sc.in_population and sc.segment]
        totals = [0.0] * TOTAL_WEEKS
        for location_id in ds.location_ids:
            for row in ds.history((product_id, location_id), product.valid_to):
                offset = (ANCHOR_END - row.day).days // 7
                if offset < TOTAL_WEEKS:
                    totals[TOTAL_WEEKS - 1 - offset] += float(row.quantity)
        first_week = TOTAL_WEEKS - (ANCHOR_END - product.valid_from).days // 7
        padded = totals[max(first_week - 1, 0):]
        feats = features(padded)
        out.append(
            {
                "product_id": product_id,
                "snapshot_active": product.is_active,
                "valid_to": product.valid_to.isoformat(),
                "last_cut_in_population": last[-1].as_of.isoformat() if last else None,
                "segment_while_valid": last[-1].segment if last else None,
                "segments_while_valid": dict(sorted(Counter(sc.segment for sc in last).items())),
                "padded_weeks": feats.weeks,
                "padded_nonzero_weeks": feats.nonzero_weeks,
                "padded_adi": feats.adi,
                "padded_cv2": feats.cv2,
                "padded_segment": classify(feats, True, config),
            }
        )
    return out
