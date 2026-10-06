"""Provisional catalogue segmentation (US-051, `DT-077` PROPUESTA, OPEN until G1).

Syntetos-Boylan on the anchored weekly series of the training window of each cut (only data
``≤ as_of``): ``ADI`` = weeks / non-zero weeks, ``CV²`` = (population standard deviation / mean)² of
the non-zero weeks. Thresholds come from `ml.config` (one place). No seasonality criterion: it is
OPEN in `DT-077` and F5a does not invent one.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from .config import F5aConfig

SMOOTH = "SMOOTH"  # suave
ERRATIC = "ERRATIC"  # errática
INTERMITTENT = "INTERMITTENT"  # intermitente
LUMPY = "LUMPY"  # irregular
SHORT_HISTORY = "SHORT_HISTORY"  # nuevo o histórico corto
DISCONTINUED = "DISCONTINUED"  # descontinuado (inactivo o fuera de vigencia)
NO_DEMAND = "NO_DEMAND"  # sin ninguna semana no nula: ADI y CV² no definidos

SEGMENTS: tuple[str, ...] = (SMOOTH, ERRATIC, INTERMITTENT, LUMPY, SHORT_HISTORY, NO_DEMAND, DISCONTINUED)
SEGMENT_LABELS_ES = {
    SMOOTH: "suave",
    ERRATIC: "errática",
    INTERMITTENT: "intermitente",
    LUMPY: "irregular",
    SHORT_HISTORY: "nuevo o histórico corto",
    NO_DEMAND: "sin demanda",
    DISCONTINUED: "descontinuado",
}


@dataclass(frozen=True, slots=True)
class SegmentFeatures:
    weeks: int
    nonzero_weeks: int
    zero_share: float
    adi: float | None
    cv2: float | None


def features(weekly: Sequence[float]) -> SegmentFeatures:
    n = len(weekly)
    nonzero = [w for w in weekly if w != 0]
    k = len(nonzero)
    if n == 0:
        return SegmentFeatures(0, 0, 0.0, None, None)
    if k == 0:
        return SegmentFeatures(n, 0, 1.0, None, None)
    mean = math.fsum(nonzero) / k
    variance = math.fsum((w - mean) ** 2 for w in nonzero) / k
    return SegmentFeatures(n, k, (n - k) / n, n / k, variance / (mean * mean))


def classify(feats: SegmentFeatures, in_population: bool, config: F5aConfig) -> str:
    """Segment of one series at one cut. Non-population series are «descontinuado» (`DT-056` D-11)."""
    if not in_population:
        return DISCONTINUED
    if feats.weeks < config.short_history_weeks:
        return SHORT_HISTORY
    if feats.adi is None or feats.cv2 is None:
        return NO_DEMAND
    intermittent = feats.adi >= config.adi_threshold
    erratic = feats.cv2 >= config.cv2_threshold
    if intermittent and erratic:
        return LUMPY
    if intermittent:
        return INTERMITTENT
    if erratic:
        return ERRATIC
    return SMOOTH


def lag_autocorrelation(weekly: Sequence[float], lag: int) -> float | None:
    """Sample autocorrelation at ``lag`` (``Σ (y_t − ȳ)(y_{t+lag} − ȳ) / Σ (y_t − ȳ)²``); ``None`` if undefined."""
    n = len(weekly)
    if n <= lag:
        return None
    mean = math.fsum(weekly) / n
    deviations = [w - mean for w in weekly]
    denominator = math.fsum(d * d for d in deviations)
    if denominator == 0:
        return None
    return math.fsum(deviations[t] * deviations[t + lag] for t in range(n - lag)) / denominator


def seasonality(weekly: Sequence[float], min_weeks: int = 104, lag: int = 52, z: float = 1.96) -> tuple[float | None, bool]:
    """F5c criterion (`DT-093` point 7): seasonal if ``n ≥ min_weeks`` and the autocorrelation at ``lag`` exceeds
    ``z / √n``, with ``n`` the training weeks. Returns the autocorrelation (``None`` when undefined or too short)."""
    n = len(weekly)
    if n < min_weeks:
        return None, False
    acf = lag_autocorrelation(weekly, lag)
    return acf, acf is not None and acf > z / math.sqrt(n)
