"""Products, product history (`DT-067`), product forecast and product recommendation routes."""

from __future__ import annotations

import datetime as _dt
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, Path, Query

from app.db.read import consumption as consumption_read
from app.db.read import forecasts as forecasts_read
from app.db.read import products as products_read
from app.db.read import recommendations as recommendations_read

from ..auth import ALL_ROLES, HISTORY_ROLES, require_roles
from ..errors import ApiError
from ..history import DEFAULT_GRANULARITY, DayRow, build_history, statistics
from ..pagination import PageParams, page_params, parse_sort
from ..provenance import forecast_provenance, recommendation_provenance
from ..schemas import History, ProductDetail, ProductForecast, ProductPage, RecommendationDetail
from . import connection, errors, resolve_run
from .forecasts import series_from_rows
from .recommendations import detail_from_row

router = APIRouter(prefix="/api/v1/products", tags=["products"])

_SORT_FIELDS = tuple(products_read.SORT_COLUMNS)


def product_item(row: dict) -> dict:
    return {
        "id": row["id"],
        "sku": row["sku"],
        "name": row["name"],
        "category": {"id": row["category_id"], "code": row["category_code"], "name": row["category_name"]},
        "unit_of_measure": row["unit_of_measure"],
        "is_active": row["is_active"],
        "valid_from": row["valid_from"],
        "valid_to": row["valid_to"],
        "data_origin": row["data_origin"],
    }


def require_product(conn: psycopg.Connection, product_id: int) -> None:
    if not products_read.product_exists(conn, product_id):
        raise ApiError(404, "PRODUCT_NOT_FOUND", "No existe un producto con el identificador indicado.",
                       {"product_id": product_id})


@router.get("", response_model=ProductPage, responses=errors(400, 401, 403, 422),
            summary="Productos (VIEWER, ANALYST, PLANNER, ADMIN)")
def list_products(
    search: str | None = Query(None, min_length=1, max_length=100, description="Subcadena en sku o nombre"),
    category_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    sort: str | None = Query(None, description="sku | name | id, con - para descendente; por defecto sku"),
    page: PageParams = Depends(page_params),
    _identity=Depends(require_roles(ALL_ROLES)),
    conn: psycopg.Connection = Depends(connection),
) -> dict:
    order = parse_sort(sort, _SORT_FIELDS, "sku")
    total, rows = products_read.list_products(
        conn, search=search, category_id=category_id, is_active=is_active, sort=order.field,
        descending=order.descending, limit=page.page_size, offset=page.offset,
    )
    return {"items": [product_item(r) for r in rows], "total": total, "page": page.page, "page_size": page.page_size}


@router.get("/{product_id}", response_model=ProductDetail, responses=errors(401, 403, 404, 422),
            summary="Detalle del producto con inventario y proveedores (los cuatro roles)")
def get_product(
    product_id: int = Path(..., ge=1),
    _identity=Depends(require_roles(ALL_ROLES)),
    conn: psycopg.Connection = Depends(connection),
) -> dict:
    row = products_read.get_product(conn, product_id)
    if row is None:
        raise ApiError(404, "PRODUCT_NOT_FOUND", "No existe un producto con el identificador indicado.",
                       {"product_id": product_id})
    suppliers = [
        {
            "supplier": {"id": s["supplier_id"], "code": s["supplier_code"], "name": s["supplier_name"]},
            "moq": s["moq"], "order_multiple": s["order_multiple"], "unit_cost": s["unit_cost"],
            "agreed_lead_time_days": s["agreed_lead_time_days"], "is_preferred": s["is_preferred"],
            "is_active": s["is_active"],
        }
        for s in products_read.product_suppliers(conn, product_id)
    ]
    return {**product_item(row), "inventory": products_read.product_inventory(conn, product_id), "suppliers": suppliers}


@router.get("/{product_id}/history", response_model=History, responses=errors(400, 401, 403, 404, 422),
            summary="Historia de consumo con estadísticos poblacionales (ANALYST, PLANNER, ADMIN)")
def product_history(
    product_id: int = Path(..., ge=1),
    date_from: _dt.date | None = Query(None, description="Inclusivo; por defecto, primer día con consumo"),
    date_to: _dt.date | None = Query(None, description="Inclusivo; por defecto, último día con consumo"),
    granularity: Literal["daily", "weekly", "monthly"] = Query(DEFAULT_GRANULARITY),
    _identity=Depends(require_roles(HISTORY_ROLES)),
    conn: psycopg.Connection = Depends(connection),
) -> dict:
    require_product(conn, product_id)
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ApiError(400, "INVALID_DATE_RANGE", "date_from no puede ser posterior a date_to.")
    if date_from is None or date_to is None:
        first, last = consumption_read.bounds(conn, product_id)
        date_from = date_from if date_from is not None else first
        date_to = date_to if date_to is not None else last
    if date_from is None or date_to is None or date_from > date_to:
        result = {"periods": [], "statistics": statistics([])}  # no consumption in the requested range
    else:
        rows = [DayRow(r["day"], r["quantity"], r["stockout"])
                for r in consumption_read.daily(conn, product_id, date_from, date_to)]
        result = build_history(rows, date_from, date_to, granularity)
    return {"product_id": product_id, "granularity": granularity, "date_from": date_from, "date_to": date_to, **result}


@router.get("/{product_id}/forecast", response_model=ProductForecast, responses=errors(401, 403, 404, 422),
            summary="Serie primaria del producto (los cuatro roles)")
def product_forecast(
    product_id: int = Path(..., ge=1),
    run_id: int | None = Query(None, ge=1),
    _identity=Depends(require_roles(ALL_ROLES)),
    conn: psycopg.Connection = Depends(connection),
) -> dict:
    require_product(conn, product_id)
    run = resolve_run(conn, "FORECAST", run_id)
    series = series_from_rows(forecasts_read.product_series(conn, run["id"], product_id))
    if not series:
        raise ApiError(404, "FORECAST_NOT_FOUND", "El producto no tiene serie primaria en esa ejecución.",
                       {"product_id": product_id, "run_id": run["id"]})
    return {**series[0], "provenance": forecast_provenance(run)}


@router.get("/{product_id}/recommendation", response_model=RecommendationDetail, responses=errors(401, 403, 404, 422),
            summary="Evaluación del producto en la ejecución, con cualquier outcome (los cuatro roles)")
def product_recommendation(
    product_id: int = Path(..., ge=1),
    run_id: int | None = Query(None, ge=1),
    _identity=Depends(require_roles(ALL_ROLES)),
    conn: psycopg.Connection = Depends(connection),
) -> dict:
    require_product(conn, product_id)
    run = resolve_run(conn, "RECOMMENDATION", run_id)
    row = recommendations_read.product_recommendation(conn, run["id"], product_id)
    if row is None:
        raise ApiError(404, "RECOMMENDATION_NOT_FOUND", "No hay evaluación del producto en esa ejecución.",
                       {"product_id": product_id, "run_id": run["id"]})
    return {**detail_from_row(row), "provenance": recommendation_provenance(run)}
