"""Every PROPUESTA / OPEN value used by F5a, in one place and labelled provisional.

The accepted protocol (`DT-075`: cuts, horizon, holdout) lives in `ml.cuts` and is not configurable
here. The values below are proposals of F5a or of `DT-076` point 7 and `DT-077`; none of them fixes
`DT-021`, the official baseline (`docs/05` §6) or the acceptance values of `DT-079`, which belong
to gate G1.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.supply_engine import V1_PROVISIONAL_PARAMETERS, PolicyParameters

#: Label attached to every value of this module in outputs and reports.
PROVISIONAL = "PROPUESTA (provisional)"

# Population rule per cut (`DT-075` point 6 as interpreted by `DT-087`, ACEPTADA).
#: Default (`DT-087`): validity on the cut only (``valid_from ≤ A ≤ valid_to``). ``is_active`` is a
#: snapshot of the dataset end and is not used: applied to past cuts it would leak the future and
#: create survivorship bias.
POPULATION_AS_OF_VALIDITY = "AS_OF_VALIDITY"
#: Alternative kept for comparison: the literal U3 rule (`DT-056` point 10), ``is_active`` AND valid.
POPULATION_U3_SNAPSHOT = "U3_SNAPSHOT"
#: The other rule, run alongside for the comparison of the report.
ALTERNATIVE_POPULATION = {POPULATION_AS_OF_VALIDITY: POPULATION_U3_SNAPSHOT, POPULATION_U3_SNAPSHOT: POPULATION_AS_OF_VALIDITY}

# Zero denominator of the MASE/RMSSE scale (constant training series).
#: The series-cut is left out of MASE/RMSSE and counted.
ZERO_SCALE_EXCLUDE = "EXCLUDE_AND_COUNT"

# Scale of MASE/RMSSE at the protection horizon L + R.
#: Weekly one-step naïve scale multiplied by ``(L + R) / 7`` (squared for RMSSE).
LR_SCALE_WEEKLY_PRORATED = "WEEKLY_SCALE_PRORATED"

# Initial level of the simple exponential smoothing.
SES_INIT_FIRST_OBSERVATION = "FIRST_OBSERVATION"


def _alpha_grid() -> tuple[float, ...]:
    """0.05 … 0.95 step 0.05, built from integers so that the grid is exact and reproducible."""
    return tuple(k / 20 for k in range(1, 20))


@dataclass(frozen=True)
class F5aConfig:
    """Configuration of one F5a run. Defaults are the proposals documented in the report."""

    # Population (DT-075 point 6, DT-087): validity on the cut, without the is_active snapshot.
    population_rule: str = POPULATION_AS_OF_VALIDITY
    # SES (DT-076 point 7, PROPUESTA).
    ses_alpha_grid: tuple[float, ...] = field(default_factory=_alpha_grid)
    ses_initial_level: str = SES_INIT_FIRST_OBSERVATION
    #: Same minimum as the naïve baseline: 11 errors at h = 14 need 25 weeks (DT-056 point 7).
    ses_min_history_weeks: int = 25
    # Segmentation (DT-077, PROPUESTA, OPEN until G1).
    adi_threshold: float = 1.32
    cv2_threshold: float = 0.49
    #: «Nuevo o histórico corto»: fewer weeks than the method minimum (25, DT-056).
    short_history_weeks: int = 25
    # Level 1 (DT-076).
    zero_scale_policy: str = ZERO_SCALE_EXCLUDE
    lr_scale_policy: str = LR_SCALE_WEEKLY_PRORATED
    # U1 policy used to derive L (the one U1 would use, DT-076 point 3).
    policy: PolicyParameters = V1_PROVISIONAL_PARAMETERS

    def describe(self) -> dict[str, Any]:
        """JSON-ready description with the provisional label on every proposal."""
        policy = asdict(self.policy)
        policy["z"] = str(self.policy.z)
        return {
            "label": PROVISIONAL,
            "population_rule": self.population_rule,
            "population_rule_source": "DT-087 (ACEPTADA)" if self.population_rule == POPULATION_AS_OF_VALIDITY else "alternative",
            "ses": {
                "alpha_grid": [f"{a:.2f}" for a in self.ses_alpha_grid],
                "selection": "minimum one-step SSE inside the training window; ties → smallest alpha",
                "initial_level": self.ses_initial_level,
                "min_history_weeks": self.ses_min_history_weeks,
                "interval": "nearest-rank 10/90 of DT-056 on SES errors per horizon (fixed alpha)",
            },
            "segmentation": {
                "adi_threshold": self.adi_threshold,
                "cv2_threshold": self.cv2_threshold,
                "short_history_weeks": self.short_history_weeks,
                "seasonality": "OPEN (no criterion, DT-077)",
            },
            "level1": {
                "zero_scale_policy": self.zero_scale_policy,
                "lr_scale_policy": self.lr_scale_policy,
            },
            "u1_policy": policy,
        }
