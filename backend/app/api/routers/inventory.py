"""Inventory routes (`docs/07` §7.2 and §7.4)."""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, Path, Query

from app.db.read import inventory as inventory_read

from ..auth import ALL_ROLES, require_roles
from ..errors import ApiError
from ..pagination import PageParams, page_params, parse_sort
from ..schemas import InventoryDetail, InventoryPage
from . import connection, errors

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])

_SORT_FIELDS = tuple(inventory_read.SORT_COLUMNS)
_ITEM_FIELDS = ("product_id", "sku", "on_hand", "reserved", "available", "in_transit_total",
                "inventory_position_accounting", "last_movement_at", "data_origin")


def inventory_item(row: dict) -> dict:
    return {field: row[field] for field in _ITEM_FIELDS}


@router.get("", response_model=InventoryPage, responses=errors(400, 401, 403, 422),
            summary="Posición de inventario del catálogo (los cuatro roles)")
def list_inventory(
    product_id: int | None = Query(None, ge=1),
    category_id: int | None = Query(None),
    sort: str | None = Query(None, description="sku | on_hand | available, con - para descendente; por defecto sku"),
    page: PageParams = Depends(page_params),
    _identity=Depends(require_roles(ALL_ROLES)),
    conn: psycopg.Connection = Depends(connection),
) -> dict:
    order = parse_sort(sort, _SORT_FIELDS, "sku")
    total, rows = inventory_read.list_inventory(
        conn, product_id=product_id, category_id=category_id, sort=order.field, descending=order.descending,
        limit=page.page_size, offset=page.offset,
    )
    return {"items": [inventory_item(r) for r in rows], "total": total, "page": page.page, "page_size": page.page_size}


@router.get("/{product_id}", response_model=InventoryDetail, responses=errors(401, 403, 404, 422),
            summary="Inventario del producto con sus líneas abiertas (los cuatro roles)")
def get_inventory(
    product_id: int = Path(..., ge=1),
    _identity=Depends(require_roles(ALL_ROLES)),
    conn: psycopg.Connection = Depends(connection),
) -> dict:
    row = inventory_read.get_inventory(conn, product_id)
    if row is None:
        raise ApiError(404, "PRODUCT_NOT_FOUND", "No existe inventario para el producto indicado.",
                       {"product_id": product_id})
    lines = [
        {
            "order_number": line["order_number"],
            "supplier": {"id": line["supplier_id"], "code": line["supplier_code"], "name": line["supplier_name"]},
            "status": line["status"],
            "expected_on": line["expected_on"],
            "quantity_pending": line["quantity_pending"],
        }
        for line in inventory_read.open_lines(conn, product_id, row["location_id"])
    ]
    return {**inventory_item(row), "open_lines": lines}
