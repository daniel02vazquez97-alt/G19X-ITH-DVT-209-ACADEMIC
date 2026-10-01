"""Column contract of the synthetic dataset 0.4.0, as the ingestion consumes it.

One entry per CSV file, in **load order** (foreign keys first, `docs/04` §9.5), with its columns in
the contract's name and order (`DT-024` for the five master files, `DT-034` for ``demand``,
`DT-038` for consumption, movements and inventory, `DT-039` for the purchase orders). The ingestion
reads the generator's *contract*, never its code (`docs/03` §16.4).

Column kinds:

* ``id`` / ``ref``      integer ≥ 1 (technical key / foreign key);
* ``int``               integer (any sign); ``int_nonneg`` integer ≥ 0;
* ``qty`` + domain      quantity, an integer in 0.4.0, stored as ``numeric`` (`DT-044`);
* ``money``             decimal with exactly two decimals;
* ``text``, ``bool``, ``date``, ``datetime`` (``YYYY-MM-DDTHH:MM:SSZ``, UTC);
* ``origin``            ``SYNTHETIC`` | ``REAL``;
* ``vocab``             closed vocabulary of the model (`docs/04` §3);
* ``stamped``           technical audit column the ingestion sets with the load instant; it must be
                        empty in the CSV (`DT-024`, `docs/04` §9.3).
"""

from __future__ import annotations

from dataclasses import dataclass

DATA_ORIGINS = ("SYNTHETIC", "REAL")
MOVEMENT_TYPES = ("RECEIPT", "ISSUE", "ADJUSTMENT", "RETURN", "TRANSFER_IN", "TRANSFER_OUT", "SCRAP")
ORDER_STATUSES = ("DRAFT", "ISSUED", "PARTIALLY_RECEIVED", "RECEIVED", "CANCELLED")

#: The eleven fields of ``manifest.json`` (`DT-025`).
MANIFEST_FIELDS = (
    "dataset_version",
    "generator_version",
    "seed",
    "generated_at",
    "time_range",
    "data_origin",
    "config",
    "components",
    "files",
    "scenario_assignment",
    "quality_report",
)


@dataclass(frozen=True)
class Column:
    name: str
    kind: str
    nullable: bool = False
    #: For ``qty``: ``"nonneg"`` (≥ 0), ``"pos"`` (> 0), ``"nonzero"`` (≠ 0) or ``"any"``.
    #: For ``vocab``: the allowed values.
    domain: object = None


def _c(name: str, kind: str, nullable: bool = False, domain: object = None) -> Column:
    return Column(name, kind, nullable, domain)


#: File name → columns, in load order.
FILES: dict[str, tuple[Column, ...]] = {
    "locations.csv": (
        _c("id", "id"),
        _c("code", "text"),
        _c("name", "text"),
        _c("type", "text"),
        _c("is_active", "bool"),
        _c("data_origin", "origin"),
    ),
    "categories.csv": (
        _c("id", "id"),
        _c("code", "text"),
        _c("name", "text"),
        _c("parent_id", "ref", nullable=True),
        _c("is_active", "bool"),
        _c("data_origin", "origin"),
    ),
    "suppliers.csv": (
        _c("id", "id"),
        _c("code", "text"),
        _c("name", "text"),
        _c("contact_info", "text", nullable=True),
        _c("is_active", "bool"),
        _c("currency", "text", nullable=True),
        _c("created_at", "stamped"),
        _c("updated_at", "stamped"),
        _c("data_origin", "origin"),
    ),
    "products.csv": (
        _c("id", "id"),
        _c("sku", "text"),
        _c("name", "text"),
        _c("description", "text", nullable=True),
        _c("category_id", "ref"),
        _c("unit_of_measure", "text"),
        _c("is_active", "bool"),
        _c("abc_class", "text", nullable=True),
        _c("rotation_class", "text", nullable=True),
        _c("shelf_life_days", "int_nonneg", nullable=True),
        _c("valid_from", "date"),
        _c("valid_to", "date", nullable=True),
        _c("created_at", "stamped"),
        _c("updated_at", "stamped"),
        _c("data_origin", "origin"),
    ),
    "product_suppliers.csv": (
        _c("id", "id"),
        _c("product_id", "ref"),
        _c("supplier_id", "ref"),
        _c("agreed_lead_time_days", "int"),
        _c("moq", "qty", domain="nonneg"),
        _c("order_multiple", "qty", domain="pos"),
        _c("unit_cost", "money"),
        _c("is_preferred", "bool"),
        _c("is_active", "bool"),
        _c("data_origin", "origin"),
    ),
    "purchase_orders.csv": (
        _c("id", "id"),
        _c("order_number", "text"),
        _c("supplier_id", "ref"),
        _c("location_id", "ref"),
        _c("status", "vocab", domain=ORDER_STATUSES),
        _c("issued_at", "datetime"),
        _c("expected_at", "datetime"),
        _c("closed_at", "datetime", nullable=True),
        _c("currency", "text", nullable=True),
        _c("total_amount", "money", nullable=True),
        _c("created_by", "text", nullable=True),
        _c("created_at", "stamped"),
        _c("updated_at", "stamped"),
        _c("data_origin", "origin"),
    ),
    "purchase_order_items.csv": (
        _c("id", "id"),
        _c("purchase_order_id", "ref"),
        _c("product_id", "ref"),
        _c("quantity_ordered", "qty", domain="pos"),
        _c("quantity_received", "qty", domain="nonneg"),
        _c("unit_cost", "money"),
        _c("expected_at", "datetime", nullable=True),
        _c("data_origin", "origin"),
    ),
    "purchase_order_receipts.csv": (
        _c("id", "id"),
        _c("purchase_order_item_id", "ref"),
        _c("received_at", "datetime"),
        _c("quantity_received", "qty", domain="pos"),
        _c("quality_rejected", "qty", nullable=True, domain="nonneg"),
        _c("data_origin", "origin"),
    ),
    "demand.csv": (
        _c("id", "id"),
        _c("product_id", "ref"),
        _c("location_id", "ref"),
        _c("occurred_on", "date"),
        _c("quantity", "qty", domain="nonneg"),
        _c("data_origin", "origin"),
    ),
    "consumption.csv": (
        _c("id", "id"),
        _c("product_id", "ref"),
        _c("location_id", "ref"),
        _c("occurred_on", "date"),
        _c("quantity", "qty", domain="nonneg"),
        _c("channel", "text", nullable=True),
        _c("is_stockout_affected", "bool"),
        _c("data_origin", "origin"),
    ),
    "inventory_movements.csv": (
        _c("id", "id"),
        _c("product_id", "ref"),
        _c("location_id", "ref"),
        _c("movement_type", "vocab", domain=MOVEMENT_TYPES),
        _c("quantity", "qty", domain="nonzero"),
        _c("occurred_at", "datetime"),
        _c("recorded_at", "datetime"),
        _c("reference_type", "text"),
        _c("reference_id", "ref", nullable=True),
        _c("reason_code", "text", nullable=True),
        _c("data_origin", "origin"),
        _c("created_by", "text", nullable=True),
    ),
    "inventory.csv": (
        _c("id", "id"),
        _c("product_id", "ref"),
        _c("location_id", "ref"),
        _c("quantity_on_hand", "qty", domain="nonneg"),
        _c("quantity_reserved", "qty", domain="any"),
        _c("quantity_in_transit", "qty", domain="nonneg"),
        _c("last_movement_at", "datetime", nullable=True),
        _c("updated_at", "stamped"),
        _c("data_origin", "origin"),
    ),
}


def table_name(file_name: str) -> str:
    """The table of a file: its name without ``.csv`` (`docs/04` §9.1)."""
    return file_name[: -len(".csv")]


def header(file_name: str) -> list[str]:
    """The exact header the contract requires."""
    return [column.name for column in FILES[file_name]]
