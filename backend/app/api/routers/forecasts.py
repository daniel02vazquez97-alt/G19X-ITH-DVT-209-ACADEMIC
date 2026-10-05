"""``GET /api/v1/forecasts``: primary series of the selected FORECAST run (`DT-066`); never recalculated."""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, Query

from app.db.read import forecasts as forecasts_read

from ..auth import ALL_ROLES, require_roles
from ..pagination import PageParams, page_params
from ..provenance import forecast_provenance
from ..schemas import ForecastPage
from . import connection, errors, resolve_run

router = APIRouter(prefix="/api/v1/forecasts", tags=["forecasts"])

_PERIOD_FIELDS = ("period_start", "period_end", "predicted_quantity", "lower_bound", "upper_bound",
                  "confidence_level", "method_used", "confidence_flag")


def series_from_rows(rows: list[dict]) -> list[dict]:
    """Group period rows (ordered by product and period) into one series per product."""
    series: list[dict] = []
    for row in rows:
        if not series or series[-1]["product"]["id"] != row["product_id"]:
            series.append(
                {
                    "product": {"id": row["product_id"], "sku": row["sku"]},
                    "model_version": {"name": row["model_name"], "version": row["model_version"]},
                    "periods": [],
                }
            )
        series[-1]["periods"].append({field: row[field] for field in _PERIOD_FIELDS})
    return series


@router.get("", response_model=ForecastPage, responses=errors(400, 401, 403, 404, 422),
            summary="Series primarias de la ejecución de forecast (los cuatro roles)")
def list_forecasts(
    product_id: int | None = Query(None, ge=1),
    category_id: int | None = Query(None),
    run_id: int | None = Query(None, ge=1, description="Por defecto, la regla determinista de DT-066"),
    page: PageParams = Depends(page_params),
    _identity=Depends(require_roles(ALL_ROLES)),
    conn: psycopg.Connection = Depends(connection),
) -> dict:
    run = resolve_run(conn, "FORECAST", run_id)
    total, rows = forecasts_read.series_page(
        conn, run["id"], product_id=product_id, category_id=category_id, limit=page.page_size, offset=page.offset
    )
    return {"items": series_from_rows(rows), "total": total, "page": page.page, "page_size": page.page_size,
            "provenance": forecast_provenance(run)}
