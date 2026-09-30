"""Component 8 - Dataset Validator + quality report (`DT-042`).

Phase 1 - Data. Validates the dataset **as materialised in the workspace** - the twelve
CSV files and ``manifest.json`` that Components 2 to 7 wrote - and, only when every check
passes, adds ``quality_report`` to the manifest.

The facts C8 validates come from the files, never from objects C2-C7 kept in memory: the
boundary it guards is *internal state -> serialisation -> files -> coherence between
files*. It may reproduce a contractual criterion with a public, pure function of the
generator (``orders.cancelled_target``, ``scenarios.build_assignment``...), but it never
generates, selects, draws, repairs or rewrites anything.

Criteria tagged ``SYNTHETIC_COVERAGE_CRITERION`` (`DT-041`) exist only to show coverage of
the synthetic dataset. They are not business rules and close none of `BR-X03`, `DT-P11`,
`BR-P10` or `DT-011`.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Callable

from ..config.config import DatasetConfig, Scenario
from . import policies as pol
from . import scenarios as sc
from .catalog import (
    CATEGORY_COLUMNS,
    LOCATION_COLUMNS,
    PRODUCT_COLUMNS,
    PRODUCT_SUPPLIER_COLUMNS,
    SUPPLIER_COLUMNS,
)
from .demand import DEMAND_COLUMNS
from .inventory import CONSUMPTION_COLUMNS, INVENTORY_COLUMNS, MOVEMENT_COLUMNS
from .orders import (
    PURCHASE_ORDER_COLUMNS,
    PURCHASE_ORDER_ITEM_COLUMNS,
    PURCHASE_ORDER_RECEIPT_COLUMNS,
    cancelled_target,
    format_order_number,
    is_eligible_for_cancel,
    order_number_width,
    planned_close,
)
from .rng import (
    COMPONENT_CATALOG,
    COMPONENT_DEMAND,
    COMPONENT_INVENTORY,
    COMPONENT_ORDERS,
    COMPONENT_SCENARIOS,
    COMPONENT_SUPPLIER_BEHAVIOUR,
    COMPONENT_VALIDATOR,
    sub_seed,
)
from .supplier_behaviour import build_supplier_profiles
from .writer import (
    CATALOG_VERSION,
    DEMAND_VERSION,
    GENERATOR_VERSION,
    INVENTORY_VERSION,
    ORDERS_VERSION,
    SCENARIOS_VERSION,
    SUPPLIER_BEHAVIOUR_VERSION,
    VALIDATOR_VERSION,
    add_manifest_field,
    dataset_version,
    extend_manifest,
    write_manifest,
)

__all__ = [
    "QUALITY_REPORT_FIELD",
    "CHECKS",
    "KNOWN_LIMITATIONS",
    "ANOMALY_LIMITATION",
    "Check",
    "validate",
    "generate",
]

MANIFEST_FILE = "manifest.json"
QUALITY_REPORT_FIELD = "quality_report"

#: Findings detailed per check in the error message; the rest are counted (`DT-042` §7).
DETAIL_LIMIT = 20

_BOM = b"\xef\xbb\xbf"
_NULL_TOKENS = frozenset({"NULL", "null", "None", "NaN", "nan"})
_POSITIVE = re.compile(r"[1-9][0-9]*")
_NON_NEGATIVE = re.compile(r"0|[1-9][0-9]*")
_SIGNED = re.compile(r"-?(0|[1-9][0-9]*)")
_MONEY = re.compile(r"(0|[1-9][0-9]*)\.[0-9]{2}")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_DATETIME = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2}:[0-9]{2}:[0-9]{2})Z")
_MIDNIGHT = "00:00:00"

#: `DT-036` section 9: the clock of each movement type.
_MOVEMENT_TIME = {"ADJUSTMENT": "00:00:00", "RECEIPT": "06:00:00", "ISSUE": "18:00:00"}
#: `DT-038` section 5.2: reference type and reason of each movement type.
_MOVEMENT_REFERENCE = {
    "ADJUSTMENT": ("INITIAL_INVENTORY", "OPENING_BALANCE"),
    "RECEIPT": ("PURCHASE_ORDER_RECEIPT", ""),
    "ISSUE": ("CONSUMPTION", ""),
}
#: `DT-038` section 5.4: rank of each movement type in the row order.
_TYPE_RANK = {"ADJUSTMENT": 0, "RECEIPT": 1, "ISSUE": 2}
_ORDER_STATUSES = ("ISSUED", "PARTIALLY_RECEIVED", "RECEIVED", "CANCELLED")
_PENDING = frozenset({"ISSUED", "PARTIALLY_RECEIVED"})
_SHAPES = tuple(
    s.value
    for s in (
        Scenario.STABLE_DEMAND,
        Scenario.GROWING_DEMAND,
        Scenario.DECLINING_DEMAND,
        Scenario.SEASONAL_DEMAND,
        Scenario.INTERMITTENT_DEMAND,
        Scenario.ERRATIC_DEMAND,
    )
)
_SUPPLIER_UNIT = "supplier"

# ---------------------------------------------------------------------------------------
# The contract of every file - DT-024, DT-034, DT-038, DT-039
# ---------------------------------------------------------------------------------------

#: Column kinds: ``id`` positive integer; ``int`` signed; ``nat`` >= 0; ``pos`` > 0;
#: ``date``; ``datetime``; ``bool``; ``money`` (two decimals); ``text`` non-empty;
#: ``empty`` always empty. A trailing ``?`` makes the column nullable (empty field).
_SCHEMAS: dict[str, dict[str, str]] = {
    "categories.csv": {
        "id": "id",
        "code": "text",
        "name": "text",
        "parent_id": "empty",
        "is_active": "bool",
        "data_origin": "text",
    },
    "products.csv": {
        "id": "id",
        "sku": "text",
        "name": "text",
        "description": "empty",
        "category_id": "id",
        "unit_of_measure": "text",
        "is_active": "bool",
        "abc_class": "empty",
        "rotation_class": "empty",
        "shelf_life_days": "empty",
        "valid_from": "date",
        "valid_to": "date?",
        "created_at": "empty",
        "updated_at": "empty",
        "data_origin": "text",
    },
    "suppliers.csv": {
        "id": "id",
        "code": "text",
        "name": "text",
        "contact_info": "empty",
        "is_active": "bool",
        "currency": "empty",
        "created_at": "empty",
        "updated_at": "empty",
        "data_origin": "text",
    },
    "product_suppliers.csv": {
        "id": "id",
        "product_id": "id",
        "supplier_id": "id",
        "agreed_lead_time_days": "int",
        "moq": "nat",
        "order_multiple": "int",
        "unit_cost": "money",
        "is_preferred": "bool",
        "is_active": "bool",
        "data_origin": "text",
    },
    "locations.csv": {
        "id": "id",
        "code": "text",
        "name": "text",
        "type": "text",
        "is_active": "bool",
        "data_origin": "text",
    },
    "demand.csv": {
        "id": "id",
        "product_id": "id",
        "location_id": "id",
        "occurred_on": "date",
        "quantity": "nat",
        "data_origin": "text",
    },
    "consumption.csv": {
        "id": "id",
        "product_id": "id",
        "location_id": "id",
        "occurred_on": "date",
        "quantity": "nat",
        "channel": "empty",
        "is_stockout_affected": "bool",
        "data_origin": "text",
    },
    "inventory_movements.csv": {
        "id": "id",
        "product_id": "id",
        "location_id": "id",
        "movement_type": "text",
        "quantity": "int",
        "occurred_at": "datetime",
        "recorded_at": "datetime",
        "reference_type": "text",
        "reference_id": "id?",
        "reason_code": "text?",
        "data_origin": "text",
        "created_by": "empty",
    },
    "inventory.csv": {
        "id": "id",
        "product_id": "id",
        "location_id": "id",
        "quantity_on_hand": "nat",
        "quantity_reserved": "int",
        "quantity_in_transit": "nat",
        "last_movement_at": "datetime?",
        "updated_at": "empty",
        "data_origin": "text",
    },
    "purchase_orders.csv": {
        "id": "id",
        "order_number": "text",
        "supplier_id": "id",
        "location_id": "id",
        "status": "text",
        "issued_at": "datetime",
        "expected_at": "datetime",
        "closed_at": "datetime?",
        "currency": "empty",
        "total_amount": "empty",
        "created_by": "empty",
        "created_at": "empty",
        "updated_at": "empty",
        "data_origin": "text",
    },
    "purchase_order_items.csv": {
        "id": "id",
        "purchase_order_id": "id",
        "product_id": "id",
        "quantity_ordered": "int",
        "quantity_received": "nat",
        "unit_cost": "money",
        "expected_at": "empty",
        "data_origin": "text",
    },
    "purchase_order_receipts.csv": {
        "id": "id",
        "purchase_order_item_id": "id",
        "received_at": "datetime",
        "quantity_received": "int",
        "quality_rejected": "empty",
        "data_origin": "text",
    },
}

#: The twelve files, their column contract and the entity the manifest names.
CONTRACT: dict[str, tuple[tuple[str, ...], str]] = {
    "categories.csv": (CATEGORY_COLUMNS, "Category"),
    "consumption.csv": (CONSUMPTION_COLUMNS, "Consumption"),
    "demand.csv": (DEMAND_COLUMNS, "Demand"),
    "inventory.csv": (INVENTORY_COLUMNS, "Inventory"),
    "inventory_movements.csv": (MOVEMENT_COLUMNS, "InventoryMovement"),
    "locations.csv": (LOCATION_COLUMNS, "Location"),
    "product_suppliers.csv": (PRODUCT_SUPPLIER_COLUMNS, "ProductSupplier"),
    "products.csv": (PRODUCT_COLUMNS, "Product"),
    "purchase_order_items.csv": (PURCHASE_ORDER_ITEM_COLUMNS, "PurchaseOrderItem"),
    "purchase_order_receipts.csv": (
        PURCHASE_ORDER_RECEIPT_COLUMNS,
        "PurchaseOrderReceipt",
    ),
    "purchase_orders.csv": (PURCHASE_ORDER_COLUMNS, "PurchaseOrder"),
    "suppliers.csv": (SUPPLIER_COLUMNS, "Supplier"),
}

#: The components a workspace holds when C8 runs: C2-C7 (`DT-042` §8).
PRIOR_COMPONENTS: dict[str, str] = {
    COMPONENT_CATALOG: CATALOG_VERSION,
    COMPONENT_DEMAND: DEMAND_VERSION,
    COMPONENT_INVENTORY: INVENTORY_VERSION,
    COMPONENT_ORDERS: ORDERS_VERSION,
    COMPONENT_SCENARIOS: SCENARIOS_VERSION,
    COMPONENT_SUPPLIER_BEHAVIOUR: SUPPLIER_BEHAVIOUR_VERSION,
}

#: `DT-025`: the nine mandatory fields, in the order ``build_manifest`` writes them.
MANDATORY_FIELDS = (
    "dataset_version",
    "generator_version",
    "seed",
    "generated_at",
    "time_range",
    "data_origin",
    "config",
    "components",
    "files",
)

#: The limitation `DT-042` section 6 requires, word for word.
ANOMALY_LIMITATION = (
    "No existe actualmente un criterio contractual de anomalía para este generador; una "
    "lista vacía no implica que el dataset haya sido revisado bajo una taxonomía de "
    "anomalías inexistente."
)

#: Item 20 of section 35: the limitations the documents already declare.
KNOWN_LIMITATIONS: tuple[dict[str, str], ...] = (
    {"id": "L-01", "text": ANOMALY_LIMITATION, "source": "DT-042 §6"},
    {
        "id": "L-02",
        "text": "Datos sintéticos: ningún resultado de este informe es una métrica real "
        "del negocio.",
        "source": "spec §35; DT-004",
    },
    {
        "id": "L-03",
        "text": "Los criterios SYNTHETIC_COVERAGE_CRITERION demuestran cobertura y no son "
        "reglas de negocio; BR-X03, DT-P11, BR-P10 y DT-011 siguen pendientes.",
        "source": "DT-041 §7; DT-023",
    },
    {
        "id": "L-04",
        "text": "No se generan entregas anticipadas: el lead time observado nunca es "
        "menor que el acordado.",
        "source": "DT-037 §5 O-1",
    },
    {
        "id": "L-05",
        "text": "El lead time observado no alcanza el techo de V1-09.2, de modo que "
        "LEAD_TIME_CAPPED no se ejercita.",
        "source": "DT-037 §5 O-2",
    },
    {
        "id": "L-06",
        "text": "Durante los primeros W días de cada producto la ventana de demanda "
        "reciente depende de demanda posterior (warm-up sintético).",
        "source": "DT-036 §5",
    },
    {
        "id": "L-07",
        "text": "Los productos cuyo mínimo pedible supera su necesidad mantienen "
        "sobreinventario permanente, y los productos sin proveedor activo terminan sin "
        "existencias.",
        "source": "DT-036 §4, §6",
    },
    {
        "id": "L-08",
        "text": "No se emiten órdenes DRAFT ni movimientos RETURN, TRANSFER_IN, "
        "TRANSFER_OUT o SCRAP; recorded_at es siempre igual a occurred_at.",
        "source": "DT-039 §5.3; DT-038 §5.1; DT-036 §9",
    },
    {
        "id": "L-09",
        "text": "Sin caso en el dataset: producto con proveedores y ninguno preferente, y "
        "diferencia por abc_class (vacía en todas las filas).",
        "source": "DT-031 casos 9 y 11",
    },
)


# ---------------------------------------------------------------------------------------
# The workspace as C8 reads it
# ---------------------------------------------------------------------------------------


class _Unreadable(Exception):
    """A file or value a check needs cannot be read; the check fails with the reason."""


def _day(value: str) -> _dt.date:
    if not _DATE.fullmatch(value):
        raise _Unreadable(f"{value!r} is not a date")
    return _dt.date.fromisoformat(value)


def _moment(value: str) -> tuple[_dt.date, str]:
    match = _DATETIME.fullmatch(value)
    if not match:
        raise _Unreadable(f"{value!r} is not a UTC date-time")
    return _dt.date.fromisoformat(match.group(1)), match.group(2)


class _Workspace:
    """The files of one workspace, read once; typed views are built on demand."""

    def __init__(self, config: DatasetConfig, root: Path) -> None:
        self.config = config
        self.root = root
        self.start = config.period.start_date
        self.end = config.period.end_date
        self.manifest: dict[str, Any] | None = None
        path = root / MANIFEST_FILE
        if path.is_file():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                self.manifest = loaded if isinstance(loaded, dict) else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                self.manifest = None
        self.raw: dict[str, bytes | None] = {}
        self.records: dict[str, list[list[str]] | None] = {}
        for name in CONTRACT:
            file_path = root / name
            data = file_path.read_bytes() if file_path.is_file() else None
            self.raw[name] = data
            records = None
            if data is not None:
                try:
                    text = data.decode("utf-8")
                    records = list(csv.reader(io.StringIO(text, newline="")))
                except (UnicodeDecodeError, csv.Error):
                    records = None
            self.records[name] = records

    # --- raw rows --------------------------------------------------------------------

    def rows(self, name: str) -> list[dict[str, str]]:
        """Every well-formed row of ``name`` as ``{column: value}``, by the file's header."""
        records = self.records.get(name)
        if not records:
            raise _Unreadable(f"{name} is missing or unreadable")
        header = records[0]
        return [dict(zip(header, r)) for r in records[1:] if len(r) == len(header)]

    # --- typed views -----------------------------------------------------------------

    @cached_property
    def products(self) -> dict[int, dict[str, Any]]:
        found = {}
        for r in self.rows("products.csv"):
            found[int(r["id"])] = {
                "category": int(r["category_id"]),
                "active": r["is_active"] == "true",
                "valid_from": _day(r["valid_from"]),
                "valid_to": _day(r["valid_to"]) if r["valid_to"] else None,
                "unit": r["unit_of_measure"],
            }
        return found

    @cached_property
    def relations(self) -> dict[tuple[int, int], dict[str, Any]]:
        return {
            (int(r["product_id"]), int(r["supplier_id"])): {
                "id": int(r["id"]),
                "lead": int(r["agreed_lead_time_days"]),
                "moq": int(r["moq"]),
                "multiple": int(r["order_multiple"]),
                "cost": r["unit_cost"],
                "preferred": r["is_preferred"] == "true",
                "active": r["is_active"] == "true",
            }
            for r in self.rows("product_suppliers.csv")
        }

    @cached_property
    def preferred(self) -> dict[int, list[int]]:
        found: dict[int, list[int]] = defaultdict(list)
        for (product, supplier), rel in sorted(self.relations.items()):
            if rel["preferred"] and rel["active"]:
                found[product].append(supplier)
        return found

    @cached_property
    def orders(self) -> dict[int, dict[str, Any]]:
        found = {}
        for r in self.rows("purchase_orders.csv"):
            issued, issued_time = _moment(r["issued_at"])
            expected, expected_time = _moment(r["expected_at"])
            closed = _moment(r["closed_at"]) if r["closed_at"] else None
            found[int(r["id"])] = {
                "number": r["order_number"],
                "supplier": int(r["supplier_id"]),
                "location": int(r["location_id"]),
                "status": r["status"],
                "issued": issued,
                "issued_time": issued_time,
                "expected": expected,
                "expected_time": expected_time,
                "closed": closed[0] if closed else None,
                "closed_time": closed[1] if closed else None,
            }
        return found

    @cached_property
    def items(self) -> dict[int, dict[str, Any]]:
        return {
            int(r["id"]): {
                "order": int(r["purchase_order_id"]),
                "product": int(r["product_id"]),
                "ordered": int(r["quantity_ordered"]),
                "received": int(r["quantity_received"]),
                "cost": r["unit_cost"],
            }
            for r in self.rows("purchase_order_items.csv")
        }

    @cached_property
    def lines_of(self) -> dict[int, list[int]]:
        found: dict[int, list[int]] = defaultdict(list)
        for item_id, item in sorted(self.items.items()):
            found[item["order"]].append(item_id)
        return found

    @cached_property
    def receipts(self) -> dict[int, dict[str, Any]]:
        found = {}
        for r in self.rows("purchase_order_receipts.csv"):
            day, time = _moment(r["received_at"])
            found[int(r["id"])] = {
                "item": int(r["purchase_order_item_id"]),
                "day": day,
                "time": time,
                "quantity": int(r["quantity_received"]),
            }
        return found

    @cached_property
    def receipts_of(self) -> dict[int, list[int]]:
        found: dict[int, list[int]] = defaultdict(list)
        for receipt_id, receipt in sorted(
            self.receipts.items(), key=lambda kv: (kv[1]["day"], kv[0])
        ):
            found[receipt["item"]].append(receipt_id)
        return found

    @cached_property
    def movements(self) -> list[dict[str, Any]]:
        found = []
        for r in self.rows("inventory_movements.csv"):
            day, time = _moment(r["occurred_at"])
            found.append(
                {
                    "id": int(r["id"]),
                    "pair": (int(r["product_id"]), int(r["location_id"])),
                    "type": r["movement_type"],
                    "quantity": int(r["quantity"]),
                    "occurred_at": r["occurred_at"],
                    "day": day,
                    "time": time,
                    "recorded_at": r["recorded_at"],
                    "reference_type": r["reference_type"],
                    "reference": int(r["reference_id"]) if r["reference_id"] else None,
                    "reason": r["reason_code"],
                }
            )
        return found

    @cached_property
    def demand(self) -> dict[tuple[int, int, _dt.date], int]:
        return {
            (int(r["product_id"]), int(r["location_id"]), _day(r["occurred_on"])): int(
                r["quantity"]
            )
            for r in self.rows("demand.csv")
        }

    @cached_property
    def consumption(self) -> dict[tuple[int, int, _dt.date], dict[str, Any]]:
        return {
            (int(r["product_id"]), int(r["location_id"]), _day(r["occurred_on"])): {
                "id": int(r["id"]),
                "quantity": int(r["quantity"]),
                "flag": r["is_stockout_affected"] == "true",
            }
            for r in self.rows("consumption.csv")
        }

    @cached_property
    def close(self) -> dict[tuple[int, int], list[int]]:
        """Stock at the close of every day of the period, per pair (`DT-038` §5.1)."""
        days = (self.end - self.start).days
        net: dict[tuple[int, int], Counter] = defaultdict(Counter)
        for m in self.movements:
            net[m["pair"]][(m["day"] - self.start).days] += m["quantity"]
        found = {}
        for pair, by_day in net.items():
            balance, closes = 0, []
            for offset in range(days):
                balance += by_day.get(offset, 0)
                closes.append(balance)
            found[pair] = closes
        return found

    def close_on(self, pair: tuple[int, int], day: _dt.date) -> int:
        offset = (day - self.start).days
        closes = self.close.get(pair)
        if closes is None:
            return 0
        if not 0 <= offset < len(closes):
            raise _Unreadable(f"{day} is outside the period")
        return closes[offset]

    @cached_property
    def causal(self) -> dict[int, dict[str, Any]]:
        return {i: o for i, o in self.orders.items() if o["status"] != "CANCELLED"}

    @cached_property
    def cancelled(self) -> dict[int, dict[str, Any]]:
        return {i: o for i, o in self.orders.items() if o["status"] == "CANCELLED"}

    def line(self, order_id: int) -> dict[str, Any]:
        lines = self.lines_of.get(order_id, [])
        if len(lines) != 1:
            raise _Unreadable(f"order {order_id} does not have exactly one line")
        return self.items[lines[0]]

    @cached_property
    def assignment(self) -> dict[str, Any]:
        value = (self.manifest or {}).get(sc.SCENARIO_ASSIGNMENT_FIELD)
        if not isinstance(value, dict):
            raise _Unreadable("the manifest has no scenario_assignment object")
        return value

    @cached_property
    def emergent(self) -> sc.EmergentProperties:
        return sc.emergent_properties(sc.load_facts(self.config, self.root))


# ---------------------------------------------------------------------------------------
# The checks - DT-042 section 4
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Check:
    """One check of the catalogue: a stable id, its family and the contract it restates."""

    id: str
    family: str
    source: str
    run: Callable[[_Workspace], list[str]]


def _manifest(ws: _Workspace) -> dict[str, Any]:
    if ws.manifest is None:
        raise _Unreadable(f"{MANIFEST_FILE} is missing or is not a JSON object")
    return ws.manifest


def _man_fields(ws: _Workspace) -> list[str]:
    keys = list(_manifest(ws))
    expected = list(MANDATORY_FIELDS) + [sc.SCENARIO_ASSIGNMENT_FIELD]
    if keys != expected:
        return [f"manifest fields are {keys} (expected {expected})"]
    return []


def _man_identity(ws: _Workspace) -> list[str]:
    m, config = _manifest(ws), ws.config
    expected = {
        "generator_version": GENERATOR_VERSION,
        "seed": config.seed,
        "time_range": config.period.to_dict(),
        "data_origin": pol.DATA_ORIGIN,
        "config": config.to_dict(),
        "dataset_version": dataset_version(config, GENERATOR_VERSION),
    }
    found = [
        f"manifest {key} is {m.get(key)!r} (expected {value!r})"
        for key, value in expected.items()
        if m.get(key) != value
    ]
    if not (
        isinstance(m.get("generated_at"), str)
        and _DATETIME.fullmatch(m["generated_at"])
    ):
        found.append(
            f"manifest generated_at {m.get('generated_at')!r} is not a UTC date-time"
        )
    return found


def _man_components(ws: _Workspace) -> list[str]:
    expected = [
        {"name": name, "version": version, "sub_seed": sub_seed(ws.config.seed, name)}
        for name, version in sorted(PRIOR_COMPONENTS.items())
    ]
    observed = _manifest(ws).get("components")
    if observed != expected:
        return [f"manifest components are {observed!r} (expected {expected!r})"]
    return []


def _man_files(ws: _Workspace) -> list[str]:
    found = []
    files = _manifest(ws).get("files")
    if not isinstance(files, list):
        return ["manifest files is not a list"]
    names = [f.get("name") for f in files if isinstance(f, dict)]
    if names != sorted(CONTRACT):
        found.append(f"manifest files are {names} (expected {sorted(CONTRACT)})")
    for entry in files:
        if not isinstance(entry, dict) or entry.get("name") not in CONTRACT:
            continue
        name = entry["name"]
        if set(entry) != {"name", "entity", "rows", "sha256"}:
            found.append(f"{name}: manifest entry fields are {sorted(entry)}")
        if entry.get("entity") != CONTRACT[name][1]:
            found.append(
                f"{name}: entity {entry.get('entity')!r} (expected {CONTRACT[name][1]!r})"
            )
        data = ws.raw.get(name)
        if data is None:
            found.append(f"{name}: listed in the manifest but missing")
            continue
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry.get("sha256"):
            found.append(f"{name}: sha256 {digest} (manifest {entry.get('sha256')})")
        records = ws.records.get(name)
        rows = len(records) - 1 if records else None
        if rows != entry.get("rows"):
            found.append(f"{name}: {rows} rows (manifest {entry.get('rows')})")
    on_disk = sorted(p.name for p in ws.root.iterdir())
    expected = sorted(set(CONTRACT) | {MANIFEST_FILE})
    if on_disk != expected:
        found.append(f"the workspace holds {on_disk} (expected {expected})")
    directories = sorted(p.name for p in ws.root.iterdir() if not p.is_file())
    if directories:
        found.append(f"the workspace holds directories: {directories}")
    return found


def _fmt_encoding(ws: _Workspace) -> list[str]:
    found = []
    for name in CONTRACT:
        data = ws.raw.get(name)
        if data is None:
            found.append(f"{name}: missing")
            continue
        if data.startswith(_BOM):
            found.append(f"{name}: starts with a UTF-8 BOM")
        if b"\r" in data:
            found.append(f"{name}: contains CR characters (expected LF line endings)")
        if not data.endswith(b"\n"):
            found.append(f"{name}: does not end with a line feed")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            found.append(f"{name}: not valid UTF-8 ({exc.reason})")
    return found


def _fmt_header(ws: _Workspace) -> list[str]:
    found = []
    for name, (columns, _) in CONTRACT.items():
        records = ws.records.get(name)
        header = tuple(records[0]) if records else None
        if header != columns:
            found.append(f"{name}: header {header} (expected {columns})")
    return found


def _fmt_fields(ws: _Workspace) -> list[str]:
    found = []
    for name in CONTRACT:
        records = ws.records.get(name)
        if not records:
            found.append(f"{name}: missing or unreadable")
            continue
        width = len(records[0])
        for line, record in enumerate(records[1:], start=2):
            if len(record) != width:
                found.append(
                    f"{name}: line {line} has {len(record)} fields (expected {width})"
                )
    return found


def _valid(kind: str, value: str) -> bool:
    if kind.endswith("?"):
        return value == "" or _valid(kind[:-1], value)
    if kind == "empty":
        return value == ""
    if kind == "id" or kind == "pos":
        return bool(_POSITIVE.fullmatch(value))
    if kind == "nat":
        return bool(_NON_NEGATIVE.fullmatch(value))
    if kind == "int":
        return bool(_SIGNED.fullmatch(value))
    if kind == "money":
        return bool(_MONEY.fullmatch(value))
    if kind == "bool":
        return value in ("true", "false")
    if kind == "date":
        if not _DATE.fullmatch(value):
            return False
        try:
            _dt.date.fromisoformat(value)
        except ValueError:
            return False
        return True
    if kind == "datetime":
        match = _DATETIME.fullmatch(value)
        if not match:
            return False
        try:
            _dt.datetime.fromisoformat(f"{match.group(1)}T{match.group(2)}")
        except ValueError:
            return False
        return True
    if kind == "text":
        return value != "" and value not in _NULL_TOKENS
    raise ValueError(f"unknown column kind {kind!r}")


def _fmt_types(ws: _Workspace) -> list[str]:
    found = []
    for name, schema in _SCHEMAS.items():
        for number, row in enumerate(ws.rows(name), start=2):
            for column, kind in schema.items():
                value = row.get(column)
                if value is None:
                    continue  # a missing column is FMT-02's finding
                if value in _NULL_TOKENS or not _valid(kind, value):
                    found.append(
                        f"{name}: line {number}, {column} = {value!r} is not a valid {kind}"
                    )
    return found


def _org(ws: _Workspace) -> list[str]:
    found = []
    for name in CONTRACT:
        for number, row in enumerate(ws.rows(name), start=2):
            if row.get("data_origin") != pol.DATA_ORIGIN:
                found.append(
                    f"{name}: line {number}, data_origin = {row.get('data_origin')!r} "
                    f"(expected {pol.DATA_ORIGIN!r})"
                )
    return found


def _sequential(name: str, ids: list[int]) -> list[str]:
    expected = list(range(1, len(ids) + 1))
    if ids != expected:
        first = next(i for i, (a, b) in enumerate(zip(ids, expected)) if a != b)
        return [
            f"{name}: id {ids[first]} at row {first + 1} (expected {expected[first]})"
        ]
    return []


_SEQUENTIAL = (
    "categories.csv",
    "products.csv",
    "suppliers.csv",
    "product_suppliers.csv",
    "locations.csv",
    "demand.csv",
    "consumption.csv",
    "inventory_movements.csv",
    "inventory.csv",
    "purchase_orders.csv",
    "purchase_order_items.csv",
)


def _idn_ids(ws: _Workspace) -> list[str]:
    found = []
    for name in _SEQUENTIAL:
        found += _sequential(name, [int(r["id"]) for r in ws.rows(name)])
    for item_id, item in ws.items.items():
        if item_id != item["order"]:
            found.append(
                f"purchase_order_items.csv: id {item_id} belongs to order {item['order']} "
                "(DT-038 §8: a line carries the id of its order)"
            )
    rows = ws.rows("purchase_order_receipts.csv")
    ranked = sorted(
        rows, key=lambda r: (r["received_at"], int(r["purchase_order_item_id"]))
    )
    for position, r in enumerate(ranked, start=1):
        if int(r["id"]) != position:
            found.append(
                f"purchase_order_receipts.csv: receipt of item {r['purchase_order_item_id']} "
                f"on {r['received_at']} has id {r['id']} (expected {position}, "
                "numbered by (received_at, purchase_order_item_id))"
            )
    return found


def _business_keys(ws: _Workspace) -> dict[str, list[tuple]]:
    def ints(r: dict[str, str], *columns: str) -> tuple:
        return tuple(int(r[c]) for c in columns)

    return {
        "categories.csv": [(r["code"],) for r in ws.rows("categories.csv")],
        "products.csv": [(r["sku"],) for r in ws.rows("products.csv")],
        "suppliers.csv": [(r["code"],) for r in ws.rows("suppliers.csv")],
        "locations.csv": [(r["code"],) for r in ws.rows("locations.csv")],
        "product_suppliers.csv": [
            ints(r, "product_id", "supplier_id")
            for r in ws.rows("product_suppliers.csv")
        ],
        "demand.csv": [
            ints(r, "product_id", "location_id") + (r["occurred_on"],)
            for r in ws.rows("demand.csv")
        ],
        "consumption.csv": [
            ints(r, "product_id", "location_id") + (r["occurred_on"],)
            for r in ws.rows("consumption.csv")
        ],
        "inventory.csv": [
            ints(r, "product_id", "location_id") for r in ws.rows("inventory.csv")
        ],
        "inventory_movements.csv": [
            ints(r, "product_id", "location_id")
            + (
                r["occurred_at"],
                _TYPE_RANK.get(r["movement_type"], 9),
                int(r["reference_id"] or 0),
            )
            for r in ws.rows("inventory_movements.csv")
        ],
        "purchase_orders.csv": [
            (r["order_number"],) for r in ws.rows("purchase_orders.csv")
        ],
        "purchase_order_items.csv": [
            ints(r, "purchase_order_id", "product_id")
            for r in ws.rows("purchase_order_items.csv")
        ],
        "purchase_order_receipts.csv": [
            (int(r["purchase_order_item_id"]), r["received_at"])
            for r in ws.rows("purchase_order_receipts.csv")
        ],
    }


def _idn_keys(ws: _Workspace) -> list[str]:
    found = []
    for name, keys in _business_keys(ws).items():
        for position in range(1, len(keys)):
            if not keys[position - 1] < keys[position]:
                found.append(
                    f"{name}: row {position + 1} key {keys[position]} does not follow "
                    f"{keys[position - 1]} (business keys unique and ascending)"
                )
    return found


def _idn_preferred(ws: _Workspace) -> list[str]:
    return [
        f"product_suppliers.csv: product {p} has {len(s)} preferred active relations {s}"
        for p, s in sorted(ws.preferred.items())
        if len(s) > 1
    ]


def _ref_foreign_keys(ws: _Workspace) -> list[str]:
    ids = {
        name: {int(r["id"]) for r in ws.rows(name)}
        for name in (
            "categories.csv",
            "products.csv",
            "suppliers.csv",
            "locations.csv",
            "purchase_orders.csv",
            "purchase_order_items.csv",
            "purchase_order_receipts.csv",
        )
    }
    links = (
        ("products.csv", "category_id", "categories.csv"),
        ("product_suppliers.csv", "product_id", "products.csv"),
        ("product_suppliers.csv", "supplier_id", "suppliers.csv"),
        ("demand.csv", "product_id", "products.csv"),
        ("demand.csv", "location_id", "locations.csv"),
        ("consumption.csv", "product_id", "products.csv"),
        ("consumption.csv", "location_id", "locations.csv"),
        ("inventory_movements.csv", "product_id", "products.csv"),
        ("inventory_movements.csv", "location_id", "locations.csv"),
        ("inventory.csv", "product_id", "products.csv"),
        ("inventory.csv", "location_id", "locations.csv"),
        ("purchase_orders.csv", "supplier_id", "suppliers.csv"),
        ("purchase_orders.csv", "location_id", "locations.csv"),
        ("purchase_order_items.csv", "purchase_order_id", "purchase_orders.csv"),
        ("purchase_order_items.csv", "product_id", "products.csv"),
        (
            "purchase_order_receipts.csv",
            "purchase_order_item_id",
            "purchase_order_items.csv",
        ),
    )
    found = []
    for name, column, target in links:
        for r in ws.rows(name):
            if int(r[column]) not in ids[target]:
                found.append(
                    f"{name}: id {r['id']}, {column} = {r[column]} not in {target}"
                )
    return found


def _ref_lines(ws: _Workspace) -> list[str]:
    found = []
    for order_id in sorted(ws.orders):
        count = len(ws.lines_of.get(order_id, []))
        if count != 1:
            found.append(
                f"purchase_orders.csv: order {order_id} has {count} lines (expected 1)"
            )
    for item_id, receipts in sorted(ws.receipts_of.items()):
        if len(receipts) > 2:
            found.append(
                f"purchase_order_receipts.csv: line {item_id} has {len(receipts)} receipts "
                "(at most 2, DT-039 §8)"
            )
    return found


def _ref_preferred(ws: _Workspace) -> list[str]:
    found = []
    for order_id, order in sorted(ws.orders.items()):
        product = ws.line(order_id)["product"]
        suppliers = ws.preferred.get(product, [])
        if suppliers != [order["supplier"]]:
            found.append(
                f"purchase_orders.csv: order {order_id} of product {product} uses supplier "
                f"{order['supplier']} (preferred active: {suppliers})"
            )
    return found


def _ref_receipt_movements(ws: _Workspace) -> list[str]:
    found = []
    by_receipt: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for m in ws.movements:
        if m["type"] == "RECEIPT":
            by_receipt[m["reference"]].append(m)
    for ref in sorted(set(by_receipt) - set(ws.receipts), key=lambda x: (x is None, x)):
        found.append(
            f"inventory_movements.csv: RECEIPT references receipt {ref}, which does not exist"
        )
    for receipt_id, receipt in sorted(ws.receipts.items()):
        moves = by_receipt.get(receipt_id, [])
        if len(moves) != 1:
            found.append(
                f"purchase_order_receipts.csv: receipt {receipt_id} has {len(moves)} RECEIPT "
                "movements (expected 1)"
            )
            continue
        m = moves[0]
        item = ws.items[receipt["item"]]
        pair = (item["product"], ws.orders[item["order"]]["location"])
        observed = (m["pair"], m["day"], m["quantity"])
        expected = (pair, receipt["day"], receipt["quantity"])
        if observed != expected:
            found.append(
                f"inventory_movements.csv: movement {m['id']} for receipt {receipt_id} is "
                f"{observed} (expected {expected})"
            )
    return found


def _ref_issue_movements(ws: _Workspace) -> list[str]:
    found = []
    by_consumption: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for m in ws.movements:
        if m["type"] == "ISSUE":
            by_consumption[m["reference"]].append(m)
    known = {c["id"] for c in ws.consumption.values()}
    for ref in sorted(set(by_consumption) - known, key=lambda x: (x is None, x)):
        found.append(
            f"inventory_movements.csv: ISSUE references consumption {ref}, which does not exist"
        )
    for (product, location, day), c in sorted(ws.consumption.items()):
        moves = by_consumption.get(c["id"], [])
        expected_count = 1 if c["quantity"] > 0 else 0
        if len(moves) != expected_count:
            found.append(
                f"consumption.csv: consumption {c['id']} of {c['quantity']} units has "
                f"{len(moves)} ISSUE movements (expected {expected_count})"
            )
            continue
        for m in moves:
            observed = (m["pair"], m["day"], m["quantity"])
            expected = ((product, location), day, -c["quantity"])
            if observed != expected:
                found.append(
                    f"inventory_movements.csv: movement {m['id']} for consumption {c['id']} "
                    f"is {observed} (expected {expected})"
                )
    return found


def _first_days(ws: _Workspace) -> dict[tuple[int, int], _dt.date]:
    first: dict[tuple[int, int], _dt.date] = {}
    for product, location, day in ws.demand:
        pair = (product, location)
        if pair not in first or day < first[pair]:
            first[pair] = day
    return first


def _ref_opening(ws: _Workspace) -> list[str]:
    found = []
    first = _first_days(ws)
    seen: Counter = Counter()
    for m in ws.movements:
        if m["type"] != "ADJUSTMENT":
            continue
        seen[m["pair"]] += 1
        if m["day"] != first.get(m["pair"]):
            found.append(
                f"inventory_movements.csv: opening balance {m['id']} of {m['pair']} on "
                f"{m['day']} (expected the first day in force, {first.get(m['pair'])})"
            )
    for pair, count in sorted(seen.items()):
        if count > 1:
            found.append(
                f"inventory_movements.csv: {pair} has {count} opening balances"
            )
    return found


def _ref_inventory_pairs(ws: _Workspace) -> list[str]:
    products = sorted(int(r["id"]) for r in ws.rows("products.csv"))
    locations = sorted(int(r["id"]) for r in ws.rows("locations.csv"))
    expected = [(p, loc) for p in products for loc in locations]
    observed = [
        (int(r["product_id"]), int(r["location_id"])) for r in ws.rows("inventory.csv")
    ]
    if observed != expected:
        missing = sorted(set(expected) - set(observed))
        extra = sorted(set(observed) - set(expected))
        return [
            f"inventory.csv: one row per product x location expected; missing {missing[:10]}, "
            f"unexpected {extra[:10]}, {len(observed)} rows for {len(expected)} pairs"
        ]
    return []


def _com_relations(ws: _Workspace) -> list[str]:
    found = []
    for (product, supplier), rel in sorted(ws.relations.items()):
        key = f"product_suppliers.csv: ({product}, {supplier})"
        if rel["moq"] < 0:
            found.append(f"{key}: moq {rel['moq']} (expected >= 0)")
        if rel["multiple"] < 1:
            found.append(f"{key}: order_multiple {rel['multiple']} (expected >= 1)")
        if rel["lead"] < 1:
            found.append(f"{key}: agreed_lead_time_days {rel['lead']} (expected >= 1)")
    return found


def _relation_of(ws: _Workspace, order_id: int) -> dict[str, Any]:
    order, line = ws.orders[order_id], ws.line(order_id)
    rel = ws.relations.get((line["product"], order["supplier"]))
    if rel is None:
        raise _Unreadable(
            f"order {order_id}: no relation ({line['product']}, {order['supplier']})"
        )
    return rel


def _com_quantity(ws: _Workspace) -> list[str]:
    found = []
    for order_id in sorted(ws.orders):
        line, rel = ws.line(order_id), _relation_of(ws, order_id)
        q = line["ordered"]
        if q <= 0 or q < rel["moq"] or q % rel["multiple"]:
            found.append(
                f"purchase_order_items.csv: order {order_id} quantity_ordered {q} "
                f"(expected > 0, >= moq {rel['moq']}, multiple of {rel['multiple']})"
            )
    return found


def _com_cost(ws: _Workspace) -> list[str]:
    found = []
    for order_id in sorted(ws.orders):
        line, rel = ws.line(order_id), _relation_of(ws, order_id)
        if line["cost"] != rel["cost"]:
            found.append(
                f"purchase_order_items.csv: order {order_id} unit_cost {line['cost']} "
                f"(expected {rel['cost']}, its relation)"
            )
    return found


def _com_expected(ws: _Workspace) -> list[str]:
    found = []
    for order_id, order in sorted(ws.orders.items()):
        rel = _relation_of(ws, order_id)
        expected = order["issued"] + _dt.timedelta(days=rel["lead"])
        if order["expected"] != expected or order["expected_time"] != _MIDNIGHT:
            found.append(
                f"purchase_orders.csv: order {order_id} expected_at {order['expected']} "
                f"{order['expected_time']} (expected {expected} {_MIDNIGHT} = issued_at + "
                f"{rel['lead']} days)"
            )
    return found


def _rcp_receipts(ws: _Workspace) -> list[str]:
    found = []
    for receipt_id, r in sorted(ws.receipts.items()):
        order = ws.orders[ws.items[r["item"]]["order"]]
        if r["quantity"] <= 0:
            found.append(
                f"purchase_order_receipts.csv: receipt {receipt_id} quantity {r['quantity']}"
            )
        if not order["issued"] <= r["day"] < ws.end or r["time"] != _MIDNIGHT:
            found.append(
                f"purchase_order_receipts.csv: receipt {receipt_id} on {r['day']} {r['time']} "
                f"(expected {_MIDNIGHT}, between issue {order['issued']} and before {ws.end})"
            )
    return found


def _rcp_sums(ws: _Workspace) -> list[str]:
    found = []
    for item_id, item in sorted(ws.items.items()):
        total = sum(ws.receipts[r]["quantity"] for r in ws.receipts_of.get(item_id, []))
        if total != item["received"] or item["received"] > item["ordered"]:
            found.append(
                f"purchase_order_items.csv: line {item_id} quantity_received "
                f"{item['received']}, receipts {total}, ordered {item['ordered']} "
                "(expected receipts = received <= ordered, V1-12)"
            )
    return found


def _rcp_status(ws: _Workspace) -> list[str]:
    found = []
    for order_id, order in sorted(ws.causal.items()):
        line = ws.line(order_id)
        receipts = [
            ws.receipts[r] for r in ws.receipts_of.get(ws.lines_of[order_id][0], [])
        ]
        received = sum(r["quantity"] for r in receipts)
        if received == 0:
            expected = ("ISSUED", None)
        elif received < line["ordered"]:
            expected = ("PARTIALLY_RECEIVED", None)
        else:
            expected = ("RECEIVED", max(r["day"] for r in receipts))
        observed = (order["status"], order["closed"])
        if observed != expected or (
            order["closed"] and order["closed_time"] != _MIDNIGHT
        ):
            found.append(
                f"purchase_orders.csv: order {order_id} is {observed} with {received} of "
                f"{line['ordered']} received (expected {expected})"
            )
    return found


def _can_shape(ws: _Workspace) -> list[str]:
    found = []
    for order_id, order in sorted(ws.cancelled.items()):
        line = ws.line(order_id)
        closed = planned_close(order["issued"])
        receipts = ws.receipts_of.get(ws.lines_of[order_id][0], [])
        if (order["closed"], order["closed_time"]) != (closed, _MIDNIGHT):
            found.append(
                f"purchase_orders.csv: cancelled order {order_id} closed_at {order['closed']} "
                f"(expected {closed}, issued_at + {pol.ORDERS_CANCELLED_CLOSE_LAG_DAYS} day)"
            )
        if line["received"] != 0 or receipts:
            found.append(
                f"purchase_orders.csv: cancelled order {order_id} has {line['received']} "
                f"received and {len(receipts)} receipts (expected none)"
            )
    return found


def _order_key(ws: _Workspace, order_id: int) -> tuple:
    order = ws.orders[order_id]
    return (
        order["issued"],
        order["supplier"],
        ws.line(order_id)["product"],
        order["location"],
    )


def _eligible(ws: _Workspace, order_id: int) -> bool:
    product = ws.line(order_id)["product"]
    valid_to = ws.products[product]["valid_to"]
    return is_eligible_for_cancel(ws.orders[order_id]["issued"], valid_to, ws.end)


def _can_templates(ws: _Workspace) -> list[str]:
    found = []
    causal_by_key = {_order_key(ws, i): i for i in ws.causal}
    used: Counter = Counter()
    for order_id in sorted(ws.cancelled):
        template = causal_by_key.get(_order_key(ws, order_id))
        if template is None:
            found.append(
                f"purchase_orders.csv: cancelled order {order_id} has no causal template"
            )
            continue
        used[template] += 1
        twin, source = ws.orders[order_id], ws.orders[template]
        a, b = ws.line(order_id), ws.line(template)
        if (twin["expected"], a["ordered"], a["cost"]) != (
            source["expected"],
            b["ordered"],
            b["cost"],
        ):
            found.append(
                f"purchase_orders.csv: cancelled order {order_id} does not copy its template "
                f"{template} (expected_at, quantity_ordered, unit_cost)"
            )
        if not _eligible(ws, template):
            found.append(
                f"purchase_orders.csv: cancelled order {order_id} copies order {template}, "
                "which is not eligible (DT-039 §5.2 point 1)"
            )
    for template, count in sorted(used.items()):
        if count > 1:
            found.append(
                f"purchase_orders.csv: order {template} is the template of {count} twins"
            )
    return found


def _can_count(ws: _Workspace) -> list[str]:
    causal = len(ws.causal)
    eligible = sum(1 for i in ws.causal if _eligible(ws, i))
    expected = min(cancelled_target(causal), eligible)
    observed = len(ws.cancelled)
    if observed != expected or observed < 1:
        return [
            f"purchase_orders.csv: {observed} cancelled orders (expected min(K = "
            f"{cancelled_target(causal)}, {eligible} eligible) = {expected}, at least 1)"
        ]
    return []


def _can_numbering(ws: _Workspace) -> list[str]:
    found = []
    causal = sorted(ws.causal, key=lambda i: _order_key(ws, i))
    cancelled = sorted(ws.cancelled, key=lambda i: _order_key(ws, i))
    expected = list(range(1, len(causal) + len(cancelled) + 1))
    if causal + cancelled != expected:
        found.append(
            "purchase_orders.csv: ids are not the causal orders by (issued, supplier, "
            "product, location) from 1, followed by the cancelled ones in the same key order "
            "(DT-038 §8, DT-039 §5.2)"
        )
    return found


def _onb(ws: _Workspace) -> list[str]:
    found = []
    if not ws.orders:
        return ["purchase_orders.csv: no orders"]
    width = order_number_width(max(ws.orders))
    for order_id, order in sorted(ws.orders.items()):
        expected = format_order_number(order_id, width)
        if order["number"] != expected:
            found.append(
                f"purchase_orders.csv: order {order_id} order_number {order['number']!r} "
                f"(expected {expected!r})"
            )
    return found


def _inv_movements(ws: _Workspace) -> list[str]:
    found = []
    for m in ws.movements:
        kind = m["type"]
        if kind not in _MOVEMENT_REFERENCE:
            found.append(f"inventory_movements.csv: movement {m['id']} type {kind!r}")
            continue
        reference_type, reason = _MOVEMENT_REFERENCE[kind]
        sign_ok = m["quantity"] < 0 if kind == "ISSUE" else m["quantity"] > 0
        problems = []
        if not sign_ok:
            problems.append(f"quantity {m['quantity']}")
        if m["reference_type"] != reference_type:
            problems.append(
                f"reference_type {m['reference_type']!r} (expected {reference_type!r})"
            )
        if (m["reference"] is None) != (kind == "ADJUSTMENT"):
            problems.append(f"reference_id {m['reference']}")
        if m["reason"] != reason:
            problems.append(f"reason_code {m['reason']!r} (expected {reason!r})")
        if m["time"] != _MOVEMENT_TIME[kind]:
            problems.append(f"time {m['time']} (expected {_MOVEMENT_TIME[kind]})")
        if m["recorded_at"] != m["occurred_at"]:
            problems.append("recorded_at differs from occurred_at")
        if not ws.start <= m["day"] < ws.end:
            problems.append(f"day {m['day']} outside [{ws.start}, {ws.end})")
        if problems:
            found.append(
                f"inventory_movements.csv: {kind} {m['id']}: " + "; ".join(problems)
            )
    return found


def _inv_balance(ws: _Workspace) -> list[str]:
    found = []
    ordered = sorted(
        ws.movements,
        key=lambda m: (
            m["pair"],
            m["occurred_at"],
            _TYPE_RANK.get(m["type"], 9),
            m["reference"] or 0,
        ),
    )
    balance: Counter = Counter()
    for m in ordered:
        balance[m["pair"]] += m["quantity"]
        if balance[m["pair"]] < 0:
            found.append(
                f"inventory_movements.csv: stock of {m['pair']} is {balance[m['pair']]} after "
                f"movement {m['id']} (V1-13: never negative)"
            )
    return found


def _inv_snapshot(ws: _Workspace) -> list[str]:
    found = []
    total: Counter = Counter()
    last: dict[tuple[int, int], str] = {}
    for m in ws.movements:
        total[m["pair"]] += m["quantity"]
        last[m["pair"]] = max(last.get(m["pair"], ""), m["occurred_at"])
    for r in ws.rows("inventory.csv"):
        pair = (int(r["product_id"]), int(r["location_id"]))
        observed = (
            int(r["quantity_on_hand"]),
            int(r["quantity_reserved"]),
            r["last_movement_at"],
        )
        expected = (total.get(pair, 0), 0, last.get(pair, ""))
        if observed != expected:
            found.append(
                f"inventory.csv: {pair} (on_hand, reserved, last_movement_at) = {observed} "
                f"(expected {expected})"
            )
    return found


def _inv_transit(ws: _Workspace) -> list[str]:
    found = []
    pending: Counter = Counter()
    for order_id, order in ws.orders.items():
        if order["status"] in _PENDING:
            line = ws.line(order_id)
            pending[(line["product"], order["location"])] += (
                line["ordered"] - line["received"]
            )
    for r in ws.rows("inventory.csv"):
        pair = (int(r["product_id"]), int(r["location_id"]))
        if int(r["quantity_in_transit"]) != pending.get(pair, 0):
            found.append(
                f"inventory.csv: {pair} quantity_in_transit {r['quantity_in_transit']} "
                f"(expected {pending.get(pair, 0)}, pending of ISSUED and PARTIALLY_RECEIVED)"
            )
    return found


def _con_grid(ws: _Workspace) -> list[str]:
    demand, consumption = set(ws.demand), set(ws.consumption)
    if demand != consumption:
        return [
            f"consumption.csv: grid differs from demand.csv; missing "
            f"{sorted(demand - consumption)[:5]}, unexpected {sorted(consumption - demand)[:5]}"
        ]
    return []


def _con_formula(ws: _Workspace) -> list[str]:
    found = []
    for key, c in sorted(ws.consumption.items()):
        if key not in ws.demand:
            continue
        latent, consumed = ws.demand[key], c["quantity"]
        before = ws.close_on((key[0], key[1]), key[2]) + consumed
        if not 0 <= consumed <= latent or consumed != min(latent, before):
            found.append(
                f"consumption.csv: {key} consumed {consumed} with latent {latent} and "
                f"{before} on hand before consumption (expected min = {min(latent, before)})"
            )
    return found


def _con_flag(ws: _Workspace) -> list[str]:
    found = []
    for key, c in sorted(ws.consumption.items()):
        if key in ws.demand and c["flag"] != (ws.demand[key] > c["quantity"]):
            found.append(
                f"consumption.csv: {key} is_stockout_affected {c['flag']} with latent "
                f"{ws.demand[key]} and consumption {c['quantity']}"
            )
    return found


def _tmp_validity(ws: _Workspace) -> list[str]:
    return [
        f"products.csv: product {p} valid_to {v['valid_to']} before valid_from {v['valid_from']}"
        for p, v in sorted(ws.products.items())
        if v["valid_to"] is not None and v["valid_to"] < v["valid_from"]
    ]


def _in_force(ws: _Workspace, product: int) -> tuple[_dt.date, _dt.date]:
    p = ws.products[product]
    first = max(ws.start, p["valid_from"])
    last = ws.end - _dt.timedelta(days=1)
    if p["valid_to"] is not None:
        last = min(last, p["valid_to"])
    return first, last


def _tmp_demand(ws: _Workspace) -> list[str]:
    found = []
    by_pair: dict[tuple[int, int], set] = defaultdict(set)
    for product, location, day in ws.demand:
        by_pair[(product, location)].add(day)
    locations = sorted(int(r["id"]) for r in ws.rows("locations.csv"))
    for product in sorted(ws.products):
        first, last = _in_force(ws, product)
        expected = {
            first + _dt.timedelta(days=k) for k in range((last - first).days + 1)
        }
        for location in locations:
            observed = by_pair.get((product, location), set())
            if observed != expected:
                found.append(
                    f"demand.csv: ({product}, {location}) has {len(observed)} days, "
                    f"{len(observed - expected)} outside [{first}, {last}] and "
                    f"{len(expected - observed)} missing (dense series of the days in force)"
                )
    return found


def _tmp_orders(ws: _Workspace) -> list[str]:
    found = []
    for order_id, order in sorted(ws.orders.items()):
        product = ws.line(order_id)["product"]
        first, last = _in_force(ws, product)
        problems = []
        if not first <= order["issued"] <= last:
            problems.append(
                f"issued {order['issued']} outside the days in force [{first}, {last}]"
            )
        if order["issued_time"] != _MIDNIGHT:
            problems.append(f"issued_at time {order['issued_time']}")
        if order["expected"] < order["issued"]:
            problems.append(f"expected {order['expected']} before issued")
        if order["closed"] is not None and order["closed"] < order["issued"]:
            problems.append(f"closed {order['closed']} before issued")
        if problems:
            found.append(
                f"purchase_orders.csv: order {order_id}: " + "; ".join(problems)
            )
    return found


def _tmp_movements(ws: _Workspace) -> list[str]:
    found = []
    order_of_receipt = {
        rid: ws.items[r["item"]]["order"]
        for rid, r in ws.receipts.items()
        if r["item"] in ws.items
    }
    for m in ws.movements:
        product = m["pair"][0]
        if product not in ws.products:
            continue
        first, last = _in_force(ws, product)
        if m["type"] in ("ADJUSTMENT", "ISSUE") and not first <= m["day"] <= last:
            found.append(
                f"inventory_movements.csv: {m['type']} {m['id']} on {m['day']} outside the "
                f"days in force [{first}, {last}]"
            )
        if m["type"] == "RECEIPT" and m["reference"] in order_of_receipt:
            order = ws.orders[order_of_receipt[m["reference"]]]
            if m["day"] < order["issued"] or (
                m["day"] > last and order["issued"] > last
            ):
                found.append(
                    f"inventory_movements.csv: RECEIPT {m['id']} on {m['day']} of an order "
                    f"issued {order['issued']} (after valid_to only for orders issued in force,"
                    " DT-027)"
                )
    return found


def _tmp_lead_time(ws: _Workspace) -> list[str]:
    found = []
    for order_id, order in sorted(ws.causal.items()):
        if order["status"] != "RECEIVED":
            continue
        receipts = ws.receipts_of.get(ws.lines_of[order_id][0], [])
        if not receipts or order["closed"] is None:
            found.append(
                f"purchase_orders.csv: RECEIVED order {order_id} has no lead time"
            )
        elif (order["closed"] - order["issued"]).days < 0:
            found.append(
                f"purchase_orders.csv: order {order_id} has a negative lead time"
            )
    return found


def _mst_vocabularies(ws: _Workspace) -> list[str]:
    found = [
        f"products.csv: product {r['id']} unit_of_measure {r['unit_of_measure']!r}"
        for r in ws.rows("products.csv")
        if r["unit_of_measure"] not in pol.UNIT_OF_MEASURE_VALUES
    ]
    found += [
        f"locations.csv: location {r['id']} type {r['type']!r}"
        for r in ws.rows("locations.csv")
        if r["type"] not in pol.LOCATION_TYPE_VALUES
    ]
    return found


def _scn_structure(ws: _Workspace) -> list[str]:
    found = []
    assignment = ws.assignment
    names = [s.value for s in Scenario]
    if list(assignment) != names:
        return [f"scenario_assignment keys are {list(assignment)} (expected {names})"]
    products = {int(r["id"]) for r in ws.rows("products.csv")}
    suppliers = {int(r["id"]) for r in ws.rows("suppliers.csv")}
    for name, entry in assignment.items():
        if not isinstance(entry, dict) or tuple(entry) != sc.ENTRY_FIELDS:
            found.append(
                f"scenario_assignment {name}: fields are not {sc.ENTRY_FIELDS}"
            )
            continue
        ids = entry["products"]
        if not (
            isinstance(ids, list) and all(type(i) is int for i in ids)
        ) or ids != sorted(set(ids)):
            found.append(
                f"scenario_assignment {name}: products is not an ascending id list"
            )
        elif not set(ids) <= products:
            found.append(
                f"scenario_assignment {name}: unknown products {sorted(set(ids) - products)}"
            )
        sups = entry["suppliers"]
        if entry["unit"] == _SUPPLIER_UNIT:
            if not (
                isinstance(sups, list) and all(type(i) is int for i in sups)
            ) or sups != sorted(set(sups)):
                found.append(
                    f"scenario_assignment {name}: suppliers is not an ascending id list"
                )
            elif not set(sups) <= suppliers:
                found.append(
                    f"scenario_assignment {name}: unknown suppliers {sorted(set(sups) - suppliers)}"
                )
        elif sups is not None:
            found.append(
                f"scenario_assignment {name}: suppliers must be null for unit {entry['unit']!r}"
            )
    return found


def _scn_coherence(ws: _Workspace) -> list[str]:
    profiles = build_supplier_profiles(ws.config, ws.root)
    expected = sc.build_assignment(ws.config, ws.root, profiles)
    return [
        f"scenario_assignment {name}: {ws.assignment.get(name)!r} (the workspace gives "
        f"{expected[name]!r})"
        for name in expected
        if ws.assignment.get(name) != expected[name]
    ]


def _cov(ws: _Workspace) -> list[str]:
    found = []
    for scenario in ws.config.required_scenarios:
        entry = ws.assignment.get(scenario.value) or {}
        empty = not entry.get("products") or (
            entry.get("unit") == _SUPPLIER_UNIT and not entry.get("suppliers")
        )
        if empty:
            found.append(
                f"scenario_assignment {scenario.value}: required by scenarios.required but "
                "not covered (V1-08)"
            )
    return found


def _level_c(field: str, situation: int) -> Callable[[_Workspace], list[str]]:
    def check(ws: _Workspace) -> list[str]:
        if not getattr(ws.emergent, field):
            return [f"situation {situation} of spec §25 has no product ({field})"]
        return []

    return check


#: `DT-042` section 4, in report order.
CHECKS: tuple[Check, ...] = (
    Check("MAN-01", "MAN", "DT-025", _man_fields),
    Check("MAN-02", "MAN", "DT-025; DT-033", _man_identity),
    Check("MAN-03", "MAN", "DT-025; DT-030", _man_components),
    Check("MAN-04", "MAN", "DT-025; DT-040 §4; spec §34", _man_files),
    Check("FMT-01", "FMT", "DT-024", _fmt_encoding),
    Check("FMT-02", "FMT", "DT-024; DT-034; DT-038; DT-039", _fmt_header),
    Check("FMT-03", "FMT", "DT-024", _fmt_fields),
    Check("FMT-04", "FMT", "DT-024; DT-034; DT-038; DT-039; spec §34", _fmt_types),
    Check("ORG-01", "ORG", "DT-026; spec §34", _org),
    Check("IDN-01", "IDN", "DT-024; DT-038 §8; DT-039 §7", _idn_ids),
    Check("IDN-02", "IDN", "DT-024; DT-034; DT-038; DT-039", _idn_keys),
    Check("IDN-03", "IDN", "docs/04 §3.4; V1-08", _idn_preferred),
    Check("REF-01", "REF", "spec §34; V1-08", _ref_foreign_keys),
    Check("REF-02", "REF", "DT-038 §7; DT-039 §8", _ref_lines),
    Check("REF-03", "REF", "DT-036 §3; DT-038 §7", _ref_preferred),
    Check("REF-04", "REF", "DT-038 §5.2; DT-039 §8", _ref_receipt_movements),
    Check("REF-05", "REF", "DT-038 §5.2-§5.3", _ref_issue_movements),
    Check("REF-06", "REF", "DT-036 §1; DT-038 §5.2", _ref_opening),
    Check("REF-07", "REF", "DT-038 §6", _ref_inventory_pairs),
    Check("COM-01", "COM", "DT-028 §1; V1-08", _com_relations),
    Check("COM-02", "COM", "DT-036 §4; V1-06; docs/04 §3.10", _com_quantity),
    Check("COM-03", "COM", "DT-038 §12; DT-039 §3", _com_cost),
    Check("COM-04", "COM", "DT-037 §3; DT-038 §12", _com_expected),
    Check("RCP-01", "RCP", "DT-038 §9; DT-039 §4; spec §20", _rcp_receipts),
    Check("RCP-02", "RCP", "V1-12; DT-039 §8", _rcp_sums),
    Check("RCP-03", "RCP", "DT-038 §10", _rcp_status),
    Check("CAN-01", "CAN", "DT-039 §5.2 point 4", _can_shape),
    Check("CAN-02", "CAN", "DT-039 §5.2 points 1 and 4", _can_templates),
    Check("CAN-03", "CAN", "DT-039 §5.2 point 2", _can_count),
    Check("CAN-04", "CAN", "DT-038 §8; DT-039 §5.2, §7", _can_numbering),
    Check("ONB-01", "ONB", "DT-039 §6", _onb),
    Check("INV-01", "INV", "DT-036 §9; DT-038 §5.1-§5.2", _inv_movements),
    Check("INV-02", "INV", "V1-13; spec §22", _inv_balance),
    Check("INV-03", "INV", "DT-038 §6; spec §22", _inv_snapshot),
    Check("INV-04", "INV", "DT-038 §6.1; spec §23", _inv_transit),
    Check("CON-01", "CON", "DT-034; DT-038 §4", _con_grid),
    Check("CON-02", "CON", "DT-038 §4", _con_formula),
    Check("CON-03", "CON", "DT-038 §4", _con_flag),
    Check("TMP-01", "TMP", "DT-027", _tmp_validity),
    Check("TMP-02", "TMP", "DT-027; DT-034", _tmp_demand),
    Check("TMP-03", "TMP", "DT-027; DT-036 §9; spec §20", _tmp_orders),
    Check("TMP-04", "TMP", "DT-027 (amended 2026-09-24); DT-038 §9", _tmp_movements),
    Check("TMP-05", "TMP", "spec §20, §34 (decision C7/C8-14)", _tmp_lead_time),
    Check("MST-01", "MST", "DT-028 §5-§6 (decision C7/C8-14)", _mst_vocabularies),
    Check("SCN-01", "SCN", "DT-041 §4-§5", _scn_structure),
    Check("SCN-02", "SCN", "DT-041 §6", _scn_coherence),
    Check("COV-01", "COV", "V1-08; DT-041 §10", _cov),
    Check("LVC-08", "LVC", "DT-023; DT-038 §4", _level_c("censored_demand", 8)),
    Check("LVC-12", "LVC", "DT-023; DT-041 §8", _level_c("late_transit", 12)),
    Check("LVC-18", "LVC", "DT-023; DT-041 §8", _level_c("moq_overstock", 18)),
    Check("LVC-20", "LVC", "DT-023; spec §18", _level_c("inactive_with_history", 20)),
)

_LEVEL_C = (
    ("8", "censored_demand", "Demanda censurada", "DOCUMENTED_DEFINITION", "DT-038 §4"),
    (
        "12",
        "late_transit",
        "Tránsito total suficiente / efectivo insuficiente",
        sc.CRITERION_SYNTHETIC,
        "DT-041 §8",
    ),
    (
        "18",
        "moq_overstock",
        "Conflicto MOQ / sobreinventario",
        sc.CRITERION_SYNTHETIC,
        "DT-041 §8",
    ),
    (
        "20",
        "inactive_with_history",
        "Producto inactivo con histórico",
        "DOCUMENTED_DEFINITION",
        "spec §18",
    ),
)


def _run_checks(ws: _Workspace) -> tuple[list[dict[str, str]], list[str]]:
    results, problems = [], []
    for check in CHECKS:
        try:
            findings = check.run(ws)
        except pol.GeneratorError as exc:
            findings = [f"could not be evaluated: {'; '.join(exc.problems)}"]
        except (
            _Unreadable,
            KeyError,
            ValueError,
            TypeError,
            IndexError,
            AttributeError,
            OSError,
        ) as exc:
            findings = [f"could not be evaluated: {type(exc).__name__}: {exc}"]
        results.append(
            {
                "id": check.id,
                "family": check.family,
                "source": check.source,
                "status": "FAIL" if findings else "PASS",
            }
        )
        for finding in findings[:DETAIL_LIMIT]:
            problems.append(f"[{check.id}] {finding}")
        if len(findings) > DETAIL_LIMIT:
            problems.append(
                f"[{check.id}] ... and {len(findings) - DETAIL_LIMIT} more "
                f"({len(findings)} findings in total)"
            )
    return results, problems


# ---------------------------------------------------------------------------------------
# The report - DT-042 section 5, the twenty items of section 35
# ---------------------------------------------------------------------------------------


def _distribution(values: list[int]) -> list[dict[str, int]]:
    return [{"days": d, "count": c} for d, c in sorted(Counter(values).items())]


def _report(ws: _Workspace, results: list[dict[str, str]]) -> dict[str, Any]:
    m = _manifest(ws)
    assignment = ws.assignment
    required = {s.value for s in ws.config.required_scenarios}
    distribution = {}
    for name, entry in assignment.items():
        supplier_axis = entry["unit"] == _SUPPLIER_UNIT
        distribution[name] = {
            "unit": entry["unit"],
            "criterion": entry["criterion"],
            "required": name in required,
            "covered": bool(entry["products"])
            and (not supplier_axis or bool(entry["suppliers"])),
            "suppliers": len(entry["suppliers"]) if supplier_axis else None,
            "products": len(entry["products"]),
        }
    stockout = [key for key, c in ws.consumption.items() if c["flag"]]
    by_status = Counter(o["status"] for o in ws.orders.values())
    observed = []
    for order_id, order in ws.causal.items():
        if order["status"] == "RECEIVED":
            last = max(
                ws.receipts[r]["day"] for r in ws.receipts_of[ws.lines_of[order_id][0]]
            )
            observed.append((last - order["issued"]).days)
    passed = sum(1 for r in results if r["status"] == "PASS")
    return {
        "result": "PASS",
        "dataset_version": m["dataset_version"],
        "generator_version": m["generator_version"],
        "seed": m["seed"],
        "time_range": m["time_range"],
        "records_by_entity": {f["name"]: f["rows"] for f in m["files"]},
        "counts": {
            "products": len(ws.rows("products.csv")),
            "suppliers": len(ws.rows("suppliers.csv")),
            "categories": len(ws.rows("categories.csv")),
            "locations": len(ws.rows("locations.csv")),
        },
        "scenario_distribution": distribution,
        "products_by_demand_pattern": {
            shape: len(assignment[shape]["products"]) for shape in _SHAPES
        },
        "stockout": {
            "pair_days": len(stockout),
            "products": len({key[0] for key in stockout}),
        },
        "orders": {
            "total": len(ws.orders),
            "by_status": {
                status: by_status.get(status, 0) for status in _ORDER_STATUSES
            },
        },
        "receipts": len(ws.receipts),
        "lead_time_distribution": {
            "agreed": _distribution([rel["lead"] for rel in ws.relations.values()]),
            "observed": _distribution(observed),
        },
        "validations": {
            "executed": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "checks": results,
            "level_c": {
                number: {
                    "situation": situation,
                    "criterion": criterion,
                    "source": source,
                    "products": len(getattr(ws.emergent, field)),
                }
                for number, field, situation, criterion, source in _LEVEL_C
            },
        },
        "anomalies": [],
        "known_limitations": [dict(item) for item in KNOWN_LIMITATIONS],
    }


def validate(config: DatasetConfig, input_dir: Path | str) -> dict[str, Any]:
    """Run every check of `DT-042` on the workspace; write nothing.

    Returns:
        The ``quality_report``, only if every check passed.

    Raises:
        GeneratorError: with every finding of every failed check (`DT-042` section 7).
    """
    ws = _Workspace(config, Path(input_dir))
    results, problems = _run_checks(ws)
    if problems:
        raise pol.GeneratorError(
            [f"Component 8 rejected the dataset: {len(problems)} finding(s)"] + problems
        )
    return _report(ws, results)


def generate(config: DatasetConfig, output_dir: Path | str) -> dict[str, Any]:
    """Validate the workspace and record ``quality_report`` and this component.

    Nothing but ``manifest.json`` changes, and only when every check passes. The
    manifest is never overwritten: a ``quality_report`` field or a ``validator``
    component already present fails before anything is checked.

    Returns:
        The extended manifest, already written to disk.

    Raises:
        GeneratorError: when a check fails or the manifest would be overwritten.
    """
    target = Path(output_dir)
    path = target / MANIFEST_FILE
    if not path.is_file():
        raise pol.GeneratorError(
            [f"{MANIFEST_FILE} not found in {target}; Component 8 extends it"]
        )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    if QUALITY_REPORT_FIELD in manifest:
        problems.append(f"the manifest already has {QUALITY_REPORT_FIELD!r}")
    if any(
        c.get("name") == COMPONENT_VALIDATOR for c in manifest.get("components", [])
    ):
        problems.append(
            f"the manifest already has the {COMPONENT_VALIDATOR!r} component"
        )
    if problems:
        raise pol.GeneratorError(
            problems + ["Component 8 never overwrites (DT-042 §3)"]
        )

    report = validate(config, target)
    manifest = extend_manifest(
        manifest,
        component={
            "name": COMPONENT_VALIDATOR,
            "version": VALIDATOR_VERSION,
            "sub_seed": sub_seed(config.seed, COMPONENT_VALIDATOR),
        },
        files=[],
    )
    manifest = add_manifest_field(manifest, QUALITY_REPORT_FIELD, report)
    write_manifest(path, manifest)
    return manifest
