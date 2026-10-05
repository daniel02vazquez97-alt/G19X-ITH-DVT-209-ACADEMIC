"""``ExplanationContext`` from persisted values only (`DT-068` point 4).

``api`` reads the recommendation row, the run context and ``products.unit_of_measure`` and hands plain
values here. This module copies them into frozen structures; it receives no connection and no function
of the engine, and it reads, transforms and explains — it never recalculates.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterable, Mapping
from typing import Any

from .errors import ExplanationError
from .facts import build_facts
from .types import KIND, OUTCOMES, ExplanationContext, Provenance


def _texts(values: Iterable[Any] | None, name: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        raise ExplanationError(f"{name} must be a collection of codes")
    result = tuple(values)
    if not all(isinstance(value, str) for value in result):
        raise ExplanationError(f"{name} must contain text codes")
    return result


def _int(value: Any, name: str, optional: bool = False) -> int | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExplanationError(f"{name} must be an integer")
    return value


def _date(value: Any) -> _dt.date:
    if isinstance(value, _dt.datetime):
        raise ExplanationError("as_of_date must be a date")
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str):
        return _dt.date.fromisoformat(value)
    raise ExplanationError("as_of_date must be a date")


def build_provenance(provenance: Mapping[str, Any]) -> Provenance:
    """The recommendation ``provenance`` of `DT-066`, frozen; ``notices`` unchanged."""
    try:
        return Provenance(
            data_origin=provenance["data_origin"],
            dataset_version=provenance["dataset_version"],
            generator_version=provenance["generator_version"],
            data_load_id=_int(provenance["data_load_id"], "data_load_id"),
            as_of_date=_date(provenance["as_of_date"]),
            run_id=_int(provenance["run_id"], "run_id"),
            engine_version=provenance["engine_version"],
            policy_set=provenance["policy_set"],
            forecast_run_id=_int(provenance["forecast_run_id"], "forecast_run_id", optional=True),
            notices=_texts(provenance["notices"], "notices"),
        )
    except KeyError as exc:
        raise ExplanationError(f"provenance without {exc.args[0]}") from exc


def build_context(
    *,
    recommendation_id: int,
    run_id: int,
    outcome: str,
    flags: Iterable[str],
    reasons: Iterable[str],
    missing_policy_parameters: Iterable[str],
    breakdown: Mapping[str, Any],
    unit_of_measure: str | None,
    provenance: Mapping[str, Any],
) -> ExplanationContext:
    if outcome not in OUTCOMES:
        raise ExplanationError(f"unknown outcome {outcome!r}")
    if not isinstance(breakdown, Mapping):
        raise ExplanationError("breakdown must be a mapping")
    flag_codes = _texts(flags, "flags")
    source = breakdown.get("lead_time_source")
    if source is not None and not isinstance(source, str):
        raise ExplanationError("lead_time_source must be text")
    if unit_of_measure is not None and not isinstance(unit_of_measure, str):
        raise ExplanationError("unit_of_measure must be text")
    return ExplanationContext(
        kind=KIND,
        recommendation_id=_int(recommendation_id, "recommendation_id"),
        run_id=_int(run_id, "run_id"),
        outcome=outcome,
        facts=build_facts(outcome, flag_codes, breakdown),
        flags=flag_codes,
        reasons=_texts(reasons, "reasons"),
        missing_policy_parameters=_texts(missing_policy_parameters, "missing_policy_parameters"),
        lead_time_source=source,
        unit_of_measure=unit_of_measure,
        provenance=build_provenance(provenance),
    )
