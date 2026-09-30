"""Component 4 - Inventory Simulator: the causal reality of stock.

Phase 1 - Data.

    products.csv, locations.csv, product_suppliers.csv, demand.csv
        + supplier profiles (Component 6, in memory)
            -> build_inventory() -> Inventory -> generate()
                -> consumption.csv, inventory_movements.csv, inventory.csv
                -> SimulationResult (causal orders and receipts, for Component 5)

**What this component owns.** Stock, and everything stock decides: the opening balance,
satisfied demand (``consumption.csv``) and its stockout flag, every inventory movement,
the final snapshot, and the causal purchase orders and receipts that replenish it. It
turns latent demand (`DT-034`) into satisfied demand: ``demand.csv`` is read, never
written.

**What it does not own**, each for a documented reason:

* **Supplier profiles** are Component 6's (`DT-037`). This module *consumes* them through
  :class:`SupplierProfile` and applies them to concrete orders; it does not assign them,
  does not know the profile mix and does not hold the per mille values of `DT-037`.
* **Purchase order files** are Component 5's (`DT-039`). This module computes the causal
  orders, lines and receipts and assigns their identifiers (`DT-038` section 8); it does
  not write ``purchase_orders.csv``, does not form ``order_number`` (decision A2) and
  knows nothing about cancelled orders or their policy.
* **Publication** is the orchestrator's (`DT-040`). This module writes into the
  directory it is given and has **no default output directory**, so it cannot write to
  ``data/synthetic/output/`` by accident.

**Not a supply engine.** The threshold ``s`` and the quantity ``Q`` of `DT-036` are
synthetic simulation parameters: ``s`` is not a reorder point, ``Q`` is not a
recommendation, and the lead time used is the **agreed** one of the preferred active
relation - never the observed lead time of `V1-09`, which belongs to the engine (decision
D-C4-3).

Contracts implemented here: `DT-036` (synthetic policies), `DT-037` section 3 (how a
profile turns into receipts, with the split rule of decision D-C4-1), `DT-038` (output
contract, daily order, identifiers, preconditions of decision D-C4-2), `DT-027` as
amended (receipts of in-flight orders may fall after ``valid_to``).
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from ..config.config import DatasetConfig
from . import policies as pol
from .rng import COMPONENT_INVENTORY, DeterministicRandom, sub_seed
from .writer import (
    INVENTORY_VERSION,
    extend_manifest,
    file_entry,
    render_csv,
    write_manifest,
)

__all__ = [
    "CONSUMPTION_FILE",
    "MOVEMENTS_FILE",
    "INVENTORY_FILE",
    "CONSUMPTION_COLUMNS",
    "MOVEMENT_COLUMNS",
    "INVENTORY_COLUMNS",
    "SupplierProfile",
    "SimulatedReceipt",
    "SimulatedOrderLine",
    "SimulatedOrder",
    "SimulationResult",
    "Inventory",
    "opening_balance",
    "reorder_threshold",
    "order_quantity",
    "split_quantities",
    "build_inventory",
    "generate",
]

# ---------------------------------------------------------------------------------------
# Files and column contracts - DT-038 sections 4 to 6
# ---------------------------------------------------------------------------------------

CONSUMPTION_FILE = "consumption.csv"
MOVEMENTS_FILE = "inventory_movements.csv"
INVENTORY_FILE = "inventory.csv"
MANIFEST_FILE = "manifest.json"

#: The four files this component reads (`DT-038` section 1). ``categories.csv`` and
#: ``suppliers.csv`` are deliberately not read: nothing in the causal loop depends on a
#: product's category or on supplier attributes beyond the profile.
PRODUCTS_FILE = "products.csv"
LOCATIONS_FILE = "locations.csv"
PRODUCT_SUPPLIERS_FILE = "product_suppliers.csv"
DEMAND_FILE = "demand.csv"

#: `DT-038` section 4.
CONSUMPTION_COLUMNS = (
    "id",
    "product_id",
    "location_id",
    "occurred_on",
    "quantity",
    "channel",
    "is_stockout_affected",
    "data_origin",
)

#: `DT-038` section 5.
MOVEMENT_COLUMNS = (
    "id",
    "product_id",
    "location_id",
    "movement_type",
    "quantity",
    "occurred_at",
    "recorded_at",
    "reference_type",
    "reference_id",
    "reason_code",
    "data_origin",
    "created_by",
)

#: `DT-038` section 6.
INVENTORY_COLUMNS = (
    "id",
    "product_id",
    "location_id",
    "quantity_on_hand",
    "quantity_reserved",
    "quantity_in_transit",
    "last_movement_at",
    "updated_at",
    "data_origin",
)

# ---------------------------------------------------------------------------------------
# Movement and order vocabulary - DT-038 sections 5 and 10, DT-036 sections 7 and 9
# ---------------------------------------------------------------------------------------

ADJUSTMENT = "ADJUSTMENT"
RECEIPT = "RECEIPT"
ISSUE = "ISSUE"

INITIAL_INVENTORY = "INITIAL_INVENTORY"
PURCHASE_ORDER_RECEIPT = "PURCHASE_ORDER_RECEIPT"
CONSUMPTION_REFERENCE = "CONSUMPTION"
OPENING_BALANCE = "OPENING_BALANCE"

#: `DT-036` section 9: the clock of each movement type. Only movements carry an hour,
#: because only there is the order within a day meaningful.
_CLOCK = {
    ADJUSTMENT: _dt.time(0, 0, 0, tzinfo=_dt.timezone.utc),
    RECEIPT: _dt.time(6, 0, 0, tzinfo=_dt.timezone.utc),
    ISSUE: _dt.time(18, 0, 0, tzinfo=_dt.timezone.utc),
}

#: `DT-038` section 5.4: tie-break rank inside the same instant.
_TYPE_RANK = {ADJUSTMENT: 0, RECEIPT: 1, ISSUE: 2}

STATUS_ISSUED = "ISSUED"
STATUS_PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
STATUS_RECEIVED = "RECEIVED"

_PERMILLE = 1000


# ---------------------------------------------------------------------------------------
# Contract consumed from Component 6 - DT-037 section 3
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SupplierProfile:
    """Behaviour of one supplier, as Component 6 hands it to Component 4.

    **This is a consumed contract, not an implementation of Component 6.** The type is
    declared here because Component 4 is its consumer; Component 6
    (:mod:`.supplier_behaviour`) produces instances of it (decision A2, 2026-09-28).
    Nothing in this module assigns profiles to suppliers, knows the profile mix, or holds
    the per mille values of `DT-037` section 2: those are Component 6's authority. The
    tests of this module also build profiles by hand.

    Fields and types are those of the table in `DT-037` section 3. ``split_range`` and
    ``completion_lag_days`` are ``None`` when the supplier never splits
    (``partial_permille == 0``).
    """

    supplier_id: int
    punctuality: str
    integrity: str
    on_time_permille: int
    delay_days: tuple[int, int]
    partial_permille: int
    split_range: tuple[int, int] | None
    completion_lag_days: tuple[int, int] | None

    def problems(self) -> list[str]:
        """Range violations of the `DT-037` section 3 table, all of them at once."""
        found = []
        name = f"profile of supplier {self.supplier_id}"
        if not 0 <= self.on_time_permille <= _PERMILLE:
            found.append(f"{name}: on_time_permille must be in [0, 1000]")
        low, high = self.delay_days
        if low < 1 or low > high:
            found.append(f"{name}: delay_days must be (min >= 1, min <= max)")
        if not 0 <= self.partial_permille <= _PERMILLE:
            found.append(f"{name}: partial_permille must be in [0, 1000]")
        if self.partial_permille > 0:
            if self.split_range is None or self.completion_lag_days is None:
                found.append(
                    f"{name}: a supplier that splits needs split_range and "
                    "completion_lag_days"
                )
            else:
                split_low, split_high = self.split_range
                if not 0 <= split_low <= split_high <= _PERMILLE:
                    found.append(f"{name}: split_range must lie in [0, 1000]")
                lag_low, lag_high = self.completion_lag_days
                if lag_low < 1 or lag_low > lag_high:
                    found.append(
                        f"{name}: completion_lag_days must be (min >= 1, min <= max)"
                    )
        return found


# ---------------------------------------------------------------------------------------
# Structure handed to Component 5 - DT-038 section 12
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SimulatedReceipt:
    """One receipt of a causal order, inside the period (`DT-038` section 9)."""

    id: int
    purchase_order_item_id: int
    received_on: _dt.date
    quantity: int


@dataclass(frozen=True)
class SimulatedOrderLine:
    """The single line of a causal order (`DT-038` section 7: one line per order)."""

    id: int
    purchase_order_id: int
    product_id: int
    quantity_ordered: int
    quantity_received: int
    unit_cost_cents: int


@dataclass(frozen=True)
class SimulatedOrder:
    """A causal purchase order.

    **No ``order_number``** (decision A2): Component 5 forms it for every order, because
    its width depends on a total that includes the cancelled orders Component 4 does not
    know about. ``expected_on`` is the only source of the committed date; Component 5
    copies it and never recalculates it.
    """

    id: int
    supplier_id: int
    location_id: int
    issued_on: _dt.date
    expected_on: _dt.date
    closed_on: _dt.date | None
    status: str
    line: SimulatedOrderLine
    receipts: tuple[SimulatedReceipt, ...]


@dataclass(frozen=True)
class SimulationResult:
    """What Component 4 hands to Component 5, identifiers already assigned.

    `DT-038` section 12 also names a ``metrics`` member. It is **not implemented**: the
    definitions it points to ("`DT-036` section 17 of the agreement") exist in no
    document of the repository, and inventing formulas is forbidden. Every figure those
    metrics would need is derivable from the files this component writes.
    """

    orders: tuple[SimulatedOrder, ...]


@dataclass(frozen=True)
class Inventory:
    """Everything Component 4 produces, before it is written."""

    consumption: list[dict[str, Any]] = field(default_factory=list)
    movements: list[dict[str, Any]] = field(default_factory=list)
    inventory: list[dict[str, Any]] = field(default_factory=list)
    simulation: SimulationResult = field(default_factory=lambda: SimulationResult(()))
    #: Opening profile of each ``(product_id, location_id)`` pair. Not written anywhere
    #: (`DT-025` forbids generation labels in entities); kept for inspection and tests.
    opening_profiles: dict[tuple[int, int], str] = field(default_factory=dict)


# ---------------------------------------------------------------------------------------
# The formulas of DT-036, as pure integer functions
# ---------------------------------------------------------------------------------------


def _ceil_div(numerator: int, denominator: int) -> int:
    """``ceil(numerator / denominator)`` for a positive denominator, without floats."""
    return -(-numerator // denominator)


def opening_balance(
    window_sum: int, window: int, lead_time: int, margin: int, factor_permille: int
) -> int:
    """Opening balance of `DT-036` section 1.

    ``on_hand_base = ceil(d x (L + M))`` and ``on_hand = ceil(base x factor / 1000)``,
    with ``d = window_sum / window`` kept as an **exact rational**: the mean is never
    rounded before the single ``ceil`` of each step.
    """
    base = _ceil_div(window_sum * (lead_time + margin), window)
    return _ceil_div(base * factor_permille, _PERMILLE)


def reorder_threshold(window_sum: int, window: int, lead_time: int) -> int:
    """Synthetic threshold ``s = ceil(d_recent x L)`` of `DT-036` section 3.

    A synthetic simulation parameter, **not a reorder point**: no safety stock, no
    forecast, no service level. ``lead_time`` is the agreed lead time (D-C4-3).
    """
    return _ceil_div(window_sum * lead_time, window)


def order_quantity(
    window_sum: int, window: int, coverage: int, moq: int, order_multiple: int
) -> int | None:
    """Synthetic order quantity of `DT-036` section 4, with the whole of `V1-06`.

    ``raw_need = Q = ceil(d_recent x C)``. **If ``raw_need <= 0`` there is no order** -
    the guard of `V1-06` that precedes any computation of ``Q_final``. Otherwise
    ``Q_final = ceil(max(raw_need, MOQ) / order_multiple) x order_multiple``. MOQ and the
    order multiple stay two separate constraints, applied in that order. Returns
    ``None`` for "no order": there is no artificial minimum of one unit, and a
    ``quantity_ordered`` of zero can never come out of here.
    """
    raw_need = _ceil_div(window_sum * coverage, window)
    if raw_need <= 0:
        return None
    q_moq = max(raw_need, moq)
    return _ceil_div(q_moq, order_multiple) * order_multiple


def split_quantities(q_final: int, split_permille: int) -> tuple[int, int]:
    """The two receipts of a partial delivery - decision D-C4-1 (option O1).

    ``q1 = min(Q_final - 1, max(1, ceil(Q_final x split / 1000)))`` and
    ``q2 = Q_final - q1``. The upper bound is what the first version of `DT-037`
    lacked: with ``ceil`` alone a small order could give ``q2 = 0``, a receipt of zero
    units. Now ``1 <= q1 <= Q_final - 1`` and ``1 <= q2 <= Q_final - 1`` for every
    ``Q_final >= 2``, and ``q1 + q2 = Q_final`` exactly, so no over-receipt is possible.
    """
    if q_final < 2:
        raise ValueError(f"a partial delivery needs Q_final >= 2, got {q_final}")
    q1_raw = _ceil_div(q_final * split_permille, _PERMILLE)
    q1 = min(q_final - 1, max(1, q1_raw))
    return q1, q_final - q1


def _window_start(position: int, window: int) -> int:
    """Start of the demand window of `DT-036` section 5, as an offset in the series.

    ``a(t) = max(first_day, t - W)``: during the first ``W`` days of a series the window
    is frozen on its first ``W`` days (the declared synthetic warm-up); from then on it
    is ``[t - W, t)``. Both branches coincide at ``t = first_day + W``, so there is no
    discontinuity. The window is always exactly ``W`` days wide.
    """
    return max(0, position - window)


# ---------------------------------------------------------------------------------------
# Reading the inputs - DT-038 section 1
# ---------------------------------------------------------------------------------------


def _read_csv(path: Path, expected: Sequence[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise pol.GeneratorError(
            [
                f"{path.name} not found in {path.parent}; Component 4 consumes the "
                "output of Components 2 and 3, which must be generated first"
            ]
        )
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in expected if name not in (reader.fieldnames or [])]
        if missing:
            raise pol.GeneratorError(
                [f"{path.name} is missing the column(s) {missing}"]
            )
        return list(reader)


def _parse_bool(value: str, column: str) -> bool:
    if value in ("true", "false"):
        return value == "true"
    raise pol.GeneratorError([f"{column} must be 'true' or 'false', got {value!r}"])


def _parse_date(value: str, column: str) -> _dt.date:
    try:
        return _dt.date.fromisoformat(value)
    except ValueError as exc:
        raise pol.GeneratorError([f"{column} is not an ISO date: {value!r}"]) from exc


_AMOUNT = re.compile(r"(\d+)\.(\d{2})")


def _parse_cents(value: str, column: str) -> int:
    """An amount written with exactly two decimals (`DT-024`), read as integer cents."""
    match = _AMOUNT.fullmatch(value)
    if match is None:
        raise pol.GeneratorError(
            [f"{column} must have exactly two decimals, got {value!r}"]
        )
    return int(match.group(1)) * 100 + int(match.group(2))


@dataclass(frozen=True)
class _Relation:
    supplier_id: int
    agreed_lead_time_days: int
    moq: int
    order_multiple: int
    unit_cost_cents: int
    is_preferred: bool
    is_active: bool


def _read_inputs(input_dir: Path) -> tuple[
    list[dict[str, Any]],
    list[int],
    dict[int, list[_Relation]],
    dict[tuple[int, int], list[tuple[_dt.date, int]]],
]:
    products = [
        {
            "id": int(row["id"]),
            "valid_from": _parse_date(row["valid_from"], "products.valid_from"),
            "valid_to": (
                _parse_date(row["valid_to"], "products.valid_to")
                if row["valid_to"]
                else None
            ),
        }
        for row in _read_csv(
            input_dir / PRODUCTS_FILE, ("id", "valid_from", "valid_to")
        )
    ]
    products.sort(key=lambda row: row["id"])

    locations = sorted(
        int(row["id"]) for row in _read_csv(input_dir / LOCATIONS_FILE, ("id",))
    )

    relations: dict[int, list[_Relation]] = {}
    for row in _read_csv(
        input_dir / PRODUCT_SUPPLIERS_FILE,
        (
            "product_id",
            "supplier_id",
            "agreed_lead_time_days",
            "moq",
            "order_multiple",
            "unit_cost",
            "is_preferred",
            "is_active",
        ),
    ):
        relations.setdefault(int(row["product_id"]), []).append(
            _Relation(
                supplier_id=int(row["supplier_id"]),
                agreed_lead_time_days=int(row["agreed_lead_time_days"]),
                moq=int(row["moq"]),
                order_multiple=int(row["order_multiple"]),
                unit_cost_cents=_parse_cents(
                    row["unit_cost"], "product_suppliers.unit_cost"
                ),
                is_preferred=_parse_bool(
                    row["is_preferred"], "product_suppliers.is_preferred"
                ),
                is_active=_parse_bool(row["is_active"], "product_suppliers.is_active"),
            )
        )
    for rows in relations.values():
        rows.sort(key=lambda relation: relation.supplier_id)

    demand: dict[tuple[int, int], list[tuple[_dt.date, int]]] = {}
    for row in _read_csv(
        input_dir / DEMAND_FILE,
        ("product_id", "location_id", "occurred_on", "quantity"),
    ):
        demand.setdefault((int(row["product_id"]), int(row["location_id"])), []).append(
            (
                _parse_date(row["occurred_on"], "demand.occurred_on"),
                int(row["quantity"]),
            )
        )
    for series in demand.values():
        series.sort()
    return products, locations, relations, demand


# ---------------------------------------------------------------------------------------
# Preconditions - DT-038 section 16 (decision D-C4-2) and DT-036 section 6
# ---------------------------------------------------------------------------------------


def _validity_days(
    product: dict[str, Any], start: _dt.date, end: _dt.date
) -> list[_dt.date]:
    """Days of ``[start, end)`` inside ``[valid_from, valid_to]``, both ends included."""
    first = max(start, product["valid_from"])
    last = end - _dt.timedelta(days=1)
    if product["valid_to"] is not None:
        last = min(last, product["valid_to"])
    if last < first:
        return []
    return [first + _dt.timedelta(days=k) for k in range((last - first).days + 1)]


def _opening_relation(relations: Sequence[_Relation]) -> _Relation:
    """The relation whose agreed lead time sizes the opening balance (`DT-036` §6).

    The active preferred relation if there is one; otherwise the relation with the lowest
    ``supplier_id``, **only** to size the opening balance - never to order, select a
    supplier or compute an observed lead time.
    """
    for relation in relations:
        if relation.is_preferred and relation.is_active:
            return relation
    return relations[0]


def _ordering_relation(relations: Sequence[_Relation]) -> _Relation | None:
    """The active preferred relation, the only one that may place orders (`DT-038` §7)."""
    for relation in relations:
        if relation.is_preferred and relation.is_active:
            return relation
    return None


def _check_preconditions(
    config: DatasetConfig,
    products: Sequence[dict[str, Any]],
    locations: Sequence[int],
    relations: dict[int, list[_Relation]],
    demand: dict[tuple[int, int], list[tuple[_dt.date, int]]],
    profiles: dict[int, SupplierProfile],
    profile_problems: list[str],
) -> None:
    window = pol.INVENTORY_WINDOW_DAYS
    start, end = config.period.start_date, config.period.end_date
    problems = list(profile_problems)

    # P-C4-2 (D-C4-2): the period must hold one whole window.
    if config.period.days < window:
        problems.append(
            f"P-C4-2: the period has {config.period.days} days and the demand window of "
            f"DT-036 needs {window}; the window is never shortened (DT-038)"
        )

    if not locations:
        problems.append("locations.csv has no rows")

    pairs = [
        (product["id"], location) for product in products for location in locations
    ]
    # Floor of one pair per opening profile (DT-036 section 2).
    if len(pairs) < len(pol.INVENTORY_OPENING_PROFILES):
        problems.append(
            f"at least {len(pol.INVENTORY_OPENING_PROFILES)} product-location pairs are "
            f"needed, one per opening profile (DT-036 section 2); found {len(pairs)}"
        )

    for product in products:
        product_relations = relations.get(product["id"], [])
        # DT-036 section 6: no invented default lead time.
        if not product_relations:
            problems.append(
                f"DT-036 section 6: product {product['id']} has no row in "
                "product_suppliers.csv; no lead time can size its opening balance "
                "and none is invented"
            )
            continue
        preferred = [r for r in product_relations if r.is_preferred and r.is_active]
        if len(preferred) > 1:
            problems.append(
                f"product {product['id']} has {len(preferred)} active preferred "
                "relations; DT-038 section 7 orders from the single one (DT-028 §2.4)"
            )
        if preferred and preferred[0].supplier_id not in profiles:
            problems.append(
                f"supplier {preferred[0].supplier_id} places orders for product "
                f"{product['id']} but has no SupplierProfile (DT-037 section 3)"
            )

        valid = _validity_days(product, start, end)
        # P-C4-3 (D-C4-2): every product must hold one whole window.
        if len(valid) < window:
            problems.append(
                f"P-C4-3: product {product['id']} is in force for {len(valid)} days of "
                f"the period and the demand window of DT-036 needs {window}; the window "
                "is never shortened, padded or extrapolated (DT-038)"
            )
        for location in locations:
            series = [day for day, _ in demand.get((product["id"], location), [])]
            if series != valid:
                problems.append(
                    f"demand.csv does not hold exactly one row per day in force for "
                    f"product {product['id']} at location {location} (DT-034)"
                )

    if problems:
        raise pol.GeneratorError(problems)


# ---------------------------------------------------------------------------------------
# Opening profiles - DT-036 section 2
# ---------------------------------------------------------------------------------------


def _assign_opening_profiles(
    pairs: Sequence[tuple[int, int]], base: int
) -> dict[tuple[int, int], str]:
    """Split the pairs 30 / 40 / 30 across the three opening profiles.

    Largest remainder with a floor of one (the helper of `DT-028` section 3.2, shared
    with Component 3), and a **seeded permutation** decides which pair gets which slot -
    never ``abc_class`` or ``rotation_class``, which are empty in the catalogue
    (`DT-036` section 2).
    """
    counts = pol.demand_mix_counts(
        pol.INVENTORY_OPENING_MIX, pol.INVENTORY_OPENING_PROFILES, len(pairs)
    )
    slots: list[str] = []
    for name in pol.INVENTORY_OPENING_PROFILES:
        slots.extend([name] * counts[name])
    order = DeterministicRandom(base, "opening-profile-assignment").permutation(
        len(pairs)
    )
    return {pair: slots[order[position]] for position, pair in enumerate(pairs)}


# ---------------------------------------------------------------------------------------
# The causal loop - DT-038 section 3
# ---------------------------------------------------------------------------------------


@dataclass
class _Order:
    """A causal order while it is being simulated, before identifiers exist."""

    ref: int
    pair: tuple[int, int]
    supplier_id: int
    issued_on: _dt.date
    expected_on: _dt.date
    quantity: int
    unit_cost_cents: int
    #: Receipts that actually happened inside the period, as ``(day, quantity)``.
    received: list[tuple[_dt.date, int]] = field(default_factory=list)


@dataclass
class _PairState:
    first: _dt.date
    last: _dt.date
    quantities: list[int]
    prefix: list[int]
    ordering: _Relation | None
    on_hand: int = 0
    on_order: int = 0
    scheduled: dict[_dt.date, list[tuple[int, int]]] = field(default_factory=dict)


def _schedule_receipts(
    quantity: int,
    expected_on: _dt.date,
    profile: SupplierProfile,
    timing: DeterministicRandom,
    splitting: DeterministicRandom,
) -> list[tuple[_dt.date, int]]:
    """How the supplier delivers one order - `DT-037` section 3, applied by C4.

    Punctuality: a draw below ``on_time_permille`` arrives on ``expected_on``; otherwise
    a delay in ``delay_days``. Integrity: a draw below ``partial_permille`` with
    ``Q_final >= 2`` splits the delivery (decision D-C4-1), the second receipt coming
    ``completion_lag_days`` after the first. Two streams per pair, so the draws of one
    product never shift those of another.
    """
    first = expected_on
    if timing.below(_PERMILLE) >= profile.on_time_permille:
        first = expected_on + _dt.timedelta(days=timing.between(*profile.delay_days))
    if splitting.below(_PERMILLE) < profile.partial_permille and quantity >= 2:
        assert profile.split_range is not None
        assert profile.completion_lag_days is not None
        q1, q2 = split_quantities(quantity, splitting.between(*profile.split_range))
        lag = splitting.between(*profile.completion_lag_days)
        return [(first, q1), (first + _dt.timedelta(days=lag), q2)]
    return [(first, quantity)]


def build_inventory(
    config: DatasetConfig,
    input_dir: Path | str,
    profiles: Sequence[SupplierProfile],
) -> Inventory:
    """Simulate stock day by day and return every row Component 4 is responsible for.

    Reads the published output of Components 2 and 3 from ``input_dir``; writes nothing.

    Raises:
        GeneratorError: if a precondition fails. Every problem is reported at once and
            nothing is simulated.
    """
    source = Path(input_dir)
    window = pol.INVENTORY_WINDOW_DAYS
    margin = pol.INVENTORY_OPENING_MARGIN_DAYS
    coverage = pol.INVENTORY_ORDER_COVERAGE_DAYS
    start, end = config.period.start_date, config.period.end_date

    products, locations, relations, demand = _read_inputs(source)

    by_supplier: dict[int, SupplierProfile] = {}
    profile_problems: list[str] = []
    for profile in profiles:
        if profile.supplier_id in by_supplier:
            profile_problems.append(
                f"supplier {profile.supplier_id} has more than one SupplierProfile"
            )
        by_supplier[profile.supplier_id] = profile
        profile_problems.extend(profile.problems())

    _check_preconditions(
        config, products, locations, relations, demand, by_supplier, profile_problems
    )

    base = sub_seed(config.seed, COMPONENT_INVENTORY)
    pairs = [
        (product["id"], location) for product in products for location in locations
    ]
    opening_profiles = _assign_opening_profiles(pairs, base)

    states: dict[tuple[int, int], _PairState] = {}
    opening: dict[tuple[int, int], int] = {}
    for product_id, location_id in pairs:
        series = demand[(product_id, location_id)]
        quantities = [quantity for _, quantity in series]
        prefix = [0]
        for quantity in quantities:
            prefix.append(prefix[-1] + quantity)
        product_relations = relations[product_id]
        pair = (product_id, location_id)
        states[pair] = _PairState(
            first=series[0][0],
            last=series[-1][0],
            quantities=quantities,
            prefix=prefix,
            ordering=_ordering_relation(product_relations),
        )
        opening[pair] = opening_balance(
            prefix[window],
            window,
            _opening_relation(product_relations).agreed_lead_time_days,
            margin,
            pol.INVENTORY_OPENING_FACTOR_PERMILLE[opening_profiles[pair]],
        )

    timing: dict[tuple[int, int], DeterministicRandom] = {}
    splitting: dict[tuple[int, int], DeterministicRandom] = {}

    orders: list[_Order] = []
    consumption: list[dict[str, Any]] = []
    #: ``(pair, type, quantity, day, reference)``; the reference is resolved to an
    #: identifier once identifiers exist: ``(order_ref, receipt_index)`` for a receipt,
    #: the day for an issue.
    movements: list[tuple[tuple[int, int], str, int, _dt.date, Any]] = []

    day = start
    while day < end:
        for pair in pairs:
            state = states[pair]

            # 1. Opening of the day. The opening balance enters on the first day in force.
            if day == state.first and opening[pair] > 0:
                state.on_hand += opening[pair]
                movements.append((pair, ADJUSTMENT, opening[pair], day, None))

            # 2. Receipts scheduled for today - also after valid_to (DT-027 as amended).
            for order_ref, quantity in state.scheduled.pop(day, []):
                order = orders[order_ref]
                state.on_hand += quantity
                state.on_order -= quantity
                order.received.append((day, quantity))
                movements.append(
                    (pair, RECEIPT, quantity, day, (order_ref, len(order.received) - 1))
                )

            if not state.first <= day <= state.last:
                continue  # no demand, no consumption, no trigger outside the validity

            # 3-4. Latent demand and consumption: min(demand, stock), no backlog.
            position = (day - state.first).days
            latent = state.quantities[position]
            consumed = min(latent, state.on_hand)
            state.on_hand -= consumed
            consumption.append(
                {
                    "product_id": pair[0],
                    "location_id": pair[1],
                    "occurred_on": day,
                    "quantity": consumed,
                    "channel": None,
                    "is_stockout_affected": latent > consumed,
                    "data_origin": pol.DATA_ORIGIN,
                }
            )
            if consumed > 0:
                movements.append((pair, ISSUE, -consumed, day, day))

            # 5-6. Trigger, after consumption, every day, only with a preferred relation.
            relation = state.ordering
            if relation is None:
                continue
            first_of_window = _window_start(position, window)
            recent = (
                state.prefix[first_of_window + window] - state.prefix[first_of_window]
            )
            threshold = reorder_threshold(
                recent, window, relation.agreed_lead_time_days
            )
            if state.on_hand + state.on_order > threshold:
                continue
            quantity = order_quantity(
                recent, window, coverage, relation.moq, relation.order_multiple
            )
            if quantity is None:
                continue  # raw_need <= 0: no order (V1-06 guard)

            expected_on = day + _dt.timedelta(days=relation.agreed_lead_time_days)
            order = _Order(
                ref=len(orders),
                pair=pair,
                supplier_id=relation.supplier_id,
                issued_on=day,
                expected_on=expected_on,
                quantity=quantity,
                unit_cost_cents=relation.unit_cost_cents,
            )
            orders.append(order)
            state.on_order += quantity
            label = f"{pair[0]}:{pair[1]}"
            if pair not in timing:
                timing[pair] = DeterministicRandom(base, f"receipt-timing:{label}")
                splitting[pair] = DeterministicRandom(base, f"receipt-split:{label}")
            for receipt_day, receipt_quantity in _schedule_receipts(
                quantity,
                expected_on,
                by_supplier[relation.supplier_id],
                timing[pair],
                splitting[pair],
            ):
                state.scheduled.setdefault(receipt_day, []).append(
                    (order.ref, receipt_quantity)
                )
        day += _dt.timedelta(days=1)

    return _materialise(pairs, states, orders, consumption, movements, opening_profiles)


# ---------------------------------------------------------------------------------------
# Identifiers and rows - DT-038 sections 4 to 8
# ---------------------------------------------------------------------------------------


def _moment(day: _dt.date, movement_type: str) -> _dt.datetime:
    return _dt.datetime.combine(day, _CLOCK[movement_type])


def _materialise(
    pairs: Sequence[tuple[int, int]],
    states: dict[tuple[int, int], _PairState],
    orders: list[_Order],
    consumption: list[dict[str, Any]],
    movements: list[tuple[tuple[int, int], str, int, _dt.date, Any]],
    opening_profiles: dict[tuple[int, int], str],
) -> Inventory:
    """Assign identifiers in the six steps of `DT-038` section 8 and build the rows.

    Only causal entities are numbered here. Cancelled orders and their lines are created
    and numbered by Component 5, after this numbering is closed (`DT-039` section 5.2).
    """
    # Step 1 - causal orders. Step 2 - their lines (one per order, same sequence).
    ordered = sorted(
        orders,
        key=lambda o: (o.issued_on, o.supplier_id, o.pair[0], o.pair[1]),
    )
    order_id = {order.ref: position + 1 for position, order in enumerate(ordered)}

    # Step 3 - receipts inside the period, by (received_on, purchase_order_item_id).
    receipt_keys = sorted(
        (received_on, order_id[order.ref], order.ref, index)
        for order in orders
        for index, (received_on, _) in enumerate(order.received)
    )
    receipt_id = {
        (ref, index): position + 1
        for position, (_, _, ref, index) in enumerate(receipt_keys)
    }

    # Step 4 - consumption, by (product_id, location_id, occurred_on).
    consumption.sort(
        key=lambda row: (row["product_id"], row["location_id"], row["occurred_on"])
    )
    consumption_id: dict[tuple[tuple[int, int], _dt.date], int] = {}
    for position, row in enumerate(consumption):
        row["id"] = position + 1
        consumption_id[
            ((row["product_id"], row["location_id"]), row["occurred_on"])
        ] = (position + 1)

    # Step 5 - movements, by (product, location, occurred_at, type rank, reference_id).
    movement_rows = []
    for pair, movement_type, quantity, day, reference in movements:
        if movement_type == ADJUSTMENT:
            reference_type, reference_id, reason = (
                INITIAL_INVENTORY,
                None,
                OPENING_BALANCE,
            )
        elif movement_type == RECEIPT:
            reference_type, reference_id, reason = (
                PURCHASE_ORDER_RECEIPT,
                receipt_id[reference],
                None,
            )
        else:
            reference_type, reference_id, reason = (
                CONSUMPTION_REFERENCE,
                consumption_id[(pair, reference)],
                None,
            )
        moment = _moment(day, movement_type)
        movement_rows.append(
            {
                "product_id": pair[0],
                "location_id": pair[1],
                "movement_type": movement_type,
                "quantity": quantity,
                "occurred_at": moment,
                "recorded_at": moment,
                "reference_type": reference_type,
                "reference_id": reference_id,
                "reason_code": reason,
                "data_origin": pol.DATA_ORIGIN,
                "created_by": None,
            }
        )
    movement_rows.sort(
        key=lambda row: (
            row["product_id"],
            row["location_id"],
            row["occurred_at"],
            _TYPE_RANK[row["movement_type"]],
            row["reference_id"] or 0,
        )
    )
    for position, row in enumerate(movement_rows):
        row["id"] = position + 1

    # Orders handed to Component 5.
    simulated = []
    for order in ordered:
        oid = order_id[order.ref]
        receipts = tuple(
            sorted(
                (
                    SimulatedReceipt(
                        id=receipt_id[(order.ref, index)],
                        purchase_order_item_id=oid,
                        received_on=received_on,
                        quantity=quantity,
                    )
                    for index, (received_on, quantity) in enumerate(order.received)
                ),
                key=lambda receipt: (receipt.received_on, receipt.id),
            )
        )
        received = sum(receipt.quantity for receipt in receipts)
        if received == 0:
            status, closed_on = STATUS_ISSUED, None
        elif received < order.quantity:
            status, closed_on = STATUS_PARTIALLY_RECEIVED, None
        else:
            status, closed_on = STATUS_RECEIVED, receipts[-1].received_on
        simulated.append(
            SimulatedOrder(
                id=oid,
                supplier_id=order.supplier_id,
                location_id=order.pair[1],
                issued_on=order.issued_on,
                expected_on=order.expected_on,
                closed_on=closed_on,
                status=status,
                line=SimulatedOrderLine(
                    id=oid,
                    purchase_order_id=oid,
                    product_id=order.pair[0],
                    quantity_ordered=order.quantity,
                    quantity_received=received,
                    unit_cost_cents=order.unit_cost_cents,
                ),
                receipts=receipts,
            )
        )

    # Step 6 - the final snapshot, one row per pair.
    last_movement: dict[tuple[int, int], _dt.datetime] = {}
    for row in movement_rows:
        last_movement[(row["product_id"], row["location_id"])] = row["occurred_at"]
    inventory_rows = []
    for position, pair in enumerate(sorted(pairs)):
        inventory_rows.append(
            {
                "id": position + 1,
                "product_id": pair[0],
                "location_id": pair[1],
                "quantity_on_hand": states[pair].on_hand,
                "quantity_reserved": 0,
                "quantity_in_transit": states[pair].on_order,
                "last_movement_at": last_movement.get(pair),
                "updated_at": None,
                "data_origin": pol.DATA_ORIGIN,
            }
        )

    result = Inventory(
        consumption=consumption,
        movements=movement_rows,
        inventory=inventory_rows,
        simulation=SimulationResult(orders=tuple(simulated)),
        opening_profiles=opening_profiles,
    )
    _check_inventory(result)
    return result


def _check_inventory(result: Inventory) -> None:
    """Restate the invariants of `DT-038` on the rows about to be written.

    Every problem is collected; nothing is written if any is found.
    """
    problems = []
    balance: dict[tuple[int, int], int] = {}
    for row in result.movements:
        pair = (row["product_id"], row["location_id"])
        if row["quantity"] == 0:
            problems.append(f"movement {row['id']} has quantity 0 (docs/04 §3.7)")
        balance[pair] = balance.get(pair, 0) + row["quantity"]
        if balance[pair] < 0:
            problems.append(f"stock of {pair} goes negative (V1-13)")
    for row in result.inventory:
        pair = (row["product_id"], row["location_id"])
        if balance.get(pair, 0) != row["quantity_on_hand"]:
            problems.append(f"inventory.csv of {pair} is not the sum of its movements")
    in_transit: dict[tuple[int, int], int] = {}
    for order in result.simulation.orders:
        line = order.line
        if line.quantity_ordered <= 0:
            problems.append(
                f"order {order.id} has quantity_ordered <= 0 (docs/04 §3.10)"
            )
        if line.quantity_received > line.quantity_ordered:
            problems.append(f"order {order.id} is over-received (V1-12)")
        if any(receipt.quantity <= 0 for receipt in order.receipts):
            problems.append(f"order {order.id} has a receipt of zero units")
        if order.status != STATUS_RECEIVED:
            pair = (line.product_id, order.location_id)
            in_transit[pair] = (
                in_transit.get(pair, 0) + line.quantity_ordered - line.quantity_received
            )
    for row in result.inventory:
        pair = (row["product_id"], row["location_id"])
        if in_transit.get(pair, 0) != row["quantity_in_transit"]:
            problems.append(f"quantity_in_transit of {pair} does not match its orders")
    if problems:
        raise pol.GeneratorError(problems)


# ---------------------------------------------------------------------------------------
# Writing - into the directory received, never into a default (DT-040)
# ---------------------------------------------------------------------------------------


def generate(
    config: DatasetConfig,
    output_dir: Path | str,
    profiles: Sequence[SupplierProfile],
) -> tuple[dict[str, Any], SimulationResult]:
    """Simulate stock and write the three files of Component 4 into ``output_dir``.

    ``output_dir`` is **required**: it is the workspace of the run (`DT-040`), which
    already holds the output of Components 2 and 3. This function never writes to
    ``data/synthetic/output/`` on its own, and publishing is not its business.

    Returns:
        The extended manifest, already written, and the :class:`SimulationResult` that
        Component 5 will materialise.

    Raises:
        GeneratorError: if a precondition or an invariant fails. Nothing is written in
            that case - every check runs before the first file is opened.
        ValueError: if the manifest already records this component or its files (a
            second run into the same directory). Nothing is written in that case either.
    """
    target = Path(output_dir)
    inventory = build_inventory(config, target, profiles)

    manifest_path = target / MANIFEST_FILE
    if not manifest_path.is_file():
        raise pol.GeneratorError(
            [
                f"{MANIFEST_FILE} not found in {target}; Components 2 and 3 write it first"
            ]
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Render first, extend the manifest second, write last: a manifest that already
    # holds this component (a second run into the same directory) is rejected by
    # ``extend_manifest`` before any file of this component is touched.
    texts: list[tuple[str, str]] = []
    entries = []
    for filename, entity, columns, rows in (
        (CONSUMPTION_FILE, "Consumption", CONSUMPTION_COLUMNS, inventory.consumption),
        (INVENTORY_FILE, "Inventory", INVENTORY_COLUMNS, inventory.inventory),
        (MOVEMENTS_FILE, "InventoryMovement", MOVEMENT_COLUMNS, inventory.movements),
    ):
        text = render_csv(columns, [[row[name] for name in columns] for row in rows])
        texts.append((filename, text))
        entries.append(file_entry(filename, entity, len(rows), text))

    manifest = extend_manifest(
        manifest,
        component={
            "name": COMPONENT_INVENTORY,
            "version": INVENTORY_VERSION,
            "sub_seed": sub_seed(config.seed, COMPONENT_INVENTORY),
        },
        files=entries,
    )
    for filename, text in texts:
        # Same bytes as ``writer.write_csv``: UTF-8 without BOM, LF kept on every OS.
        (target / filename).write_text(text, encoding="utf-8", newline="")
    write_manifest(manifest_path, manifest)
    return manifest, inventory.simulation
