"""Tests for Component 5: the Purchase Order Generator.

Run from the repository root::

    python3 -m unittest discover -s data/synthetic/tests -t .

Standard library ``unittest``, like Components 1 to 4 (`docs/13-testing.md`).

Scope: `DT-039` - materialising Component 4's orders, lines and receipts without
recomputing anything, forming ``order_number``, and the synthetic ``CANCELLED`` twins of
section 5.2 with the eligibility rule closed on 2026-09-27 (D-01, option A).

Two kinds of input:

* **hand-made ``SimulationResult`` objects**, built directly from Component 4's
  dataclasses, to pin each rule down with dates chosen for it;
* **the real pipeline** C2 -> C3 -> C4 -> C5, small and full scale, checked by an
  independent audit (:func:`audit`) that reads only the written files.

The eligibility rule is checked against :func:`expected_eligibility` of
``test_cancelled_eligibility.py``, the executable specification written when D-01 was
closed, so the implementation and the contract cannot drift apart unnoticed.
"""

from __future__ import annotations

import ast
import collections
import dataclasses
import datetime as _dt
import inspect
import json
import math
import re
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

from data.synthetic.generator import orders as od
from data.synthetic.generator import policies as pol
from data.synthetic.generator.catalog import DEFAULT_OUTPUT_DIR
from data.synthetic.generator.inventory import (
    SimulatedOrder,
    SimulatedOrderLine,
    SimulatedReceipt,
    SimulationResult,
)
from data.synthetic.generator.inventory import generate as generate_inventory
from data.synthetic.generator.orders import (
    PURCHASE_ORDER_COLUMNS,
    PURCHASE_ORDER_ITEM_COLUMNS,
    PURCHASE_ORDER_ITEMS_FILE,
    PURCHASE_ORDER_RECEIPT_COLUMNS,
    PURCHASE_ORDER_RECEIPTS_FILE,
    PURCHASE_ORDERS_FILE,
    build_orders,
    cancelled_target,
    format_order_number,
    generate,
    is_eligible_for_cancel,
    order_number_width,
    planned_close,
)
from data.synthetic.generator.rng import COMPONENT_ORDERS, DeterministicRandom, sub_seed
from data.synthetic.generator.writer import (
    GENERATOR_VERSION,
    ORDERS_VERSION,
    build_manifest,
    write_manifest,
)
from data.synthetic.tests.test_cancelled_eligibility import (
    expected_eligibility,
    expected_k,
)
from data.synthetic.tests.test_inventory import (
    FIXED_TIME,
    REPO_ROOT,
    SMALL,
    START,
    build_pipeline,
    digest,
    dt037_profiles,
    make_config,
    make_profile,
    read_rows,
    run_handmade,
    tree_digest,
)

DAY = _dt.timedelta(days=1)
PERIOD_START = _dt.date(2025, 1, 1)
PERIOD_END = _dt.date(2025, 7, 1)
CONFIG = make_config(
    period={"start_date": PERIOD_START.isoformat(), "end_date": PERIOD_END.isoformat()}
)


# =======================================================================================
# Hand-made inputs
# =======================================================================================


def causal_order(
    order_id: int,
    issued_on: _dt.date,
    product_id: int,
    *,
    supplier_id: int = 1,
    location_id: int = 1,
    quantity: int = 10,
    lead: int = 5,
    expected_on: _dt.date | None = None,
    receipts: tuple[tuple[int, _dt.date, int], ...] = (),
    unit_cost_cents: int = 1234,
) -> SimulatedOrder:
    """A causal order as Component 4 hands it over, status derived from its receipts."""
    received = sum(q for _, _, q in receipts)
    if received == 0:
        status, closed = "ISSUED", None
    elif received < quantity:
        status, closed = "PARTIALLY_RECEIVED", None
    else:
        status, closed = "RECEIVED", max(d for _, d, _ in receipts)
    return SimulatedOrder(
        id=order_id,
        supplier_id=supplier_id,
        location_id=location_id,
        issued_on=issued_on,
        expected_on=expected_on or issued_on + _dt.timedelta(days=lead),
        closed_on=closed,
        status=status,
        line=SimulatedOrderLine(
            id=order_id,
            purchase_order_id=order_id,
            product_id=product_id,
            quantity_ordered=quantity,
            quantity_received=received,
            unit_cost_cents=unit_cost_cents,
        ),
        receipts=tuple(
            SimulatedReceipt(rid, order_id, day, q) for rid, day, q in receipts
        ),
    )


def workspace(tmp: str, valid_to: dict[int, _dt.date | None]) -> Path:
    """``products.csv`` and an empty manifest: all Component 5 reads from disk."""
    directory = Path(tmp) / "work"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "products.csv").open("w", encoding="utf-8", newline="") as h:
        h.write("id,valid_from,valid_to\n")
        for product_id, end in sorted(valid_to.items()):
            h.write(f"{product_id},{PERIOD_START},{end or ''}\n")
    write_manifest(
        directory / "manifest.json",
        build_manifest(config=CONFIG, generated_at=FIXED_TIME, components=[], files=[]),
    )
    return directory


def many_orders(count: int, product_id: int = 1) -> list[SimulatedOrder]:
    """``count`` eligible causal orders of one product, one per day from the start."""
    return [
        causal_order(i + 1, PERIOD_START + i * DAY, product_id) for i in range(count)
    ]


# =======================================================================================
# The exact selection, recomputed independently - DT-039 section 5.2, points 1 to 3
# =======================================================================================


def expected_selection(
    simulation: SimulationResult,
    valid_to: dict[int, _dt.date | None],
    config,
) -> set[int]:
    """Ids of the causal orders that must serve as CANCELLED templates.

    Recomputed from the documented rules only - literal values, own date arithmetic,
    exact rational ``ceil`` - and **without calling any function of Component 5**, so
    that the check is not circular:

    1. universe: causal orders, in canonical (id) order, whose planned close
       ``issued_on + 1 day`` is ``< end_date`` and, when the product has a ``valid_to``,
       ``<= valid_to``;
    2. ``K = max(1, ceil(N x 20 / 1000))`` with ``N`` = causal orders, capped by the size
       of the universe;
    3. the first ``K`` positions of the permutation drawn from the stream
       ``cancelled-selection`` over ``sub_seed(seed, "orders")``, applied to the universe.
    """
    end = config.period.end_date
    universe = []
    for order in sorted(simulation.orders, key=lambda o: o.id):
        close = order.issued_on + _dt.timedelta(days=1)
        limit = valid_to[order.line.product_id]
        if close < end and (limit is None or close <= limit):
            universe.append(order.id)
    n = len(simulation.orders)
    k = max(1, math.ceil(Fraction(n * 20, 1000)))
    emitted = min(k, len(universe))
    permutation = DeterministicRandom(
        sub_seed(config.seed, "orders"), "cancelled-selection"
    ).permutation(len(universe))
    return {universe[position] for position in permutation[:emitted]}


# =======================================================================================
# The independent audit of the written files
# =======================================================================================


def audit(directory: Path, config, simulation: SimulationResult) -> list[str]:
    """Check the three files against `DT-039`, from the files and the input alone."""
    problems: list[str] = []
    end = config.period.end_date
    valid_to = {
        int(r["id"]): (_dt.date.fromisoformat(r["valid_to"]) if r["valid_to"] else None)
        for r in read_rows(directory, "products.csv")
    }
    orders = read_rows(directory, PURCHASE_ORDERS_FILE)
    items = read_rows(directory, PURCHASE_ORDER_ITEMS_FILE)
    receipts = read_rows(directory, PURCHASE_ORDER_RECEIPTS_FILE)
    causal = {o.id: o for o in simulation.orders}
    at = "{}T00:00:00Z".format

    # order_number: DT-039 section 6.
    highest = max(int(r["id"]) for r in orders) if orders else 0
    width = max(6, len(str(highest)))
    for row in orders:
        if row["order_number"] != f"PO-{int(row['id']):0{width}d}":
            problems.append(f"order {row['id']}: order_number {row['order_number']}")
    if [r["order_number"] for r in orders] != sorted(r["order_number"] for r in orders):
        problems.append("purchase_orders.csv is not sorted by order_number")
    if len({r["order_number"] for r in orders}) != len(orders):
        problems.append("order_number repeats")

    item_of = {int(r["purchase_order_id"]): r for r in items}
    if len(item_of) != len(items) or set(item_of) != {int(r["id"]) for r in orders}:
        problems.append("orders and lines are not one to one")

    # Causal orders: copied, never recomputed.
    for row in orders:
        oid = int(row["id"])
        if oid not in causal:
            continue
        o = causal[oid]
        expected = (
            str(o.supplier_id),
            str(o.location_id),
            o.status,
            at(o.issued_on),
            at(o.expected_on),
            at(o.closed_on) if o.closed_on else "",
        )
        got = (
            row["supplier_id"],
            row["location_id"],
            row["status"],
            row["issued_at"],
            row["expected_at"],
            row["closed_at"],
        )
        if got != expected:
            problems.append(f"causal order {oid} was not copied verbatim")
        item = item_of.get(oid)
        if item is None or (
            int(item["id"]),
            int(item["product_id"]),
            int(item["quantity_ordered"]),
            int(item["quantity_received"]),
            item["unit_cost"],
        ) != (
            o.line.id,
            o.line.product_id,
            o.line.quantity_ordered,
            o.line.quantity_received,
            f"{o.line.unit_cost_cents // 100}.{o.line.unit_cost_cents % 100:02d}",
        ):
            problems.append(f"line of causal order {oid} was not copied verbatim")

    # Receipts: exactly Component 4's, nothing added, nothing changed.
    expected_receipts = sorted(
        (r.id, r.purchase_order_item_id, at(r.received_on), r.quantity)
        for o in simulation.orders
        for r in o.receipts
    )
    got_receipts = sorted(
        (
            int(r["id"]),
            int(r["purchase_order_item_id"]),
            r["received_at"],
            int(r["quantity_received"]),
        )
        for r in receipts
    )
    if got_receipts != expected_receipts:
        problems.append("receipts differ from Component 4's")

    # CANCELLED twins: DT-039 section 5.2.
    cancelled = [r for r in orders if r["status"] == "CANCELLED"]
    eligible = [
        o
        for o in simulation.orders
        if expected_eligibility(o.issued_on, valid_to[o.line.product_id], end)
    ]
    wanted = min(expected_k(len(simulation.orders)), len(eligible))
    if len(cancelled) != wanted:
        problems.append(f"{len(cancelled)} cancelled orders, expected {wanted}")
    if sorted(int(r["id"]) for r in cancelled) != list(
        range(len(causal) + 1, len(causal) + 1 + len(cancelled))
    ):
        problems.append("cancelled ids do not continue Component 4's sequence")
    by_key = collections.defaultdict(list)
    for o in eligible:
        by_key[
            (
                o.supplier_id,
                o.location_id,
                at(o.issued_on),
                at(o.expected_on),
                o.line.product_id,
                o.line.quantity_ordered,
            )
        ].append(o)
    used = set()
    for row in cancelled:
        item = item_of[int(row["id"])]
        key = (
            int(row["supplier_id"]),
            int(row["location_id"]),
            row["issued_at"],
            row["expected_at"],
            int(item["product_id"]),
            int(item["quantity_ordered"]),
        )
        templates = [o for o in by_key.get(key, []) if o.id not in used]
        if not templates:
            problems.append(f"cancelled order {row['id']} has no eligible template")
            continue
        used.add(templates[0].id)
        issued = _dt.date.fromisoformat(row["issued_at"][:10])
        if row["closed_at"] != at(issued + DAY):
            problems.append(f"cancelled order {row['id']}: closed_at is not issued + 1")
        if item["quantity_received"] != "0":
            problems.append(f"cancelled order {row['id']} has received quantity")
        if any(r["purchase_order_item_id"] == item["id"] for r in receipts):
            problems.append(f"cancelled order {row['id']} has a receipt")
    # The exact templates, not only their number (pending item of the C5 audit).
    if eligible and used != expected_selection(simulation, valid_to, config):
        problems.append("the cancelled templates are not the documented selection")
    return problems


# =======================================================================================
# The rules as functions
# =======================================================================================


class ParameterTests(unittest.TestCase):
    def test_dt039_values(self) -> None:
        self.assertEqual(pol.ORDERS_CANCELLED_PERMILLE, 20)
        self.assertEqual(pol.ORDERS_CANCELLED_CLOSE_LAG_DAYS, 1)
        self.assertEqual(ORDERS_VERSION, "0.1.0")

    def test_generator_version(self) -> None:
        # One bump for the batch C6 + C4 + C5 (DT-036 section 8), applied with W1.
        self.assertEqual(GENERATOR_VERSION, "0.4.0")


class EligibilityTests(unittest.TestCase):
    """`DT-039` section 5.2, point 1. ``cierre_previsto = issued_on + 1 día``."""

    END = PERIOD_END

    def test_null_valid_to_and_close_before_end_is_eligible(self) -> None:
        self.assertTrue(is_eligible_for_cancel(self.END - 2 * DAY, None, self.END))

    def test_close_equal_to_end_date_is_excluded(self) -> None:
        self.assertFalse(is_eligible_for_cancel(self.END - DAY, None, self.END))

    def test_close_after_end_date_is_excluded(self) -> None:
        self.assertFalse(is_eligible_for_cancel(self.END, None, self.END))
        self.assertFalse(is_eligible_for_cancel(self.END + 5 * DAY, None, self.END))

    def test_close_equal_to_valid_to_is_eligible(self) -> None:
        valid_to = _dt.date(2025, 4, 2)
        self.assertTrue(is_eligible_for_cancel(valid_to - DAY, valid_to, self.END))

    def test_close_before_valid_to_is_eligible(self) -> None:
        valid_to = _dt.date(2025, 4, 2)
        self.assertTrue(is_eligible_for_cancel(valid_to - 5 * DAY, valid_to, self.END))

    def test_close_after_valid_to_is_excluded(self) -> None:
        valid_to = _dt.date(2025, 4, 2)
        self.assertFalse(is_eligible_for_cancel(valid_to, valid_to, self.END))
        self.assertFalse(is_eligible_for_cancel(valid_to + DAY, valid_to, self.END))

    def test_several_failing_conditions_are_excluded(self) -> None:
        self.assertFalse(
            is_eligible_for_cancel(self.END - DAY, self.END - 3 * DAY, self.END)
        )

    def test_agrees_with_the_d01_specification_everywhere(self) -> None:
        for valid_to in (
            None,
            self.END - 10 * DAY,
            self.END - DAY,
            self.END,
            self.END + DAY,
        ):
            for offset in range(-15, 3):
                issued = self.END + offset * DAY
                with self.subTest(issued=issued, valid_to=valid_to):
                    self.assertEqual(
                        is_eligible_for_cancel(issued, valid_to, self.END),
                        expected_eligibility(issued, valid_to, self.END),
                    )

    def test_planned_close_cannot_see_end_date_or_valid_to(self) -> None:
        # The date that becomes closed_at depends on issued_on alone: nothing clips it.
        self.assertEqual(
            list(inspect.signature(planned_close).parameters), ["issued_on"]
        )
        self.assertEqual(planned_close(_dt.date(2025, 4, 2)), _dt.date(2025, 4, 3))

    def test_no_clipping_expression_in_the_module(self) -> None:
        source = inspect.getsource(od)
        self.assertIsNone(re.search(r"min\([^)]*(valid_to|end|close)", source))
        self.assertIsNone(re.search(r"max\([^)]*(valid_to|end_date)", source))


class TargetTests(unittest.TestCase):
    """`DT-039` section 5.2, point 2: ``K = max(1, ceil(N x 20 / 1000))``."""

    def test_formula(self) -> None:
        for n, k in ((0, 1), (1, 1), (50, 1), (51, 2), (100, 2), (3625, 73)):
            with self.subTest(n=n):
                self.assertEqual(cancelled_target(n), k)
                self.assertEqual(expected_k(n), k)

    def test_zero_candidates_still_means_k_is_one(self) -> None:
        # The D-01 invariant: K never depends on the number of candidates.
        self.assertEqual(cancelled_target(0), 1)


class OrderNumberTests(unittest.TestCase):
    """`DT-039` section 6."""

    def test_width(self) -> None:
        self.assertEqual(order_number_width(1), 6)
        self.assertEqual(order_number_width(999_999), 6)
        self.assertEqual(order_number_width(1_000_000), 7)

    def test_format(self) -> None:
        self.assertEqual(format_order_number(1, 6), "PO-000001")
        self.assertEqual(format_order_number(1240, 6), "PO-001240")
        self.assertEqual(format_order_number(1_000_000, 7), "PO-1000000")

    def test_lexicographic_order_is_numeric_order_across_the_widening(self) -> None:
        ids = [1, 9, 10, 999_999, 1_000_000, 1_000_001]
        width = order_number_width(max(ids))
        numbers = [format_order_number(i, width) for i in ids]
        self.assertEqual(numbers, sorted(numbers))
        self.assertTrue(all(len(n) == 3 + width for n in numbers))


# =======================================================================================
# The CANCELLED policy on hand-made inputs
# =======================================================================================


class HandMadeCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def build(self, orders, valid_to=None, config=CONFIG):
        work = workspace(self.tmp, valid_to or {1: None, 2: None, 3: None})
        return build_orders(config, work, SimulationResult(tuple(orders)))


class OrderOfOperationsTests(HandMadeCase):
    """Filter first; K, B2 and ``cancelled-selection`` only see the filtered universe."""

    def three_orders(self):
        valid_to = {1: _dt.date(2025, 3, 10), 2: None, 3: None}
        orders = [
            causal_order(1, _dt.date(2025, 2, 1), 2),  # eligible
            causal_order(2, _dt.date(2025, 3, 10), 1),  # issued on valid_to: out
            causal_order(3, PERIOD_END - DAY, 3),  # closes on end_date: out
        ]
        return orders, valid_to

    def test_ineligible_orders_never_enter_the_universe(self) -> None:
        orders, valid_to = self.three_orders()
        result = self.build(orders, valid_to)
        self.assertEqual(result.candidates, (1,))

    def test_ineligible_orders_are_never_selected_whatever_the_seed(self) -> None:
        orders, valid_to = self.three_orders()
        for seed in range(25):
            with self.subTest(seed=seed):
                result = self.build(
                    orders,
                    valid_to,
                    make_config(
                        **{
                            "seed": seed,
                            "period": {
                                "start_date": PERIOD_START.isoformat(),
                                "end_date": PERIOD_END.isoformat(),
                            },
                        }
                    ),
                )
                self.assertEqual([t.template_id for t in result.cancelled], [1])

    def test_selection_permutes_the_filtered_universe_only(self) -> None:
        orders, valid_to = self.three_orders()
        original = od.DeterministicRandom.permutation
        with mock.patch.object(
            od.DeterministicRandom, "permutation", autospec=True, side_effect=original
        ) as spy:
            self.build(orders, valid_to)
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(spy.call_args.args[1], 1)  # one candidate, not three orders

    def test_k_counts_causal_orders_and_the_cap_counts_candidates(self) -> None:
        # 60 causal orders: K = ceil(60 x 20 / 1000) = 2. 59 of them are issued on their
        # product's valid_to and are out; one twin is emitted - the cap, not an error.
        day = _dt.date(2025, 3, 10)
        valid_to = {p: day for p in range(2, 61)}
        valid_to[1] = None
        orders = [causal_order(1, day - 10 * DAY, 1)] + [
            causal_order(p, day, p) for p in range(2, 61)
        ]
        result = self.build(orders, valid_to)
        self.assertEqual(result.target, 2)
        self.assertEqual(result.candidates, (1,))
        self.assertEqual([t.template_id for t in result.cancelled], [1])

    def test_k_is_emitted_in_full_when_candidates_suffice(self) -> None:
        result = self.build(many_orders(120))
        self.assertEqual(result.target, 3)
        self.assertEqual(len(result.cancelled), 3)
        self.assertEqual(len(set(t.template_id for t in result.cancelled)), 3)


class ExactSelectionTests(HandMadeCase):
    """Which orders are cancelled, recomputed independently (:func:`expected_selection`).

    Compares the exact set of template ids - not a count - so a single different order
    fails the test. Checked both on the in-memory result and on the written file.
    """

    def config(self, seed: int = 20260913):
        return make_config(
            seed=seed,
            period={
                "start_date": PERIOD_START.isoformat(),
                "end_date": PERIOD_END.isoformat(),
            },
        )

    def check(self, orders, valid_to, config) -> set[int]:
        simulation = SimulationResult(tuple(orders))
        work = workspace(self.tmp, valid_to)
        chosen = {
            t.template_id for t in build_orders(config, work, simulation).cancelled
        }
        expected = expected_selection(simulation, valid_to, config)
        self.assertEqual(chosen, expected)
        generate(config, work, simulation)
        written = {
            (r["supplier_id"], r["location_id"], r["issued_at"])
            for r in read_rows(work, PURCHASE_ORDERS_FILE)
            if r["status"] == "CANCELLED"
        }
        by_id = {o.id: o for o in orders}
        self.assertEqual(
            written,
            {
                (
                    str(by_id[i].supplier_id),
                    str(by_id[i].location_id),
                    f"{by_id[i].issued_on}T00:00:00Z",
                )
                for i in expected
            },
        )
        self.assertEqual(audit(work, config, simulation), [])
        return chosen

    def test_small_case(self) -> None:
        orders = [causal_order(i + 1, PERIOD_START + i * DAY, 1) for i in range(5)]
        self.assertEqual(len(self.check(orders, {1: None}, self.config())), 1)

    def test_several_cancellations(self) -> None:
        # N = 150: K = ceil(150 x 20 / 1000) = 3.
        chosen = self.check(many_orders(150), {1: None}, self.config())
        self.assertEqual(len(chosen), 3)

    def test_with_ineligible_orders(self) -> None:
        # 120 causal orders: 60 of product 1 (no valid_to), one per day, and one order
        # for each of products 2..61, issued on its own valid_to - out of the universe.
        valid_to: dict[int, _dt.date | None] = {1: None}
        keys = [(PERIOD_START + d * DAY, 1, 1) for d in range(60)]
        for product in range(2, 62):
            day = PERIOD_START + (product - 2) * DAY
            valid_to[product] = day
            keys.append((day, 2, product))
        keys.sort()
        orders = [
            causal_order(i + 1, day, product, supplier_id=supplier)
            for i, (day, supplier, product) in enumerate(keys)
        ]
        excluded = {o.id for o in orders if o.line.product_id != 1}
        chosen = self.check(orders, valid_to, self.config())
        self.assertEqual(len(chosen), 3)  # K = ceil(120 x 20 / 1000)
        self.assertEqual(chosen & excluded, set())

    def test_same_seed_same_selection_and_every_seed_matches(self) -> None:
        orders = many_orders(150)
        first = self.check(orders, {1: None}, self.config(11))
        self.assertEqual(self.check(orders, {1: None}, self.config(11)), first)
        seen = {
            frozenset(self.check(orders, {1: None}, self.config(s))) for s in range(6)
        }
        self.assertGreater(len(seen), 1)


class B2Tests(HandMadeCase):
    def test_zero_candidates_fails(self) -> None:
        valid_to = {1: _dt.date(2025, 3, 10), 2: None, 3: None}
        orders = [
            causal_order(1, _dt.date(2025, 3, 10), 1),
            causal_order(2, PERIOD_END - DAY, 2),
        ]
        with self.assertRaises(pol.GeneratorError) as raised:
            self.build(orders, valid_to)
        self.assertTrue(any(p.startswith("B2") for p in raised.exception.problems))

    def test_no_causal_orders_fails(self) -> None:
        # N = 0: the floor gives K = 1 and there is no template.
        with self.assertRaises(pol.GeneratorError) as raised:
            self.build([])
        self.assertTrue(any(p.startswith("B2") for p in raised.exception.problems))

    def test_b2_writes_nothing(self) -> None:
        work = workspace(self.tmp, {1: _dt.date(2025, 3, 10)})
        before = tree_digest(work)
        with self.assertRaises(pol.GeneratorError):
            generate(
                CONFIG,
                work,
                SimulationResult((causal_order(1, _dt.date(2025, 3, 10), 1),)),
            )
        self.assertEqual(tree_digest(work), before)

    def test_a_single_candidate_is_enough(self) -> None:
        result = self.build([causal_order(1, _dt.date(2025, 2, 1), 1)])
        self.assertEqual(len(result.cancelled), 1)


class ClosedAtTests(HandMadeCase):
    def test_closed_at_is_issued_plus_one_day(self) -> None:
        result = self.build(many_orders(120))
        for twin in result.cancelled:
            self.assertEqual(twin.closed_on, twin.issued_on + DAY)

    def test_close_on_valid_to_is_kept_exactly(self) -> None:
        valid_to = _dt.date(2025, 4, 2)
        result = self.build([causal_order(1, valid_to - DAY, 1)], {1: valid_to})
        self.assertEqual(result.cancelled[0].closed_on, valid_to)

    def test_close_on_the_last_day_of_the_period_is_kept_exactly(self) -> None:
        result = self.build([causal_order(1, PERIOD_END - 2 * DAY, 1)])
        self.assertEqual(result.cancelled[0].closed_on, PERIOD_END - DAY)

    def test_twin_dates_ignore_valid_to_and_end_date(self) -> None:
        # Building a twin never looks at the period or the validity: a template that
        # would close after both keeps issued + 1 (it can only exist because the filter
        # upstream keeps such templates out).
        template = causal_order(1, PERIOD_END + 10 * DAY, 1)
        (twin,) = od._twins([template], 2, 2)
        self.assertEqual(twin.closed_on, template.issued_on + DAY)

    def test_no_clipping_even_if_the_filter_were_bypassed(self) -> None:
        # Bypass the filter: an order issued on valid_to becomes a twin. If C5 clipped,
        # closed_at would silently become valid_to and pass. It stays issued + 1 and the
        # output invariant stops the run instead.
        valid_to = _dt.date(2025, 3, 10)
        with mock.patch.object(od, "is_eligible_for_cancel", lambda *args: True):
            with self.assertRaises(pol.GeneratorError) as raised:
                self.build([causal_order(1, valid_to, 1)], {1: valid_to})
        self.assertTrue(
            any("closed_at 2025-03-11" in p for p in raised.exception.problems)
        )


class InputValidationTests(HandMadeCase):
    """Component 5 refuses an inconsistent ``SimulationResult`` rather than fix it."""

    def test_a_non_causal_state_is_refused(self) -> None:
        bad = dataclasses.replace(
            causal_order(1, _dt.date(2025, 2, 1), 1), status="CANCELLED"
        )
        with self.assertRaises(pol.GeneratorError) as raised:
            self.build([bad])
        self.assertTrue(
            any("not a causal state" in p for p in raised.exception.problems)
        )

    def test_twins_never_serve_as_templates(self) -> None:
        result = self.build(many_orders(120))
        causal_ids = set(range(1, 121))
        self.assertTrue(set(result.candidates) <= causal_ids)
        self.assertTrue(all(t.template_id in causal_ids for t in result.cancelled))

    def test_inconsistent_orders_are_refused(self) -> None:
        good = causal_order(
            1, _dt.date(2025, 2, 1), 1, receipts=((1, _dt.date(2025, 2, 6), 10),)
        )
        cases = {
            "ids": [dataclasses.replace(good, id=5)],
            "status": [dataclasses.replace(good, status="ISSUED", closed_on=None)],
            "product": [causal_order(1, _dt.date(2025, 2, 1), 9)],
            "receipt": [
                dataclasses.replace(
                    good, receipts=(SimulatedReceipt(1, 1, PERIOD_END, 10),)
                )
            ],
        }
        for name, orders in cases.items():
            with self.subTest(name=name), self.assertRaises(pol.GeneratorError):
                self.build(orders)


class MaterialisationTests(HandMadeCase):
    """C5 copies; it does not recompute (`DT-039` section 1)."""

    def test_expected_at_is_a_copy_of_expected_on(self) -> None:
        # expected_on deliberately unrelated to any lead time: C5 must reflect it.
        odd = causal_order(
            1, _dt.date(2025, 2, 1), 1, expected_on=_dt.date(2025, 6, 17)
        )
        work = workspace(self.tmp, {1: None})
        generate(CONFIG, work, SimulationResult((odd,)))
        rows = {r["id"]: r for r in read_rows(work, PURCHASE_ORDERS_FILE)}
        self.assertEqual(rows["1"]["expected_at"], "2025-06-17T00:00:00Z")
        # The twin copies its template's expected_at too.
        self.assertEqual(rows["2"]["status"], "CANCELLED")
        self.assertEqual(rows["2"]["expected_at"], "2025-06-17T00:00:00Z")
        self.assertEqual(rows["2"]["issued_at"], "2025-02-01T00:00:00Z")
        self.assertEqual(rows["2"]["closed_at"], "2025-02-02T00:00:00Z")

    def test_receipts_quantities_and_ids_are_kept(self) -> None:
        orders = [
            causal_order(
                1,
                _dt.date(2025, 2, 1),
                1,
                quantity=7,
                receipts=((2, _dt.date(2025, 2, 9), 4), (3, _dt.date(2025, 2, 10), 3)),
            ),
            causal_order(
                2,
                _dt.date(2025, 2, 3),
                2,
                quantity=5,
                receipts=((1, _dt.date(2025, 2, 8), 2),),
            ),
        ]
        work = workspace(self.tmp, {1: None, 2: None})
        generate(CONFIG, work, SimulationResult(tuple(orders)))
        self.assertEqual(audit(work, CONFIG, SimulationResult(tuple(orders))), [])
        receipts = read_rows(work, PURCHASE_ORDER_RECEIPTS_FILE)
        # Rows by (purchase_order_item_id, received_at); ids untouched.
        self.assertEqual([r["id"] for r in receipts], ["2", "3", "1"])
        items = {r["id"]: r for r in read_rows(work, PURCHASE_ORDER_ITEMS_FILE)}
        self.assertEqual(items["1"]["unit_cost"], "12.34")
        self.assertEqual(items["2"]["quantity_received"], "2")

    def test_twin_ids_continue_component_4s_sequences(self) -> None:
        result = self.build(many_orders(120))
        self.assertEqual([t.id for t in result.cancelled], [121, 122, 123])
        self.assertEqual([t.line_id for t in result.cancelled], [121, 122, 123])
        keys = [
            (t.issued_on, t.supplier_id, t.product_id, t.location_id)
            for t in result.cancelled
        ]
        self.assertEqual(keys, sorted(keys))

    def test_one_line_per_order(self) -> None:
        # DT-039 sections 2 and 8: 1 : 1. There is no multi-line order to materialise.
        result = self.build(many_orders(120))
        counts = collections.Counter(r["purchase_order_id"] for r in result.items)
        self.assertEqual(set(counts.values()), {1})
        self.assertEqual(len(counts), len(result.purchase_orders))


# =======================================================================================
# The real pipeline
# =======================================================================================


class SmallPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config = make_config(**SMALL)
        cls.out = build_pipeline(Path(cls._tmp.name) / "work", cls.config)
        suppliers = [int(r["id"]) for r in read_rows(cls.out, "suppliers.csv")]
        _, cls.simulation = generate_inventory(
            cls.config, cls.out, dt037_profiles(suppliers)
        )
        cls.before = tree_digest(cls.out)
        cls.output_before = tree_digest(REPO_ROOT / DEFAULT_OUTPUT_DIR)
        cls.manifest = generate(cls.config, cls.out, cls.simulation)
        cls.output_after = tree_digest(REPO_ROOT / DEFAULT_OUTPUT_DIR)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()


class PipelineTests(SmallPipeline):
    def test_audit(self) -> None:
        self.assertEqual(audit(self.out, self.config, self.simulation), [])

    def test_there_is_a_cancelled_order(self) -> None:
        statuses = {r["status"] for r in read_rows(self.out, PURCHASE_ORDERS_FILE)}
        self.assertIn("CANCELLED", statuses)

    def test_column_contracts(self) -> None:
        for name, columns in (
            (PURCHASE_ORDERS_FILE, PURCHASE_ORDER_COLUMNS),
            (PURCHASE_ORDER_ITEMS_FILE, PURCHASE_ORDER_ITEM_COLUMNS),
            (PURCHASE_ORDER_RECEIPTS_FILE, PURCHASE_ORDER_RECEIPT_COLUMNS),
        ):
            header = (self.out / name).read_text(encoding="utf-8").split("\n")[0]
            self.assertEqual(header, ",".join(columns))
        self.assertEqual(len(PURCHASE_ORDER_COLUMNS), 14)
        self.assertEqual(len(PURCHASE_ORDER_ITEM_COLUMNS), 8)
        self.assertEqual(len(PURCHASE_ORDER_RECEIPT_COLUMNS), 6)

    def test_always_empty_fields(self) -> None:
        for row in read_rows(self.out, PURCHASE_ORDERS_FILE):
            for name in (
                "currency",
                "total_amount",
                "created_by",
                "created_at",
                "updated_at",
            ):
                self.assertEqual(row[name], "")
            self.assertEqual(
                row["closed_at"] != "", row["status"] in ("RECEIVED", "CANCELLED")
            )
            self.assertEqual(row["data_origin"], "SYNTHETIC")
        for row in read_rows(self.out, PURCHASE_ORDER_ITEMS_FILE):
            self.assertEqual(row["expected_at"], "")
        for row in read_rows(self.out, PURCHASE_ORDER_RECEIPTS_FILE):
            self.assertEqual(row["quality_rejected"], "")

    def test_receipt_movements_reference_written_receipts(self) -> None:
        receipt_ids = {
            r["id"] for r in read_rows(self.out, PURCHASE_ORDER_RECEIPTS_FILE)
        }
        moved = {
            r["reference_id"]
            for r in read_rows(self.out, "inventory_movements.csv")
            if r["movement_type"] == "RECEIPT"
        }
        self.assertEqual(moved, receipt_ids)

    def test_cancelled_orders_do_not_touch_inventory(self) -> None:
        # In transit is ISSUED + PARTIALLY_RECEIVED only (docs/04 §3.9).
        items = {
            r["purchase_order_id"]: r
            for r in read_rows(self.out, PURCHASE_ORDER_ITEMS_FILE)
        }
        transit = collections.Counter()
        for row in read_rows(self.out, PURCHASE_ORDERS_FILE):
            if row["status"] in ("ISSUED", "PARTIALLY_RECEIVED"):
                item = items[row["id"]]
                transit[item["product_id"]] += int(item["quantity_ordered"]) - int(
                    item["quantity_received"]
                )
        for row in read_rows(self.out, "inventory.csv"):
            self.assertEqual(
                int(row["quantity_in_transit"]), transit[row["product_id"]]
            )

    def test_earlier_files_untouched(self) -> None:
        after = tree_digest(self.out)
        for name, value in self.before.items():
            if name != "manifest.json":
                self.assertEqual(after[name], value, name)

    def test_writes_exactly_its_three_files(self) -> None:
        added = sorted(set(tree_digest(self.out)) - set(self.before))
        self.assertEqual(
            added,
            sorted(
                [
                    PURCHASE_ORDERS_FILE,
                    PURCHASE_ORDER_ITEMS_FILE,
                    PURCHASE_ORDER_RECEIPTS_FILE,
                ]
            ),
        )

    def test_manifest(self) -> None:
        entry = [c for c in self.manifest["components"] if c["name"] == "orders"]
        self.assertEqual(
            entry,
            [
                {
                    "name": COMPONENT_ORDERS,
                    "version": ORDERS_VERSION,
                    "sub_seed": sub_seed(self.config.seed, COMPONENT_ORDERS),
                }
            ],
        )
        files = {f["name"]: f for f in self.manifest["files"]}
        for name, entity in (
            (PURCHASE_ORDERS_FILE, "PurchaseOrder"),
            (PURCHASE_ORDER_ITEMS_FILE, "PurchaseOrderItem"),
            (PURCHASE_ORDER_RECEIPTS_FILE, "PurchaseOrderReceipt"),
        ):
            self.assertEqual(files[name]["entity"], entity)
            self.assertEqual(files[name]["sha256"], digest(self.out / name))
            self.assertEqual(files[name]["rows"], len(read_rows(self.out, name)))
        self.assertEqual(
            json.loads((self.out / "manifest.json").read_text()), self.manifest
        )
        self.assertEqual(self.manifest["generator_version"], "0.4.0")

    def test_output_directory_untouched(self) -> None:
        self.assertEqual(self.output_after, self.output_before)

    def test_a_second_run_writes_nothing(self) -> None:
        snapshot = tree_digest(self.out)
        with self.assertRaises(ValueError):
            generate(self.config, self.out, self.simulation)
        self.assertEqual(tree_digest(self.out), snapshot)

    def test_no_default_output_and_reached_only_through_w1(self) -> None:
        signature = inspect.signature(generate)
        self.assertIs(
            signature.parameters["output_dir"].default, inspect.Parameter.empty
        )
        self.assertNotIn("DEFAULT_OUTPUT_DIR", inspect.getsource(od))
        from data.synthetic.generator import __main__ as cli
        from data.synthetic.generator import pipeline

        self.assertNotIn("orders", inspect.getsource(cli))
        self.assertIn("orders.generate", inspect.getsource(pipeline))

    def test_component_4_is_imported_for_annotations_only(self) -> None:
        # DT-039 section 1: C5 does not import C4 to recompute anything.
        tree = ast.parse(inspect.getsource(od))
        runtime_imports = [
            node
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "inventory"
        ]
        self.assertEqual(runtime_imports, [])
        self.assertNotIn("receipt-timing", inspect.getsource(od))


class DeterminismTests(unittest.TestCase):
    def test_same_input_same_bytes(self) -> None:
        config = make_config(**SMALL)
        digests = []
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("a", "b"):
                work = build_pipeline(Path(tmp) / name, config)
                suppliers = [int(r["id"]) for r in read_rows(work, "suppliers.csv")]
                _, simulation = generate_inventory(
                    config, work, dt037_profiles(suppliers)
                )
                generate(config, work, simulation)
                digests.append(tree_digest(work))
        self.assertEqual(digests[0], digests[1])

    def test_the_seed_drives_the_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = workspace(tmp, {1: None})
            simulation = SimulationResult(tuple(many_orders(150)))
            picks = {
                tuple(
                    t.template_id
                    for t in build_orders(
                        make_config(
                            seed=seed,
                            period={
                                "start_date": PERIOD_START.isoformat(),
                                "end_date": PERIOD_END.isoformat(),
                            },
                        ),
                        work,
                        simulation,
                    ).cancelled
                )
                for seed in range(5)
            }
        self.assertGreater(len(picks), 1)


class ValidToScenarioTests(unittest.TestCase):
    """The case of D-01, through C4: an order issued on its product's ``valid_to``."""

    def test_excluded_and_its_late_receipt_materialised(self) -> None:
        valid_to = START + _dt.timedelta(days=42)
        with tempfile.TemporaryDirectory() as tmp:
            config, out, simulation = run_handmade(
                tmp,
                "vt",
                products=[(1, START, valid_to), (2, START, None), (3, START, None)],
                relations=[
                    (1, 2, 5, 0, 1, True, True),
                    (2, 1, 3, 0, 1, True, True),
                    (3, 2, 7, 0, 1, True, True),
                ],
                demand={1: lambda k: 10, 2: lambda k: 6, 3: lambda k: 8},
                profiles=[make_profile(1), make_profile(2, on_time=0, delay=(10, 10))],
            )
            result = build_orders(config, out, simulation)
            (on_valid_to,) = [
                o
                for o in simulation.orders
                if o.line.product_id == 1 and o.issued_on == valid_to
            ]
            self.assertNotIn(on_valid_to.id, result.candidates)
            generate(config, out, simulation)
            self.assertEqual(audit(out, config, simulation), [])
            late = [
                r
                for r in read_rows(out, PURCHASE_ORDER_RECEIPTS_FILE)
                if int(r["purchase_order_item_id"]) == on_valid_to.line.id
            ]
            self.assertTrue(late)
            self.assertTrue(
                all(r["received_at"][:10] > valid_to.isoformat() for r in late)
            )


class FullScaleTests(unittest.TestCase):
    def test_full_pipeline(self) -> None:
        config = make_config()
        with tempfile.TemporaryDirectory() as tmp:
            work = build_pipeline(Path(tmp) / "work", config)
            suppliers = [int(r["id"]) for r in read_rows(work, "suppliers.csv")]
            _, simulation = generate_inventory(config, work, dt037_profiles(suppliers))
            generate(config, work, simulation)
            self.assertEqual(audit(work, config, simulation), [])
            statuses = collections.Counter(
                r["status"] for r in read_rows(work, PURCHASE_ORDERS_FILE)
            )
        self.assertEqual(
            statuses["CANCELLED"], cancelled_target(len(simulation.orders))
        )
        self.assertEqual(
            set(statuses), {"RECEIVED", "PARTIALLY_RECEIVED", "ISSUED", "CANCELLED"}
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
