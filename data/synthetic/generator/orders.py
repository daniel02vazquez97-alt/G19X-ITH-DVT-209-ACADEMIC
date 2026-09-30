"""Component 5 - Purchase Order Generator: materialises orders, lines and receipts.

Phase 1 - Data.

    SimulationResult (Component 4, in memory) + products.csv
        -> build_orders() -> Orders -> generate()
            -> purchase_orders.csv, purchase_order_items.csv, purchase_order_receipts.csv

**A materialiser, not a simulator** (`DT-039`). Every causal fact - which orders exist,
their supplier, dates, quantities, receipts, status and identifiers - was decided by
Component 4 and is written here as received. This module recomputes no ``s``, ``Q``,
demand, lead time, delay, split or date; it does not import Component 4 at run time and
does not use the ``inventory`` random stream. Component 4's types appear only in
annotations.

What it adds, and only this, each with its authority:

* **``order_number``** of every order (`DT-039` section 6, decision A2): a pure function
  of the ``id`` and of the highest ``id`` of the run.
* **Synthetic ``CANCELLED`` orders** (`DT-039` section 5.2): twins of causal orders,
  chosen from a universe of eligible templates that is **filtered first** - the rule of
  point 1, closed on 2026-09-27 (D-01, option A) - and only then counted (``K``),
  checked (B2) and sampled (``cancelled-selection``). A twin's ``closed_at`` is
  ``issued_at + ORDERS_CANCELLED_CLOSE_LAG_DAYS``, never clipped.
* **Identifiers of the twins and their lines only** (`DT-039` sections 5.2 and 7),
  continuing Component 4's sequences. Nothing received is renumbered or reordered.

**Publication is not its business** (`DT-040`): it writes into the directory it is given
and has **no default output directory**.
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence

from ..config.config import DatasetConfig
from . import policies as pol
from .rng import COMPONENT_ORDERS, DeterministicRandom, sub_seed
from .writer import (
    ORDERS_VERSION,
    extend_manifest,
    file_entry,
    format_cents,
    render_csv,
    write_manifest,
)

if TYPE_CHECKING:  # annotations only: C5 never calls into C4 (DT-039 section 1)
    from .inventory import SimulatedOrder, SimulationResult

__all__ = [
    "PURCHASE_ORDERS_FILE",
    "PURCHASE_ORDER_ITEMS_FILE",
    "PURCHASE_ORDER_RECEIPTS_FILE",
    "PURCHASE_ORDER_COLUMNS",
    "PURCHASE_ORDER_ITEM_COLUMNS",
    "PURCHASE_ORDER_RECEIPT_COLUMNS",
    "CancelledOrder",
    "Orders",
    "planned_close",
    "is_eligible_for_cancel",
    "cancelled_target",
    "order_number_width",
    "format_order_number",
    "build_orders",
    "generate",
]

# ---------------------------------------------------------------------------------------
# Files and column contracts - DT-039 sections 2 to 4
# ---------------------------------------------------------------------------------------

PURCHASE_ORDERS_FILE = "purchase_orders.csv"
PURCHASE_ORDER_ITEMS_FILE = "purchase_order_items.csv"
PURCHASE_ORDER_RECEIPTS_FILE = "purchase_order_receipts.csv"
MANIFEST_FILE = "manifest.json"

#: Read for ``valid_to`` only: the eligibility of `DT-039` section 5.2, point 1.
PRODUCTS_FILE = "products.csv"

#: `DT-039` section 2.
PURCHASE_ORDER_COLUMNS = (
    "id",
    "order_number",
    "supplier_id",
    "location_id",
    "status",
    "issued_at",
    "expected_at",
    "closed_at",
    "currency",
    "total_amount",
    "created_by",
    "created_at",
    "updated_at",
    "data_origin",
)

#: `DT-039` section 3.
PURCHASE_ORDER_ITEM_COLUMNS = (
    "id",
    "purchase_order_id",
    "product_id",
    "quantity_ordered",
    "quantity_received",
    "unit_cost",
    "expected_at",
    "data_origin",
)

#: `DT-039` section 4.
PURCHASE_ORDER_RECEIPT_COLUMNS = (
    "id",
    "purchase_order_item_id",
    "received_at",
    "quantity_received",
    "quality_rejected",
    "data_origin",
)

STATUS_ISSUED = "ISSUED"
STATUS_PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
STATUS_RECEIVED = "RECEIVED"
STATUS_CANCELLED = "CANCELLED"

#: The only states Component 4 emits (`DT-038` section 10). A causal order in any other
#: state is not a causal order: the input is inconsistent and C5 refuses it.
CAUSAL_STATUSES = (STATUS_ISSUED, STATUS_PARTIALLY_RECEIVED, STATUS_RECEIVED)

#: `DT-039` section 6.
ORDER_NUMBER_PREFIX = "PO-"
ORDER_NUMBER_MIN_WIDTH = 6

#: `DT-039` section 5.2, point 3.
SELECTION_STREAM = "cancelled-selection"

_MIDNIGHT_UTC = _dt.time(0, 0, 0, tzinfo=_dt.timezone.utc)


# ---------------------------------------------------------------------------------------
# The rules of DT-039, as pure functions
# ---------------------------------------------------------------------------------------


def planned_close(issued_on: _dt.date) -> _dt.date:
    """``issued_on + ORDERS_CANCELLED_CLOSE_LAG_DAYS``: the ``closed_at`` of a twin.

    `DT-039` section 5.2, points 1 and 4. The same value decides eligibility and becomes
    the twin's ``closed_at``. It takes no ``end_date`` and no ``valid_to`` on purpose:
    **nothing can clip it**.
    """
    return issued_on + _dt.timedelta(days=pol.ORDERS_CANCELLED_CLOSE_LAG_DAYS)


def is_eligible_for_cancel(
    issued_on: _dt.date, valid_to: _dt.date | None, end_date: _dt.date
) -> bool:
    """`DT-039` section 5.2, point 1, for one **causal** order.

    ``planned_close < end_date`` (strict: the period is ``[start_date, end_date)``) and
    ``valid_to`` is null or ``planned_close <= valid_to`` (the validity interval is
    closed, `DT-027`). The first condition of the rule - being a causal order - is met
    by construction: the universe is built from ``SimulationResult.orders`` alone,
    before any twin exists.
    """
    close = planned_close(issued_on)
    return close < end_date and (valid_to is None or close <= valid_to)


def cancelled_target(causal_orders: int) -> int:
    """``K = max(1, ceil(N x ORDERS_CANCELLED_PERMILLE / 1000))`` - `DT-039` §5.2 point 2.

    ``N`` is the number of **causal** orders, as the contract says; the cap by the number
    of eligible templates is applied by the caller. Integer arithmetic, no floats.
    """
    return max(1, -(-causal_orders * pol.ORDERS_CANCELLED_PERMILLE // 1000))


def order_number_width(highest_id: int) -> int:
    """``w = max(6, digits of the highest id of the run)`` - `DT-039` section 6."""
    return max(ORDER_NUMBER_MIN_WIDTH, len(str(highest_id)))


def format_order_number(order_id: int, width: int) -> str:
    """``"PO-" + str(id).zfill(w)`` - `DT-039` section 6. Never renumbers the id."""
    return ORDER_NUMBER_PREFIX + str(order_id).zfill(width)


# ---------------------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CancelledOrder:
    """A synthetic ``CANCELLED`` twin (`DT-039` section 5.2, point 4).

    Every business field is copied from its template; ``closed_on`` is
    :func:`planned_close` of the copied ``issued_on``; the line has
    ``quantity_received = 0`` and there are no receipts.
    """

    id: int
    line_id: int
    template_id: int
    supplier_id: int
    location_id: int
    product_id: int
    issued_on: _dt.date
    expected_on: _dt.date
    closed_on: _dt.date
    quantity_ordered: int
    unit_cost_cents: int


@dataclass(frozen=True)
class Orders:
    """Everything Component 5 produces, before it is written.

    ``candidates`` (ids of the eligible universe, in canonical order), ``target`` (``K``
    before the cap) and ``cancelled`` are kept so that the order of operations of
    `DT-039` section 5.2 can be inspected and tested.
    """

    purchase_orders: list[dict[str, Any]]
    items: list[dict[str, Any]]
    receipts: list[dict[str, Any]]
    candidates: tuple[int, ...]
    target: int
    cancelled: tuple[CancelledOrder, ...]
    width: int


# ---------------------------------------------------------------------------------------
# Inputs and their validation
# ---------------------------------------------------------------------------------------


def _read_valid_to(input_dir: Path) -> dict[int, _dt.date | None]:
    path = input_dir / PRODUCTS_FILE
    if not path.is_file():
        raise pol.GeneratorError(
            [
                f"{PRODUCTS_FILE} not found in {input_dir}; Component 5 reads the "
                "validity of each product from Component 2's output"
            ]
        )
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in ("id", "valid_to") if c not in (reader.fieldnames or [])]
        if missing:
            raise pol.GeneratorError(
                [f"{PRODUCTS_FILE} is missing the column(s) {missing}"]
            )
        valid_to: dict[int, _dt.date | None] = {}
        for row in reader:
            try:
                valid_to[int(row["id"])] = (
                    _dt.date.fromisoformat(row["valid_to"]) if row["valid_to"] else None
                )
            except ValueError as exc:
                raise pol.GeneratorError(
                    [f"products.valid_to is not an ISO date: {row['valid_to']!r}"]
                ) from exc
    return valid_to


def _check_simulation(
    orders: Sequence[SimulatedOrder],
    valid_to: dict[int, _dt.date | None],
    start: _dt.date,
    end: _dt.date,
) -> None:
    """Refuse an inconsistent ``SimulationResult`` before writing anything.

    Verifies what `DT-038` sections 8 to 12 promise; decides nothing. Every problem is
    reported at once.
    """
    problems: list[str] = []
    expected_ids = list(range(1, len(orders) + 1))
    if [o.id for o in orders] != expected_ids:
        problems.append("causal order ids are not 1..N in canonical order (DT-038 §8)")
    keys = [
        (o.issued_on, o.supplier_id, o.line.product_id, o.location_id) for o in orders
    ]
    if keys != sorted(keys) or len(set(keys)) != len(keys):
        problems.append(
            "causal orders are not in the canonical order of DT-038 §8, or repeat a key"
        )
    receipt_ids: set[int] = set()
    for order in orders:
        name = f"causal order {order.id}"
        line = order.line
        if order.status not in CAUSAL_STATUSES:
            problems.append(f"{name}: status {order.status!r} is not a causal state")
        if line.id != order.id or line.purchase_order_id != order.id:
            problems.append(f"{name}: its line must share its id (DT-038 §8)")
        if line.product_id not in valid_to:
            problems.append(f"{name}: product {line.product_id} is not in products.csv")
        elif (
            valid_to[line.product_id] is not None
            and order.issued_on > valid_to[line.product_id]
        ):
            problems.append(f"{name}: issued after its product's valid_to (DT-027)")
        if not start <= order.issued_on < end:
            problems.append(f"{name}: issued_on {order.issued_on} outside the period")
        if line.quantity_ordered <= 0:
            problems.append(f"{name}: quantity_ordered must be > 0 (docs/04 §3.10)")
        received = 0
        for receipt in order.receipts:
            if receipt.id in receipt_ids:
                problems.append(f"receipt {receipt.id} appears twice")
            receipt_ids.add(receipt.id)
            if receipt.purchase_order_item_id != line.id:
                problems.append(
                    f"receipt {receipt.id} does not belong to {name}'s line"
                )
            if receipt.quantity <= 0:
                problems.append(f"receipt {receipt.id}: quantity must be > 0")
            if not order.issued_on <= receipt.received_on < end:
                problems.append(f"receipt {receipt.id}: received_on outside the period")
            received += receipt.quantity
        if received != line.quantity_received:
            problems.append(f"{name}: quantity_received is not the sum of its receipts")
        if received > line.quantity_ordered:
            problems.append(f"{name}: over-received (V1-12)")
        if received == 0:
            state, closed = STATUS_ISSUED, None
        elif received < line.quantity_ordered:
            state, closed = STATUS_PARTIALLY_RECEIVED, None
        else:
            state, closed = STATUS_RECEIVED, max(r.received_on for r in order.receipts)
        if order.status in CAUSAL_STATUSES and (order.status, order.closed_on) != (
            state,
            closed,
        ):
            problems.append(f"{name}: status and closed_on disagree with its receipts")
    if problems:
        raise pol.GeneratorError(problems)


# ---------------------------------------------------------------------------------------
# The CANCELLED policy - DT-039 section 5.2, in its four steps
# ---------------------------------------------------------------------------------------


def _eligible_universe(
    orders: Sequence[SimulatedOrder],
    valid_to: dict[int, _dt.date | None],
    end: _dt.date,
) -> list[SimulatedOrder]:
    """Point 1: the whole universe of templates, computed **before** anything else.

    Canonical order is the order received (ids ascending). An order outside this list is
    never counted in the cap, never checked by B2 and never sampled.
    """
    return [
        order
        for order in orders
        if is_eligible_for_cancel(order.issued_on, valid_to[order.line.product_id], end)
    ]


def _select_templates(
    universe: Sequence[SimulatedOrder], target: int, seed: int
) -> list[SimulatedOrder]:
    """Points 2 (cap and B2) and 3 (``cancelled-selection``), on the filtered universe."""
    if target > 0 and not universe:
        raise pol.GeneratorError(
            [
                f"B2 (DT-039 §5.2): {target} cancelled order(s) required and no causal "
                "order is eligible as a template; the run fails and nothing is published "
                "(DT-040)"
            ]
        )
    emitted = min(target, len(universe))
    order = DeterministicRandom(
        sub_seed(seed, COMPONENT_ORDERS), SELECTION_STREAM
    ).permutation(len(universe))
    return [universe[position] for position in order[:emitted]]


def _twins(
    templates: Sequence[SimulatedOrder], first_order_id: int, first_line_id: int
) -> list[CancelledOrder]:
    """Point 4 and the identifiers of `DT-039` section 5.2: copy, close, number."""
    ordered = sorted(
        templates,
        key=lambda o: (o.issued_on, o.supplier_id, o.line.product_id, o.location_id),
    )
    return [
        CancelledOrder(
            id=first_order_id + position,
            line_id=first_line_id + position,
            template_id=template.id,
            supplier_id=template.supplier_id,
            location_id=template.location_id,
            product_id=template.line.product_id,
            issued_on=template.issued_on,
            expected_on=template.expected_on,
            closed_on=planned_close(template.issued_on),
            quantity_ordered=template.line.quantity_ordered,
            unit_cost_cents=template.line.unit_cost_cents,
        )
        for position, template in enumerate(ordered)
    ]


# ---------------------------------------------------------------------------------------
# Rows
# ---------------------------------------------------------------------------------------


def _moment(day: _dt.date | None) -> _dt.datetime | None:
    """The day at ``T00:00:00Z`` (`DT-036` section 9); ``None`` stays empty."""
    return None if day is None else _dt.datetime.combine(day, _MIDNIGHT_UTC)


def _order_row(
    order_id: int,
    width: int,
    supplier_id: int,
    location_id: int,
    status: str,
    issued_on: _dt.date,
    expected_on: _dt.date,
    closed_on: _dt.date | None,
) -> dict[str, Any]:
    return {
        "id": order_id,
        "order_number": format_order_number(order_id, width),
        "supplier_id": supplier_id,
        "location_id": location_id,
        "status": status,
        "issued_at": _moment(issued_on),
        "expected_at": _moment(expected_on),  # copied from C4, never recomputed
        "closed_at": _moment(closed_on),
        "currency": None,
        "total_amount": None,
        "created_by": None,
        "created_at": None,
        "updated_at": None,
        "data_origin": pol.DATA_ORIGIN,
    }


def _item_row(
    item_id: int,
    order_id: int,
    product_id: int,
    ordered: int,
    received: int,
    unit_cost_cents: int,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "purchase_order_id": order_id,
        "product_id": product_id,
        "quantity_ordered": ordered,
        "quantity_received": received,
        "unit_cost": format_cents(unit_cost_cents),
        "expected_at": None,  # docs/04 §3.10: only if it differs from the header
        "data_origin": pol.DATA_ORIGIN,
    }


def build_orders(
    config: DatasetConfig,
    input_dir: Path | str,
    simulation: SimulationResult,
) -> Orders:
    """Materialise Component 4's orders and add the synthetic ``CANCELLED`` twins.

    Reads ``products.csv`` from ``input_dir`` (for ``valid_to``); writes nothing.

    Raises:
        GeneratorError: if the ``SimulationResult`` is inconsistent, if B2 fails (no
            eligible template), or if an output invariant fails. Every problem is
            reported at once and nothing is built.
    """
    start, end = config.period.start_date, config.period.end_date
    valid_to = _read_valid_to(Path(input_dir))
    causal = list(simulation.orders)
    _check_simulation(causal, valid_to, start, end)

    # DT-039 section 5.2: filter -> K -> B2 -> selection -> twins.
    universe = _eligible_universe(causal, valid_to, end)
    target = cancelled_target(len(causal))
    templates = _select_templates(universe, target, config.seed)
    last_order_id = max((o.id for o in causal), default=0)
    last_line_id = max((o.line.id for o in causal), default=0)
    twins = _twins(templates, last_order_id + 1, last_line_id + 1)

    highest = max([last_order_id] + [t.id for t in twins])
    width = order_number_width(highest)

    purchase_orders = [
        _order_row(
            o.id,
            width,
            o.supplier_id,
            o.location_id,
            o.status,
            o.issued_on,
            o.expected_on,
            o.closed_on,
        )
        for o in causal
    ] + [
        _order_row(
            t.id,
            width,
            t.supplier_id,
            t.location_id,
            STATUS_CANCELLED,
            t.issued_on,
            t.expected_on,
            t.closed_on,
        )
        for t in twins
    ]
    purchase_orders.sort(key=lambda row: row["order_number"])

    items = [
        _item_row(
            o.line.id,
            o.id,
            o.line.product_id,
            o.line.quantity_ordered,
            o.line.quantity_received,
            o.line.unit_cost_cents,
        )
        for o in causal
    ] + [
        _item_row(
            t.line_id, t.id, t.product_id, t.quantity_ordered, 0, t.unit_cost_cents
        )
        for t in twins
    ]
    items.sort(key=lambda row: (row["purchase_order_id"], row["product_id"]))

    receipts = [
        {
            "id": r.id,
            "purchase_order_item_id": r.purchase_order_item_id,
            "received_at": _moment(r.received_on),
            "quantity_received": r.quantity,
            "quality_rejected": None,
            "data_origin": pol.DATA_ORIGIN,
        }
        for o in causal
        for r in o.receipts
    ]
    receipts.sort(key=lambda row: (row["purchase_order_item_id"], row["received_at"]))

    result = Orders(
        purchase_orders=purchase_orders,
        items=items,
        receipts=receipts,
        candidates=tuple(o.id for o in universe),
        target=target,
        cancelled=tuple(twins),
        width=width,
    )
    _check_orders(result, valid_to, end)
    return result


def _check_orders(
    result: Orders, valid_to: dict[int, _dt.date | None], end: _dt.date
) -> None:
    """Restate the invariants of `DT-039` on the rows about to be written.

    An invariant check, not a filter: it never removes or adjusts a row. If it fails the
    generator has a defect, and the run stops.
    """
    problems: list[str] = []
    orders = {row["id"]: row for row in result.purchase_orders}
    if len(orders) != len(result.purchase_orders):
        problems.append("purchase_orders.id is not unique")
    numbers = [row["order_number"] for row in result.purchase_orders]
    if len(set(numbers)) != len(numbers):
        problems.append("order_number is not unique")
    if numbers != sorted(numbers) or [
        r["id"] for r in result.purchase_orders
    ] != sorted(orders):
        problems.append("order_number order and id order disagree (DT-039 §6)")
    items = {row["id"]: row for row in result.items}
    if len(items) != len(result.items):
        problems.append("purchase_order_items.id is not unique")
    per_order: dict[int, int] = {}
    for row in result.items:
        if row["purchase_order_id"] not in orders:
            problems.append(f"item {row['id']} references a missing order")
        per_order[row["purchase_order_id"]] = (
            per_order.get(row["purchase_order_id"], 0) + 1
        )
    if any(count != 1 for count in per_order.values()) or set(per_order) != set(orders):
        problems.append("every order must have exactly one line (DT-039 §8)")
    receipt_ids = [row["id"] for row in result.receipts]
    if len(set(receipt_ids)) != len(receipt_ids):
        problems.append("purchase_order_receipts.id is not unique")
    for row in result.receipts:
        if row["purchase_order_item_id"] not in items:
            problems.append(f"receipt {row['id']} references a missing line")
    for twin in result.cancelled:
        if twin.template_id not in result.candidates:
            problems.append(f"cancelled order {twin.id} has an ineligible template")
        if twin.closed_on != twin.issued_on + _dt.timedelta(
            days=pol.ORDERS_CANCELLED_CLOSE_LAG_DAYS
        ):
            problems.append(
                f"cancelled order {twin.id}: closed_at is not issued_at + lag"
            )
        product_valid_to = valid_to[twin.product_id]
        if not twin.closed_on < end or (
            product_valid_to is not None and twin.closed_on > product_valid_to
        ):
            problems.append(
                f"cancelled order {twin.id}: closed_at {twin.closed_on} outside the "
                "period or the product's validity (DT-039 §5.2, DT-027)"
            )
        line = items.get(twin.line_id)
        if line is None or line["purchase_order_id"] != twin.id:
            problems.append(f"cancelled order {twin.id}: its line is missing")
        elif line["quantity_received"] != 0 or any(
            row["purchase_order_item_id"] == twin.line_id for row in result.receipts
        ):
            problems.append(f"cancelled order {twin.id}: its line has receipts")
    if problems:
        raise pol.GeneratorError(problems)


# ---------------------------------------------------------------------------------------
# Writing - into the directory received, never into a default (DT-039 §11, DT-040)
# ---------------------------------------------------------------------------------------


def generate(
    config: DatasetConfig,
    output_dir: Path | str,
    simulation: SimulationResult,
) -> dict[str, Any]:
    """Write the three files of Component 5 into ``output_dir`` and extend the manifest.

    ``output_dir`` is **required**: the workspace of the run, which already holds the
    output of Components 2 to 4. Nothing is written if anything fails - B2 included
    (`DT-039` section 11): every check, the rendering and the manifest extension happen
    before the first file is opened.

    Returns:
        The extended manifest, already written.

    Raises:
        GeneratorError: see :func:`build_orders`; also if ``manifest.json`` is missing.
        ValueError: if the manifest already records this component or its files.
    """
    target = Path(output_dir)
    orders = build_orders(config, target, simulation)

    manifest_path = target / MANIFEST_FILE
    if not manifest_path.is_file():
        raise pol.GeneratorError(
            [
                f"{MANIFEST_FILE} not found in {target}; earlier components write it first"
            ]
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    texts: list[tuple[str, str]] = []
    entries = []
    for filename, entity, columns, rows in (
        (
            PURCHASE_ORDERS_FILE,
            "PurchaseOrder",
            PURCHASE_ORDER_COLUMNS,
            orders.purchase_orders,
        ),
        (
            PURCHASE_ORDER_ITEMS_FILE,
            "PurchaseOrderItem",
            PURCHASE_ORDER_ITEM_COLUMNS,
            orders.items,
        ),
        (
            PURCHASE_ORDER_RECEIPTS_FILE,
            "PurchaseOrderReceipt",
            PURCHASE_ORDER_RECEIPT_COLUMNS,
            orders.receipts,
        ),
    ):
        text = render_csv(columns, [[row[name] for name in columns] for row in rows])
        texts.append((filename, text))
        entries.append(file_entry(filename, entity, len(rows), text))

    manifest = extend_manifest(
        manifest,
        component={
            "name": COMPONENT_ORDERS,
            "version": ORDERS_VERSION,
            "sub_seed": sub_seed(config.seed, COMPONENT_ORDERS),
        },
        files=entries,
    )
    for filename, text in texts:
        # Same bytes as ``writer.write_csv``: UTF-8 without BOM, LF kept on every OS.
        (target / filename).write_text(text, encoding="utf-8", newline="")
    write_manifest(manifest_path, manifest)
    return manifest
