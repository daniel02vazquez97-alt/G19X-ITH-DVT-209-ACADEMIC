"""Tests for Component 2: the Catalog Generator.

Run from the repository root::

    python3 -m unittest discover -s data/synthetic/tests -t .

Standard library ``unittest``, like Component 1: no test dependency beyond PyYAML
(`docs/13-testing.md`).

Scope: the five master entities, their output contract and the determinism that carries
them. Nothing about demand, inventory, orders or the supply engine - none of that exists.

The expected values are checked against the ADRs, not against whatever the code happens
to produce: the Zipf distribution against `DT-028` section 3.3, the column order against
`DT-024`, the sub-seed against the formula in `DT-030`.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from data.synthetic.config.config import DatasetConfig, Scenario
from data.synthetic.generator import policies as pol
from data.synthetic.generator.catalog import (
    CATEGORY_COLUMNS,
    LOCATION_COLUMNS,
    PRODUCT_COLUMNS,
    PRODUCT_SUPPLIER_COLUMNS,
    SUPPLIER_COLUMNS,
    build_catalog,
    generate,
)
from data.synthetic.generator.rng import (
    COMPONENT_CATALOG,
    COMPONENT_IDS,
    DeterministicRandom,
    sub_seed,
)
from data.synthetic.generator.writer import (
    CATALOG_VERSION,
    GENERATOR_VERSION,
    dataset_version,
    format_cents,
    format_value,
    render_csv,
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

FIXED_TIME = _dt.datetime(2026, 9, 21, 12, 0, 0, tzinfo=_dt.timezone.utc)


def make_config(**overrides) -> DatasetConfig:
    """A valid configuration, with ``scale`` and ``period`` overridable per test."""
    raw = json.loads(json.dumps(BASE_CONFIG))
    for key, value in overrides.items():
        if key in ("scale", "period"):
            raw[key].update(value)
        else:
            raw[key] = value
    return DatasetConfig.from_mapping(raw)


# =======================================================================================
# Determinism - DT-030, DT-032
# =======================================================================================


class SubSeedTests(unittest.TestCase):
    def test_matches_the_formula_of_dt_030(self) -> None:
        # Recomputed here from the ADR text rather than imported, so the test fails if
        # the implementation drifts from the decision.
        expected = int.from_bytes(
            hashlib.sha256(b"20260913:catalog").digest()[:8], "big"
        )
        self.assertEqual(sub_seed(20260913, COMPONENT_CATALOG), expected)

    def test_component_identifier_is_catalog(self) -> None:
        self.assertEqual(COMPONENT_CATALOG, "catalog")

    def test_different_components_get_different_sub_seeds(self) -> None:
        self.assertNotEqual(sub_seed(1, "catalog"), sub_seed(1, "demand"))

    def test_different_seeds_get_different_sub_seeds(self) -> None:
        self.assertNotEqual(sub_seed(1, "catalog"), sub_seed(2, "catalog"))

    def test_rejects_a_negative_seed(self) -> None:
        with self.assertRaises(ValueError):
            sub_seed(-1, "catalog")


class CanonicalComponentIdTests(unittest.TestCase):
    """The canonical identifier table of `DT-030`, fixed on 2026-09-21.

    These identifiers are the input of the sub-seed, so pinning them is pinning the
    data. A test that merely read the constants back would prove nothing; each expected
    value is written out here as a literal, so changing an identifier in the source
    fails loudly instead of silently producing a different dataset.
    """

    EXPECTED = {
        2: "catalog",
        3: "demand",
        4: "inventory",
        5: "orders",
        6: "supplier_behaviour",
        7: "scenarios",
        8: "validator",
    }

    def test_the_table_is_exactly_the_approved_one(self) -> None:
        self.assertEqual(COMPONENT_IDS, self.EXPECTED)

    def test_component_2_keeps_the_identifier_it_already_used(self) -> None:
        # Changing this would change every byte Component 2 has produced so far.
        self.assertEqual(COMPONENT_CATALOG, "catalog")
        self.assertEqual(COMPONENT_IDS[2], COMPONENT_CATALOG)

    def test_component_1_has_no_identifier(self) -> None:
        # DatasetConfig draws nothing from the stream, so it has no sub-seed to derive.
        self.assertNotIn(1, COMPONENT_IDS)

    def test_identifiers_are_short_lowercase_ascii(self) -> None:
        for number, name in COMPONENT_IDS.items():
            with self.subTest(component=number):
                self.assertTrue(name.isascii(), name)
                self.assertEqual(name, name.lower())
                self.assertRegex(name, r"^[a-z][a-z_]*[a-z]$")
                self.assertLessEqual(len(name), 20, name)

    def test_identifiers_are_distinct_from_their_number(self) -> None:
        # DT-030 requires this: an identifier derived from the number would make
        # renumbering the components rewrite the data.
        for number, name in COMPONENT_IDS.items():
            with self.subTest(component=number):
                self.assertFalse(name.isdigit())
                self.assertNotIn(str(number), name)

    def test_identifiers_are_unique(self) -> None:
        self.assertEqual(len(set(COMPONENT_IDS.values())), len(COMPONENT_IDS))

    def test_every_identifier_yields_a_distinct_sub_seed(self) -> None:
        seeds = {name: sub_seed(20260913, name) for name in COMPONENT_IDS.values()}
        self.assertEqual(len(set(seeds.values())), len(seeds), seeds)

    def test_each_sub_seed_matches_the_formula_of_dt_030(self) -> None:
        for number, name in COMPONENT_IDS.items():
            with self.subTest(component=number, identifier=name):
                expected = int.from_bytes(
                    hashlib.sha256(f"20260913:{name}".encode("utf-8")).digest()[:8],
                    "big",
                )
                self.assertEqual(sub_seed(20260913, name), expected)

    def test_renumbering_would_not_change_any_sub_seed(self) -> None:
        # The property the table exists to guarantee: the sub-seed depends on the
        # identifier alone, so shifting every number by one changes nothing.
        shifted = {number + 1: name for number, name in COMPONENT_IDS.items()}
        self.assertEqual(
            [sub_seed(7, n) for n in COMPONENT_IDS.values()],
            [sub_seed(7, n) for n in shifted.values()],
        )


class DeterministicRandomTests(unittest.TestCase):
    def test_same_seed_and_label_give_the_same_sequence(self) -> None:
        a = DeterministicRandom(7, "x")
        b = DeterministicRandom(7, "x")
        self.assertEqual(
            [a.below(1000) for _ in range(20)], [b.below(1000) for _ in range(20)]
        )

    def test_labels_are_independent_streams(self) -> None:
        a = DeterministicRandom(7, "x")
        b = DeterministicRandom(7, "y")
        self.assertNotEqual(
            [a.below(10**6) for _ in range(10)], [b.below(10**6) for _ in range(10)]
        )

    def test_between_stays_inside_the_closed_interval(self) -> None:
        stream = DeterministicRandom(11, "range")
        values = [stream.between(3, 5) for _ in range(300)]
        self.assertTrue(all(3 <= v <= 5 for v in values))
        self.assertEqual(set(values), {3, 4, 5})

    def test_permutation_is_a_permutation(self) -> None:
        items = DeterministicRandom(11, "perm").permutation(50)
        self.assertEqual(sorted(items), list(range(50)))

    def test_permutation_of_zero_is_empty(self) -> None:
        self.assertEqual(DeterministicRandom(11, "perm").permutation(0), [])

    def test_rejects_a_non_positive_bound(self) -> None:
        with self.assertRaises(ValueError):
            DeterministicRandom(1, "x").below(0)


# =======================================================================================
# Preconditions - DT-028 section 8, DT-029
# =======================================================================================


class PreconditionTests(unittest.TestCase):
    def assert_rejected(self, fragment: str, **overrides) -> None:
        with self.assertRaises(pol.GeneratorError) as ctx:
            build_catalog(make_config(**overrides))
        joined = "\n".join(ctx.exception.problems)
        self.assertIn(fragment, joined)

    def test_p1_more_categories_than_products(self) -> None:
        self.assert_rejected("P-1", scale={"product_count": 5, "category_count": 20})

    def test_p2_fewer_than_four_products(self) -> None:
        self.assert_rejected(
            "P-2", scale={"product_count": 3, "category_count": 2, "supplier_count": 3}
        )

    def test_p3_fewer_than_three_suppliers(self) -> None:
        self.assert_rejected("P-3", scale={"supplier_count": 2})

    def test_p4_more_suppliers_than_relations(self) -> None:
        # product_count = 4 gives R = 7, so 7 suppliers is already too many: the
        # inequality is strict, otherwise no supplier would serve several products.
        self.assert_rejected(
            "P-4", scale={"product_count": 4, "category_count": 2, "supplier_count": 7}
        )

    def test_p4_accepts_one_supplier_below_the_relation_count(self) -> None:
        catalog = build_catalog(
            make_config(
                scale={"product_count": 4, "category_count": 2, "supplier_count": 6}
            )
        )
        self.assertEqual(len(catalog.product_suppliers), 7)

    def test_p5_period_shorter_than_two_days(self) -> None:
        self.assert_rejected(
            "P-5", period={"start_date": "2023-01-01", "end_date": "2023-01-02"}
        )

    def test_more_than_one_location_is_rejected(self) -> None:
        self.assert_rejected("DT-029", scale={"location_count": 3})

    def test_every_failed_precondition_is_reported_together(self) -> None:
        with self.assertRaises(pol.GeneratorError) as ctx:
            build_catalog(
                make_config(
                    scale={
                        "product_count": 3,
                        "category_count": 10,
                        "supplier_count": 2,
                        "location_count": 4,
                    },
                    period={"start_date": "2023-01-01", "end_date": "2023-01-02"},
                )
            )
        joined = "\n".join(ctx.exception.problems)
        for code in ("P-1", "P-2", "P-3", "P-5", "DT-029"):
            self.assertIn(code, joined)

    def test_nothing_is_written_when_a_precondition_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out"
            with self.assertRaises(pol.GeneratorError):
                generate(make_config(scale={"supplier_count": 2}), target)
            self.assertFalse(target.exists())


# =======================================================================================
# Category distribution - DT-028 section 3
# =======================================================================================


class CategoryDistributionTests(unittest.TestCase):
    def test_matches_the_table_of_dt_028(self) -> None:
        self.assertEqual(
            pol.category_distribution(10, 100), [34, 17, 11, 9, 7, 6, 5, 4, 4, 3]
        )

    def test_sums_to_the_product_count(self) -> None:
        for categories, products in ((10, 100), (3, 50), (7, 7), (5, 999)):
            with self.subTest(categories=categories, products=products):
                counts = pol.category_distribution(categories, products)
                self.assertEqual(sum(counts), products)
                self.assertEqual(len(counts), categories)

    def test_no_category_is_left_empty(self) -> None:
        # The case DT-028 section 3.2 uses to show why the donor must be recomputed: a
        # fixed donor reaches zero before the three empty categories are filled.
        self.assertEqual(pol.category_distribution(10, 10), [1] * 10)

    def test_is_a_pure_function_of_its_two_arguments(self) -> None:
        self.assertEqual(
            pol.category_distribution(10, 100), pol.category_distribution(10, 100)
        )

    def test_rejects_more_categories_than_products(self) -> None:
        with self.assertRaises(pol.GeneratorError):
            pol.category_distribution(10, 9)


class ClassSplitTests(unittest.TestCase):
    def test_matches_the_table_of_dt_028(self) -> None:
        split = pol.class_split(100)
        self.assertEqual(
            (split.class_a, split.class_b, split.class_c, split.class_d),
            (80, 10, 5, 5),
        )
        self.assertEqual(split.relation_count, 120)

    def test_each_class_keeps_its_floor_of_one(self) -> None:
        split = pol.class_split(4)
        self.assertEqual(
            (split.class_a, split.class_b, split.class_c, split.class_d), (1, 1, 1, 1)
        )

    def test_the_split_covers_every_product(self) -> None:
        for count in (4, 5, 17, 100, 1000):
            with self.subTest(count=count):
                self.assertEqual(pol.class_split(count).product_count, count)


# =======================================================================================
# Shape of the generated catalogue
# =======================================================================================


class CatalogShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = make_config()
        cls.catalog = build_catalog(cls.config)

    def test_row_counts_follow_the_configured_scale(self) -> None:
        self.assertEqual(len(self.catalog.categories), 10)
        self.assertEqual(len(self.catalog.products), 100)
        self.assertEqual(len(self.catalog.suppliers), 10)
        self.assertEqual(len(self.catalog.locations), 1)
        self.assertEqual(len(self.catalog.product_suppliers), 120)

    def test_business_keys_are_unique_and_zero_padded(self) -> None:
        self.assertEqual(self.catalog.categories[0]["code"], "CAT-001")
        self.assertEqual(self.catalog.products[0]["sku"], "SKU-00001")
        self.assertEqual(self.catalog.products[99]["sku"], "SKU-00100")
        self.assertEqual(self.catalog.suppliers[0]["code"], "SUP-001")
        self.assertEqual(self.catalog.locations[0]["code"], "LOC-001")
        skus = [p["sku"] for p in self.catalog.products]
        self.assertEqual(len(set(skus)), len(skus))

    def test_rows_are_ordered_by_business_key_and_ids_follow(self) -> None:
        for rows, key in (
            (self.catalog.categories, "code"),
            (self.catalog.products, "sku"),
            (self.catalog.suppliers, "code"),
            (self.catalog.locations, "code"),
        ):
            with self.subTest(key=key):
                keys = [row[key] for row in rows]
                self.assertEqual(keys, sorted(keys))
                self.assertEqual(
                    [row["id"] for row in rows], list(range(1, len(rows) + 1))
                )

        pairs = [
            (r["product_id"], r["supplier_id"]) for r in self.catalog.product_suppliers
        ]
        self.assertEqual(pairs, sorted(pairs))
        self.assertEqual(len(set(pairs)), len(pairs))
        self.assertEqual(
            [r["id"] for r in self.catalog.product_suppliers],
            list(range(1, len(pairs) + 1)),
        )

    def test_every_row_is_marked_synthetic(self) -> None:
        for rows in (
            self.catalog.categories,
            self.catalog.products,
            self.catalog.suppliers,
            self.catalog.product_suppliers,
            self.catalog.locations,
        ):
            self.assertTrue(all(row["data_origin"] == "SYNTHETIC" for row in rows))

    def test_referential_integrity(self) -> None:
        category_ids = {row["id"] for row in self.catalog.categories}
        product_ids = {row["id"] for row in self.catalog.products}
        supplier_ids = {row["id"] for row in self.catalog.suppliers}
        self.assertTrue(
            all(p["category_id"] in category_ids for p in self.catalog.products)
        )
        for relation in self.catalog.product_suppliers:
            self.assertIn(relation["product_id"], product_ids)
            self.assertIn(relation["supplier_id"], supplier_ids)

    def test_the_fields_dt_029_excludes_are_empty(self) -> None:
        for product in self.catalog.products:
            for column in (
                "description",
                "abc_class",
                "rotation_class",
                "shelf_life_days",
                "created_at",
                "updated_at",
            ):
                self.assertIsNone(product[column], column)
        for supplier in self.catalog.suppliers:
            for column in ("contact_info", "currency", "created_at", "updated_at"):
                self.assertIsNone(supplier[column], column)
        for category in self.catalog.categories:
            self.assertIsNone(category["parent_id"])

    def test_categories_are_distributed_as_dt_028_states(self) -> None:
        counts: dict[int, int] = {}
        for product in self.catalog.products:
            counts[product["category_id"]] = counts.get(product["category_id"], 0) + 1
        self.assertEqual(
            sorted(counts.values(), reverse=True), [34, 17, 11, 9, 7, 6, 5, 4, 4, 3]
        )
        self.assertEqual(len(counts), 10)

    def test_units_of_measure_come_from_the_closed_vocabulary(self) -> None:
        # DT-028 section 5 requires a *closed* vocabulary. It does not require all three
        # values to appear, and the generator does not force them, so asserting equality
        # here would be asserting an accident of this scale and seed - and it does not
        # hold at the minimum scale.
        used = {p["unit_of_measure"] for p in self.catalog.products}
        self.assertTrue(used <= set(pol.UNIT_OF_MEASURE_VALUES))
        self.assertTrue(used)

    def test_the_only_location_type_is_the_main_warehouse(self) -> None:
        self.assertEqual(self.catalog.locations[0]["type"], "MAIN_WAREHOUSE")


# =======================================================================================
# States and validity - DT-027, DT-028 section 7
# =======================================================================================


class ProductStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = make_config()
        cls.catalog = build_catalog(cls.config)

    def test_both_states_are_present(self) -> None:
        states = {p["is_active"] for p in self.catalog.products}
        self.assertEqual(states, {True, False})

    def test_five_percent_are_inactive(self) -> None:
        inactive = [p for p in self.catalog.products if not p["is_active"]]
        self.assertEqual(len(inactive), 5)

    def test_an_active_product_has_no_end_of_validity(self) -> None:
        for product in self.catalog.products:
            if product["is_active"]:
                self.assertIsNone(product["valid_to"])

    def test_an_inactive_product_keeps_three_quarters_of_the_window(self) -> None:
        # floor(0.75 * 1096) = 822 days after 2023-01-01 is 2025-04-02 - the date
        # DT-028 section 7.1 states.
        for product in self.catalog.products:
            if not product["is_active"]:
                self.assertEqual(product["valid_from"], _dt.date(2023, 1, 1))
                self.assertEqual(product["valid_to"], _dt.date(2025, 4, 2))

    def test_validity_is_a_closed_interval(self) -> None:
        # DT-027, restriction 2, as corrected: valid_from <= valid_to.
        for product in self.catalog.products:
            if product["valid_to"] is not None:
                self.assertLessEqual(product["valid_from"], product["valid_to"])

    def test_inactive_products_and_class_d_products_are_disjoint(self) -> None:
        # DT-028 section 7.1: overlapping them would merge two distinct test cases.
        by_product: dict[int, list[dict]] = {}
        for relation in self.catalog.product_suppliers:
            by_product.setdefault(relation["product_id"], []).append(relation)
        class_d = {
            product_id
            for product_id, group in by_product.items()
            if all(not r["is_active"] for r in group)
        }
        inactive = {p["id"] for p in self.catalog.products if not p["is_active"]}
        self.assertTrue(class_d)
        self.assertTrue(inactive)
        self.assertEqual(class_d & inactive, set())


# =======================================================================================
# Coverage guarantees - DT-028 sections 1 and 2
# =======================================================================================


class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = build_catalog(make_config())
        cls.relations = cls.catalog.product_suppliers
        cls.active = [r for r in cls.relations if r["is_active"]]

    def test_a_relation_without_a_significant_moq_is_truly_unconstrained(self) -> None:
        # DT-028 section 1.1: the witness must also carry order_multiple = 1, or its
        # real minimum order is the multiple, not the MOQ.
        self.assertTrue(
            any(
                r["moq"] in pol.MOQ_NO_MINIMUM_VALUES and r["order_multiple"] == 1
                for r in self.active
            )
        )

    def test_a_relation_carries_a_real_moq(self) -> None:
        self.assertTrue(
            any(r["moq"] in pol.MOQ_WITH_MINIMUM_VALUES for r in self.active)
        )

    def test_a_large_order_multiple_is_present(self) -> None:
        self.assertTrue(any(r["order_multiple"] >= 48 for r in self.active))

    def test_a_lead_time_is_not_a_multiple_of_seven(self) -> None:
        self.assertTrue(
            any(r["agreed_lead_time_days"] % 7 != 0 for r in self.relations)
        )

    def test_lead_times_stay_inside_the_declared_range(self) -> None:
        for relation in self.relations:
            self.assertGreaterEqual(relation["agreed_lead_time_days"], 1)
            self.assertLessEqual(relation["agreed_lead_time_days"], 45)

    def test_every_multi_supplier_product_has_two_lead_times(self) -> None:
        by_product: dict[int, list[dict]] = {}
        for relation in self.relations:
            by_product.setdefault(relation["product_id"], []).append(relation)
        multi = [g for g in by_product.values() if len(g) > 1]
        self.assertTrue(multi)
        for group in multi:
            self.assertGreater(len({r["agreed_lead_time_days"] for r in group}), 1)

    def test_values_come_from_the_declared_sets(self) -> None:
        for relation in self.relations:
            self.assertIn(relation["moq"], pol.MOQ_VALUES)
            self.assertIn(relation["order_multiple"], pol.ORDER_MULTIPLE_VALUES)

    def test_unit_costs_stay_inside_the_declared_range(self) -> None:
        for relation in self.relations:
            cost = relation["unit_cost"]
            self.assertRegex(cost, r"^\d+\.\d{2}$")
            self.assertGreaterEqual(float(cost), 0.50)
            self.assertLessEqual(float(cost), 2500.00)

    def test_no_supplier_is_left_without_relations(self) -> None:
        covered = {r["supplier_id"] for r in self.relations}
        self.assertEqual(covered, {row["id"] for row in self.catalog.suppliers})

    def test_some_supplier_serves_several_products(self) -> None:
        counts: dict[int, int] = {}
        for relation in self.relations:
            counts[relation["supplier_id"]] = counts.get(relation["supplier_id"], 0) + 1
        self.assertTrue(any(value > 1 for value in counts.values()))

    def test_at_most_one_preferred_supplier_per_product(self) -> None:
        by_product: dict[int, list[dict]] = {}
        for relation in self.relations:
            by_product.setdefault(relation["product_id"], []).append(relation)
        for product_id, group in by_product.items():
            preferred = [r for r in group if r["is_preferred"]]
            self.assertLessEqual(len(preferred), 1, product_id)
            if any(r["is_active"] for r in group):
                self.assertEqual(len(preferred), 1, product_id)

    def test_a_preferred_supplier_is_never_an_inactive_relation(self) -> None:
        for relation in self.relations:
            if relation["is_preferred"]:
                self.assertTrue(relation["is_active"])

    def test_a_product_with_no_active_supplier_exists(self) -> None:
        by_product: dict[int, list[dict]] = {}
        for relation in self.relations:
            by_product.setdefault(relation["product_id"], []).append(relation)
        without = [
            product_id
            for product_id, group in by_product.items()
            if all(not r["is_active"] for r in group)
        ]
        self.assertEqual(len(without), 5)
        # DT-028 section 2.5: the canonical form keeps exactly one inactive row, it does
        # not remove the relation.
        for product_id in without:
            self.assertEqual(len(by_product[product_id]), 1)

    def test_every_product_has_at_least_one_relation(self) -> None:
        with_relations = {r["product_id"] for r in self.relations}
        self.assertEqual(with_relations, {p["id"] for p in self.catalog.products})


# =======================================================================================
# Output contract - DT-024, DT-025
# =======================================================================================


class FormatTests(unittest.TestCase):
    def test_null_is_an_empty_field(self) -> None:
        self.assertEqual(format_value(None), "")

    def test_booleans_are_lowercase_and_not_integers(self) -> None:
        # True is an int in Python; the contract says "true", not "1".
        self.assertEqual(format_value(True), "true")
        self.assertEqual(format_value(False), "false")

    def test_integers_carry_no_sign_or_separator(self) -> None:
        self.assertEqual(format_value(1234567), "1234567")

    def test_dates_and_timestamps_are_iso(self) -> None:
        self.assertEqual(format_value(_dt.date(2023, 1, 1)), "2023-01-01")
        self.assertEqual(
            format_value(_dt.datetime(2023, 1, 1, 2, 3, 4, tzinfo=_dt.timezone.utc)),
            "2023-01-01T02:03:04Z",
        )

    def test_an_unsupported_type_is_refused(self) -> None:
        with self.assertRaises(TypeError):
            format_value(1.5)

    def test_amounts_keep_exactly_two_decimals(self) -> None:
        self.assertEqual(format_cents(50), "0.50")
        self.assertEqual(format_cents(250_000), "2500.00")
        self.assertEqual(format_cents(1005), "10.05")

    def test_quoting_is_minimal_and_rfc_4180(self) -> None:
        text = render_csv(
            ("a", "b"), [["plain", 'has "quote"'], ["has,comma", "line\nbreak"]]
        )
        self.assertEqual(
            text,
            'a,b\nplain,"has ""quote"""\n"has,comma","line\nbreak"\n',
        )

    def test_a_row_of_the_wrong_width_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            render_csv(("a", "b"), [["only-one"]])


class WrittenOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = make_config()
        cls._tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls._tmp.name) / "output"
        cls.manifest = generate(cls.config, cls.out, generated_at=FIXED_TIME)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_the_six_expected_files_are_written(self) -> None:
        self.assertEqual(
            sorted(p.name for p in self.out.iterdir()),
            [
                "categories.csv",
                "locations.csv",
                "manifest.json",
                "product_suppliers.csv",
                "products.csv",
                "suppliers.csv",
            ],
        )

    def test_headers_match_the_column_contract(self) -> None:
        expected = {
            "categories.csv": CATEGORY_COLUMNS,
            "products.csv": PRODUCT_COLUMNS,
            "suppliers.csv": SUPPLIER_COLUMNS,
            "product_suppliers.csv": PRODUCT_SUPPLIER_COLUMNS,
            "locations.csv": LOCATION_COLUMNS,
        }
        for filename, columns in expected.items():
            with self.subTest(filename=filename):
                header = (
                    (self.out / filename).read_text(encoding="utf-8").split("\n")[0]
                )
                self.assertEqual(header, ",".join(columns))

    def test_line_endings_are_lf_without_bom(self) -> None:
        for path in self.out.iterdir():
            raw = path.read_bytes()
            with self.subTest(name=path.name):
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
                self.assertNotIn(b"\r", raw)
                self.assertTrue(raw.endswith(b"\n"))

    def test_nulls_are_empty_fields_never_the_word_null(self) -> None:
        text = (self.out / "products.csv").read_text(encoding="utf-8")
        for token in (",NULL,", ",None,", ",NaN,", ",-,"):
            self.assertNotIn(token, text)
        # Row 1 is active, so description, the three derived fields, valid_to and the
        # two audit timestamps are all empty.
        first = text.split("\n")[1].split(",")
        self.assertEqual(first[3], "")
        self.assertEqual(first[7:10], ["", "", ""])

    def test_manifest_carries_the_nine_mandatory_fields(self) -> None:
        for field_name in (
            "dataset_version",
            "generator_version",
            "seed",
            "generated_at",
            "time_range",
            "data_origin",
            "config",
            "components",
            "files",
        ):
            self.assertIn(field_name, self.manifest)

    def test_manifest_omits_the_fields_of_later_components(self) -> None:
        # DT-025 is explicit: these come from Components 7 and 8, and a Component 2
        # manifest that lacks them is not invalid.
        self.assertNotIn("scenario_assignment", self.manifest)
        self.assertNotIn("quality_report", self.manifest)

    def test_manifest_records_the_configuration_verbatim(self) -> None:
        self.assertEqual(self.manifest["config"], self.config.to_dict())
        self.assertEqual(self.manifest["seed"], self.config.seed)
        self.assertEqual(self.manifest["time_range"], self.config.period.to_dict())
        self.assertEqual(self.manifest["data_origin"], "SYNTHETIC")

    def test_manifest_records_the_component_and_its_sub_seed(self) -> None:
        self.assertEqual(
            self.manifest["components"],
            [
                {
                    "name": "catalog",
                    "version": CATALOG_VERSION,
                    "sub_seed": sub_seed(self.config.seed, "catalog"),
                }
            ],
        )

    def test_manifest_digests_match_the_files_on_disk(self) -> None:
        self.assertEqual(len(self.manifest["files"]), 5)
        for entry in self.manifest["files"]:
            with self.subTest(name=entry["name"]):
                raw = (self.out / entry["name"]).read_bytes()
                self.assertEqual(entry["sha256"], hashlib.sha256(raw).hexdigest())
                # rows excludes the header line and the trailing newline.
                self.assertEqual(entry["rows"], raw.decode("utf-8").count("\n") - 1)

    def test_manifest_is_valid_json_on_disk(self) -> None:
        loaded = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(loaded, self.manifest)


class DatasetVersionTests(unittest.TestCase):
    def test_is_reproducible(self) -> None:
        config = make_config()
        self.assertEqual(
            dataset_version(config, "0.1.0"), dataset_version(config, "0.1.0")
        )

    def test_changes_with_the_generator_version(self) -> None:
        config = make_config()
        self.assertNotEqual(
            dataset_version(config, "0.1.0"), dataset_version(config, "0.2.0")
        )

    def test_changes_with_the_configuration(self) -> None:
        self.assertNotEqual(
            dataset_version(make_config(), GENERATOR_VERSION),
            dataset_version(make_config(seed=1), GENERATOR_VERSION),
        )

    def test_has_the_declared_shape(self) -> None:
        self.assertRegex(dataset_version(make_config(), "0.1.0"), r"^ds-[0-9a-f]{12}$")


# =======================================================================================
# Reproducibility - specification section 44
# =======================================================================================


class ReproducibilityTests(unittest.TestCase):
    def test_same_configuration_and_seed_give_identical_data_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a"
            second = Path(tmp) / "b"
            generate(make_config(), first, generated_at=FIXED_TIME)
            generate(
                make_config(),
                second,
                generated_at=FIXED_TIME + _dt.timedelta(days=3),
            )
            for name in (
                "categories.csv",
                "locations.csv",
                "product_suppliers.csv",
                "products.csv",
                "suppliers.csv",
            ):
                with self.subTest(name=name):
                    self.assertEqual(
                        (first / name).read_bytes(), (second / name).read_bytes()
                    )

    def test_only_generated_at_differs_between_the_two_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            a = generate(make_config(), Path(tmp) / "a", generated_at=FIXED_TIME)
            b = generate(
                make_config(),
                Path(tmp) / "b",
                generated_at=FIXED_TIME + _dt.timedelta(days=3),
            )
            self.assertNotEqual(a["generated_at"], b["generated_at"])
            a.pop("generated_at")
            b.pop("generated_at")
            self.assertEqual(a, b)

    def test_a_different_seed_gives_a_different_catalogue(self) -> None:
        one = build_catalog(make_config())
        other = build_catalog(make_config(seed=999))
        self.assertNotEqual(
            [r["agreed_lead_time_days"] for r in one.product_suppliers],
            [r["agreed_lead_time_days"] for r in other.product_suppliers],
        )

    def test_regenerating_over_an_existing_directory_replaces_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out"
            generate(make_config(), target, generated_at=FIXED_TIME)
            before = (target / "products.csv").read_bytes()
            generate(make_config(), target, generated_at=FIXED_TIME)
            self.assertEqual((target / "products.csv").read_bytes(), before)


class SmallScaleTests(unittest.TestCase):
    """The smallest configuration the preconditions admit still satisfies everything."""

    def test_the_minimum_viable_scale_generates(self) -> None:
        catalog = build_catalog(
            make_config(
                scale={"product_count": 4, "category_count": 4, "supplier_count": 3},
                period={"start_date": "2023-01-01", "end_date": "2023-01-03"},
            )
        )
        self.assertEqual(len(catalog.products), 4)
        self.assertEqual(len(catalog.product_suppliers), 7)
        self.assertEqual(
            sorted(p["category_id"] for p in catalog.products), [1, 2, 3, 4]
        )
        self.assertEqual({p["is_active"] for p in catalog.products}, {True, False})


# =======================================================================================
# Regressions found by the code review of 2026-09-21
# =======================================================================================


class CodeWidthTests(unittest.TestCase):
    """The fixed code width must widen with the scale, or the row order breaks.

    DT-028 section 4 says the width "is widened if it falls short for a larger scale",
    and DT-024 justifies ordering rows by business key with the padding making the
    lexicographic order agree with the numeric one. Overflowing the width breaks that
    silently: every row is still present and unique, only the file is out of order.
    """

    def test_width_is_the_tabulated_one_until_it_overflows(self) -> None:
        self.assertEqual(pol.code_width("category", 10), 3)
        self.assertEqual(pol.code_width("category", 999), 3)
        self.assertEqual(pol.code_width("category", 1000), 4)
        self.assertEqual(pol.code_width("product", 100), 5)
        self.assertEqual(pol.code_width("product", 99999), 5)
        self.assertEqual(pol.code_width("product", 1_000_000), 7)

    def test_ordering_survives_a_scale_that_overflows_the_width(self) -> None:
        catalog = build_catalog(
            make_config(
                scale={
                    "product_count": 1200,
                    "supplier_count": 10,
                    "category_count": 1000,
                }
            )
        )
        codes = [row["code"] for row in catalog.categories]
        self.assertEqual(codes, sorted(codes))
        self.assertEqual(codes[-1], "CAT-1000")
        skus = [row["sku"] for row in catalog.products]
        self.assertEqual(skus, sorted(skus))

    def test_the_default_scale_keeps_the_codes_of_the_adr(self) -> None:
        catalog = build_catalog(make_config())
        self.assertEqual(catalog.categories[-1]["code"], "CAT-010")
        self.assertEqual(catalog.products[-1]["sku"], "SKU-00100")


class WideBoundTests(unittest.TestCase):
    """below() must terminate for any positive bound, not only small ones."""

    def test_a_bound_above_the_word_size_still_returns(self) -> None:
        bound = 2**64 + 1
        value = DeterministicRandom(1, "wide").below(bound)
        self.assertTrue(0 <= value < bound)

    def test_a_very_large_bound_still_returns(self) -> None:
        bound = 2**200
        value = DeterministicRandom(1, "wide").below(bound)
        self.assertTrue(0 <= value < bound)

    def test_a_bound_that_fits_one_word_draws_one_word(self) -> None:
        # The wide path must not change the sequence for ordinary bounds: a single draw
        # per value, exactly as before. Ten values -> ten counter steps.
        stream = DeterministicRandom(5, "small")
        [stream.below(7) for _ in range(10)]
        self.assertIn("counter=10", repr(stream))


class UtcTests(unittest.TestCase):
    """A trailing Z asserts UTC; stamping it on a local time would be a false instant."""

    def test_an_offset_timestamp_is_converted(self) -> None:
        moment = _dt.datetime(
            2026, 1, 1, 0, 0, 0, tzinfo=_dt.timezone(_dt.timedelta(hours=5))
        )
        self.assertEqual(format_value(moment), "2025-12-31T19:00:00Z")

    def test_a_naive_timestamp_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            format_value(_dt.datetime(2026, 1, 1, 7, 30))

    def test_the_manifest_records_the_instant_in_utc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = generate(
                make_config(),
                Path(tmp) / "out",
                generated_at=_dt.datetime(
                    2026, 1, 1, 0, 0, 0, tzinfo=_dt.timezone(_dt.timedelta(hours=5))
                ),
            )
        self.assertEqual(manifest["generated_at"], "2025-12-31T19:00:00Z")


class CoverageCheckTests(unittest.TestCase):
    """The safety net must restate the guarantees, not trust the construction."""

    def setUp(self) -> None:
        catalog = build_catalog(make_config())
        self.kwargs = dict(
            categories=[dict(r) for r in catalog.categories],
            products=[dict(r) for r in catalog.products],
            suppliers=[dict(r) for r in catalog.suppliers],
            locations=[dict(r) for r in catalog.locations],
            relations=[dict(r) for r in catalog.product_suppliers],
            supplier_count=10,
        )

    def check(self):
        from data.synthetic.generator.catalog import _check_coverage

        return _check_coverage(**self.kwargs)

    def test_the_untouched_catalogue_passes(self) -> None:
        self.check()  # must not raise

    def test_a_product_left_without_a_preferred_supplier_is_caught(self) -> None:
        seen = False
        for row in self.kwargs["relations"]:
            if row["is_preferred"]:
                if seen:
                    row["is_preferred"] = False
                seen = True
        with self.assertRaises(pol.GeneratorError) as ctx:
            self.check()
        self.assertIn("none preferred", "\n".join(ctx.exception.problems))

    def test_an_inactive_category_is_caught(self) -> None:
        self.kwargs["categories"][0]["is_active"] = False
        with self.assertRaises(pol.GeneratorError) as ctx:
            self.check()
        self.assertIn("categories", "\n".join(ctx.exception.problems))

    def test_an_inactive_supplier_is_caught(self) -> None:
        self.kwargs["suppliers"][0]["is_active"] = False
        with self.assertRaises(pol.GeneratorError) as ctx:
            self.check()
        self.assertIn("suppliers", "\n".join(ctx.exception.problems))

    def test_a_preferred_but_inactive_relation_is_caught(self) -> None:
        for row in self.kwargs["relations"]:
            if not row["is_active"]:
                row["is_preferred"] = True
                break
        with self.assertRaises(pol.GeneratorError) as ctx:
            self.check()
        self.assertIn("preferred but inactive", "\n".join(ctx.exception.problems))

    def test_every_problem_is_reported_together(self) -> None:
        self.kwargs["categories"][0]["is_active"] = False
        self.kwargs["suppliers"][0]["is_active"] = False
        self.kwargs["locations"][0]["is_active"] = False
        with self.assertRaises(pol.GeneratorError) as ctx:
            self.check()
        self.assertEqual(len(ctx.exception.problems), 3)


class CoverageAcrossScalesTests(unittest.TestCase):
    """DT-028 section 1.5 warns the guarantees fail about half the time at small scale.

    That is precisely the case the single default-scale fixture does not exercise, so it
    is swept here: if the witness construction ever regressed, this is what would fail.
    """

    def test_guarantees_hold_at_many_scales_and_seeds(self) -> None:
        scales = (
            {"product_count": 4, "supplier_count": 3, "category_count": 4},
            {"product_count": 7, "supplier_count": 3, "category_count": 2},
            {"product_count": 20, "supplier_count": 5, "category_count": 20},
            {"product_count": 100, "supplier_count": 10, "category_count": 10},
            {"product_count": 250, "supplier_count": 99, "category_count": 7},
        )
        for scale in scales:
            for seed in (0, 1, 7, 20260913, 999_999):
                with self.subTest(scale=scale["product_count"], seed=seed):
                    # build_catalog runs _check_coverage itself, so a missed guarantee
                    # raises here rather than producing a quietly degraded catalogue.
                    catalog = build_catalog(make_config(scale=scale, seed=seed))
                    self.assertEqual(len(catalog.products), scale["product_count"])


class CrossProcessDeterminismTests(unittest.TestCase):
    """Section 44 asks for byte identity, which a same-process comparison cannot show."""

    def test_two_separate_processes_produce_the_same_bytes(self) -> None:
        root = Path(__file__).resolve().parents[3]
        script = (
            "import sys, datetime, hashlib, tempfile, pathlib; sys.path.insert(0, %r);"
            "from data.synthetic.config.config import load_config;"
            "from data.synthetic.generator.catalog import generate;"
            "out = pathlib.Path(tempfile.mkdtemp());"
            "generate(load_config(), out, generated_at="
            "datetime.datetime(2026,1,1,tzinfo=datetime.timezone.utc));"
            "h = hashlib.sha256();"
            "[h.update(p.read_bytes()) for p in sorted(out.iterdir()) "
            "if p.name != 'manifest.json'];"
            "print(h.hexdigest())"
        ) % str(root)
        digests = set()
        for hash_seed in ("0", "1", "12345"):
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                env={"PYTHONHASHSEED": hash_seed, "PATH": os.environ.get("PATH", "")},
                cwd=str(root),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            digests.add(result.stdout.strip())
        self.assertEqual(len(digests), 1, digests)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
