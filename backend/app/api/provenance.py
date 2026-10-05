"""``provenance`` block of forecast and recommendation responses (`DT-066`, `docs/07` §7.1)."""

from __future__ import annotations

from typing import Any

SYNTHETIC_DATA = "SYNTHETIC_DATA"
V1_PROVISIONAL_POLICY = "V1_PROVISIONAL_POLICY"
SYNTHETIC = "SYNTHETIC"
V1_PROVISIONAL = "V1_PROVISIONAL"


def notices(data_origin: str | None, policy_set: str | None = None) -> list[str]:
    """``SYNTHETIC_DATA`` iff the load is synthetic; ``V1_PROVISIONAL_POLICY`` iff the policy is V1's."""
    result = []
    if data_origin == SYNTHETIC:
        result.append(SYNTHETIC_DATA)
    if policy_set == V1_PROVISIONAL:
        result.append(V1_PROVISIONAL_POLICY)
    return result


def _common(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "data_origin": run["data_origin"],
        "dataset_version": run["dataset_version"],
        "generator_version": run["generator_version"],
        "data_load_id": run["data_load_id"],
        "as_of_date": run["as_of_date"],
        "run_id": run["id"],
    }


def forecast_provenance(run: dict[str, Any]) -> dict[str, Any]:
    model = None
    if run.get("reference_model_name") is not None:
        model = {"name": run["reference_model_name"], "version": run["reference_model_version"]}
    return {**_common(run), "model_version": model, "notices": notices(run["data_origin"])}


def recommendation_provenance(run: dict[str, Any]) -> dict[str, Any]:
    policy_set = (run.get("summary") or {}).get("policy_set")
    return {
        **_common(run),
        "engine_version": run["engine_version"],
        "policy_set": policy_set,
        "forecast_run_id": run["forecast_run_id"],
        "notices": notices(run["data_origin"], policy_set),
    }
