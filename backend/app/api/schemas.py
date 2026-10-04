"""Response schemas (Pydantic v2) of the API V1 (`docs/07` §7.2 and §7.4).

Quantities are `Decimal`, serialized as JSON strings: never ``float`` (`DT-066`). Request parameters are
declared on the endpoints with ``Query``/``Path``; there are no request bodies (read-only API).
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    model_config = ConfigDict(frozen=True)


# --- errors -----------------------------------------------------------------------------------


class ErrorBody(Schema):
    code: str
    message: str
    details: dict[str, Any] | list[Any]
    correlation_id: str | None


class ErrorResponse(Schema):
    error: ErrorBody


# --- health and identity ----------------------------------------------------------------------


class Health(Schema):
    status: Literal["ok"]
    version: str


class Me(Schema):
    subject_id: str
    roles: list[str]


# --- references -------------------------------------------------------------------------------


class CategoryRef(Schema):
    id: int
    code: str
    name: str


class SupplierRef(Schema):
    id: int
    code: str
    name: str


class ProductRef(Schema):
    id: int
    sku: str


class ProductNamedRef(Schema):
    id: int
    sku: str
    name: str


class ModelRef(Schema):
    name: str
    version: str


# --- products and inventory -------------------------------------------------------------------


class Product(Schema):
    id: int
    sku: str
    name: str
    category: CategoryRef
    unit_of_measure: str
    is_active: bool
    valid_from: _dt.date
    valid_to: _dt.date | None
    data_origin: str


class ProductPage(Schema):
    items: list[Product]
    total: int
    page: int
    page_size: int


class ProductInventory(Schema):
    on_hand: Decimal
    reserved: Decimal
    in_transit_total: Decimal
    last_movement_at: _dt.datetime | None


class ProductSupplier(Schema):
    supplier: SupplierRef
    moq: Decimal
    order_multiple: Decimal
    unit_cost: Decimal
    agreed_lead_time_days: int
    is_preferred: bool
    is_active: bool


class ProductDetail(Product):
    inventory: ProductInventory | None
    suppliers: list[ProductSupplier]


class InventoryItem(Schema):
    product_id: int
    sku: str
    on_hand: Decimal
    reserved: Decimal
    available: Decimal
    in_transit_total: Decimal
    inventory_position_accounting: Decimal
    last_movement_at: _dt.datetime | None
    data_origin: str


class InventoryPage(Schema):
    items: list[InventoryItem]
    total: int
    page: int
    page_size: int


class OpenLine(Schema):
    order_number: str
    supplier: SupplierRef
    status: str
    expected_on: _dt.date
    quantity_pending: Decimal


class InventoryDetail(InventoryItem):
    open_lines: list[OpenLine]


# --- history (DT-067) --------------------------------------------------------------------------


class HistoryPeriod(Schema):
    period_start: _dt.date
    period_end: _dt.date
    days: int
    days_observed: int
    quantity: Decimal
    stockout_days: int
    complete: bool


class HistoryStatistics(Schema):
    periods_used: int
    mean: Decimal | None
    std_dev: Decimal | None
    cv: Decimal | None
    zero_periods: int | None


class History(Schema):
    product_id: int
    granularity: Literal["daily", "weekly", "monthly"]
    date_from: _dt.date | None
    date_to: _dt.date | None
    periods: list[HistoryPeriod]
    statistics: HistoryStatistics


# --- provenance (DT-066) -----------------------------------------------------------------------


class _Provenance(Schema):
    data_origin: str | None
    dataset_version: str
    generator_version: str | None
    data_load_id: int
    as_of_date: _dt.date
    run_id: int
    notices: list[Literal["SYNTHETIC_DATA", "V1_PROVISIONAL_POLICY"]]


class ForecastProvenance(_Provenance):
    model_version: ModelRef | None


class RecommendationProvenance(_Provenance):
    engine_version: str | None
    policy_set: str | None
    forecast_run_id: int | None


# --- forecasts ---------------------------------------------------------------------------------


class ForecastPeriod(Schema):
    period_start: _dt.date
    period_end: _dt.date
    predicted_quantity: Decimal
    lower_bound: Decimal
    upper_bound: Decimal
    confidence_level: Decimal
    method_used: str
    confidence_flag: str


class ForecastSeries(Schema):
    product: ProductRef
    model_version: ModelRef
    periods: list[ForecastPeriod]


class ForecastPage(Schema):
    items: list[ForecastSeries]
    total: int
    page: int
    page_size: int
    provenance: ForecastProvenance


class ProductForecast(ForecastSeries):
    provenance: ForecastProvenance


# --- recommendations ---------------------------------------------------------------------------

Outcome = Literal["RECOMMEND", "NO_NEED", "NOT_CALCULABLE"]


class RecommendationItem(Schema):
    id: int
    product: ProductNamedRef
    supplier: SupplierRef | None
    recommended_quantity: Decimal | None
    raw_quantity: Decimal | None
    suggested_order_date: _dt.date | None
    outcome: Outcome
    flags: list[str]


class RecommendationPage(Schema):
    items: list[RecommendationItem]
    total: int
    page: int
    page_size: int
    provenance: RecommendationProvenance


class RecommendationDetail(Schema):
    id: int
    run_id: int
    product: ProductNamedRef
    supplier: SupplierRef | None
    as_of_date: _dt.date
    outcome: Outcome
    reasons: list[str]
    flags: list[str]
    missing_policy_parameters: list[str]
    forecast_id: int | None
    suggested_order_date: _dt.date | None
    recommended_quantity: Decimal | None
    raw_quantity: Decimal | None
    reorder_point: Decimal | None
    safety_stock: Decimal | None
    lead_time_used_days: int | None
    demand_during_lead_time: Decimal | None
    inventory_position_at_calc: Decimal | None
    policy_set: str
    policy_snapshot: dict[str, Any]
    calculation_inputs: dict[str, Any]
    engine_version: str
    generated_at: _dt.datetime
    provenance: RecommendationProvenance


# --- runs -----------------------------------------------------------------------------------------


class RunDataLoad(Schema):
    id: int
    dataset_version: str
    generator_version: str | None
    data_origin: str | None


class RunVersions(Schema):
    engine_version: str | None
    forecast_run_id: int | None
    reference_model_version: ModelRef | None
    config_sha256: str


class RunDetail(Schema):
    id: int
    run_type: Literal["FORECAST", "RECOMMENDATION"]
    status: Literal["COMPLETED", "FAILED"]
    as_of_date: _dt.date
    data_load: RunDataLoad
    versions: RunVersions
    counts: dict[str, Any]
    started_at: _dt.datetime
    finished_at: _dt.datetime
    error: dict[str, Any] | None
