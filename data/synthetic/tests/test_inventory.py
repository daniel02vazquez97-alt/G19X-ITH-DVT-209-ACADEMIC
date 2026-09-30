"""Tests for Component 4: the Inventory Simulator.

Run from the repository root::

    python3 -m unittest discover -s data/synthetic/tests -t .

Standard library ``unittest``, like Components 1 to 3 (`docs/13-testing.md`).

Scope: the causal reality of stock - opening balance, satisfied demand, movements, the
final snapshot and the causal orders and receipts handed to Component 5. Nothing about
Component 5 files, cancelled orders, ``order_number``, Component 6 assignment or the
publication of the dataset: none of that is C4's.

**The central check is an independent replay.** :func:`audit` re-derives, day by day and
from the written files alone, what the contracts of `DT-036` / `DT-038` say must have
happened - consumption, the stockout flag, the daily trigger, the order quantity, the
committed date, the receipts, the snapshot - using its own arithmetic (``Fraction`` and
the literal values W = 28, C = 21), not the functions of the module under test. A
simulator that satisfied its own internal checks but not the documented rules fails it.

**Supplier profiles are built by hand.** Component 4 *consumes* :class:`SupplierProfile`
instances, whoever builds them; Component 6 is tested on its own in
``test_supplier_behaviour.py``. The tests either copy the table of
`DT-037` section 2 as test data or use deliberately artificial profiles, which is what
shows that C4 applies whatever it receives and decides no behaviour of its own.
"""

from __future__ import annotations

import collections
import csv
import dataclasses
import datetime as _dt
import hashlib
import inspect
import json
import math
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

from data.synthetic.config.config import DatasetConfig, Scenario
from data.synthetic.generator import inventory as inv
from data.synthetic.generator import policies as pol
from data.synthetic.generator.catalog import DEFAULT_OUTPUT_DIR
from data.synthetic.generator.catalog import generate as generate_catalog
from data.synthetic.generator.demand import generate as generate_demand
from data.synthetic.generator.inventory import (
    CONSUMPTION_COLUMNS,
    CONSUMPTION_FILE,
    INVENTORY_COLUMNS,
    INVENTORY_FILE,
    MOVEMENT_COLUMNS,
    MOVEMENTS_FILE,
    SimulatedOrder,
    SupplierProfile,
    build_inventory,
    generate,
    opening_balance,
    order_quantity,
    reorder_threshold,
    split_quantities,
)
from data.synthetic.generator.rng import COMPONENT_INVENTORY, sub_seed
from data.synthetic.generator.writer import (
    GENERATOR_VERSION,
    INVENTORY_VERSION,
    build_manifest,
    write_manifest,
)

BASE_CONFIG: dict = {
    "seed": 20260913,
    "period": {"start_date": "2023-01-01", "end_date": "2026-01-01"},
    "scale": {
        "product_count": 100,
        "supplier_count": 10,
        "category_count": 10,
        "location_count": 1,
    },
    "scenarios": {"required": [s.value for s in Scenario]},
}

FIXED_TIME = _dt.datetime(2026, 9, 23, 12, 0, 0, tzinfo=_dt.timezone.utc)

#: Same small dataset as the Component 3 tests: 12 products, 59 days.
SMALL = {
    "scale": {"product_count": 12, "supplier_count": 4, "category_count": 3},
    "period": {"start_date": "2023-01-01", "end_date": "2023-03-01"},
}

#: `DT-036`, written out here so the replay does not read the module under test.
W, M, C = 28, 7, 21

REPO_ROOT = Path(__file__).resolve().parents[3]


def make_config(**overrides) -> DatasetConfig:
    raw = json.loads(json.dumps(BASE_CONFIG))
    for key, value in overrides.items():
        if key in ("scale", "period"):
            raw[key].update(value)
        else:
            raw[key] = value
    return DatasetConfig.from_mapping(raw)


def dt037_profiles(supplier_ids) -> list[SupplierProfile]:
    """One profile per supplier, cycling through the combinations of `DT-037` §2.

    **Test data, not Component 6.** The values are copied from the table of `DT-037`;
    the assignment is a plain cycle chosen so that every combination appears, and it is
    not - and must not be mistaken for - the seeded 40/40/20 x 70/30 assignment that
    Component 6 owns.
    """
    punctuality = (
        ("PUNCTUAL", 900, (1, 3)),
        ("IRREGULAR", 650, (1, 7)),
        ("LATE", 250, (3, 14)),
    )
    profiles = []
    for position, supplier_id in enumerate(sorted(supplier_ids)):
        name, on_time, delay = punctuality[position % 3]
        if position % 2:
            integrity, partial, split, lag = "SPLIT", 250, (400, 800), (1, 10)
        else:
            integrity, partial, split, lag = "COMPLETE", 0, None, None
        profiles.append(
            SupplierProfile(
                supplier_id, name, integrity, on_time, delay, partial, split, lag
            )
        )
    return profiles


def make_profile(
    supplier_id: int,
    *,
    on_time: int = 1000,
    delay: tuple[int, int] = (1, 1),
    partial: int = 0,
    split: tuple[int, int] | None = None,
    lag: tuple[int, int] | None = None,
) -> SupplierProfile:
    """An artificial profile, to pin down exactly what C4 does with a profile."""
    return SupplierProfile(
        supplier_id,
        "TEST",
        "SPLIT" if partial else "COMPLETE",
        on_time,
        delay,
        partial,
        split,
        lag,
    )


def build_pipeline(directory: Path, config: DatasetConfig) -> Path:
    """C2 then C3 into ``directory``, the way the pipeline does."""
    generate_catalog(config, directory, generated_at=FIXED_TIME)
    generate_demand(config, directory, generated_at=FIXED_TIME)
    return directory


def read_rows(directory: Path, name: str) -> list[dict[str, str]]:
    with (directory / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(directory: Path) -> dict[str, str]:
    if not directory.is_dir():
        return {}
    return {
        str(path.relative_to(directory)): digest(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def day(text: str) -> _dt.date:
    return _dt.date.fromisoformat(text)


def ceil_fraction(numerator: int, denominator: int) -> int:
    return math.ceil(Fraction(numerator, denominator))


def expected_quantity(window_sum: int, moq: int, multiple: int) -> int | None:
    """`V1-06` complete, independently of the module: guard first, then MOQ, then multiple."""
    raw_need = ceil_fraction(window_sum * C, W)
    if raw_need <= 0:
        return None
    return math.ceil(Fraction(max(raw_need, moq), multiple)) * multiple


# =======================================================================================
# Hand-made inputs - to pin down each rule with numbers chosen for it
# =======================================================================================


def write_inputs(
    directory: Path,
    config: DatasetConfig,
    *,
    products: list[tuple[int, _dt.date, _dt.date | None]],
    relations: list[tuple[int, int, int, int, int, bool, bool]],
    demand: dict[int, object],
    locations: tuple[int, ...] = (1,),
) -> Path:
    """Write the four files C4 reads, plus an empty manifest.

    ``relations``: ``(product_id, supplier_id, lead_time, moq, order_multiple,
    is_preferred, is_active)``. ``demand``: product id -> callable of the day index
    inside the product's validity.
    """
    directory.mkdir(parents=True, exist_ok=True)
    start, end = config.period.start_date, config.period.end_date
    with (directory / "products.csv").open("w", encoding="utf-8", newline="") as h:
        h.write("id,valid_from,valid_to\n")
        for product_id, valid_from, valid_to in products:
            h.write(f"{product_id},{valid_from},{valid_to or ''}\n")
    with (directory / "locations.csv").open("w", encoding="utf-8", newline="") as h:
        h.write("id\n" + "".join(f"{location}\n" for location in locations))
    with (directory / "product_suppliers.csv").open(
        "w", encoding="utf-8", newline=""
    ) as h:
        h.write(
            "product_id,supplier_id,agreed_lead_time_days,moq,order_multiple,"
            "unit_cost,is_preferred,is_active\n"
        )
        for pid, sid, lead, moq, multiple, preferred, active in relations:
            h.write(
                f"{pid},{sid},{lead},{moq},{multiple},12.34,"
                f"{str(preferred).lower()},{str(active).lower()}\n"
            )
    rows = []
    for product_id, valid_from, valid_to in products:
        first = max(start, valid_from)
        last = end - _dt.timedelta(days=1)
        if valid_to is not None:
            last = min(last, valid_to)
        for location in locations:
            for k in range((last - first).days + 1):
                rows.append(
                    (
                        product_id,
                        location,
                        first + _dt.timedelta(days=k),
                        demand[product_id](k),
                    )
                )
    rows.sort()
    with (directory / "demand.csv").open("w", encoding="utf-8", newline="") as h:
        h.write("id,product_id,location_id,occurred_on,quantity,data_origin\n")
        for position, (pid, location, occurred_on, quantity) in enumerate(rows):
            h.write(
                f"{position + 1},{pid},{location},{occurred_on},{quantity},SYNTHETIC\n"
            )
    write_manifest(
        directory / "manifest.json",
        build_manifest(config=config, generated_at=FIXED_TIME, components=[], files=[]),
    )
    return directory


# =======================================================================================
# The independent replay
# =======================================================================================


def audit(directory: Path, config: DatasetConfig, simulation) -> list[str]:
    """Replay every documented rule of C4 against the files it wrote.

    Returns the problems found (empty when the output honours `DT-036`, `DT-037` §3 as
    amended by D-C4-1, and `DT-038`). Uses only the written CSV files, the
    ``SimulationResult`` and its own arithmetic.
    """
    problems: list[str] = []
    start, end = config.period.start_date, config.period.end_date

    preferred: dict[int, dict[str, str]] = {}
    for row in read_rows(directory, "product_suppliers.csv"):
        if row["is_preferred"] == "true" and row["is_active"] == "true":
            preferred[int(row["product_id"])] = row

    series: dict[tuple[int, int], list[tuple[_dt.date, int]]] = collections.defaultdict(
        list
    )
    for row in read_rows(directory, "demand.csv"):
        series[(int(row["product_id"]), int(row["location_id"]))].append(
            (day(row["occurred_on"]), int(row["quantity"]))
        )

    consumption = {
        ((int(r["product_id"]), int(r["location_id"])), day(r["occurred_on"])): r
        for r in read_rows(directory, CONSUMPTION_FILE)
    }
    positive: dict[tuple[tuple[int, int], _dt.date], int] = collections.defaultdict(int)
    issues: dict[tuple[tuple[int, int], _dt.date], int] = {}
    receipt_moves: dict[int, dict[str, str]] = {}
    totals: dict[tuple[int, int], int] = collections.defaultdict(int)
    last_moment: dict[tuple[int, int], str] = {}
    for row in read_rows(directory, MOVEMENTS_FILE):
        pair = (int(row["product_id"]), int(row["location_id"]))
        when = day(row["occurred_at"][:10])
        quantity = int(row["quantity"])
        totals[pair] += quantity
        last_moment[pair] = max(last_moment.get(pair, ""), row["occurred_at"])
        if row["movement_type"] == "ISSUE":
            if (pair, when) in issues:
                problems.append(f"two ISSUE movements for {pair} on {when}")
            issues[(pair, when)] = quantity
        else:
            positive[(pair, when)] += quantity
        if row["movement_type"] == "RECEIPT":
            receipt_moves[int(row["reference_id"])] = row

    orders_by_pair: dict[tuple[int, int], dict[_dt.date, SimulatedOrder]] = (
        collections.defaultdict(dict)
    )
    for order in simulation.orders:
        pair = (order.line.product_id, order.location_id)
        if order.issued_on in orders_by_pair[pair]:
            problems.append(f"two orders for {pair} on {order.issued_on}")
        orders_by_pair[pair][order.issued_on] = order

    for pair, days in sorted(series.items()):
        days.sort()
        latent_by_day = dict(days)
        quantities = [quantity for _, quantity in days]
        first = days[0][0]
        relation = preferred.get(pair[0])
        orders = orders_by_pair.get(pair, {})
        balance = 0
        current = start
        while current < end:
            balance += positive.get((pair, current), 0)
            if current not in latent_by_day:
                # After valid_to only in-flight receipts may happen (DT-038 section 9).
                if (pair, current) in issues:
                    problems.append(f"ISSUE for {pair} on {current}, outside validity")
                if (pair, current) in consumption:
                    problems.append(
                        f"consumption for {pair} on {current}, outside validity"
                    )
                if current in orders:
                    problems.append(f"order for {pair} on {current}, outside validity")
                current += _dt.timedelta(days=1)
                continue

            # DT-038 section 4: consumption = min(latent, stock), no backlog.
            latent = latent_by_day[current]
            expected = min(latent, balance)
            row = consumption.get((pair, current))
            if row is None:
                problems.append(f"no consumption row for {pair} on {current}")
            else:
                if int(row["quantity"]) != expected:
                    problems.append(
                        f"consumption of {pair} on {current} is {row['quantity']}, "
                        f"expected min({latent}, {balance}) = {expected}"
                    )
                flag = "true" if latent > expected else "false"
                if row["is_stockout_affected"] != flag:
                    problems.append(f"stockout flag of {pair} on {current} is wrong")
            issued = issues.get((pair, current))
            if expected > 0 and issued != -expected:
                problems.append(
                    f"ISSUE of {pair} on {current} is {issued}, not {-expected}"
                )
            if expected == 0 and issued is not None:
                problems.append(
                    f"ISSUE emitted for a zero consumption, {pair} {current}"
                )
            balance -= expected
            if balance < 0:
                problems.append(f"stock of {pair} negative on {current}")

            # DT-038 section 7: the trigger, every day in force, after consumption.
            if relation is None:
                if current in orders:
                    problems.append(
                        f"{pair} ordered without an active preferred relation"
                    )
            else:
                k = (current - first).days
                a = max(0, k - W)
                window_sum = sum(quantities[a : a + W])
                lead = int(relation["agreed_lead_time_days"])
                threshold = ceil_fraction(window_sum * lead, W)
                transit = sum(
                    o.line.quantity_ordered
                    - sum(r.quantity for r in o.receipts if r.received_on <= current)
                    for issued_on, o in orders.items()
                    if issued_on < current
                )
                quantity = expected_quantity(
                    window_sum, int(relation["moq"]), int(relation["order_multiple"])
                )
                should = balance + transit <= threshold and quantity is not None
                if should != (current in orders):
                    problems.append(
                        f"{pair} on {current}: on_hand {balance} + in_transit {transit} "
                        f"vs s {threshold}, Q {quantity}: order expected={should}"
                    )
                if current in orders:
                    order = orders[current]
                    if order.line.quantity_ordered != quantity:
                        problems.append(f"order {order.id}: quantity is not V1-06")
                    if order.expected_on != current + _dt.timedelta(days=lead):
                        problems.append(
                            f"order {order.id}: expected_on is not issued + L"
                        )
                    if order.supplier_id != int(relation["supplier_id"]):
                        problems.append(f"order {order.id}: not the preferred supplier")
            current += _dt.timedelta(days=1)

    # Receipts and order states - DT-038 sections 9 and 10.
    receipt_count = 0
    for order in simulation.orders:
        received = sum(r.quantity for r in order.receipts)
        receipt_count += len(order.receipts)
        if order.line.quantity_received != received:
            problems.append(f"order {order.id}: quantity_received is not the sum")
        if received > order.line.quantity_ordered:
            problems.append(f"order {order.id}: over-received")
        if received == 0:
            state, closed = "ISSUED", None
        elif received < order.line.quantity_ordered:
            state, closed = "PARTIALLY_RECEIVED", None
        else:
            state, closed = "RECEIVED", order.receipts[-1].received_on
        if (order.status, order.closed_on) != (state, closed):
            problems.append(f"order {order.id}: status/closed_on inconsistent")
        if list(order.receipts) != sorted(
            order.receipts, key=lambda r: (r.received_on, r.id)
        ):
            problems.append(
                f"order {order.id}: receipts not in (received_on, id) order"
            )
        for receipt in order.receipts:
            if receipt.quantity <= 0:
                problems.append(f"receipt {receipt.id}: quantity {receipt.quantity}")
            if not order.expected_on <= receipt.received_on < end:
                problems.append(f"receipt {receipt.id}: date {receipt.received_on}")
            if receipt.purchase_order_item_id != order.line.id:
                problems.append(f"receipt {receipt.id}: wrong line")
            move = receipt_moves.get(receipt.id)
            if move is None:
                problems.append(f"receipt {receipt.id} has no RECEIPT movement")
                continue
            if (
                int(move["product_id"]),
                int(move["location_id"]),
                move["occurred_at"],
                int(move["quantity"]),
            ) != (
                order.line.product_id,
                order.location_id,
                f"{receipt.received_on}T06:00:00Z",
                receipt.quantity,
            ):
                problems.append(f"RECEIPT movement of receipt {receipt.id} disagrees")
    if receipt_count != len(receipt_moves):
        problems.append("RECEIPT movements and receipts are not one-to-one")

    # Snapshot - DT-038 section 6.
    for row in read_rows(directory, INVENTORY_FILE):
        pair = (int(row["product_id"]), int(row["location_id"]))
        if int(row["quantity_on_hand"]) != totals.get(pair, 0):
            problems.append(f"inventory of {pair} is not the sum of its movements")
        transit = sum(
            o.line.quantity_ordered - o.line.quantity_received
            for o in orders_by_pair.get(pair, {}).values()
            if o.status in ("ISSUED", "PARTIALLY_RECEIVED")
        )
        if int(row["quantity_in_transit"]) != transit:
            problems.append(f"quantity_in_transit of {pair} is wrong")
        if row["last_movement_at"] != last_moment.get(pair, ""):
            problems.append(f"last_movement_at of {pair} is wrong")
    return problems


# =======================================================================================
# The formulas, as pure functions - DT-036 sections 1, 3, 4, 5 and DT-037 section 3
# =======================================================================================


class ParameterTests(unittest.TestCase):
    def test_dt036_values(self) -> None:
        self.assertEqual(pol.INVENTORY_WINDOW_DAYS, W)
        self.assertEqual(pol.INVENTORY_OPENING_MARGIN_DAYS, M)
        self.assertEqual(pol.INVENTORY_ORDER_COVERAGE_DAYS, C)
        self.assertEqual(
            pol.INVENTORY_OPENING_FACTOR_PERMILLE,
            {"AJUSTADO": 750, "NORMAL": 1000, "HOLGADO": 1500},
        )
        self.assertEqual(
            pol.INVENTORY_OPENING_MIX, {"AJUSTADO": 30, "NORMAL": 40, "HOLGADO": 30}
        )

    def test_factors_are_integers_per_mille(self) -> None:
        # DT-032: no floats decide an integer quantity.
        for value in pol.INVENTORY_OPENING_FACTOR_PERMILLE.values():
            self.assertIsInstance(value, int)


class OpeningBalanceFormulaTests(unittest.TestCase):
    def test_the_mean_is_an_exact_rational(self) -> None:
        # 12 units in 28 days (the smallest first window of the current catalogue):
        # d = 3/7. Rounding the mean first would give 0; the exact rule gives
        # ceil(12 x 8 / 28) = ceil(3.43) = 4.
        self.assertEqual(opening_balance(12, 28, 1, 7, 1000), 4)

    def test_two_ceilings_one_per_step(self) -> None:
        # base = ceil(28 x 17 / 28) = 17; AJUSTADO: ceil(17 x 750 / 1000) = 13.
        self.assertEqual(opening_balance(28, 28, 10, 7, 750), 13)
        self.assertEqual(opening_balance(28, 28, 10, 7, 1000), 17)
        self.assertEqual(opening_balance(28, 28, 10, 7, 1500), 26)

    def test_m_widens_the_opening_only(self) -> None:
        # M is the margin added to L for the opening balance (D-C4-3) ...
        self.assertEqual(opening_balance(280, 28, 5, 7, 1000), 120)
        self.assertEqual(opening_balance(280, 28, 5, 0, 1000), 50)
        # ... and the threshold has no parameter for it at all: s = ceil(d x L).
        self.assertEqual(
            list(inspect.signature(reorder_threshold).parameters),
            ["window_sum", "window", "lead_time"],
        )
        self.assertEqual(reorder_threshold(280, 28, 5), 50)

    def test_zero_demand_gives_zero_opening(self) -> None:
        self.assertEqual(opening_balance(0, 28, 44, 7, 1500), 0)


class OrderQuantityTests(unittest.TestCase):
    def test_guard_precedes_moq(self) -> None:
        # V1-06: raw_need <= 0 means no order, whatever MOQ and the multiple say.
        self.assertIsNone(order_quantity(0, 28, 21, 500, 12))
        self.assertIsNone(order_quantity(0, 28, 21, 0, 1))

    def test_no_artificial_minimum(self) -> None:
        # 1 unit in 28 days: raw_need = ceil(21/28) = 1, not bumped to anything else.
        self.assertEqual(order_quantity(1, 28, 21, 0, 1), 1)

    def test_moq_and_multiple_are_two_constraints_in_order(self) -> None:
        cases = [
            # window_sum, moq, multiple, expected
            (28, 0, 1, 21),  # raw only
            (28, 30, 1, 30),  # MOQ lifts it
            (28, 0, 12, 24),  # multiple rounds raw up
            (28, 30, 12, 36),  # MOQ first, then the multiple: ceil(30/12) x 12
            (28, 25, 5, 25),  # MOQ already a multiple
            (28, 20, 1, 21),  # MOQ below raw: raw wins
            (2, 0, 5, 5),  # small raw rounded to the multiple
        ]
        for window_sum, moq, multiple, expected in cases:
            with self.subTest(moq=moq, multiple=multiple):
                self.assertEqual(
                    order_quantity(window_sum, 28, 21, moq, multiple), expected
                )
                self.assertEqual(expected_quantity(window_sum, moq, multiple), expected)

    def test_never_zero(self) -> None:
        for window_sum in range(0, 60):
            for moq in (0, 1, 7):
                for multiple in (1, 4, 12):
                    q = order_quantity(window_sum, 28, 21, moq, multiple)
                    self.assertTrue(q is None or q > 0)


class SplitQuantityTests(unittest.TestCase):
    """Decision D-C4-1, option O1: ``q1 = min(Q-1, max(1, ceil(Q x split / 1000)))``."""

    SPLITS = (0, 1, 250, 400, 500, 600, 800, 999, 1000)

    def test_small_orders(self) -> None:
        expected = {
            # (Q_final, split): (q1, q2)
            (2, 400): (1, 1),
            (2, 800): (1, 1),  # the old formula gave (2, 0): a receipt of zero units
            (2, 1000): (1, 1),
            (2, 0): (1, 1),
            (3, 400): (2, 1),
            (3, 800): (2, 1),  # old: (3, 0)
            (3, 0): (1, 2),
            (4, 400): (2, 2),
            (4, 800): (3, 1),  # old: (4, 0)
            (4, 500): (2, 2),
            (5, 400): (2, 3),
            (5, 800): (4, 1),
            (5, 1000): (4, 1),
            (10, 400): (4, 6),
            (10, 800): (8, 2),
            (7, 500): (4, 3),
        }
        for (q_final, split), pair in expected.items():
            with self.subTest(q_final=q_final, split=split):
                self.assertEqual(split_quantities(q_final, split), pair)

    def test_both_parts_positive_and_exact_for_every_split(self) -> None:
        for q_final in (2, 3, 4, 5, 6, 11, 97, 1000):
            for split in self.SPLITS:
                with self.subTest(q_final=q_final, split=split):
                    q1, q2 = split_quantities(q_final, split)
                    self.assertGreaterEqual(q1, 1)
                    self.assertGreaterEqual(q2, 1)
                    self.assertEqual(q1 + q2, q_final)

    def test_large_orders_follow_the_share(self) -> None:
        # From Q_final >= 5 inside the DT-037 range the bound never binds: q1 is the
        # plain ceil of the share, as the first version of DT-037 said.
        for q_final in range(5, 200):
            for split in range(400, 801, 50):
                q1, _ = split_quantities(q_final, split)
                self.assertEqual(q1, max(1, ceil_fraction(q_final * split, 1000)))

    def test_a_single_unit_cannot_be_split(self) -> None:
        with self.assertRaises(ValueError):
            split_quantities(1, 500)


class WindowTests(unittest.TestCase):
    def test_warm_up_is_frozen_then_slides_continuously(self) -> None:
        start = inv._window_start
        self.assertEqual([start(k, 28) for k in (0, 1, 27, 28)], [0, 0, 0, 0])
        self.assertEqual([start(k, 28) for k in (29, 30, 100)], [1, 2, 72])


# =======================================================================================
# The small pipeline: C2 + C3 + C4 into a temporary directory
# =======================================================================================


class SmallPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config = make_config(**SMALL)
        cls.out = build_pipeline(Path(cls._tmp.name) / "work", cls.config)
        cls.before = tree_digest(cls.out)
        cls.manifest_before = json.loads((cls.out / "manifest.json").read_text())
        suppliers = [int(r["id"]) for r in read_rows(cls.out, "suppliers.csv")]
        cls.profiles = dt037_profiles(suppliers)
        cls.output_before = tree_digest(REPO_ROOT / DEFAULT_OUTPUT_DIR)
        cls.manifest, cls.simulation = generate(cls.config, cls.out, cls.profiles)
        cls.output_after = tree_digest(REPO_ROOT / DEFAULT_OUTPUT_DIR)
        cls.consumption = read_rows(cls.out, CONSUMPTION_FILE)
        cls.movements = read_rows(cls.out, MOVEMENTS_FILE)
        cls.inventory = read_rows(cls.out, INVENTORY_FILE)
        cls.demand = read_rows(cls.out, "demand.csv")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()


class ReplayTests(SmallPipeline):
    def test_the_independent_replay_finds_nothing(self) -> None:
        self.assertEqual(audit(self.out, self.config, self.simulation)[:20], [])

    def test_the_replay_is_not_vacuous(self) -> None:
        self.assertGreater(len(self.simulation.orders), 0)
        self.assertTrue(any(o.receipts for o in self.simulation.orders))
        self.assertTrue(any(r["quantity"] != "0" for r in self.consumption))


class ContractTests(SmallPipeline):
    def test_column_tuples_are_dt038(self) -> None:
        self.assertEqual(
            CONSUMPTION_COLUMNS,
            (
                "id",
                "product_id",
                "location_id",
                "occurred_on",
                "quantity",
                "channel",
                "is_stockout_affected",
                "data_origin",
            ),
        )
        self.assertEqual(
            MOVEMENT_COLUMNS,
            (
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
            ),
        )
        self.assertEqual(
            INVENTORY_COLUMNS,
            (
                "id",
                "product_id",
                "location_id",
                "quantity_on_hand",
                "quantity_reserved",
                "quantity_in_transit",
                "last_movement_at",
                "updated_at",
                "data_origin",
            ),
        )

    def test_headers_match_the_contract(self) -> None:
        for name, columns in (
            (CONSUMPTION_FILE, CONSUMPTION_COLUMNS),
            (MOVEMENTS_FILE, MOVEMENT_COLUMNS),
            (INVENTORY_FILE, INVENTORY_COLUMNS),
        ):
            with self.subTest(name=name):
                header = (self.out / name).read_text(encoding="utf-8").split("\n")[0]
                self.assertEqual(header, ",".join(columns))

    def test_file_encoding(self) -> None:
        for name in (CONSUMPTION_FILE, MOVEMENTS_FILE, INVENTORY_FILE):
            data = (self.out / name).read_bytes()
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn(b"\r", data)
            self.assertTrue(data.endswith(b"\n"))

    def test_consumption_is_dense_on_the_demand_grid(self) -> None:
        key = ("product_id", "location_id", "occurred_on")
        self.assertEqual(
            [tuple(r[k] for k in key) for r in self.consumption],
            [tuple(r[k] for k in key) for r in self.demand],
        )

    def test_consumption_constants(self) -> None:
        for row in self.consumption:
            self.assertEqual(row["channel"], "")
            self.assertEqual(row["data_origin"], "SYNTHETIC")
            self.assertIn(row["is_stockout_affected"], ("true", "false"))
            self.assertGreaterEqual(int(row["quantity"]), 0)

    def test_consumption_never_exceeds_latent_demand(self) -> None:
        for row, latent in zip(self.consumption, self.demand):
            self.assertLessEqual(int(row["quantity"]), int(latent["quantity"]))
            if latent["quantity"] == "0":
                self.assertEqual(row["is_stockout_affected"], "false")

    def test_movement_vocabulary_signs_and_references(self) -> None:
        for row in self.movements:
            kind, quantity = row["movement_type"], int(row["quantity"])
            self.assertNotEqual(quantity, 0)
            self.assertEqual(row["created_by"], "")
            self.assertEqual(row["data_origin"], "SYNTHETIC")
            if kind == "ADJUSTMENT":
                self.assertGreater(quantity, 0)
                self.assertEqual(row["reference_type"], "INITIAL_INVENTORY")
                self.assertEqual(row["reference_id"], "")
                self.assertEqual(row["reason_code"], "OPENING_BALANCE")
            elif kind == "RECEIPT":
                self.assertGreater(quantity, 0)
                self.assertEqual(row["reference_type"], "PURCHASE_ORDER_RECEIPT")
                self.assertNotEqual(row["reference_id"], "")
                self.assertEqual(row["reason_code"], "")
            else:
                self.assertEqual(kind, "ISSUE")
                self.assertLess(quantity, 0)
                self.assertEqual(row["reference_type"], "CONSUMPTION")
                self.assertEqual(row["reason_code"], "")

    def test_clock_of_each_movement_type(self) -> None:
        clock = {
            "ADJUSTMENT": "00:00:00Z",
            "RECEIPT": "06:00:00Z",
            "ISSUE": "18:00:00Z",
        }
        for row in self.movements:
            self.assertEqual(row["occurred_at"][10:], "T" + clock[row["movement_type"]])
            self.assertEqual(row["recorded_at"], row["occurred_at"])

    def test_issue_references_its_consumption_row(self) -> None:
        by_id = {r["id"]: r for r in self.consumption}
        for row in self.movements:
            if row["movement_type"] != "ISSUE":
                continue
            target = by_id[row["reference_id"]]
            self.assertEqual(
                (target["product_id"], target["location_id"], target["occurred_on"]),
                (row["product_id"], row["location_id"], row["occurred_at"][:10]),
            )
            self.assertEqual(int(target["quantity"]), -int(row["quantity"]))

    def test_snapshot_shape(self) -> None:
        products = read_rows(self.out, "products.csv")
        locations = read_rows(self.out, "locations.csv")
        self.assertEqual(len(self.inventory), len(products) * len(locations))
        for row in self.inventory:
            self.assertEqual(row["quantity_reserved"], "0")
            self.assertEqual(row["updated_at"], "")
            self.assertEqual(row["data_origin"], "SYNTHETIC")
            self.assertGreaterEqual(int(row["quantity_on_hand"]), 0)
            self.assertGreaterEqual(int(row["quantity_in_transit"]), 0)

    def test_running_balance_never_negative(self) -> None:
        balance: dict[tuple[str, str], int] = collections.defaultdict(int)
        for row in self.movements:
            pair = (row["product_id"], row["location_id"])
            balance[pair] += int(row["quantity"])
            self.assertGreaterEqual(balance[pair], 0)


class IdentifierTests(SmallPipeline):
    """`DT-038` section 8: six steps, each a total order, each starting at 1."""

    def assert_sequential(self, rows, key) -> None:
        self.assertEqual([int(r["id"]) for r in rows], list(range(1, len(rows) + 1)))
        keys = [key(r) for r in rows]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(set(keys)), len(keys))

    def test_consumption_ids(self) -> None:
        self.assert_sequential(
            self.consumption,
            lambda r: (int(r["product_id"]), int(r["location_id"]), r["occurred_on"]),
        )

    def test_movement_ids(self) -> None:
        rank = {"ADJUSTMENT": 0, "RECEIPT": 1, "ISSUE": 2}
        self.assert_sequential(
            self.movements,
            lambda r: (
                int(r["product_id"]),
                int(r["location_id"]),
                r["occurred_at"],
                rank[r["movement_type"]],
                int(r["reference_id"] or 0),
            ),
        )

    def test_inventory_ids(self) -> None:
        self.assert_sequential(
            self.inventory, lambda r: (int(r["product_id"]), int(r["location_id"]))
        )

    def test_causal_order_ids(self) -> None:
        orders = self.simulation.orders
        self.assertEqual([o.id for o in orders], list(range(1, len(orders) + 1)))
        keys = [
            (o.issued_on, o.supplier_id, o.line.product_id, o.location_id)
            for o in orders
        ]
        self.assertEqual(keys, sorted(keys))
        for order in orders:
            self.assertEqual(order.line.id, order.id)
            self.assertEqual(order.line.purchase_order_id, order.id)

    def test_receipt_ids(self) -> None:
        receipts = sorted(
            (r for o in self.simulation.orders for r in o.receipts), key=lambda r: r.id
        )
        self.assertEqual([r.id for r in receipts], list(range(1, len(receipts) + 1)))
        keys = [(r.received_on, r.purchase_order_item_id) for r in receipts]
        self.assertEqual(keys, sorted(keys))

    def test_no_order_number(self) -> None:
        # Decision A2: Component 5 forms order_number for every order.
        names = {f.name for f in dataclasses.fields(SimulatedOrder)}
        self.assertNotIn("order_number", names)
        self.assertEqual(
            names,
            {
                "id",
                "supplier_id",
                "location_id",
                "issued_on",
                "expected_on",
                "closed_on",
                "status",
                "line",
                "receipts",
            },
        )

    def test_no_cancelled_orders(self) -> None:
        # CANCELLED orders are Component 5's, non-causal (DT-039).
        self.assertTrue(
            {o.status for o in self.simulation.orders}
            <= {"ISSUED", "PARTIALLY_RECEIVED", "RECEIVED"}
        )


class OpeningTests(SmallPipeline):
    def test_one_opening_per_pair_on_its_first_day(self) -> None:
        first_day = {}
        for row in self.demand:
            pair = (row["product_id"], row["location_id"])
            first_day.setdefault(pair, row["occurred_on"])
        openings = [r for r in self.movements if r["movement_type"] == "ADJUSTMENT"]
        self.assertEqual(len(openings), len(first_day))  # no zero opening here
        for row in openings:
            pair = (row["product_id"], row["location_id"])
            self.assertEqual(row["occurred_at"], f"{first_day[pair]}T00:00:00Z")

    def test_opening_quantity_follows_dt036(self) -> None:
        inventory = build_inventory(self.config, self.out, self.profiles)
        relations = collections.defaultdict(list)
        for row in read_rows(self.out, "product_suppliers.csv"):
            relations[int(row["product_id"])].append(row)
        series = collections.defaultdict(list)
        for row in self.demand:
            series[(int(row["product_id"]), int(row["location_id"]))].append(
                int(row["quantity"])
            )
        openings = {
            (int(r["product_id"]), int(r["location_id"])): int(r["quantity"])
            for r in self.movements
            if r["movement_type"] == "ADJUSTMENT"
        }
        for pair, values in series.items():
            rows = sorted(relations[pair[0]], key=lambda r: int(r["supplier_id"]))
            chosen = next(
                (
                    r
                    for r in rows
                    if r["is_preferred"] == "true" and r["is_active"] == "true"
                ),
                rows[0],
            )
            lead = int(chosen["agreed_lead_time_days"])
            factor = {"AJUSTADO": 750, "NORMAL": 1000, "HOLGADO": 1500}[
                inventory.opening_profiles[pair]
            ]
            base = ceil_fraction(sum(values[:W]) * (lead + M), W)
            with self.subTest(pair=pair):
                self.assertEqual(openings[pair], ceil_fraction(base * factor, 1000))

    def test_opening_profile_mix(self) -> None:
        inventory = build_inventory(self.config, self.out, self.profiles)
        counts = collections.Counter(inventory.opening_profiles.values())
        expected = pol.demand_mix_counts(
            pol.INVENTORY_OPENING_MIX,
            pol.INVENTORY_OPENING_PROFILES,
            len(inventory.opening_profiles),
        )
        self.assertEqual(dict(counts), {k: v for k, v in expected.items() if v})

    def test_margin_enters_the_opening_and_nothing_else(self) -> None:
        # With M patched to 0 the openings shrink, and the replay - whose threshold has
        # no M - still passes: M is the opening margin, not a review period (D-C4-3).
        with tempfile.TemporaryDirectory() as tmp:
            work = build_pipeline(Path(tmp), self.config)
            with mock.patch.object(pol, "INVENTORY_OPENING_MARGIN_DAYS", 0):
                _, simulation = generate(self.config, work, self.profiles)
            self.assertEqual(audit(work, self.config, simulation)[:20], [])
            smaller = {
                (r["product_id"], r["location_id"]): int(r["quantity"])
                for r in read_rows(work, MOVEMENTS_FILE)
                if r["movement_type"] == "ADJUSTMENT"
            }
        normal = {
            (r["product_id"], r["location_id"]): int(r["quantity"])
            for r in self.movements
            if r["movement_type"] == "ADJUSTMENT"
        }
        for pair, quantity in smaller.items():
            self.assertLessEqual(quantity, normal[pair])
        self.assertLess(sum(smaller.values()), sum(normal.values()))


class LeadTimeTests(SmallPipeline):
    def test_expected_on_is_issued_plus_agreed_lead_time(self) -> None:
        agreed = {
            (int(r["product_id"]), int(r["supplier_id"])): int(
                r["agreed_lead_time_days"]
            )
            for r in read_rows(self.out, "product_suppliers.csv")
            if r["is_preferred"] == "true" and r["is_active"] == "true"
        }
        for order in self.simulation.orders:
            lead = agreed[(order.line.product_id, order.supplier_id)]
            self.assertEqual((order.expected_on - order.issued_on).days, lead)

    def test_unit_cost_comes_from_the_preferred_relation(self) -> None:
        cost = {
            (int(r["product_id"]), int(r["supplier_id"])): r["unit_cost"]
            for r in read_rows(self.out, "product_suppliers.csv")
        }
        for order in self.simulation.orders:
            text = cost[(order.line.product_id, order.supplier_id)]
            euros, cents = text.split(".")
            self.assertEqual(order.line.unit_cost_cents, int(euros) * 100 + int(cents))


class ResponsibilityTests(SmallPipeline):
    def test_demand_csv_is_read_only(self) -> None:
        self.assertEqual(digest(self.out / "demand.csv"), self.before["demand.csv"])

    def test_catalogue_files_untouched(self) -> None:
        for name in (
            "categories.csv",
            "products.csv",
            "suppliers.csv",
            "product_suppliers.csv",
            "locations.csv",
        ):
            with self.subTest(name=name):
                self.assertEqual(digest(self.out / name), self.before[name])

    def test_writes_exactly_its_three_files(self) -> None:
        added = sorted(set(tree_digest(self.out)) - set(self.before))
        self.assertEqual(
            added, sorted([CONSUMPTION_FILE, INVENTORY_FILE, MOVEMENTS_FILE])
        )

    def test_writes_no_file_of_component_5_or_later(self) -> None:
        for name in (
            "purchase_orders.csv",
            "purchase_order_items.csv",
            "purchase_order_receipts.csv",
            "stockouts.csv",
            "scenario_assignment.csv",
            "quality_report.json",
            "supplier_behaviour.csv",
        ):
            self.assertFalse((self.out / name).exists())

    def test_output_directory_untouched(self) -> None:
        self.assertEqual(self.output_after, self.output_before)

    def test_no_default_output_directory(self) -> None:
        signature = inspect.signature(generate)
        for name in ("output_dir", "profiles"):
            self.assertIs(signature.parameters[name].default, inspect.Parameter.empty)
        self.assertIs(
            inspect.signature(build_inventory).parameters["input_dir"].default,
            inspect.Parameter.empty,
        )
        self.assertNotIn("DEFAULT_OUTPUT_DIR", inspect.getsource(inv))

    def test_reached_only_through_w1(self) -> None:
        # The command line never calls a component directly: it runs W1 (DT-040),
        # which calls C4 inside the workspace of the run.
        from data.synthetic.generator import __main__ as cli
        from data.synthetic.generator import pipeline

        self.assertNotIn("inventory", inspect.getsource(cli))
        self.assertIn("inventory.generate", inspect.getsource(pipeline))


class ManifestTests(SmallPipeline):
    def test_component_entry(self) -> None:
        entry = [c for c in self.manifest["components"] if c["name"] == "inventory"]
        self.assertEqual(
            entry,
            [
                {
                    "name": COMPONENT_INVENTORY,
                    "version": INVENTORY_VERSION,
                    "sub_seed": sub_seed(self.config.seed, COMPONENT_INVENTORY),
                }
            ],
        )
        self.assertEqual(INVENTORY_VERSION, "0.1.0")

    def test_file_entries_match_the_bytes(self) -> None:
        files = {f["name"]: f for f in self.manifest["files"]}
        for name, entity, rows in (
            (CONSUMPTION_FILE, "Consumption", self.consumption),
            (INVENTORY_FILE, "Inventory", self.inventory),
            (MOVEMENTS_FILE, "InventoryMovement", self.movements),
        ):
            with self.subTest(name=name):
                self.assertEqual(files[name]["entity"], entity)
                self.assertEqual(files[name]["rows"], len(rows))
                self.assertEqual(files[name]["sha256"], digest(self.out / name))

    def test_written_manifest_is_the_returned_one(self) -> None:
        self.assertEqual(
            json.loads((self.out / "manifest.json").read_text()), self.manifest
        )

    def test_versions(self) -> None:
        # The single bump of DT-036 section 8 for the batch C6 + C4 + C5, applied when
        # W1 put the batch into the published artefact (DT-033 rule).
        self.assertEqual(GENERATOR_VERSION, "0.4.0")
        self.assertEqual(self.manifest["generator_version"], "0.4.0")
        self.assertEqual(
            self.manifest["dataset_version"], self.manifest_before["dataset_version"]
        )

    def test_a_second_run_into_the_same_directory_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = build_pipeline(Path(tmp), self.config)
            generate(self.config, work, self.profiles)
            snapshot = tree_digest(work)
            with self.assertRaises(ValueError):
                generate(self.config, work, self.profiles)
            self.assertEqual(tree_digest(work), snapshot)


# =======================================================================================
# Determinism - DT-030, DT-032
# =======================================================================================


class DeterminismTests(unittest.TestCase):
    def test_same_seed_same_bytes_and_same_orders(self) -> None:
        config = make_config(**SMALL)
        runs = []
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("a", "b"):
                work = build_pipeline(Path(tmp) / name, config)
                suppliers = [int(r["id"]) for r in read_rows(work, "suppliers.csv")]
                manifest, simulation = generate(config, work, dt037_profiles(suppliers))
                runs.append((tree_digest(work), simulation, manifest))
        self.assertEqual(runs[0][0], runs[1][0])
        self.assertEqual(runs[0][1], runs[1][1])
        self.assertEqual(runs[0][2], runs[1][2])

    def test_the_seed_drives_the_simulation(self) -> None:
        # Same input files, two seeds: only C4's own draws can differ.
        config = make_config(**SMALL)
        with tempfile.TemporaryDirectory() as tmp:
            work = build_pipeline(Path(tmp), config)
            suppliers = [int(r["id"]) for r in read_rows(work, "suppliers.csv")]
            profiles = dt037_profiles(suppliers)
            one = build_inventory(config, work, profiles)
            other = build_inventory(make_config(**SMALL, seed=7), work, profiles)
        self.assertNotEqual(
            (one.opening_profiles, one.movements),
            (other.opening_profiles, other.movements),
        )


# =======================================================================================
# Hand-made scenarios
# =======================================================================================

START = _dt.date(2023, 1, 1)
END = _dt.date(2023, 5, 1)  # 120 days


def run_handmade(tmp: str, name: str, *, seed: int = 20260913, **inputs):
    config = make_config(
        seed=seed,
        period={"start_date": START.isoformat(), "end_date": END.isoformat()},
    )
    profiles = inputs.pop("profiles")
    work = write_inputs(Path(tmp) / name, config, **inputs)
    manifest, simulation = generate(config, work, profiles)
    return config, work, simulation


class RampScenarioTests(unittest.TestCase):
    """Zero demand, then demand: the guard, the warm-up, lost sales, daily triggers."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config, cls.out, cls.simulation = run_handmade(
            cls._tmp.name,
            "ramp",
            products=[(1, START, None), (2, START, None), (3, START, None)],
            relations=[
                (1, 1, 40, 0, 1, True, True),
                (2, 1, 5, 0, 1, True, True),
                (3, 2, 10, 0, 1, False, False),  # no active preferred relation
            ],
            demand={
                1: lambda k: 0 if k < 28 else 10,
                2: lambda k: 5,
                3: lambda k: 4,
            },
            profiles=[make_profile(1)],
        )
        cls.orders = collections.defaultdict(list)
        for order in cls.simulation.orders:
            cls.orders[order.line.product_id].append(order)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_replay(self) -> None:
        self.assertEqual(audit(self.out, self.config, self.simulation)[:20], [])

    def test_guard_holds_while_the_window_is_empty(self) -> None:
        # Days 0..28: s = 0 and on_hand + in_transit = 0 <= s, so the trigger fires
        # every day - and raw_need = 0 stops every one of them (V1-06).
        first = min(o.issued_on for o in self.orders[1])
        self.assertEqual(first, START + _dt.timedelta(days=29))
        opening = [
            r
            for r in read_rows(self.out, MOVEMENTS_FILE)
            if r["product_id"] == "1" and r["movement_type"] == "ADJUSTMENT"
        ]
        self.assertEqual(opening, [])  # zero opening: no movement (DT-038 §5.3)

    def test_the_trigger_is_evaluated_every_day(self) -> None:
        # With L = 40 > C = 21 one order does not lift the position above s, so the
        # trigger fires again the next day: there is no review period (no R_v1).
        days = sorted(o.issued_on for o in self.orders[1])
        consecutive = [b for a, b in zip(days, days[1:]) if (b - a).days == 1]
        self.assertGreaterEqual(len(consecutive), 3)

    def test_lost_sales_are_not_carried(self) -> None:
        rows = [
            r for r in read_rows(self.out, CONSUMPTION_FILE) if r["product_id"] == "1"
        ]
        stockout = [r for r in rows if r["is_stockout_affected"] == "true"]
        self.assertGreater(len(stockout), 0)
        # No backlog: a day never consumes more than its own latent demand.
        self.assertTrue(all(int(r["quantity"]) <= 10 for r in rows))

    def test_product_without_active_supplier_depletes_and_never_orders(self) -> None:
        self.assertEqual(self.orders[3], [])
        rows = [
            r for r in read_rows(self.out, CONSUMPTION_FILE) if r["product_id"] == "3"
        ]
        self.assertEqual(rows[-1]["is_stockout_affected"], "true")
        moves = [
            r for r in read_rows(self.out, MOVEMENTS_FILE) if r["product_id"] == "3"
        ]
        self.assertNotIn("RECEIPT", {r["movement_type"] for r in moves})
        # Opening sized with the inactive relation's L = 10 (DT-036 section 6).
        base = ceil_fraction(4 * W * (10 + M), W)  # 68
        self.assertIn(
            int(moves[0]["quantity"]),
            {ceil_fraction(base * factor, 1000) for factor in (750, 1000, 1500)},
        )

    def test_draws_are_per_pair(self) -> None:
        # Changing product 3's demand does not move a single order of products 1 and 2.
        with tempfile.TemporaryDirectory() as tmp:
            _, _, other = run_handmade(
                tmp,
                "ramp2",
                products=[(1, START, None), (2, START, None), (3, START, None)],
                relations=[
                    (1, 1, 40, 0, 1, True, True),
                    (2, 1, 5, 0, 1, True, True),
                    (3, 2, 10, 0, 1, False, False),
                ],
                demand={
                    1: lambda k: 0 if k < 28 else 10,
                    2: lambda k: 5,
                    3: lambda k: 9,
                },
                profiles=[make_profile(1)],
            )

        def shape(simulation):
            return sorted(
                (
                    o.line.product_id,
                    o.issued_on,
                    o.expected_on,
                    o.line.quantity_ordered,
                    tuple((r.received_on, r.quantity) for r in o.receipts),
                )
                for o in simulation.orders
                if o.line.product_id in (1, 2)
            )

        self.assertEqual(shape(self.simulation), shape(other))


class LateSupplierAndDiscontinuedTests(unittest.TestCase):
    """Agreed lead time, not the observed one; in-flight receipts after valid_to."""

    VALID_TO = START + _dt.timedelta(days=45)  # order on day 42 arrives on day 57
    LATE_START = START + _dt.timedelta(days=30)

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config, cls.out, cls.simulation = run_handmade(
            cls._tmp.name,
            "late",
            products=[
                (1, START, cls.VALID_TO),
                (2, START, None),
                (3, cls.LATE_START, None),
            ],
            relations=[
                (1, 2, 5, 0, 1, True, True),
                (2, 1, 3, 0, 1, True, True),
                (3, 2, 7, 0, 1, True, True),
            ],
            demand={1: lambda k: 10, 2: lambda k: 6, 3: lambda k: 8},
            profiles=[
                make_profile(1),
                # Always late by exactly 10 days: observed lead time = agreed + 10.
                make_profile(2, on_time=0, delay=(10, 10)),
            ],
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_replay(self) -> None:
        self.assertEqual(audit(self.out, self.config, self.simulation)[:20], [])

    def test_committed_date_ignores_observed_lead_times(self) -> None:
        # No V1-09: every order commits issued + agreed, however late the previous
        # receipts were.
        late = [o for o in self.simulation.orders if o.supplier_id == 2]
        self.assertGreater(len(late), 2)
        for order in late:
            lead = 5 if order.line.product_id == 1 else 7
            self.assertEqual(order.expected_on, order.issued_on + _dt.timedelta(lead))
            for receipt in order.receipts:
                self.assertEqual(
                    receipt.received_on, order.expected_on + _dt.timedelta(10)
                )

    def test_nothing_happens_after_valid_to_but_in_flight_receipts(self) -> None:
        orders = [o for o in self.simulation.orders if o.line.product_id == 1]
        self.assertTrue(all(o.issued_on <= self.VALID_TO for o in orders))
        consumption = [
            r for r in read_rows(self.out, CONSUMPTION_FILE) if r["product_id"] == "1"
        ]
        self.assertEqual(consumption[-1]["occurred_on"], self.VALID_TO.isoformat())
        after = [
            r
            for r in read_rows(self.out, MOVEMENTS_FILE)
            if r["product_id"] == "1" and day(r["occurred_at"][:10]) > self.VALID_TO
        ]
        self.assertGreater(len(after), 0, "the scenario must have an in-flight receipt")
        for row in after:
            self.assertEqual(row["movement_type"], "RECEIPT")
            self.assertEqual(row["reference_type"], "PURCHASE_ORDER_RECEIPT")
            self.assertNotEqual(row["reference_id"], "")

    def test_late_start_opens_on_its_first_day(self) -> None:
        moves = [
            r for r in read_rows(self.out, MOVEMENTS_FILE) if r["product_id"] == "3"
        ]
        self.assertEqual(moves[0]["movement_type"], "ADJUSTMENT")
        self.assertEqual(moves[0]["occurred_at"], f"{self.LATE_START}T00:00:00Z")


class SplitScenarioTests(unittest.TestCase):
    """D-C4-1 inside the simulation: Q_final = 2, 3, 4, 5 with two split values."""

    #: product -> (supplier, moq, order_multiple, Q_final). One unit every 14 days
    #: puts exactly 2 units in every 28-day window: raw_need = ceil(2 x 21 / 28) = 2.
    CASES = {
        1: (1, 0, 1, 2),
        2: (1, 3, 1, 3),
        3: (1, 4, 1, 4),
        4: (1, 0, 5, 5),
        5: (2, 0, 1, 2),
        6: (2, 3, 1, 3),
        7: (2, 4, 1, 4),
        8: (2, 0, 5, 5),
    }
    SPLIT = {1: 800, 2: 400}
    EXPECTED = {
        (2, 800): (1, 1),
        (3, 800): (2, 1),
        (4, 800): (3, 1),
        (5, 800): (4, 1),
        (2, 400): (1, 1),
        (3, 400): (2, 1),
        (4, 400): (2, 2),
        (5, 400): (2, 3),
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config, cls.out, cls.simulation = run_handmade(
            cls._tmp.name,
            "split",
            products=[(p, START, None) for p in cls.CASES],
            relations=[
                (p, s, 1, moq, multiple, True, True)
                for p, (s, moq, multiple, _) in cls.CASES.items()
            ],
            demand={p: (lambda k: 1 if k % 14 == 0 else 0) for p in cls.CASES},
            profiles=[
                make_profile(s, partial=1000, split=(split, split), lag=(1, 1))
                for s, split in cls.SPLIT.items()
            ],
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_replay(self) -> None:
        self.assertEqual(audit(self.out, self.config, self.simulation)[:20], [])

    def test_every_case_is_exercised_with_two_positive_receipts(self) -> None:
        split_seen = collections.Counter()
        for order in self.simulation.orders:
            supplier, _, _, q_final = self.CASES[order.line.product_id]
            self.assertEqual(order.line.quantity_ordered, q_final)
            expected = self.EXPECTED[(q_final, self.SPLIT[supplier])]
            got = tuple(r.quantity for r in order.receipts)
            if len(got) == 2:
                self.assertEqual(got, expected)
                self.assertEqual(
                    (
                        order.receipts[1].received_on - order.receipts[0].received_on
                    ).days,
                    1,
                )
                split_seen[order.line.product_id] += 1
            else:
                # Only the last order of a product can be cut by the end of the period.
                self.assertIn(got, ((), expected[:1]))
                self.assertNotEqual(order.status, "RECEIVED")
        self.assertEqual(set(split_seen), set(self.CASES))

    def test_moq_and_multiple_stay_independent(self) -> None:
        by_product = {
            o.line.product_id: o.line.quantity_ordered for o in self.simulation.orders
        }
        self.assertEqual(by_product[2], 3)  # MOQ 3 lifts raw 2
        self.assertEqual(by_product[4], 5)  # multiple 5 rounds raw 2, MOQ 0


# =======================================================================================
# Preconditions - DT-038 (decision D-C4-2) and DT-036 section 6
# =======================================================================================


class PreconditionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def attempt(self, *, start=START, end=END, profiles=None, **inputs) -> list[str]:
        config = make_config(
            period={"start_date": start.isoformat(), "end_date": end.isoformat()}
        )
        defaults = dict(
            products=[(1, start, None), (2, start, None), (3, start, None)],
            relations=[(p, 1, 5, 0, 1, True, True) for p in (1, 2, 3)],
            demand={1: lambda k: 3, 2: lambda k: 3, 3: lambda k: 3},
        )
        defaults.update(inputs)
        work = write_inputs(self.tmp / "work", config, **defaults)
        before = tree_digest(work)
        try:
            generate(
                config, work, profiles if profiles is not None else [make_profile(1)]
            )
        except pol.GeneratorError as exc:
            self.assertEqual(tree_digest(work), before, "nothing may be written")
            return exc.problems
        return []

    def test_a_valid_minimal_input_passes(self) -> None:
        self.assertEqual(self.attempt(), [])

    def test_p_c4_2_period_shorter_than_the_window(self) -> None:
        problems = self.attempt(end=START + _dt.timedelta(days=20))
        self.assertTrue(any(p.startswith("P-C4-2") for p in problems), problems)

    def test_period_of_exactly_one_window_passes(self) -> None:
        self.assertEqual(self.attempt(end=START + _dt.timedelta(days=28)), [])

    def test_p_c4_3_product_ending_too_early(self) -> None:
        problems = self.attempt(
            products=[
                (1, START, None),
                (2, START, START + _dt.timedelta(days=9)),
                (3, START, None),
            ]
        )
        self.assertEqual(
            [p for p in problems if p.startswith("P-C4-3")],
            [p for p in problems if "product 2 " in p and p.startswith("P-C4-3")],
        )
        self.assertTrue(any(p.startswith("P-C4-3: product 2 ") for p in problems))

    def test_p_c4_3_product_starting_too_late(self) -> None:
        problems = self.attempt(
            products=[
                (1, START, None),
                (2, START, None),
                (3, END - _dt.timedelta(days=20), None),
            ]
        )
        self.assertTrue(any(p.startswith("P-C4-3: product 3 ") for p in problems))

    def test_p_c4_3_boundary_of_exactly_one_window_passes(self) -> None:
        self.assertEqual(
            self.attempt(
                products=[
                    (1, START, START + _dt.timedelta(days=27)),
                    (2, START, None),
                    (3, END - _dt.timedelta(days=28), None),
                ]
            ),
            [],
        )

    def test_dt036_s6_product_without_any_relation(self) -> None:
        problems = self.attempt(relations=[(p, 1, 5, 0, 1, True, True) for p in (1, 2)])
        self.assertTrue(
            any(p.startswith("DT-036 section 6: product 3 ") for p in problems)
        )

    def test_ordering_supplier_needs_a_profile(self) -> None:
        problems = self.attempt(
            relations=[
                (1, 1, 5, 0, 1, True, True),
                (2, 1, 5, 0, 1, True, True),
                (3, 7, 5, 0, 1, True, True),
            ]
        )
        self.assertTrue(
            any("supplier 7" in p and "SupplierProfile" in p for p in problems),
            problems,
        )

    def test_a_supplier_that_never_orders_needs_no_profile(self) -> None:
        problems = self.attempt(
            relations=[
                (1, 1, 5, 0, 1, True, True),
                (2, 1, 5, 0, 1, True, True),
                (3, 7, 5, 0, 1, False, False),
            ]
        )
        self.assertEqual(problems, [])

    def test_invalid_and_duplicated_profiles(self) -> None:
        problems = self.attempt(
            profiles=[make_profile(1), make_profile(1, delay=(0, 3))]
        )
        self.assertTrue(any("more than one SupplierProfile" in p for p in problems))
        self.assertTrue(any("delay_days" in p for p in problems))
        problems = self.attempt(profiles=[make_profile(1, partial=250)])
        self.assertTrue(any("split_range" in p for p in problems))

    def test_two_active_preferred_relations(self) -> None:
        problems = self.attempt(
            relations=[(p, 1, 5, 0, 1, True, True) for p in (1, 2, 3)]
            + [(1, 2, 5, 0, 1, True, True)],
            profiles=[make_profile(1), make_profile(2)],
        )
        self.assertTrue(any("active preferred" in p for p in problems))

    def test_demand_grid_must_match_the_validity(self) -> None:
        config = make_config(
            period={"start_date": START.isoformat(), "end_date": END.isoformat()}
        )
        work = write_inputs(
            self.tmp / "grid",
            config,
            products=[(1, START, None), (2, START, None), (3, START, None)],
            relations=[(p, 1, 5, 0, 1, True, True) for p in (1, 2, 3)],
            demand={1: lambda k: 3, 2: lambda k: 3, 3: lambda k: 3},
        )
        lines = (work / "demand.csv").read_text().split("\n")
        (work / "demand.csv").write_text("\n".join(lines[:5] + lines[6:]))
        with self.assertRaises(pol.GeneratorError) as raised:
            build_inventory(config, work, [make_profile(1)])
        self.assertTrue(any("demand.csv" in p for p in raised.exception.problems))

    def test_fewer_pairs_than_opening_profiles(self) -> None:
        problems = self.attempt(
            products=[(1, START, None), (2, START, None)],
            relations=[(p, 1, 5, 0, 1, True, True) for p in (1, 2)],
        )
        self.assertTrue(any("opening profile" in p for p in problems))

    def test_every_problem_is_reported_at_once(self) -> None:
        problems = self.attempt(
            end=START + _dt.timedelta(days=20),
            relations=[(p, 1, 5, 0, 1, True, True) for p in (1, 2)],
        )
        self.assertTrue(any(p.startswith("P-C4-2") for p in problems))
        self.assertTrue(any(p.startswith("P-C4-3") for p in problems))
        self.assertTrue(any(p.startswith("DT-036 section 6") for p in problems))

    def test_missing_input_file(self) -> None:
        config = make_config(**SMALL)
        with self.assertRaises(pol.GeneratorError) as raised:
            build_inventory(config, self.tmp, [])
        self.assertIn("products.csv", str(raised.exception))

    def test_missing_manifest_writes_nothing(self) -> None:
        config = make_config(
            period={"start_date": START.isoformat(), "end_date": END.isoformat()}
        )
        work = write_inputs(
            self.tmp / "nomanifest",
            config,
            products=[(1, START, None), (2, START, None), (3, START, None)],
            relations=[(p, 1, 5, 0, 1, True, True) for p in (1, 2, 3)],
            demand={1: lambda k: 3, 2: lambda k: 3, 3: lambda k: 3},
        )
        (work / "manifest.json").unlink()
        with self.assertRaises(pol.GeneratorError):
            generate(config, work, [make_profile(1)])
        self.assertFalse((work / CONSUMPTION_FILE).exists())


# =======================================================================================
# Full scale - the configuration of dataset_config.yaml
# =======================================================================================


class FullScaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config = make_config()
        cls.out = build_pipeline(Path(cls._tmp.name) / "work", cls.config)
        cls.demand_digest = digest(cls.out / "demand.csv")
        suppliers = [int(r["id"]) for r in read_rows(cls.out, "suppliers.csv")]
        cls.manifest, cls.simulation = generate(
            cls.config, cls.out, dt037_profiles(suppliers)
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_replay(self) -> None:
        self.assertEqual(audit(self.out, self.config, self.simulation)[:20], [])

    def test_demand_csv_unchanged(self) -> None:
        self.assertEqual(digest(self.out / "demand.csv"), self.demand_digest)

    def test_products_without_active_supplier_never_order(self) -> None:
        # DT-036 section 6: products 3, 20, 57, 71 and 74 in the current catalogue.
        ordering = {o.line.product_id for o in self.simulation.orders}
        self.assertEqual(ordering & {3, 20, 57, 71, 74}, set())

    def test_the_dataset_holds_the_situations_c4_owns(self) -> None:
        consumption = read_rows(self.out, CONSUMPTION_FILE)
        self.assertTrue(any(r["is_stockout_affected"] == "true" for r in consumption))
        self.assertTrue(any(len(o.receipts) == 2 for o in self.simulation.orders))
        self.assertTrue(
            any(
                r.received_on > o.expected_on
                for o in self.simulation.orders
                for r in o.receipts
            )
        )
        self.assertTrue(any(o.status != "RECEIVED" for o in self.simulation.orders))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
