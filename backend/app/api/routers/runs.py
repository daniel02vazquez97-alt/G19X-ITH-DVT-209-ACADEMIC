"""``GET /api/v1/runs/{run_id}``: any calculation run, COMPLETED or FAILED (PLANNER, ADMIN)."""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, Path

from app.db.read import runs as runs_read

from ..auth import RUN_ROLES, require_roles
from ..errors import ApiError
from ..schemas import RunDetail
from . import connection, errors

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])

#: Counters of each run type's ``summary`` exposed as ``counts`` (U3 `DT-057`, U4 `DT-062`).
COUNT_KEYS = {
    "FORECAST": ("candidates", "eligible", "excluded_count", "forecasted", "fallback_count", "no_forecast_count",
                 "forecast_rows", "primary_rows"),
    "RECOMMENDATION": ("candidates", "evaluated", "by_outcome", "by_reason", "by_flag", "rows"),
}


@router.get("/{run_id}", response_model=RunDetail, responses=errors(401, 403, 404, 422),
            summary="Ejecución de cálculo (PLANNER, ADMIN)")
def get_run(
    run_id: int = Path(..., ge=1),
    _identity=Depends(require_roles(RUN_ROLES)),
    conn: psycopg.Connection = Depends(connection),
) -> dict:
    run = runs_read.run_context(conn, run_id)
    if run is None:
        raise ApiError(404, "RUN_NOT_FOUND", "La ejecución no existe.", {"run_id": run_id})
    summary = run["summary"] or {}
    model = None
    if run["reference_model_name"] is not None:
        model = {"name": run["reference_model_name"], "version": run["reference_model_version"]}
    return {
        "id": run["id"],
        "run_type": run["run_type"],
        "status": run["status"],
        "as_of_date": run["as_of_date"],
        "data_load": {"id": run["data_load_id"], "dataset_version": run["dataset_version"],
                      "generator_version": run["generator_version"], "data_origin": run["data_origin"]},
        "versions": {"engine_version": run["engine_version"], "forecast_run_id": run["forecast_run_id"],
                     "reference_model_version": model, "config_sha256": run["config_sha256"]},
        "counts": {key: summary[key] for key in COUNT_KEYS[run["run_type"]] if key in summary},
        "started_at": run["started_at"],
        "finished_at": run["finished_at"],
        "error": run["error"],
    }
