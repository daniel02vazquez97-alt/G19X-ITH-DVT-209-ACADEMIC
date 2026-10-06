"""Level 1 metrics of `docs/05` §9.1 and `DT-076`, all of them, without choosing the primary one.

Conventions (documented in the report):

* error ``e = F − Y`` (forecast minus observed); positive bias = over-forecast;
* MASE / RMSSE of one series-cut: ``|e| / s₁`` and ``|e| / √s₂``, with ``s₁``/``s₂`` the mean absolute
  / squared one-step naïve error inside the training window of that cut (`DT-076` point 4); the
  aggregate is the mean over series. A zero scale is handled by ``zero_scale_policy`` (PROPUESTA);
* WAPE = ``Σ|e| / ΣY``; relative bias = ``Σe / ΣY`` (``None`` if ``ΣY = 0``);
* coverage = share of ``Y`` inside ``[lower, upper]`` where an interval exists (weekly horizon only);
* MAPE is informative only (`DT-021`): mean ``|e| / Y`` over ``Y > 0``; zero actuals are counted.

The truth is the observed consumption, never an imputed value (`DT-076` point 2).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .config import LR_SCALE_WEEKLY_PRORATED, ZERO_SCALE_EXCLUDE

METRICS: tuple[str, ...] = ("mase", "rmsse", "wape", "mae", "rmse", "bias", "bias_rel", "coverage", "mape")


@dataclass(frozen=True, slots=True)
class Observation:
    """One forecast of one model for one series, cut and horizon, with its observed truth."""

    as_of: str
    product_id: int
    location_id: int
    model: str
    horizon: str  # "H1" (week 1) or "LR" (L + R days)
    days: int
    segment: str
    forecast: float
    actual: float
    lower: float | None
    upper: float | None
    scale_abs: float
    scale_sq: float
    stockout: bool

    @property
    def error(self) -> float:
        return self.forecast - self.actual

    @property
    def scaled_abs(self) -> float | None:
        return abs(self.error) / self.scale_abs if self.scale_abs > 0 else None

    @property
    def scaled_rms(self) -> float | None:
        return abs(self.error) / math.sqrt(self.scale_sq) if self.scale_sq > 0 else None

    @property
    def covered(self) -> bool | None:
        if self.lower is None or self.upper is None:
            return None
        return self.lower <= self.actual <= self.upper


def naive_scale(weeks: Sequence[float]) -> tuple[float, float]:
    """Mean absolute and mean squared one-step naïve error inside the training window."""
    diffs = [weeks[t] - weeks[t - 1] for t in range(1, len(weeks))]
    if not diffs:
        return 0.0, 0.0
    return math.fsum(abs(d) for d in diffs) / len(diffs), math.fsum(d * d for d in diffs) / len(diffs)


def horizon_scale(scale_abs: float, scale_sq: float, days: int, policy: str) -> tuple[float, float]:
    """Scale at a horizon of ``days`` days; the weekly horizon (7 days) keeps the weekly scale."""
    if policy != LR_SCALE_WEEKLY_PRORATED:
        raise ValueError(f"unknown L+R scale policy {policy}")
    factor = days / 7
    return scale_abs * factor, scale_sq * factor * factor


def aggregate(observations: Iterable[Observation], zero_scale_policy: str = ZERO_SCALE_EXCLUDE) -> dict:
    """All candidate metrics over a set of observations (normally one cut)."""
    if zero_scale_policy != ZERO_SCALE_EXCLUDE:
        raise ValueError(f"unknown zero-scale policy {zero_scale_policy}")
    obs = list(observations)
    n = len(obs)
    result: dict = {"n": n}
    if n == 0:
        result.update({m: None for m in METRICS})
        result.update(n_zero_scale=0, n_interval=0, n_mape=0, n_zero_actual=0)
        return result
    errors = [o.error for o in obs]
    abs_errors = [abs(e) for e in errors]
    total_actual = math.fsum(o.actual for o in obs)
    scaled_abs = [o.scaled_abs for o in obs if o.scaled_abs is not None]
    scaled_rms = [o.scaled_rms for o in obs if o.scaled_rms is not None]
    covered = [o.covered for o in obs if o.covered is not None]
    positive = [o for o in obs if o.actual > 0]
    result.update(
        mae=math.fsum(abs_errors) / n,
        rmse=math.sqrt(math.fsum(e * e for e in errors) / n),
        mase=math.fsum(scaled_abs) / len(scaled_abs) if scaled_abs else None,
        rmsse=math.fsum(scaled_rms) / len(scaled_rms) if scaled_rms else None,
        wape=math.fsum(abs_errors) / total_actual if total_actual > 0 else None,
        bias=math.fsum(errors) / n,
        bias_rel=math.fsum(errors) / total_actual if total_actual > 0 else None,
        coverage=sum(1 for c in covered if c) / len(covered) if covered else None,
        mape=math.fsum(abs(o.error) / o.actual for o in positive) / len(positive) if positive else None,
        n_zero_scale=n - len(scaled_abs),
        n_interval=len(covered),
        n_mape=len(positive),
        n_zero_actual=n - len(positive),
    )
    return result


def dispersion(values: Iterable[float | None]) -> dict:
    """Mean, population standard deviation, minimum and maximum across cuts (``None`` skipped)."""
    present = [v for v in values if v is not None]
    if not present:
        return {"mean": None, "sd": None, "min": None, "max": None, "n_cuts": 0}
    return {
        "mean": math.fsum(present) / len(present),
        "sd": statistics.pstdev(present) if len(present) > 1 else 0.0,
        "min": min(present),
        "max": max(present),
        "n_cuts": len(present),
    }
