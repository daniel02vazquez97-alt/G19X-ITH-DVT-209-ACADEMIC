"""Tests for Component 7: Scenario Assignment.

Run from the repository root::

    python3 -m unittest discover -s data/synthetic/tests -t .

Standard library ``unittest``, like the other components (`docs/13-testing.md`).

Scope: `DT-041` - the 16 axes in canonical order with their six fields; shapes and
rotations rebuilt from Component 3 and accepted only if the rebuilt ``demand.csv`` is the
published one byte for byte; supplier axes with ``supplier`` as primary unit and products
as evidence; the observed axes and the four Level C criteria, each with a positive and a
negative case; no CSV written, no random draw, no overwrite; determinism; and the
reference configurations R1, R2, R3 plus a three-supplier variant, checked against an
independent replay written here from the CSV files alone.

The table of `DT-041` section 5, the 16 names and the constants of `DT-036` are written
out here as literals: the tests do not read the values they check from the module under
test.
"""

from __future__ import annotations

import ast
import collections
import datetime as _dt
import hashlib
import inspect
import json
import math
import shutil
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

from data.synthetic.config.config import DatasetConfig
from data.synthetic.generator import (
    catalog,
    demand,
    inventory,
    orders,
    pipeline,
    supplier_behaviour,
)
from data.synthetic.generator import policies as pol
from data.synthetic.generator import scenarios as sc
from data.synthetic.generator.inventory import SupplierProfile
from data.synthetic.generator.rng import (
    COMPONENT_DEMAND,
    COMPONENT_SCENARIOS,
    DeterministicRandom,
    sub_seed,
)
from data.synthetic.generator.supplier_behaviour import build_supplier_profiles
from data.synthetic.generator.writer import (
    SCENARIOS_VERSION,
    add_manifest_field,
)
from data.synthetic.tests.test_inventory import (
    FIXED_TIME,
    SMALL,
    make_config,
    read_rows,
    tree_digest,
)

#: `DT-036` sections 4 and 5, written out.
W, C = 28, 21

#: `DT-023` / `config.Scenario`, in the canonical order, written out.
CANONICAL = (
    "HIGH_ROTATION",
    "LOW_ROTATION",
    "STABLE_DEMAND",
    "GROWING_DEMAND",
    "DECLINING_DEMAND",
    "SEASONAL_DEMAND",
    "INTERMITTENT_DEMAND",
    "ERRATIC_DEMAND",
    "STOCKOUT",
    "OVERSTOCK",
    "LOW_INVENTORY",
    "RELIABLE_SUPPLIER",
    "DELAYED_SUPPLIER",
    "PARTIAL_DELIVERY",
    "MULTIPLE_LEAD_TIMES",
    "IN_TRANSIT",
)

_DEMAND = ("product", "ASSIGNED", "COMPONENT_DECISION", "demand: DT-035 §1-§2")
#: `DT-041` section 5, written out: unit, basis, criterion, source.
TABLE = {
    **{name: _DEMAND for name in CANONICAL[:8]},
    "STOCKOUT": (
        "product",
        "OBSERVED",
        "DOCUMENTED_DEFINITION",
        "inventory: DT-038 §4",
    ),
    "OVERSTOCK": (
        "product",
        "OBSERVED",
        "SYNTHETIC_COVERAGE_CRITERION",
        "scenarios: DT-041 §6.6",
    ),
    "LOW_INVENTORY": (
        "product",
        "OBSERVED",
        "SYNTHETIC_COVERAGE_CRITERION",
        "scenarios: DT-041 §6.5",
    ),
    "RELIABLE_SUPPLIER": (
        "supplier",
        "ASSIGNED",
        "COMPONENT_DECISION",
        "supplier_behaviour: DT-037 §2; spec §12.1",
    ),
    "DELAYED_SUPPLIER": (
        "supplier",
        "ASSIGNED",
        "COMPONENT_DECISION",
        "supplier_behaviour: DT-037 §2; spec §12.2",
    ),
    "PARTIAL_DELIVERY": (
        "supplier",
        "ASSIGNED",
        "COMPONENT_DECISION",
        "supplier_behaviour: DT-037 §2; spec §12.3",
    ),
    "MULTIPLE_LEAD_TIMES": (
        "product",
        "STRUCTURAL",
        "DOCUMENTED_DEFINITION",
        "catalog: DT-028 §1.6.3",
    ),
    "IN_TRANSIT": (
        "product",
        "OBSERVED",
        "DOCUMENTED_DEFINITION",
        "inventory: DT-038 §6.1",
    ),
}
FIELDS = ("unit", "basis", "criterion", "source", "suppliers", "products")
SUPPLIER_AXES = ("RELIABLE_SUPPLIER", "DELAYED_SUPPLIER", "PARTIAL_DELIVERY")

#: The twelve data files of the published dataset (`DT-040`), written out.
DATA_FILES = {
    "categories.csv",
    "consumption.csv",
    "demand.csv",
    "inventory.csv",
    "inventory_movements.csv",
    "locations.csv",
    "product_suppliers.csv",
    "products.csv",
    "purchase_order_items.csv",
    "purchase_order_receipts.csv",
    "purchase_orders.csv",
    "suppliers.csv",
}

#: R2 (the ``SMALL`` fixture) with the Component 6 profiles, pinned on 2026-09-29. A
#: regression oracle: any change to C2-C6 or to a criterion moves one of these lists.
R2_GOLDEN = {
    "HIGH_ROTATION": (None, [2, 4, 5, 8]),
    "LOW_ROTATION": (None, [1, 3, 6, 7, 9, 10, 11, 12]),
    "STABLE_DEMAND": (None, [3, 6, 8, 10]),
    "GROWING_DEMAND": (None, [2, 9]),
    "DECLINING_DEMAND": (None, [4, 12]),
    "SEASONAL_DEMAND": (None, [7, 11]),
    "INTERMITTENT_DEMAND": (None, [5]),
    "ERRATIC_DEMAND": (None, [1]),
    "STOCKOUT": (None, [2, 3, 4, 5, 6, 8, 10]),
    "OVERSTOCK": (None, [1, 7, 9, 10, 11]),
    "LOW_INVENTORY": (None, [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12]),
    "RELIABLE_SUPPLIER": ([3], [1, 6, 10]),
    "DELAYED_SUPPLIER": ([1], [5, 8]),
    "PARTIAL_DELIVERY": ([2], [2]),
    "MULTIPLE_LEAD_TIMES": (None, [1, 5]),
    "IN_TRANSIT": (None, [5, 6, 7, 8, 9, 11]),
}

#: `DT-037` section 2, written out: punctuality and integrity parameters.
_PUNCTUALITY = {
    "PUNCTUAL": (900, (1, 3)),
    "IRREGULAR": (650, (1, 7)),
    "LATE": (250, (3, 14)),
}
_INTEGRITY = {"COMPLETE": (0, None, None), "SPLIT": (250, (400, 800), (1, 10))}


def profile(supplier_id: int, punctuality: str, integrity: str) -> SupplierProfile:
    """A profile with the `DT-037` values of the two named profiles - test data."""
    on_time, delay = _PUNCTUALITY[punctuality]
    partial, split, lag = _INTEGRITY[integrity]
    return SupplierProfile(
        supplier_id, punctuality, integrity, on_time, delay, partial, split, lag
    )


# =======================================================================================
# Hand-made facts - to pin each criterion down with numbers chosen for it
# =======================================================================================

DAYS = 40


def series(
    product: int,
    latent: list[int] | None = None,
    *,
    consumed: list[int] | None = None,
    stockout: list[bool] | dict[int, bool] | None = None,
    on_hand: dict[int, int] | None = None,
    movements: int = 1,
    in_transit: int = 0,
) -> sc.Series:
    """A pair in force on all ``DAYS`` days; ``on_hand`` gives only the non-zero closes."""
    latent = latent if latent is not None else [1] * DAYS
    flags = [False] * len(latent)
    if isinstance(stockout, dict):
        for day, flag in stockout.items():
            flags[day] = flag
    elif stockout is not None:
        flags = list(stockout)
    closes = [0] * DAYS
    for day, value in (on_hand or {}).items():
        closes[day] = value
    return sc.Series(
        product_id=product,
        location_id=1,
        first=0,
        latent=tuple(latent),
        consumed=tuple(consumed if consumed is not None else latent),
        stockout=tuple(flags),
        on_hand=tuple(closes),
        movements=movements,
        in_transit=in_transit,
    )


def order(
    order_id: int,
    product: int,
    *,
    supplier: int = 1,
    issued: int = 0,
    expected: int = 0,
    quantity: int = 10,
    receipts: tuple[tuple[int, int], ...] = (),
    status: str = "RECEIVED",
) -> sc.Order:
    return sc.Order(
        order_id, supplier, 1, product, status, issued, expected, quantity, receipts
    )


def relation(
    product: int, supplier: int = 1, lead: int = 7, preferred: bool = True
) -> sc.Relation:
    return sc.Relation(product, supplier, lead, preferred, True)


def facts(
    *pairs: sc.Series,
    orders: tuple[sc.Order, ...] = (),
    relations: tuple[sc.Relation, ...] = (),
    inactive: tuple[int, ...] = (),
    suppliers: tuple[int, ...] = (1, 2, 3, 4, 5),
) -> sc.Facts:
    return sc.Facts(
        days=DAYS,
        active={s.product_id: s.product_id not in inactive for s in pairs},
        suppliers=frozenset(suppliers),
        relations=tuple(relations),
        series={(s.product_id, s.location_id): s for s in pairs},
        orders=tuple(orders),
    )


# =======================================================================================
# Datasets generated through the real pipeline - C2 -> C3 -> C6 -> C4 -> C5
# =======================================================================================


def generate_dataset(directory: Path, config: DatasetConfig) -> Path:
    """C2 -> C3 -> C6 -> C4 -> C5, the state Component 7 receives inside W1."""
    directory.mkdir(parents=True, exist_ok=True)
    catalog.generate(config, directory, generated_at=FIXED_TIME)
    demand.generate(config, directory, generated_at=FIXED_TIME)
    _, profiles = supplier_behaviour.generate(config, directory)
    _, simulation = inventory.generate(config, directory, profiles)
    orders.generate(config, directory, simulation)
    return directory


def copy_dataset(source: Path, target: Path) -> Path:
    shutil.copytree(source, target)
    return target


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ceil_fraction(numerator: int, denominator: int) -> int:
    return math.ceil(Fraction(numerator, denominator))


def replay(directory: Path, config: DatasetConfig, profiles) -> tuple[dict, dict]:
    """Independent replay of `DT-041` §6.2-§6.6 and §8 from the CSV files alone.

    Written without the module under test: plain dictionaries, ``Fraction`` for every
    ceiling, and the window of `DT-036` §5 recomputed from its formula.
    """
    start = config.period.start_date
    n_days = (config.period.end_date - start).days

    def offset(value: str) -> int:
        return (_dt.date.fromisoformat(value[:10]) - start).days

    latent = collections.defaultdict(dict)
    for r in read_rows(directory, "demand.csv"):
        latent[(int(r["product_id"]), int(r["location_id"]))][
            offset(r["occurred_on"])
        ] = int(r["quantity"])
    consumed, flagged = collections.defaultdict(dict), collections.defaultdict(set)
    for r in read_rows(directory, "consumption.csv"):
        pair = (int(r["product_id"]), int(r["location_id"]))
        consumed[pair][offset(r["occurred_on"])] = int(r["quantity"])
        if r["is_stockout_affected"] == "true":
            flagged[pair].add(offset(r["occurred_on"]))
    delta, moved = collections.defaultdict(collections.Counter), collections.Counter()
    for r in read_rows(directory, "inventory_movements.csv"):
        pair = (int(r["product_id"]), int(r["location_id"]))
        delta[pair][offset(r["occurred_at"])] += int(r["quantity"])
        moved[pair] += 1
    close = {}
    for pair in latent:
        running, values = 0, []
        for day in range(n_days):
            running += delta[pair][day]
            values.append(running)
        close[pair] = values

    relations = read_rows(directory, "product_suppliers.csv")
    lead = {
        int(r["product_id"]): int(r["agreed_lead_time_days"])
        for r in relations
        if r["is_preferred"] == "true" and r["is_active"] == "true"
    }
    lead_times = collections.defaultdict(set)
    for r in relations:
        lead_times[int(r["product_id"])].add(int(r["agreed_lead_time_days"]))

    ordered = {pair: sorted(days) for pair, days in latent.items()}
    prefix = {}
    for pair, days in ordered.items():
        running = [0]
        for d in days:
            running.append(running[-1] + latent[pair][d])
        prefix[pair] = running

    def window(pair, day):
        position = day - ordered[pair][0]  # the series is dense (DT-034)
        begin = max(0, position - W)
        return prefix[pair][begin + W] - prefix[pair][begin]

    def overstocked(pair, day):
        w = window(pair, day)
        return w > 0 and close[pair][day] > ceil_fraction(w * (lead[pair[0]] + C), W)

    over_days = {
        pair: [
            d for d in sorted(latent[pair]) if pair[0] in lead and overstocked(pair, d)
        ]
        for pair in latent
    }

    items = {
        int(r["purchase_order_id"]): r
        for r in read_rows(directory, "purchase_order_items.csv")
    }
    receipts = collections.defaultdict(list)
    for r in read_rows(directory, "purchase_order_receipts.csv"):
        receipts[int(r["purchase_order_item_id"])].append(
            (offset(r["received_at"]), int(r["id"]), int(r["quantity_received"]))
        )
    orders = []
    for r in read_rows(directory, "purchase_orders.csv"):
        if r["status"] == "CANCELLED":
            continue
        line = items[int(r["id"])]
        orders.append(
            {
                "supplier": int(r["supplier_id"]),
                "pair": (int(line["product_id"]), int(r["location_id"])),
                "status": r["status"],
                "issued": offset(r["issued_at"]),
                "expected": offset(r["expected_at"]),
                "quantity": int(line["quantity_ordered"]),
                "receipts": sorted(receipts[int(line["id"])]),
            }
        )

    kinds = {p.supplier_id: (p.punctuality, p.integrity) for p in profiles}
    reliable = sorted(s for s, k in kinds.items() if k == ("PUNCTUAL", "COMPLETE"))
    late = sorted(s for s, k in kinds.items() if k[0] == "LATE")
    split = sorted(s for s, k in kinds.items() if k[1] == "SPLIT")
    axes = {
        "STOCKOUT": sorted({p for p, _ in flagged if flagged[(p, _)]}),
        "IN_TRANSIT": sorted(
            int(r["product_id"])
            for r in read_rows(directory, "inventory.csv")
            if int(r["quantity_in_transit"]) > 0
        ),
        "MULTIPLE_LEAD_TIMES": sorted(p for p, v in lead_times.items() if len(v) > 1),
        "LOW_INVENTORY": sorted(
            {o["pair"][0] for o in orders if close[o["pair"]][o["issued"]] > 0}
        ),
        "OVERSTOCK": sorted({pair[0] for pair, days in over_days.items() if days}),
        "RELIABLE_SUPPLIER": (
            reliable,
            sorted(
                {
                    o["pair"][0]
                    for o in orders
                    if o["supplier"] in reliable and o["status"] == "RECEIVED"
                }
            ),
        ),
        "DELAYED_SUPPLIER": (
            late,
            sorted(
                {
                    o["pair"][0]
                    for o in orders
                    if o["supplier"] in late
                    and o["receipts"]
                    and o["receipts"][0][0] > o["expected"]
                }
            ),
        ),
        "PARTIAL_DELIVERY": (
            split,
            sorted(
                {
                    o["pair"][0]
                    for o in orders
                    if o["supplier"] in split
                    and any(q < o["quantity"] for _, _, q in o["receipts"])
                }
            ),
        ),
    }

    censored = sorted(
        {
            pair[0]
            for pair, days in flagged.items()
            if any(latent[pair][d] > consumed[pair][d] for d in days)
        }
    )
    late_transit, moq_overstock = set(), set()
    for o in orders:
        pair = o["pair"]
        first = o["receipts"][0][0] if o["receipts"] else n_days
        span = [d for d in latent[pair] if o["issued"] < d < first]
        if o["quantity"] > sum(latent[pair][d] for d in span) and any(
            d in flagged[pair] for d in span
        ):
            late_transit.add(pair[0])
        if pair[0] in lead and o["receipts"]:
            q_sint = ceil_fraction(window(pair, o["issued"]) * C, W)
            if o["quantity"] > q_sint and any(d >= first for d in over_days[pair]):
                moq_overstock.add(pair[0])
    received = {o["pair"][0] for o in orders if o["receipts"]}
    history = sorted(
        int(r["id"])
        for r in read_rows(directory, "products.csv")
        if r["is_active"] == "false"
        and int(r["id"]) in received
        and any(
            sum(consumed[pair].values()) > 0 and moved[pair] > 0
            for pair in latent
            if pair[0] == int(r["id"])
        )
    )
    emergent = {
        "censored_demand": tuple(censored),
        "late_transit": tuple(sorted(late_transit)),
        "moq_overstock": tuple(sorted(moq_overstock)),
        "inactive_with_history": tuple(history),
    }
    return axes, emergent


# =======================================================================================
# The arithmetic of DT-041 §6.6 and §8
# =======================================================================================


class ArithmeticTests(unittest.TestCase):
    def test_policy_constants_are_dt036(self) -> None:
        self.assertEqual(
            (pol.INVENTORY_WINDOW_DAYS, pol.INVENTORY_ORDER_COVERAGE_DAYS), (W, C)
        )

    def test_window_is_frozen_during_the_warm_up_then_slides(self) -> None:
        latent = list(range(1, 61))
        for position in (0, 5, 27, 28):
            self.assertEqual(sc.window_sum(latent, position), sum(range(1, 29)))
        self.assertEqual(sc.window_sum(latent, 40), sum(latent[12:40]))
        with self.assertRaises(ValueError):
            sc.window_sum(latent[:27], 0)

    def test_overstock_threshold_is_exact(self) -> None:
        for window, lead in ((28, 7), (1, 1), (13, 40), (0, 9), (999, 45)):
            self.assertEqual(
                sc.overstock_threshold(window, lead),
                ceil_fraction(window * (lead + C), W),
            )

    def test_overstock_boundary(self) -> None:
        threshold = sc.overstock_threshold(28, 7)
        self.assertEqual(threshold, 28)
        self.assertFalse(sc.is_overstocked(threshold, 28, 7))  # at the threshold: no
        self.assertTrue(sc.is_overstocked(threshold + 1, 28, 7))  # above: yes

    def test_no_recent_demand_is_never_overstock(self) -> None:
        self.assertFalse(sc.is_overstocked(10**6, 0, 7))

    def test_synthetic_quantity(self) -> None:
        for window in (0, 1, 28, 29, 1000):
            self.assertEqual(
                sc.synthetic_quantity(window), ceil_fraction(window * C, W)
            )


# =======================================================================================
# Observed axes - DT-041 §6.3 to §6.6
# =======================================================================================


class ObservedAxisTests(unittest.TestCase):
    def test_stockout(self) -> None:
        axes = sc.observed_axes(facts(series(1, stockout={3: True}), series(2)))
        self.assertEqual(axes["STOCKOUT"], [1])

    def test_in_transit(self) -> None:
        axes = sc.observed_axes(facts(series(1, in_transit=5), series(2, in_transit=0)))
        self.assertEqual(axes["IN_TRANSIT"], [1])

    def test_multiple_lead_times(self) -> None:
        axes = sc.observed_axes(
            facts(
                series(1),
                series(2),
                series(3),
                relations=(
                    relation(1, 1, 7),  # one relation: no
                    relation(2, 1, 7),
                    relation(2, 2, 7, preferred=False),  # same LT: no
                    relation(3, 1, 7),
                    relation(3, 2, 9, preferred=False),  # distinct: yes
                ),
            )
        )
        self.assertEqual(axes["MULTIPLE_LEAD_TIMES"], [3])

    def test_low_inventory(self) -> None:
        axes = sc.observed_axes(
            facts(
                series(1, on_hand={5: 3}),
                series(2, on_hand={5: 0}),
                series(3, on_hand={5: 3}),
                orders=(
                    order(1, 1, issued=5),  # stock > 0 at the close: yes
                    order(2, 2, issued=5),  # stock = 0: the stockout itself, no
                    order(3, 3, issued=5, status="CANCELLED"),  # not causal: no
                ),
            )
        )
        self.assertEqual(axes["LOW_INVENTORY"], [1])

    def test_overstock(self) -> None:
        # Demand 1/day: window 28, L = 7, threshold ceil(28 x 28 / 28) = 28.
        axes = sc.observed_axes(
            facts(
                series(1, on_hand={d: 28 for d in range(DAYS)}),  # at the threshold
                series(2, on_hand={35: 29}),  # above it on one day
                series(3, latent=[0] * DAYS, on_hand={d: 1000 for d in range(DAYS)}),
                series(4, on_hand={35: 29}),  # no preferred active relation
                relations=(
                    relation(1),
                    relation(2),
                    relation(3),
                    relation(4, preferred=False),
                ),
            )
        )
        self.assertEqual(axes["OVERSTOCK"], [2])

    def test_two_preferred_active_relations_are_rejected(self) -> None:
        with self.assertRaises(pol.GeneratorError):
            sc.observed_axes(
                facts(series(1), relations=(relation(1, 1), relation(1, 2)))
            )


# =======================================================================================
# Supplier axes - DT-041 §6.2
# =======================================================================================


class SupplierAxisTests(unittest.TestCase):
    PROFILES = (
        profile(1, "PUNCTUAL", "COMPLETE"),
        profile(2, "PUNCTUAL", "SPLIT"),
        profile(3, "LATE", "COMPLETE"),
        profile(4, "IRREGULAR", "SPLIT"),
        profile(5, "LATE", "SPLIT"),
    )
    ORDERS = (
        order(1, 1, supplier=1, receipts=((10, 10),)),
        order(2, 2, supplier=2, receipts=((10, 10),)),
        order(3, 3, supplier=3, expected=5, receipts=((8, 10),)),
        order(4, 4, supplier=4, expected=5, receipts=((9, 4), (12, 6))),
        order(5, 5, supplier=5, expected=5, receipts=((5, 10),)),
        order(6, 6, supplier=3, expected=5, status="ISSUED"),
    )

    def setUp(self) -> None:
        self.axes = sc.supplier_axes(
            facts(series(1), orders=self.ORDERS), self.PROFILES
        )

    def test_reliable_is_punctual_and_complete(self) -> None:
        self.assertEqual(self.axes["RELIABLE_SUPPLIER"], ([1], [1]))

    def test_delayed_is_late_and_manifests_only_on_a_late_receipt(self) -> None:
        # Supplier 5 is LATE but its only order arrived on time: listed, no product.
        self.assertEqual(self.axes["DELAYED_SUPPLIER"], ([3, 5], [3]))

    def test_partial_is_split_and_manifests_only_on_a_short_receipt(self) -> None:
        # Supplier 2 is SPLIT but delivered in full; supplier 5 delivered in full too.
        self.assertEqual(self.axes["PARTIAL_DELIVERY"], ([2, 4, 5], [4]))

    def test_irregular_is_never_labelled(self) -> None:
        self.assertNotIn(4, self.axes["RELIABLE_SUPPLIER"][0])
        self.assertNotIn(4, self.axes["DELAYED_SUPPLIER"][0])

    def test_a_profile_without_evidence_does_not_manifest(self) -> None:
        axes = sc.supplier_axes(
            facts(series(1), orders=(order(1, 1, supplier=1, status="ISSUED"),)),
            (profile(1, "PUNCTUAL", "COMPLETE"),),
        )
        self.assertEqual(axes["RELIABLE_SUPPLIER"], ([1], []))

    def test_cancelled_orders_are_not_evidence(self) -> None:
        axes = sc.supplier_axes(
            facts(series(1), orders=(order(1, 1, supplier=1, status="CANCELLED"),)),
            (profile(1, "PUNCTUAL", "COMPLETE"),),
        )
        self.assertEqual(axes["RELIABLE_SUPPLIER"], ([1], []))

    def test_profiles_must_match_the_suppliers(self) -> None:
        pairs = facts(series(1), orders=(order(1, 1, supplier=1),))
        for profiles in (
            (profile(1, "LATE", "SPLIT"), profile(1, "LATE", "SPLIT")),  # duplicate
            (profile(1, "LATE", "SPLIT"), profile(99, "LATE", "SPLIT")),  # unknown
            (profile(2, "LATE", "SPLIT"),),  # an ordering supplier without a profile
        ):
            with self.subTest(profiles=profiles), self.assertRaises(pol.GeneratorError):
                sc.supplier_axes(pairs, profiles)


# =======================================================================================
# Level C - DT-041 §8, each with a positive and a negative case
# =======================================================================================


class EmergentPropertyTests(unittest.TestCase):
    def test_censored_demand(self) -> None:
        result = sc.emergent_properties(
            facts(
                series(
                    1,
                    latent=[5] * DAYS,
                    consumed=[5] * 3 + [2] + [5] * 36,
                    stockout={3: True},
                ),
                series(2, latent=[5] * DAYS, stockout={3: True}),  # flag, no shortfall
                series(
                    3, latent=[5] * DAYS, consumed=[5] * 3 + [2] + [5] * 36
                ),  # no flag
            )
        )
        self.assertEqual(result.censored_demand, (1,))

    def test_late_transit(self) -> None:
        # Demand 1/day. Open interval (0, 5): days 1-4, latent 4.
        result = sc.emergent_properties(
            facts(
                series(1, stockout={2: True}),
                series(2, stockout={0: True, 5: True}),  # only at the interval's ends
                series(3, stockout={2: True}),
                series(4, stockout={30: True}),
                series(5, stockout={2: True}),
                orders=(
                    order(1, 1, quantity=10, receipts=((5, 10),)),  # yes
                    order(2, 2, quantity=10, receipts=((5, 10),)),  # no stockout inside
                    order(3, 3, quantity=4, receipts=((5, 4),)),  # not above the need
                    order(4, 4, quantity=50, status="ISSUED"),  # no receipt: to the end
                    order(5, 5, quantity=10, status="CANCELLED"),  # not causal
                ),
            )
        )
        self.assertEqual(result.late_transit, (1, 4))

    def test_moq_overstock(self) -> None:
        # Demand 1/day: window 28, Q_sint = 21, L = 7, threshold 28.
        result = sc.emergent_properties(
            facts(
                series(1, on_hand={32: 29}),
                series(2, on_hand={32: 29}),
                series(3, on_hand={29: 29}),
                series(4, on_hand={32: 29}),
                orders=(
                    order(1, 1, issued=28, quantity=30, receipts=((30, 30),)),  # yes
                    order(
                        2, 2, issued=28, quantity=21, receipts=((30, 21),)
                    ),  # = Q_sint
                    order(
                        3, 3, issued=28, quantity=30, receipts=((30, 30),)
                    ),  # before it
                    order(4, 4, issued=28, quantity=30, status="ISSUED"),  # no receipt
                ),
                relations=(relation(1), relation(2), relation(3), relation(4)),
            )
        )
        self.assertEqual(result.moq_overstock, (1,))

    def test_inactive_with_history(self) -> None:
        result = sc.emergent_properties(
            facts(
                series(1),
                series(2),
                series(3),
                series(4, consumed=[0] * DAYS),
                series(5, movements=0),
                orders=(
                    order(1, 1, receipts=((3, 10),)),
                    order(2, 2, receipts=((3, 10),)),
                    order(3, 3, status="ISSUED"),  # no receipt
                    order(4, 4, receipts=((3, 10),)),
                    order(5, 5, receipts=((3, 10),)),
                ),
                inactive=(1, 3, 4, 5),  # 2 is active
            )
        )
        self.assertEqual(result.inactive_with_history, (1,))


# =======================================================================================
# The component on a real dataset - R2
# =======================================================================================


class R2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config = make_config(**SMALL)
        cls.source = generate_dataset(Path(cls._tmp.name) / "r2", cls.config)
        cls.profiles = build_supplier_profiles(cls.config, cls.source)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def copy(self, name: str) -> Path:
        return copy_dataset(self.source, Path(self._tmp.name) / name)

    # --- B. the 16 keys and their six fields ------------------------------------------

    def test_sixteen_keys_in_canonical_order_with_their_table(self) -> None:
        assignment = sc.build_assignment(self.config, self.source, self.profiles)
        self.assertEqual(tuple(assignment), CANONICAL)
        for name, entry in assignment.items():
            with self.subTest(scenario=name):
                self.assertEqual(tuple(entry), FIELDS)
                self.assertEqual(
                    (
                        entry["unit"],
                        entry["basis"],
                        entry["criterion"],
                        entry["source"],
                    ),
                    TABLE[name],
                )
                ids = entry["products"]
                self.assertEqual(ids, sorted(set(ids)))
                if name in SUPPLIER_AXES:
                    self.assertEqual(
                        entry["suppliers"], sorted(set(entry["suppliers"]))
                    )
                else:
                    self.assertIsNone(entry["suppliers"])

    def test_golden(self) -> None:
        assignment = sc.build_assignment(self.config, self.source, self.profiles)
        got = {k: (v["suppliers"], v["products"]) for k, v in assignment.items()}
        self.assertEqual(got, R2_GOLDEN)

    # --- C. Component 3 ---------------------------------------------------------------

    def test_shapes_and_rotations_partition_the_catalogue(self) -> None:
        assignment = sc.build_assignment(self.config, self.source, self.profiles)
        products = [int(r["id"]) for r in read_rows(self.source, "products.csv")]
        shapes = [p for name in CANONICAL[2:8] for p in assignment[name]["products"]]
        rotations = [p for name in CANONICAL[:2] for p in assignment[name]["products"]]
        self.assertEqual(sorted(shapes), products)
        self.assertEqual(sorted(rotations), products)

    def test_a_changed_demand_file_is_refused(self) -> None:
        work = self.copy("tampered-demand")
        path = work / "demand.csv"
        lines = path.read_text(encoding="utf-8").split("\n")
        fields = lines[1].split(",")
        fields[4] = str(int(fields[4]) + 1)
        lines[1] = ",".join(fields)
        path.write_text("\n".join(lines), encoding="utf-8", newline="")
        before = sha(work / "manifest.json")
        with self.assertRaises(pol.GeneratorError):
            sc.generate(self.config, work, self.profiles)
        self.assertEqual(sha(work / "manifest.json"), before)

    def test_a_changed_manifest_digest_is_refused(self) -> None:
        work = self.copy("tampered-manifest")
        manifest = json.loads((work / "manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            if entry["name"] == "demand.csv":
                entry["sha256"] = "0" * 64
        (work / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(pol.GeneratorError):
            sc.build_assignment(self.config, work, self.profiles)

    def test_a_rebuild_that_differs_from_component_3_is_refused(self) -> None:
        skewed = dict(pol.DEMAND_SHAPE_MIX)
        skewed["STABLE_DEMAND"], skewed["ERRATIC_DEMAND"] = (
            skewed["ERRATIC_DEMAND"],
            skewed["STABLE_DEMAND"],
        )
        with mock.patch.object(pol, "DEMAND_SHAPE_MIX", skewed):
            with self.assertRaises(pol.GeneratorError):
                sc.build_assignment(self.config, self.source, self.profiles)

    # --- D/E. Component 6 on a real dataset -------------------------------------------

    def test_profiles_of_component_6(self) -> None:
        kinds = {p.supplier_id: (p.punctuality, p.integrity) for p in self.profiles}
        assignment = sc.build_assignment(self.config, self.source, self.profiles)
        expected = {
            "RELIABLE_SUPPLIER": sorted(
                s for s, k in kinds.items() if k == ("PUNCTUAL", "COMPLETE")
            ),
            "DELAYED_SUPPLIER": sorted(s for s, k in kinds.items() if k[0] == "LATE"),
            "PARTIAL_DELIVERY": sorted(s for s, k in kinds.items() if k[1] == "SPLIT"),
        }
        for name, suppliers in expected.items():
            self.assertEqual(assignment[name]["suppliers"], suppliers)

    # --- L/M. only the manifest changes -----------------------------------------------

    def test_generate_writes_only_the_manifest(self) -> None:
        work = self.copy("generate")
        before = tree_digest(work)
        manifest = sc.generate(self.config, work, self.profiles)
        after = tree_digest(work)
        self.assertEqual(set(after), set(before))
        self.assertEqual(set(after), DATA_FILES | {"manifest.json"})
        changed = {name for name in before if before[name] != after[name]}
        self.assertEqual(changed, {"manifest.json"})

        on_disk = json.loads((work / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(on_disk, manifest)
        self.assertEqual(list(on_disk)[-1], "scenario_assignment")
        self.assertEqual(tuple(on_disk["scenario_assignment"]), CANONICAL)
        entry = [c for c in on_disk["components"] if c["name"] == "scenarios"]
        self.assertEqual(
            entry,
            [
                {
                    "name": "scenarios",
                    "version": "0.1.0",
                    "sub_seed": sub_seed(self.config.seed, "scenarios"),
                }
            ],
        )
        original = json.loads(
            (self.source / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(on_disk["files"], original["files"])
        for key in original:
            if key != "components":
                self.assertEqual(on_disk[key], original[key])

    def test_file_contract_of_the_dataset_is_unchanged(self) -> None:
        self.assertEqual(set(pipeline.FILE_COLUMNS), DATA_FILES)
        self.assertEqual(
            pipeline.DATASET_FILES, frozenset(DATA_FILES | {"manifest.json"})
        )

    # --- N. never overwrite -----------------------------------------------------------

    def test_a_second_call_fails_and_changes_nothing(self) -> None:
        work = self.copy("twice")
        sc.generate(self.config, work, self.profiles)
        before = tree_digest(work)
        with self.assertRaises(pol.GeneratorError):
            sc.generate(self.config, work, self.profiles)
        self.assertEqual(tree_digest(work), before)

    def test_an_existing_component_entry_also_blocks(self) -> None:
        work = self.copy("component-only")
        path = work / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["components"].append(
            {"name": "scenarios", "version": "x", "sub_seed": 0}
        )
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(pol.GeneratorError):
            sc.generate(self.config, work, self.profiles)

    def test_add_manifest_field_refuses_to_overwrite(self) -> None:
        manifest = {"a": 1}
        self.assertEqual(add_manifest_field(manifest, "b", 2), {"a": 1, "b": 2})
        self.assertEqual(manifest, {"a": 1})
        with self.assertRaises(ValueError):
            add_manifest_field(manifest, "a", 3)

    def test_missing_manifest_fails(self) -> None:
        work = self.copy("no-manifest")
        (work / "manifest.json").unlink()
        with self.assertRaises(pol.GeneratorError):
            sc.generate(self.config, work, self.profiles)

    # --- A. determinism ---------------------------------------------------------------

    def test_determinism(self) -> None:
        first, second = self.copy("run-1"), self.copy("run-2")
        sc.generate(self.config, first, self.profiles)
        sc.generate(self.config, second, list(reversed(self.profiles)))
        self.assertEqual(tree_digest(first), tree_digest(second))

    # --- O. an empty axis is recorded, not an error -----------------------------------

    def test_an_empty_axis_is_recorded(self) -> None:
        everyone_reliable = [
            profile(p.supplier_id, "PUNCTUAL", "COMPLETE") for p in self.profiles
        ]
        assignment = sc.build_assignment(self.config, self.source, everyone_reliable)
        self.assertEqual(assignment["DELAYED_SUPPLIER"]["suppliers"], [])
        self.assertEqual(assignment["DELAYED_SUPPLIER"]["products"], [])
        self.assertEqual(assignment["PARTIAL_DELIVERY"]["products"], [])

    def test_all_sixteen_whatever_scenarios_required_says(self) -> None:
        narrow = make_config(**SMALL, scenarios={"required": ["STOCKOUT"]})
        assignment = sc.build_assignment(narrow, self.source, self.profiles)
        self.assertEqual(tuple(assignment), CANONICAL)
        self.assertEqual(
            assignment, sc.build_assignment(self.config, self.source, self.profiles)
        )

    # --- no random draw ---------------------------------------------------------------

    def test_no_stream_of_its_own(self) -> None:
        bases = []
        original = DeterministicRandom.__init__

        def spy(instance, seed, label):
            bases.append(int(seed))
            original(instance, seed, label)

        with mock.patch.object(DeterministicRandom, "__init__", spy):
            sc.generate(self.config, self.copy("spy"), self.profiles)
        # The only draws are Component 3's own, repeated to rebuild its profiles.
        self.assertTrue(bases)
        self.assertEqual(set(bases), {sub_seed(self.config.seed, COMPONENT_DEMAND)})
        self.assertNotIn(sub_seed(self.config.seed, COMPONENT_SCENARIOS), bases)

    def test_source_uses_no_randomness(self) -> None:
        tree = ast.parse(inspect.getsource(sc))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        imported = {
            alias.name
            for n in ast.walk(tree)
            if isinstance(n, (ast.Import, ast.ImportFrom))
            for alias in n.names
        }
        self.assertNotIn("DeterministicRandom", names | imported)
        self.assertNotIn("random", imported)
        self.assertNotIn("write_csv", names | imported)

    # --- W1 is not integrated yet (DT-041 §12) ----------------------------------------

    def test_part_of_the_published_pipeline(self) -> None:
        # Integrated in W1 with Component 8 (DT-042 section 8, decision C7/C8-11).
        self.assertEqual(pipeline.COMPONENT_VERSIONS["scenarios"], SCENARIOS_VERSION)
        self.assertEqual(SCENARIOS_VERSION, "0.1.0")
        manifest = json.loads(
            (self.source / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("scenario_assignment", manifest)  # the fixture stops at C5
        with tempfile.TemporaryDirectory() as tmp:
            published = pipeline.generate_into(
                self.config, Path(tmp), generated_at=FIXED_TIME
            )
        self.assertEqual(
            published["scenario_assignment"],
            sc.build_assignment(self.config, self.source, self.profiles),
        )


# =======================================================================================
# P. Reference configurations, against the independent replay
# =======================================================================================


class ReferenceConfigurationTests(unittest.TestCase):
    """R1, R2, R3 (`DT-033`) and R1 with three suppliers (the floor of P-C6-1)."""

    CONFIGS = {
        "R1": {},
        "R2": SMALL,
        "R3": {
            "scale": {
                "product_count": 1200,
                "supplier_count": 10,
                "category_count": 1000,
            },
            "period": SMALL["period"],
        },
        "R1-3-suppliers": {"scale": {"supplier_count": 3}},
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.runs = {}
        for name, overrides in cls.CONFIGS.items():
            config = make_config(**overrides)
            work = generate_dataset(Path(cls._tmp.name) / name, config)
            profiles = build_supplier_profiles(config, work)
            manifest = sc.generate(config, work, profiles)
            cls.runs[name] = (
                config,
                manifest[sc.SCENARIO_ASSIGNMENT_FIELD],
                sc.emergent_properties(sc.load_facts(config, work)),
                replay(work, config, profiles),
            )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_every_axis_is_covered(self) -> None:
        for name, (_, assignment, _, _) in self.runs.items():
            for scenario in CANONICAL:
                with self.subTest(config=name, scenario=scenario):
                    self.assertTrue(assignment[scenario]["products"])
                    if scenario in SUPPLIER_AXES:
                        self.assertTrue(assignment[scenario]["suppliers"])

    def test_matches_the_independent_replay(self) -> None:
        for name, (_, assignment, emergent, (axes, expected)) in self.runs.items():
            for scenario, value in axes.items():
                with self.subTest(config=name, scenario=scenario):
                    entry = assignment[scenario]
                    if scenario in SUPPLIER_AXES:
                        self.assertEqual((entry["suppliers"], entry["products"]), value)
                    else:
                        self.assertEqual(entry["products"], value)
            with self.subTest(config=name, level="C"):
                self.assertEqual({k: getattr(emergent, k) for k in expected}, expected)

    def test_every_level_c_situation_is_present(self) -> None:
        for name, (_, _, emergent, _) in self.runs.items():
            for field in (
                "censored_demand",
                "late_transit",
                "moq_overstock",
                "inactive_with_history",
            ):
                with self.subTest(config=name, situation=field):
                    self.assertTrue(getattr(emergent, field))

    def test_r1_figures_of_the_audit(self) -> None:
        _, assignment, emergent, _ = self.runs["R1"]
        counts = {k: len(v["products"]) for k, v in assignment.items()}
        self.assertEqual(
            counts,
            {
                "HIGH_ROTATION": 30,
                "LOW_ROTATION": 70,
                "STABLE_DEMAND": 30,
                "GROWING_DEMAND": 15,
                "DECLINING_DEMAND": 15,
                "SEASONAL_DEMAND": 20,
                "INTERMITTENT_DEMAND": 10,
                "ERRATIC_DEMAND": 10,
                "STOCKOUT": 100,
                "OVERSTOCK": 43,
                "LOW_INVENTORY": 95,
                "RELIABLE_SUPPLIER": 29,
                "DELAYED_SUPPLIER": 19,
                "PARTIAL_DELIVERY": 28,
                "MULTIPLE_LEAD_TIMES": 15,
                "IN_TRANSIT": 65,
            },
        )
        self.assertEqual(
            [
                len(getattr(emergent, f))
                for f in ("censored_demand", "late_transit", "moq_overstock")
            ],
            [100, 67, 26],
        )
        self.assertEqual(emergent.inactive_with_history, (21, 26, 37, 56, 61))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
