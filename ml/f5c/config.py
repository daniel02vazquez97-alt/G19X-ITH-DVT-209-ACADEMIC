"""Configuration of F5c: accepted criteria of `DT-093` and the provisional values of this unit, labelled.

The accepted values (`DT-091`, `DT-093`) are decisions of the responsable; everything else is a PROPUESTA of F5c,
configurable and reported as provisional.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.forecasting import MOVING_AVERAGE

from ..candidates import CandidateConfig
from ..config import PROVISIONAL, F5aConfig

STRATEGY_AS_IS = "a"
STRATEGY_EXCLUDE = "b"
STRATEGY_IMPUTE = "c"
STRATEGIES: tuple[str, ...] = (STRATEGY_AS_IS, STRATEGY_EXCLUDE, STRATEGY_IMPUTE)
STRATEGY_LABELS = {
    STRATEGY_AS_IS: "(a) consumo tal cual",
    STRATEGY_EXCLUDE: "(b) excluir días con desabasto",
    STRATEGY_IMPUTE: "(c) imputar días con desabasto",
}
#: The official baseline (`DT-089`): reference of every comparison and the substitute of a failed candidate.
OFFICIAL_BASELINE = MOVING_AVERAGE.name


def _k_grid() -> tuple[float, ...]:
    """Widening factors 0.50 … 3.00 step 0.05, built from integers."""
    return tuple(k / 20 for k in range(10, 61))


@dataclass(frozen=True)
class Criteria:
    """`DT-091` and `DT-093` (ACEPTADA, provisional, SYNTHETIC)."""

    primary_metric: str = "mase"
    primary_horizon: str = "LR"
    segment_worsening: float = 0.05
    segment_min_products: int = 10
    cuts_fraction_num: int = 2
    cuts_fraction_den: int = 3
    min_comparable_cuts: int = 5
    inventory_tolerance: float = 0.05
    units_short_tolerance: float = 0.02
    fill_rate_points: float = 0.002
    bias_band: float = 0.10
    segment_bias_worsening: float = 0.05
    coverage_low: float = 0.75
    coverage_high: float = 0.85
    nominal_level: float = 0.80

    def describe(self) -> dict[str, Any]:
        return {
            "status": "ACEPTADA (DT-091, DT-093), provisional, SYNTHETIC",
            "primary": f"{self.primary_metric.upper()} at {self.primary_horizon}; h = 1 secondary (DT-093 point 1)",
            "segments": f"no segment with ≥ {self.segment_min_products} products worse than {self.segment_worsening:.0%}",
            "cuts": f"aggregate and ≥ ⌈{self.cuts_fraction_num}/{self.cuts_fraction_den}⌉ of the comparable cuts, minimum "
            f"{self.min_comparable_cuts}; fewer → not conclusive",
            "level2": f"units short ≤ +{self.units_short_tolerance:.0%}, fill rate ≥ −{self.fill_rate_points}, "
            f"average inventory ≤ +{self.inventory_tolerance:.0%}",
            "bias": f"absolute relative bias at L+R ≤ {self.bias_band}; segments ≥ {self.segment_min_products} products not worse than "
            f"{self.segment_bias_worsening}",
            "coverage": f"nominal {self.nominal_level}; calibrated if within [{self.coverage_low}, {self.coverage_high}] per horizon "
            "on the late cuts (label of the band only)",
        }


@dataclass(frozen=True)
class F5cConfig:
    f5a: F5aConfig = field(default_factory=F5aConfig)
    candidates: CandidateConfig = field(default_factory=CandidateConfig)
    criteria: Criteria = field(default_factory=Criteria)
    # Segmentation (DT-093 point 7, ACEPTADA): Syntetos-Boylan thresholds live in F5aConfig (1.32 / 0.49).
    seasonal_min_weeks: int = 104
    seasonal_lag: int = 52
    seasonal_z: float = 1.96
    # DT-011 estimators (DT-093 point 8, ACEPTADA).
    impute_window_days: int = 56
    extreme_stockout_share: float = 0.5
    #: Number of candidates studied in DT-011 besides the moving average and SES (DT-092: the two best by Level 1).
    study_top_candidates: int = 2
    # US-055 (PROPUESTA): late cuts are the cuts from this index on; each late cut is calibrated with the cuts whose
    # 14 evaluation weeks end on or before its as_of (DT-082 point 2). Multiplicative widening of the interval.
    late_cut_index: int = 8
    widening_grid: tuple[float, ...] = field(default_factory=_k_grid)
    # Simulator (DT-093 point 9, ACEPTADA): candidates re-optimise every 4 weekly decisions, state every week.
    sim_refit_every: int = 4

    def describe(self) -> dict[str, Any]:
        return {
            "label": PROVISIONAL + " where not ACEPTADA",
            "official_baseline": OFFICIAL_BASELINE + " (DT-089)",
            "criteria": self.criteria.describe(),
            "segmentation": {
                "status": "ACEPTADA (DT-093 point 7)",
                "adi_threshold": self.f5a.adi_threshold,
                "cv2_threshold": self.f5a.cv2_threshold,
                "seasonality": f"n ≥ {self.seasonal_min_weeks} training weeks and ACF(lag {self.seasonal_lag}) > "
                f"{self.seasonal_z}/√n",
            },
            "dt011": {
                "status": "ACEPTADA (DT-093 point 8)",
                "impute": f"mean of the non-stockout days of the previous {self.impute_window_days} days; none → as is",
                "exclude": "observed days × 7 / days_observed; weeks without observed days omitted",
                "extreme": f"series with more than {self.extreme_stockout_share:.0%} stockout days reported apart",
                "models": f"official baseline, SES and the {self.study_top_candidates} best candidates by Level 1 "
                "(lowest MASE at L+R relative to the official baseline on their pairwise comparable set)",
            },
            "us055": {
                "status": "PROPUESTA (provisional)",
                "late_cuts": f"cuts from index {self.late_cut_index} (0-based) on",
                "calibration": "per model and horizon, factor k of the grid that brings the coverage of "
                "[p − k(p − lower), p + k(upper − p)] (lower ≥ 0) closest to the nominal level on the cuts whose "
                "evaluation ends on or before the measured cut; ties → smaller k",
                "widening_grid": [self.widening_grid[0], self.widening_grid[-1], len(self.widening_grid)],
            },
            "simulator": {
                "status": "ACEPTADA (DT-093 points 9 and 11)",
                "candidates_refit_every_decisions": self.sim_refit_every,
                "baselines_and_ses": "as in F5b (forecast recomputed at every decision)",
                "substitution": "official baseline points when the candidate is not eligible or invalid; counted",
            },
            "candidates": self.candidates.describe(),
        }
