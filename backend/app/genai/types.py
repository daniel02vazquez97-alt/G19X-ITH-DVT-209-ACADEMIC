"""Immutable types of U6 (`DT-068` points 3, 4, 5 and 11): frozen, slotted dataclasses and tuples."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

KIND = "RECOMMENDATION_EXPLANATION"

RECOMMEND = "RECOMMEND"
NO_NEED = "NO_NEED"
NOT_CALCULABLE = "NOT_CALCULABLE"
OUTCOMES = (RECOMMEND, NO_NEED, NOT_CALCULABLE)

QUANTITY = "QUANTITY"
DAYS = "DAYS"
FACTOR = "FACTOR"  # in the vocabulary; no fact of V1 uses it
UNITS = (QUANTITY, DAYS, FACTOR)

VERIFIED = "VERIFIED"
DEGRADED = "DEGRADED"
NOT_APPLICABLE = "NOT_APPLICABLE"
NARRATIVE_UNVERIFIED = "NARRATIVE_UNVERIFIED"

#: Identity of the template generator (`DT-068` point 10): any change of the narrative raises it.
GENERATOR = "template/1.0.0"


@dataclass(frozen=True, slots=True)
class Fact:
    """An authorized figure. ``value``: the persisted text; ``display``: the only text the narrative may
    contain, used both to render and to verify (`DT-069`)."""

    key: str
    value: str
    display: str
    unit: str


@dataclass(frozen=True, slots=True)
class Provenance:
    """The recommendation ``provenance`` block of `DT-066`, frozen."""

    data_origin: str | None
    dataset_version: str
    generator_version: str | None
    data_load_id: int
    as_of_date: _dt.date
    run_id: int
    engine_version: str | None
    policy_set: str | None
    forecast_run_id: int | None
    notices: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExplanationContext:
    kind: str
    recommendation_id: int
    run_id: int
    outcome: str
    facts: tuple[Fact, ...]
    flags: tuple[str, ...]
    reasons: tuple[str, ...]
    missing_policy_parameters: tuple[str, ...]
    lead_time_source: str | None
    unit_of_measure: str | None
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class ReasonDetail:
    code: str
    text: str


@dataclass(frozen=True, slots=True)
class Explanation:
    generator: str
    status: str
    narrative: str | None
    warning: str | None
    reason_details: tuple[ReasonDetail, ...]
