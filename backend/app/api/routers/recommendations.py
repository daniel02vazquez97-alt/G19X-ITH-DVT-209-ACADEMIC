"""Recommendation routes: persisted U4 evaluations with any of the three outcomes (`DT-059`, `DT-066`)."""

from __future__ import annotations

from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, Path, Query

from app.db.read import recommendations as recommendations_read
from app.db.read import runs as runs_read

from ..auth import ALL_ROLES, require_roles
from ..errors import ApiError
from ..pagination import PageParams, page_params, parse_sort
from ..provenance import recommendation_provenance
from ..schemas import RecommendationDetail, RecommendationPage
from . import connection, errors, resolve_run

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])

_SORT_FIELDS = tuple(recommendations_read.SORT_COLUMNS)
_DETAIL_FIELDS = ("id", "as_of_date", "outcome", "reasons", "flags", "missing_policy_parameters", "forecast_id",
                  "suggested_order_date", "recommended_quantity", "raw_quantity", "reorder_point", "safety_stock",
                  "lead_time_used_days", "demand_during_lead_time", "inventory_position_at_calc", "policy_set",
                  "policy_snapshot", "calculation_inputs", "engine_version", "generated_at")


def _supplier(row: dict) -> dict | None:
    if row["supplier_id"] is None:
        return None
    return {"id": row["supplier_id"], "code": row["supplier_code"], "name": row["supplier_name"]}


def _product(row: dict) -> dict:
    return {"id": row["product_id"], "sku": row["product_sku"], "name": row["product_name"]}


def detail_from_row(row: dict) -> dict:
    """The stored evaluation, unchanged: ``calculation_inputs`` keeps U4's exact representation."""
    return {**{field: row[field] for field in _DETAIL_FIELDS}, "run_id": row["calculation_run_id"],
            "product": _product(row), "supplier": _supplier(row)}


@router.get("", response_model=RecommendationPage, responses=errors(400, 401, 403, 404, 422),
            summary="Evaluaciones de la ejecución de recomendaciones (los cuatro roles)")
def list_recommendations(
    outcome: Literal["RECOMMEND", "NO_NEED", "NOT_CALCULABLE"] = Query("RECOMMEND"),
    product_id: int | None = Query(None, ge=1),
    category_id: int | None = Query(None),
    supplier_id: int | None = Query(None),
    run_id: int | None = Query(None, ge=1, description="Por defecto, la regla determinista de DT-066"),
    sort: str | None = Query(None, description="sku | recommended_quantity | suggested_order_date; por defecto sku"),
    page: PageParams = Depends(page_params),
    _identity=Depends(require_roles(ALL_ROLES)),
    conn: psycopg.Connection = Depends(connection),
) -> dict:
    order = parse_sort(sort, _SORT_FIELDS, "sku")
    run = resolve_run(conn, "RECOMMENDATION", run_id)
    total, rows = recommendations_read.list_recommendations(
        conn, run["id"], outcome=outcome, product_id=product_id, category_id=category_id, supplier_id=supplier_id,
        sort=order.field, descending=order.descending, limit=page.page_size, offset=page.offset,
    )
    items = [
        {"id": r["id"], "product": _product(r), "supplier": _supplier(r), "recommended_quantity": r["recommended_quantity"],
         "raw_quantity": r["raw_quantity"], "suggested_order_date": r["suggested_order_date"], "outcome": r["outcome"],
         "flags": r["flags"]}
        for r in rows
    ]
    return {"items": items, "total": total, "page": page.page, "page_size": page.page_size,
            "provenance": recommendation_provenance(run)}


@router.get("/{recommendation_id}", response_model=RecommendationDetail, responses=errors(401, 403, 404, 422),
            summary="Desglose completo de una evaluación (los cuatro roles)")
def get_recommendation(
    recommendation_id: int = Path(..., ge=1),
    _identity=Depends(require_roles(ALL_ROLES)),
    conn: psycopg.Connection = Depends(connection),
) -> dict:
    row = recommendations_read.get_recommendation(conn, recommendation_id)
    if row is None:
        raise ApiError(404, "RECOMMENDATION_NOT_FOUND", "No existe la evaluación indicada.",
                       {"recommendation_id": recommendation_id})
    run = runs_read.run_context(conn, row["calculation_run_id"])
    return {**detail_from_row(row), "provenance": recommendation_provenance(run)}
