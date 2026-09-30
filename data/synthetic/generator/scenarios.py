"""Component 7 - Scenario Assignment (`DT-041`).

Phase 1 - Data. Records in ``manifest.json`` which products and which suppliers represent
each of the 16 Level A axes of `DT-023`, and measures the axes that are not assigned but
emerge from the simulation.

**C7 records; it does not decide and it does not generate.** The demand shape and the
rotation class were decided by Component 3 (`DT-035`) and the supplier profile by
Component 6 (`DT-037`); C7 writes those decisions down. The inventory axes emerged from
Component 4 (`DT-036`); C7 measures them on the files already written. It creates no row,
changes no file other than the manifest, writes no CSV and draws no random number.

The criteria tagged ``SYNTHETIC_COVERAGE_CRITERION`` exist **only** to show that the
synthetic dataset contains the situations section 25 of the specification requires. They
are not business rules, and they do not close, replace or anticipate `BR-X03`, `DT-P11`,
`BR-P10` or `DT-011` (`DT-041`, reading warning and section 7). No part of the main system
may use them as a rule.

Level C situations (`DT-023`) are **not** labelled here. Their detection criteria are
defined in `DT-041` section 8 and implemented by :func:`emergent_properties`, which this
component does not publish: Component 8 reports them.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ..config.config import DatasetConfig, Scenario
from . import policies as pol
from .catalog import PRODUCT_COLUMNS, PRODUCT_SUPPLIER_COLUMNS, SUPPLIER_COLUMNS
from .demand import DEMAND_COLUMNS, DEMAND_FILE, build_demand
from .inventory import (
    CONSUMPTION_COLUMNS,
    CONSUMPTION_FILE,
    INVENTORY_COLUMNS,
    INVENTORY_FILE,
    MOVEMENT_COLUMNS,
    MOVEMENTS_FILE,
    SupplierProfile,
)
from .orders import (
    PURCHASE_ORDER_COLUMNS,
    PURCHASE_ORDER_ITEM_COLUMNS,
    PURCHASE_ORDER_RECEIPT_COLUMNS,
    PURCHASE_ORDER_ITEMS_FILE,
    PURCHASE_ORDER_RECEIPTS_FILE,
    PURCHASE_ORDERS_FILE,
    STATUS_CANCELLED,
    STATUS_RECEIVED,
)
from .rng import COMPONENT_SCENARIOS, sub_seed
from .writer import (
    SCENARIOS_VERSION,
    add_manifest_field,
    extend_manifest,
    render_csv,
    write_manifest,
)

__all__ = [
    "SCENARIO_ASSIGNMENT_FIELD",
    "ENTRY_FIELDS",
    "UNIT_PRODUCT",
    "UNIT_SUPPLIER",
    "BASIS_ASSIGNED",
    "BASIS_STRUCTURAL",
    "BASIS_OBSERVED",
    "CRITERION_COMPONENT_DECISION",
    "CRITERION_DOCUMENTED",
    "CRITERION_SYNTHETIC",
    "Series",
    "Order",
    "Relation",
    "Facts",
    "EmergentProperties",
    "load_facts",
    "window_sum",
    "overstock_threshold",
    "is_overstocked",
    "synthetic_quantity",
    "observed_axes",
    "supplier_axes",
    "emergent_properties",
    "build_assignment",
    "generate",
]

MANIFEST_FILE = "manifest.json"
PRODUCTS_FILE = "products.csv"
SUPPLIERS_FILE = "suppliers.csv"
PRODUCT_SUPPLIERS_FILE = "product_suppliers.csv"

#: The manifest field this component contributes (`DT-025`, `DT-041` section 4).
SCENARIO_ASSIGNMENT_FIELD = "scenario_assignment"

#: The six fields of every entry, in this order (`DT-041` section 4).
ENTRY_FIELDS = ("unit", "basis", "criterion", "source", "suppliers", "products")

UNIT_PRODUCT = "product"
UNIT_SUPPLIER = "supplier"

BASIS_ASSIGNED = "ASSIGNED"
BASIS_STRUCTURAL = "STRUCTURAL"
BASIS_OBSERVED = "OBSERVED"

CRITERION_COMPONENT_DECISION = "COMPONENT_DECISION"
CRITERION_DOCUMENTED = "DOCUMENTED_DEFINITION"
CRITERION_SYNTHETIC = "SYNTHETIC_COVERAGE_CRITERION"

#: `DT-036` sections 4 and 5, read from the single place that holds them.
_WINDOW = pol.INVENTORY_WINDOW_DAYS
_COVERAGE = pol.INVENTORY_ORDER_COVERAGE_DAYS

_DEMAND_SOURCE = "demand: DT-035 §1-§2"

#: `DT-041` section 5: every axis with its unit, basis, criterion and source. The order of
#: the output is the enum's, not this table's.
_AXES: dict[Scenario, tuple[str, str, str, str]] = {
    Scenario.HIGH_ROTATION: (
        UNIT_PRODUCT,
        BASIS_ASSIGNED,
        CRITERION_COMPONENT_DECISION,
        _DEMAND_SOURCE,
    ),
    Scenario.LOW_ROTATION: (
        UNIT_PRODUCT,
        BASIS_ASSIGNED,
        CRITERION_COMPONENT_DECISION,
        _DEMAND_SOURCE,
    ),
    Scenario.STABLE_DEMAND: (
        UNIT_PRODUCT,
        BASIS_ASSIGNED,
        CRITERION_COMPONENT_DECISION,
        _DEMAND_SOURCE,
    ),
    Scenario.GROWING_DEMAND: (
        UNIT_PRODUCT,
        BASIS_ASSIGNED,
        CRITERION_COMPONENT_DECISION,
        _DEMAND_SOURCE,
    ),
    Scenario.DECLINING_DEMAND: (
        UNIT_PRODUCT,
        BASIS_ASSIGNED,
        CRITERION_COMPONENT_DECISION,
        _DEMAND_SOURCE,
    ),
    Scenario.SEASONAL_DEMAND: (
        UNIT_PRODUCT,
        BASIS_ASSIGNED,
        CRITERION_COMPONENT_DECISION,
        _DEMAND_SOURCE,
    ),
    Scenario.INTERMITTENT_DEMAND: (
        UNIT_PRODUCT,
        BASIS_ASSIGNED,
        CRITERION_COMPONENT_DECISION,
        _DEMAND_SOURCE,
    ),
    Scenario.ERRATIC_DEMAND: (
        UNIT_PRODUCT,
        BASIS_ASSIGNED,
        CRITERION_COMPONENT_DECISION,
        _DEMAND_SOURCE,
    ),
    Scenario.STOCKOUT: (
        UNIT_PRODUCT,
        BASIS_OBSERVED,
        CRITERION_DOCUMENTED,
        "inventory: DT-038 §4",
    ),
    Scenario.OVERSTOCK: (
        UNIT_PRODUCT,
        BASIS_OBSERVED,
        CRITERION_SYNTHETIC,
        "scenarios: DT-041 §6.6",
    ),
    Scenario.LOW_INVENTORY: (
        UNIT_PRODUCT,
        BASIS_OBSERVED,
        CRITERION_SYNTHETIC,
        "scenarios: DT-041 §6.5",
    ),
    Scenario.RELIABLE_SUPPLIER: (
        UNIT_SUPPLIER,
        BASIS_ASSIGNED,
        CRITERION_COMPONENT_DECISION,
        "supplier_behaviour: DT-037 §2; spec §12.1",
    ),
    Scenario.DELAYED_SUPPLIER: (
        UNIT_SUPPLIER,
        BASIS_ASSIGNED,
        CRITERION_COMPONENT_DECISION,
        "supplier_behaviour: DT-037 §2; spec §12.2",
    ),
    Scenario.PARTIAL_DELIVERY: (
        UNIT_SUPPLIER,
        BASIS_ASSIGNED,
        CRITERION_COMPONENT_DECISION,
        "supplier_behaviour: DT-037 §2; spec §12.3",
    ),
    Scenario.MULTIPLE_LEAD_TIMES: (
        UNIT_PRODUCT,
        BASIS_STRUCTURAL,
        CRITERION_DOCUMENTED,
        "catalog: DT-028 §1.6.3",
    ),
    Scenario.IN_TRANSIT: (
        UNIT_PRODUCT,
        BASIS_OBSERVED,
        CRITERION_DOCUMENTED,
        "inventory: DT-038 §6.1",
    ),
}


# ---------------------------------------------------------------------------------------
# What C7 reads - DT-041 section 3
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Series:
    """One product-location pair, day by day.

    ``first`` is the offset, from the start of the period, of the first day in force;
    ``latent``, ``consumed`` and ``stockout`` have one entry per day in force from there.
    ``on_hand`` has one entry per day **of the period**: the stock at the close of that
    day, the sum of every movement of the pair up to it (`DT-038` section 3).
    """

    product_id: int
    location_id: int
    first: int
    latent: tuple[int, ...]
    consumed: tuple[int, ...]
    stockout: tuple[bool, ...]
    on_hand: tuple[int, ...]
    movements: int
    in_transit: int


@dataclass(frozen=True)
class Order:
    """One purchase order with its single line and its receipts (`DT-039` section 8).

    Dates are offsets from the start of the period; ``receipts`` is ``(day, quantity)``
    sorted by day and then by receipt id.
    """

    id: int
    supplier_id: int
    location_id: int
    product_id: int
    status: str
    issued: int
    expected: int
    quantity_ordered: int
    receipts: tuple[tuple[int, int], ...]

    @property
    def causal(self) -> bool:
        """Every order that is not a synthetic cancelled copy of Component 5 (`DT-039` §5)."""
        return self.status != STATUS_CANCELLED


@dataclass(frozen=True)
class Relation:
    """One row of ``product_suppliers.csv``, reduced to what the criteria read."""

    product_id: int
    supplier_id: int
    lead_time: int
    is_preferred: bool
    is_active: bool


@dataclass(frozen=True)
class Facts:
    """The published dataset, reduced to what the criteria of `DT-041` read."""

    days: int
    active: dict[int, bool]
    suppliers: frozenset[int]
    relations: tuple[Relation, ...]
    series: dict[tuple[int, int], Series]
    orders: tuple[Order, ...]


def _read(directory: Path, name: str, columns: Sequence[str]) -> list[dict[str, str]]:
    path = directory / name
    if not path.is_file():
        raise pol.GeneratorError([f"{name} not found in {directory}"])
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != tuple(columns):
            raise pol.GeneratorError([f"{name}: header is not its contract"])
        return list(reader)


def _int(value: str, column: str) -> int:
    try:
        return int(value)
    except ValueError:
        raise pol.GeneratorError([f"{column}: {value!r} is not an integer"]) from None


def _bool(value: str, column: str) -> bool:
    if value in ("true", "false"):
        return value == "true"
    raise pol.GeneratorError([f"{column}: {value!r} is not true/false"])


def _offset(value: str, column: str, start: _dt.date) -> int:
    """Days from the start of the period to the day of a date or a UTC date-time."""
    if len(value) not in (10, 20):
        raise pol.GeneratorError([f"{column}: {value!r} is not a date"])
    try:
        day = _dt.date.fromisoformat(value[:10])
    except ValueError:
        raise pol.GeneratorError([f"{column}: {value!r} is not a date"]) from None
    return (day - start).days


def load_facts(config: DatasetConfig, input_dir: Path | str) -> Facts:
    """Read the files C2-C5 wrote into ``input_dir``; write nothing.

    Raises:
        GeneratorError: a file is missing, has another header, holds a malformed value,
            or does not let a criterion be evaluated (`DT-041` section 11, points 2 and 5).
    """
    source = Path(input_dir)
    start = config.period.start_date
    days = (config.period.end_date - start).days

    active = {
        _int(r["id"], "products.id"): _bool(r["is_active"], "products.is_active")
        for r in _read(source, PRODUCTS_FILE, PRODUCT_COLUMNS)
    }
    suppliers = frozenset(
        _int(r["id"], "suppliers.id")
        for r in _read(source, SUPPLIERS_FILE, SUPPLIER_COLUMNS)
    )
    relations = tuple(
        Relation(
            _int(r["product_id"], "product_suppliers.product_id"),
            _int(r["supplier_id"], "product_suppliers.supplier_id"),
            _int(r["agreed_lead_time_days"], "product_suppliers.agreed_lead_time_days"),
            _bool(r["is_preferred"], "product_suppliers.is_preferred"),
            _bool(r["is_active"], "product_suppliers.is_active"),
        )
        for r in _read(source, PRODUCT_SUPPLIERS_FILE, PRODUCT_SUPPLIER_COLUMNS)
    )

    latent: dict[tuple[int, int], dict[int, int]] = defaultdict(dict)
    for r in _read(source, DEMAND_FILE, DEMAND_COLUMNS):
        pair = (
            _int(r["product_id"], "demand.product_id"),
            _int(r["location_id"], "demand.location_id"),
        )
        latent[pair][_offset(r["occurred_on"], "demand.occurred_on", start)] = _int(
            r["quantity"], "demand.quantity"
        )
    consumption: dict[tuple[int, int], dict[int, tuple[int, bool]]] = defaultdict(dict)
    for r in _read(source, CONSUMPTION_FILE, CONSUMPTION_COLUMNS):
        pair = (
            _int(r["product_id"], "consumption.product_id"),
            _int(r["location_id"], "consumption.location_id"),
        )
        consumption[pair][
            _offset(r["occurred_on"], "consumption.occurred_on", start)
        ] = (
            _int(r["quantity"], "consumption.quantity"),
            _bool(r["is_stockout_affected"], "consumption.is_stockout_affected"),
        )
    moves: dict[tuple[int, int], dict[int, int]] = defaultdict(lambda: defaultdict(int))
    counts: dict[tuple[int, int], int] = defaultdict(int)
    for r in _read(source, MOVEMENTS_FILE, MOVEMENT_COLUMNS):
        pair = (
            _int(r["product_id"], "movements.product_id"),
            _int(r["location_id"], "movements.location_id"),
        )
        day = _offset(r["occurred_at"], "movements.occurred_at", start)
        if not 0 <= day < days:
            raise pol.GeneratorError([f"movement {r['id']} falls outside the period"])
        moves[pair][day] += _int(r["quantity"], "movements.quantity")
        counts[pair] += 1
    in_transit = {
        (
            _int(r["product_id"], "inventory.product_id"),
            _int(r["location_id"], "inventory.location_id"),
        ): _int(r["quantity_in_transit"], "inventory.quantity_in_transit")
        for r in _read(source, INVENTORY_FILE, INVENTORY_COLUMNS)
    }

    problems: list[str] = []
    series: dict[tuple[int, int], Series] = {}
    for pair in sorted(latent):
        by_day = latent[pair]
        first, last = min(by_day), max(by_day)
        if len(by_day) != last - first + 1:
            problems.append(f"demand of {pair} is not one row per day in force")
            continue
        if len(by_day) < _WINDOW:
            problems.append(
                f"demand of {pair} has fewer than W = {_WINDOW} days (DT-036 §5)"
            )
            continue
        consumed = consumption.get(pair, {})
        if set(consumed) != set(by_day):
            problems.append(
                f"consumption of {pair} does not cover the grid of its demand"
            )
            continue
        if pair not in in_transit:
            problems.append(f"{pair} has no row in {INVENTORY_FILE}")
            continue
        balance, closes = 0, []
        for day in range(days):
            balance += moves[pair].get(day, 0)
            closes.append(balance)
        offsets = range(first, last + 1)
        series[pair] = Series(
            product_id=pair[0],
            location_id=pair[1],
            first=first,
            latent=tuple(by_day[d] for d in offsets),
            consumed=tuple(consumed[d][0] for d in offsets),
            stockout=tuple(consumed[d][1] for d in offsets),
            on_hand=tuple(closes),
            movements=counts.get(pair, 0),
            in_transit=in_transit[pair],
        )

    items: dict[int, list[dict[str, str]]] = defaultdict(list)
    for r in _read(source, PURCHASE_ORDER_ITEMS_FILE, PURCHASE_ORDER_ITEM_COLUMNS):
        items[_int(r["purchase_order_id"], "items.purchase_order_id")].append(r)
    receipts: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    for r in _read(
        source, PURCHASE_ORDER_RECEIPTS_FILE, PURCHASE_ORDER_RECEIPT_COLUMNS
    ):
        receipts[
            _int(r["purchase_order_item_id"], "receipts.purchase_order_item_id")
        ].append(
            (
                _offset(r["received_at"], "receipts.received_at", start),
                _int(r["id"], "receipts.id"),
                _int(r["quantity_received"], "receipts.quantity_received"),
            )
        )
    orders = []
    for r in _read(source, PURCHASE_ORDERS_FILE, PURCHASE_ORDER_COLUMNS):
        order_id = _int(r["id"], "purchase_orders.id")
        lines = items.get(order_id, [])
        if len(lines) != 1:
            problems.append(
                f"order {order_id} does not have exactly one line (DT-039 §8)"
            )
            continue
        line = lines[0]
        issued = _offset(r["issued_at"], "purchase_orders.issued_at", start)
        if not 0 <= issued < days:
            problems.append(f"order {order_id} was issued outside the period")
            continue
        orders.append(
            Order(
                id=order_id,
                supplier_id=_int(r["supplier_id"], "purchase_orders.supplier_id"),
                location_id=_int(r["location_id"], "purchase_orders.location_id"),
                product_id=_int(line["product_id"], "items.product_id"),
                status=r["status"],
                issued=issued,
                expected=_offset(
                    r["expected_at"], "purchase_orders.expected_at", start
                ),
                quantity_ordered=_int(
                    line["quantity_ordered"], "items.quantity_ordered"
                ),
                receipts=tuple(
                    (day, quantity)
                    for day, _, quantity in sorted(
                        receipts.get(_int(line["id"], "items.id"), [])
                    )
                ),
            )
        )
    if problems:
        raise pol.GeneratorError(problems)
    return Facts(
        days=days,
        active=active,
        suppliers=suppliers,
        relations=relations,
        series=series,
        orders=tuple(sorted(orders, key=lambda o: o.id)),
    )


# ---------------------------------------------------------------------------------------
# The arithmetic of DT-041 sections 6.6 and 8 - integers only, exact
# ---------------------------------------------------------------------------------------


def _ceil_div(numerator: int, denominator: int) -> int:
    return -(-numerator // denominator)


def window_sum(latent: Sequence[int], position: int) -> int:
    """Latent demand of the window of `DT-036` section 5 at ``position`` of a series.

    The window starts at ``a(t) = max(first_day, t - W)`` and is exactly ``W`` days wide,
    so ``d_recent(t) = window_sum / W`` - the same window Component 4 used.
    """
    if len(latent) < _WINDOW or not 0 <= position < len(latent):
        raise ValueError(
            f"position {position} has no complete window of {_WINDOW} days"
        )
    begin = max(0, position - _WINDOW)
    return sum(latent[begin : begin + _WINDOW])


def overstock_threshold(window: int, lead_time: int) -> int:
    """``ceil(d_recent x (L + C))`` with ``d_recent = window / W``, kept exact (`DT-041` §6.6)."""
    return _ceil_div(window * (lead_time + _COVERAGE), _WINDOW)


def is_overstocked(on_hand: int, window: int, lead_time: int) -> bool:
    """The synthetic overstock criterion of `DT-041` section 6.6.

    ``SYNTHETIC_COVERAGE_CRITERION``: shows the dataset holds stock above what its own
    synthetic policy needs. **Not** the business definition of overstock (`BR-X03`).
    With no recent demand there is no expected need to exceed, so it is never overstock;
    at the threshold exactly it is not overstock either.
    """
    return window > 0 and on_hand > overstock_threshold(window, lead_time)


def synthetic_quantity(window: int) -> int:
    """``Q_sint = ceil(d_recent x C)`` of `DT-041` section 8 - deliberately not ``raw_need``."""
    return _ceil_div(window * _COVERAGE, _WINDOW)


def _ordering_lead_times(facts: Facts) -> dict[int, int]:
    """Lead time of the single preferred and active relation of each product (`DT-036` §3)."""
    found: dict[int, list[int]] = defaultdict(list)
    for relation in facts.relations:
        if relation.is_preferred and relation.is_active:
            found[relation.product_id].append(relation.lead_time)
    several = sorted(p for p, leads in found.items() if len(leads) > 1)
    if several:
        raise pol.GeneratorError(
            [f"products with more than one preferred active relation: {several}"]
        )
    return {product: leads[0] for product, leads in found.items()}


def _overstock_days(series: Series, lead_time: int) -> list[int]:
    """Period offsets of the days in force on which `DT-041` §6.6 holds.

    Same windows as :func:`window_sum`, taken from a prefix sum so the scan is linear.
    """
    if len(series.latent) < _WINDOW:
        raise ValueError(f"a series needs at least {_WINDOW} days in force")
    prefix = [0]
    for quantity in series.latent:
        prefix.append(prefix[-1] + quantity)
    days = []
    for position in range(len(series.latent)):
        begin = max(0, position - _WINDOW)
        window = prefix[begin + _WINDOW] - prefix[begin]
        day = series.first + position
        if is_overstocked(series.on_hand[day], window, lead_time):
            days.append(day)
    return days


# ---------------------------------------------------------------------------------------
# The observed axes - DT-041 sections 6.3 to 6.6
# ---------------------------------------------------------------------------------------


def _stockout(facts: Facts) -> list[int]:
    return sorted({s.product_id for s in facts.series.values() if any(s.stockout)})


def _in_transit(facts: Facts) -> list[int]:
    return sorted({s.product_id for s in facts.series.values() if s.in_transit > 0})


def _multiple_lead_times(facts: Facts) -> list[int]:
    leads: dict[int, set[int]] = defaultdict(set)
    for relation in facts.relations:
        leads[relation.product_id].add(relation.lead_time)
    return sorted(product for product, values in leads.items() if len(values) >= 2)


def _series_of(facts: Facts, order: Order) -> Series:
    pair = (order.product_id, order.location_id)
    if pair not in facts.series:
        raise pol.GeneratorError([f"order {order.id}: {pair} has no demand series"])
    return facts.series[pair]


def _low_inventory(facts: Facts) -> list[int]:
    found = set()
    for order in facts.orders:
        if order.causal and _series_of(facts, order).on_hand[order.issued] > 0:
            found.add(order.product_id)
    return sorted(found)


def _overstock(facts: Facts, lead_times: dict[int, int]) -> list[int]:
    return sorted(
        {
            s.product_id
            for s in facts.series.values()
            if s.product_id in lead_times
            and _overstock_days(s, lead_times[s.product_id])
        }
    )


def observed_axes(facts: Facts) -> dict[str, list[int]]:
    """Products of the five axes C7 measures instead of recording (`DT-041` §6.3-§6.6)."""
    lead_times = _ordering_lead_times(facts)
    return {
        Scenario.STOCKOUT.value: _stockout(facts),
        Scenario.OVERSTOCK.value: _overstock(facts, lead_times),
        Scenario.LOW_INVENTORY.value: _low_inventory(facts),
        Scenario.MULTIPLE_LEAD_TIMES.value: _multiple_lead_times(facts),
        Scenario.IN_TRANSIT.value: _in_transit(facts),
    }


# ---------------------------------------------------------------------------------------
# Supplier axes - DT-041 section 6.2
# ---------------------------------------------------------------------------------------


def _profiles_by_supplier(
    facts: Facts, profiles: Sequence[SupplierProfile]
) -> dict[int, SupplierProfile]:
    problems: list[str] = []
    by_supplier: dict[int, SupplierProfile] = {}
    for profile in profiles:
        if profile.supplier_id in by_supplier:
            problems.append(
                f"supplier {profile.supplier_id} has more than one SupplierProfile"
            )
        if profile.supplier_id not in facts.suppliers:
            problems.append(
                f"profile of supplier {profile.supplier_id}, not in {SUPPLIERS_FILE}"
            )
        by_supplier[profile.supplier_id] = profile
    missing = sorted(
        {
            o.supplier_id
            for o in facts.orders
            if o.causal and o.supplier_id not in by_supplier
        }
    )
    if missing:
        problems.append(
            f"suppliers with causal orders and no SupplierProfile: {missing}"
        )
    if problems:
        raise pol.GeneratorError(problems)
    return by_supplier


def _reliable(profile: SupplierProfile) -> bool:
    return profile.punctuality == "PUNCTUAL" and profile.integrity == "COMPLETE"


def _late(profile: SupplierProfile) -> bool:
    return profile.punctuality == "LATE"


def _split(profile: SupplierProfile) -> bool:
    return profile.integrity == "SPLIT"


def _received(order: Order) -> bool:
    return order.status == STATUS_RECEIVED


def _arrived_late(order: Order) -> bool:
    return bool(order.receipts) and order.receipts[0][0] > order.expected


def _partially_received(order: Order) -> bool:
    return any(quantity < order.quantity_ordered for _, quantity in order.receipts)


#: `DT-041` section 6.2: the profile that places a supplier on the axis, and the evidence
#: an order of that supplier must show for its product to manifest the axis.
_SUPPLIER_AXES = {
    Scenario.RELIABLE_SUPPLIER: (_reliable, _received),
    Scenario.DELAYED_SUPPLIER: (_late, _arrived_late),
    Scenario.PARTIAL_DELIVERY: (_split, _partially_received),
}


def supplier_axes(
    facts: Facts, profiles: Sequence[SupplierProfile]
) -> dict[str, tuple[list[int], list[int]]]:
    """``(suppliers, products)`` of the three supplier axes (`DT-041` section 6.2).

    ``suppliers`` - every supplier whose profile places it on the axis: the primary
    coverage. ``products`` - the products of that supplier's causal orders that show the
    behaviour: the evidence. A supplier with the profile and no such order adds none.
    """
    by_supplier = _profiles_by_supplier(facts, profiles)
    axes = {}
    for scenario, (has_profile, manifests) in _SUPPLIER_AXES.items():
        suppliers = sorted(s for s, p in by_supplier.items() if has_profile(p))
        members = set(suppliers)
        products = sorted(
            {
                o.product_id
                for o in facts.orders
                if o.causal and o.supplier_id in members and manifests(o)
            }
        )
        axes[scenario.value] = (suppliers, products)
    return axes


# ---------------------------------------------------------------------------------------
# Component 3 - rebuilt and checked against the published demand (DT-041 section 6.1)
# ---------------------------------------------------------------------------------------


def _demand_axes(
    config: DatasetConfig, input_dir: Path, manifest: dict[str, Any]
) -> dict[str, list[int]]:
    """Shape and rotation of every product, exactly as Component 3 decided them.

    Rebuilds the demand with the public, pure :func:`build_demand` and accepts the
    profiles only if the rebuilt ``demand.csv`` is byte for byte the published one: its
    ``sha256`` must equal both the file's on disk and the one the manifest records.
    """
    demand = build_demand(config, input_dir)
    text = render_csv(
        DEMAND_COLUMNS, [[row[c] for c in DEMAND_COLUMNS] for row in demand.rows]
    )
    rebuilt = hashlib.sha256(text.encode("utf-8")).hexdigest()
    on_disk = hashlib.sha256((input_dir / DEMAND_FILE).read_bytes()).hexdigest()
    recorded = [
        f.get("sha256")
        for f in manifest.get("files", [])
        if f.get("name") == DEMAND_FILE
    ]
    if recorded != [rebuilt] or on_disk != rebuilt:
        raise pol.GeneratorError(
            [
                f"the demand rebuilt from Component 3 does not match {DEMAND_FILE} and its "
                "manifest entry: the shapes and rotations cannot be recorded (DT-041 §6.1)"
            ]
        )
    axes: dict[str, list[int]] = defaultdict(list)
    for profile in demand.profiles:
        axes[profile.shape].append(profile.product_id)
        axes[profile.rotation].append(profile.product_id)
    return {name: sorted(ids) for name, ids in axes.items()}


# ---------------------------------------------------------------------------------------
# Level C - detection criteria, not labels (DT-041 section 8)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EmergentProperties:
    """Products showing each Level C situation of `DT-023`, by its number in section 25.

    **Not written by Component 7** and never a label: `DT-023` keeps Level C out of the
    enum and out of ``scenario_assignment``. Component 8 reports them.
    """

    censored_demand: tuple[int, ...]  # situation 8 - DT-038 §4
    late_transit: tuple[int, ...]  # situation 12 - SYNTHETIC_COVERAGE_CRITERION
    moq_overstock: tuple[int, ...]  # situation 18 - SYNTHETIC_COVERAGE_CRITERION
    inactive_with_history: tuple[int, ...]  # situation 20 - spec §18


def emergent_properties(facts: Facts) -> EmergentProperties:
    """Evaluate the four criteria of `DT-041` section 8 on the published files."""
    censored = sorted(
        {
            s.product_id
            for s in facts.series.values()
            if any(
                flag and demand > sold
                for flag, demand, sold in zip(s.stockout, s.latent, s.consumed)
            )
        }
    )

    late_transit, moq_overstock = set(), set()
    lead_times = _ordering_lead_times(facts)
    overstock_days: dict[tuple[int, int], list[int]] = {}
    for order in facts.orders:
        if not order.causal:
            continue
        series = _series_of(facts, order)
        end = series.first + len(series.latent)
        if not series.first <= order.issued < end:
            raise pol.GeneratorError(
                [f"order {order.id} was issued outside the series of its product"]
            )
        first_receipt = order.receipts[0][0] if order.receipts else facts.days
        # Situation 12: the open interval (issue, first receipt), clipped to the days in force.
        low, high = max(order.issued + 1, series.first), min(first_receipt, end)
        span = range(low - series.first, high - series.first)
        if order.quantity_ordered > sum(series.latent[k] for k in span) and any(
            series.stockout[k] for k in span
        ):
            late_transit.add(order.product_id)
        # Situation 18: Q_sint at the issue day, then overstock from the first receipt on.
        lead = lead_times.get(order.product_id)
        if lead is None or not order.receipts:
            continue
        window = window_sum(series.latent, order.issued - series.first)
        if order.quantity_ordered <= synthetic_quantity(window):
            continue
        pair = (series.product_id, series.location_id)
        if pair not in overstock_days:
            overstock_days[pair] = _overstock_days(series, lead)
        if any(day >= first_receipt for day in overstock_days[pair]):
            moq_overstock.add(order.product_id)

    received = {o.product_id for o in facts.orders if o.causal and o.receipts}
    history = sorted(
        product
        for product, is_active in facts.active.items()
        if not is_active
        and product in received
        and any(
            sum(s.consumed) > 0 and s.movements > 0
            for s in facts.series.values()
            if s.product_id == product
        )
    )
    return EmergentProperties(
        censored_demand=tuple(censored),
        late_transit=tuple(sorted(late_transit)),
        moq_overstock=tuple(sorted(moq_overstock)),
        inactive_with_history=tuple(history),
    )


# ---------------------------------------------------------------------------------------
# The assignment and the manifest - DT-041 sections 4, 5 and 11
# ---------------------------------------------------------------------------------------


def _read_manifest(directory: Path) -> dict[str, Any]:
    path = directory / MANIFEST_FILE
    if not path.is_file():
        raise pol.GeneratorError(
            [f"{MANIFEST_FILE} not found in {directory}; Component 7 extends it"]
        )
    return json.loads(path.read_text(encoding="utf-8"))


def build_assignment(
    config: DatasetConfig,
    input_dir: Path | str,
    profiles: Sequence[SupplierProfile],
) -> dict[str, dict[str, Any]]:
    """Build ``scenario_assignment`` for the dataset in ``input_dir``; write nothing.

    All 16 axes of the enum, in its canonical order, whatever ``scenarios.required``
    says: deciding whether an empty axis is acceptable is Component 8's job (`DT-041`
    section 10). An empty axis is recorded as ``[]`` and is not an error.

    Raises:
        GeneratorError: in the cases of `DT-041` section 11, points 2 to 5.
    """
    source = Path(input_dir)
    manifest = _read_manifest(source)
    demand_axes = _demand_axes(config, source, manifest)
    facts = load_facts(config, source)
    by_axis = supplier_axes(facts, profiles)
    observed = observed_axes(facts)

    assignment: dict[str, dict[str, Any]] = {}
    for scenario in Scenario:
        unit, basis, criterion, where = _AXES[scenario]
        suppliers: list[int] | None = None
        if scenario.value in by_axis:
            suppliers, products = by_axis[scenario.value]
        elif scenario.value in observed:
            products = observed[scenario.value]
        else:
            products = demand_axes.get(scenario.value, [])
        assignment[scenario.value] = {
            "unit": unit,
            "basis": basis,
            "criterion": criterion,
            "source": where,
            "suppliers": suppliers,
            "products": products,
        }
    return assignment


def generate(
    config: DatasetConfig,
    output_dir: Path | str,
    profiles: Sequence[SupplierProfile],
) -> dict[str, Any]:
    """Record ``scenario_assignment`` and this component's entry in the manifest.

    Nothing but ``manifest.json`` changes: no CSV is written or touched. The manifest is
    never overwritten - if it already has a ``scenario_assignment`` field or a
    ``scenarios`` component, this fails before computing anything.

    Returns:
        The extended manifest, already written to disk.

    Raises:
        GeneratorError: in the cases of `DT-041` section 11. Nothing is written then.
    """
    target = Path(output_dir)
    manifest = _read_manifest(target)
    problems = []
    if SCENARIO_ASSIGNMENT_FIELD in manifest:
        problems.append(f"the manifest already has {SCENARIO_ASSIGNMENT_FIELD!r}")
    if any(
        c.get("name") == COMPONENT_SCENARIOS for c in manifest.get("components", [])
    ):
        problems.append(
            f"the manifest already has the {COMPONENT_SCENARIOS!r} component"
        )
    if problems:
        raise pol.GeneratorError(
            problems + ["Component 7 never overwrites (DT-041 §11)"]
        )

    assignment = build_assignment(config, target, profiles)
    manifest = extend_manifest(
        manifest,
        component={
            "name": COMPONENT_SCENARIOS,
            "version": SCENARIOS_VERSION,
            "sub_seed": sub_seed(config.seed, COMPONENT_SCENARIOS),
        },
        files=[],
    )
    manifest = add_manifest_field(manifest, SCENARIO_ASSIGNMENT_FIELD, assignment)
    write_manifest(target / MANIFEST_FILE, manifest)
    return manifest
