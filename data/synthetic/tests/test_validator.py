"""Tests for Component 8: Dataset Validator + quality report.

Run from the repository root::

    python3 -m unittest discover -s data/synthetic/tests -t .

Standard library ``unittest``, like the other components (`docs/13-testing.md`).

Scope: `DT-042` - the catalogue of 51 checks; the twenty items of the report, their
types (no floats) and their determinism; ``anomalies: []`` with its declared limitation;
never overwriting; and, above all, **fault injection**: a valid workspace is copied and
one fact is corrupted - in a CSV, keeping the manifest digests consistent so that only
the semantic check can notice, or in the manifest itself - and the check that owns that
family must fail, with every finding accumulated in a single ``GeneratorError``.

The 51 identifiers and the twenty report keys are written out here as literals: the
tests do not read the values they check from the module under test.
"""

from __future__ import annotations

import ast
import csv
import datetime as _dt
import hashlib
import inspect
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from data.synthetic.generator import pipeline
from data.synthetic.generator import policies as pol
from data.synthetic.generator import scenarios as sc
from data.synthetic.generator import validator as c8
from data.synthetic.generator.rng import (
    COMPONENT_DEMAND,
    COMPONENT_SUPPLIER_BEHAVIOUR,
    COMPONENT_VALIDATOR,
    DeterministicRandom,
    sub_seed,
)
from data.synthetic.generator.supplier_behaviour import build_supplier_profiles
from data.synthetic.generator.writer import VALIDATOR_VERSION, write_manifest
from data.synthetic.tests.test_scenarios import generate_dataset
from data.synthetic.tests.test_inventory import (
    SMALL,
    make_config,
    tree_digest,
)

#: `DT-042` section 4, written out, in report order.
CHECK_IDS = (
    "MAN-01", "MAN-02", "MAN-03", "MAN-04",
    "FMT-01", "FMT-02", "FMT-03", "FMT-04",
    "ORG-01",
    "IDN-01", "IDN-02", "IDN-03",
    "REF-01", "REF-02", "REF-03", "REF-04", "REF-05", "REF-06", "REF-07",
    "COM-01", "COM-02", "COM-03", "COM-04",
    "RCP-01", "RCP-02", "RCP-03",
    "CAN-01", "CAN-02", "CAN-03", "CAN-04",
    "ONB-01",
    "INV-01", "INV-02", "INV-03", "INV-04",
    "CON-01", "CON-02", "CON-03",
    "TMP-01", "TMP-02", "TMP-03", "TMP-04", "TMP-05",
    "MST-01",
    "SCN-01", "SCN-02",
    "COV-01",
    "LVC-08", "LVC-12", "LVC-18", "LVC-20",
)  # fmt: skip

#: `DT-042` section 5: the report keys, in order (items 1-20 of spec §35 plus result).
REPORT_KEYS = (
    "result",
    "dataset_version",
    "generator_version",
    "seed",
    "time_range",
    "records_by_entity",
    "counts",
    "scenario_distribution",
    "products_by_demand_pattern",
    "stockout",
    "orders",
    "receipts",
    "lead_time_distribution",
    "validations",
    "anomalies",
    "known_limitations",
)

ANOMALY_LIMITATION = (
    "No existe actualmente un criterio contractual de anomalía para este generador; una "
    "lista vacía no implica que el dataset haya sido revisado bajo una taxonomía de "
    "anomalías inexistente."
)


def build_workspace(directory: Path, config) -> Path:
    """C2 -> C3 -> C6 -> C4 -> C5, then C7: the state C8 receives inside W1."""
    generate_dataset(directory, config)
    sc.generate(config, directory, build_supplier_profiles(config, directory))
    return directory


def read(directory: Path, name: str) -> tuple[list[str], list[dict[str, str]]]:
    with (directory / name).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def load_manifest(directory: Path) -> dict:
    return json.loads((directory / "manifest.json").read_text(encoding="utf-8"))


def save_manifest(directory: Path, manifest: dict) -> None:
    write_manifest(directory / "manifest.json", manifest)


def rewrite(directory: Path, name: str, change, *, digest: bool = True) -> None:
    """Apply ``change`` (in place) to the rows of ``name``; by default, keep the manifest honest.

    Updating ``sha256`` and ``rows`` is what isolates the semantic check: MAN-04 still
    passes, so only the family that owns the corrupted fact can notice.
    """
    header, rows = read(directory, name)
    change(rows)  # in place
    text = "\n".join(
        [",".join(header)] + [",".join(r[c] for c in header) for r in rows]
    )
    data = (text + "\n").encode("utf-8")
    (directory / name).write_bytes(data)
    if digest:
        manifest = load_manifest(directory)
        for entry in manifest["files"]:
            if entry["name"] == name:
                entry["sha256"] = hashlib.sha256(data).hexdigest()
                entry["rows"] = len(rows)
        save_manifest(directory, manifest)


def rewrite_bytes(directory: Path, name: str, data: bytes) -> None:
    (directory / name).write_bytes(data)
    manifest = load_manifest(directory)
    for entry in manifest["files"]:
        if entry["name"] == name:
            entry["sha256"] = hashlib.sha256(data).hexdigest()
    save_manifest(directory, manifest)


def floats_in(value) -> list:
    if isinstance(value, float):
        return [value]
    if isinstance(value, dict):
        return [f for v in value.values() for f in floats_in(v)]
    if isinstance(value, list):
        return [f for v in value for f in floats_in(v)]
    return []


class Workspace(unittest.TestCase):
    """One valid R2 workspace, copied for every test that corrupts it."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config = make_config(**SMALL)
        cls.source = build_workspace(Path(cls._tmp.name) / "valid", cls.config)
        cls.counter = 0

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def copy(self) -> Path:
        type(self).counter += 1
        return Path(
            shutil.copytree(self.source, Path(self._tmp.name) / f"w{self.counter}")
        )

    def failing(self, directory: Path) -> tuple[set[str], list[str]]:
        with self.assertRaises(pol.GeneratorError) as caught:
            c8.validate(self.config, directory)
        problems = caught.exception.problems
        ids = {p[1:7] for p in problems if p.startswith("[")}
        return ids, problems

    def assert_detected(self, directory: Path, *expected: str) -> list[str]:
        ids, problems = self.failing(directory)
        for check in expected:
            self.assertIn(check, ids, "\n".join(problems[:30]))
        return problems


# =======================================================================================
# The catalogue and the report - DT-042 sections 4 to 6
# =======================================================================================


class CatalogueTests(unittest.TestCase):
    def test_the_catalogue_is_dt042(self) -> None:
        self.assertEqual(tuple(c.id for c in c8.CHECKS), CHECK_IDS)
        self.assertEqual(len(CHECK_IDS), 51)
        for check in c8.CHECKS:
            self.assertEqual(check.family, check.id[:3])
            self.assertTrue(check.source)

    def test_the_contract_files_are_the_pipeline_files(self) -> None:
        self.assertEqual(
            {name: cols for name, (cols, _) in c8.CONTRACT.items()},
            pipeline.FILE_COLUMNS,
        )

    def test_the_validator_draws_nothing_and_writes_no_csv(self) -> None:
        tree = ast.parse(inspect.getsource(c8))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        imported = {
            alias.name
            for n in ast.walk(tree)
            if isinstance(n, (ast.Import, ast.ImportFrom))
            for alias in n.names
        }
        for forbidden in ("DeterministicRandom", "random", "write_csv", "render_csv"):
            self.assertNotIn(forbidden, names | imported)

    def test_the_anomaly_limitation_is_declared_word_for_word(self) -> None:
        self.assertEqual(c8.ANOMALY_LIMITATION, ANOMALY_LIMITATION)
        self.assertIn(ANOMALY_LIMITATION, [x["text"] for x in c8.KNOWN_LIMITATIONS])


class ReportTests(Workspace):
    def test_a_valid_workspace_passes_every_check(self) -> None:
        report = c8.validate(self.config, self.source)
        self.assertEqual(tuple(report), REPORT_KEYS)
        self.assertEqual(report["result"], "PASS")
        v = report["validations"]
        self.assertEqual((v["executed"], v["passed"], v["failed"]), (51, 51, 0))
        self.assertEqual([c["id"] for c in v["checks"]], list(CHECK_IDS))
        self.assertEqual({c["status"] for c in v["checks"]}, {"PASS"})

    def test_the_twenty_items(self) -> None:
        report = c8.validate(self.config, self.source)
        manifest = load_manifest(self.source)
        for key in ("dataset_version", "generator_version", "seed", "time_range"):
            self.assertEqual(report[key], manifest[key])
        self.assertEqual(
            report["records_by_entity"],
            {f["name"]: f["rows"] for f in manifest["files"]},
        )
        self.assertEqual(
            report["counts"],
            {"products": 12, "suppliers": 4, "categories": 3, "locations": 1},
        )
        assignment = manifest["scenario_assignment"]
        self.assertEqual(list(report["scenario_distribution"]), list(assignment))
        for name, entry in report["scenario_distribution"].items():
            self.assertEqual(entry["products"], len(assignment[name]["products"]))
            self.assertTrue(entry["required"] and entry["covered"])
        self.assertEqual(sum(report["products_by_demand_pattern"].values()), 12)
        _, consumption = read(self.source, "consumption.csv")
        self.assertEqual(
            report["stockout"]["pair_days"],
            sum(r["is_stockout_affected"] == "true" for r in consumption),
        )
        _, orders = read(self.source, "purchase_orders.csv")
        self.assertEqual(report["orders"]["total"], len(orders))
        self.assertEqual(sum(report["orders"]["by_status"].values()), len(orders))
        _, receipts = read(self.source, "purchase_order_receipts.csv")
        self.assertEqual(report["receipts"], len(receipts))
        _, relations = read(self.source, "product_suppliers.csv")
        agreed = report["lead_time_distribution"]["agreed"]
        self.assertEqual(sum(x["count"] for x in agreed), len(relations))
        self.assertEqual([x["days"] for x in agreed], sorted(x["days"] for x in agreed))
        observed = report["lead_time_distribution"]["observed"]
        self.assertEqual(
            sum(x["count"] for x in observed), report["orders"]["by_status"]["RECEIVED"]
        )
        self.assertEqual(report["anomalies"], [])
        level_c = report["validations"]["level_c"]
        self.assertEqual(list(level_c), ["8", "12", "18", "20"])
        self.assertTrue(all(x["products"] > 0 for x in level_c.values()))

    def test_deterministic_with_no_floats_and_nothing_volatile(self) -> None:
        first = c8.validate(self.config, self.source)
        other = self.copy()
        second = c8.validate(self.config, other)
        self.assertEqual(json.dumps(first), json.dumps(second))  # different directories
        self.assertEqual(floats_in(first), [])
        text = json.dumps(first)
        for volatile in ("generated_at", self._tmp.name, str(other), "2026-09-23T12"):
            self.assertNotIn(volatile, text)

    def test_generate_adds_only_the_report_and_the_component(self) -> None:
        work = self.copy()
        before = tree_digest(work)
        manifest = c8.generate(self.config, work)
        after = tree_digest(work)
        self.assertEqual(
            {n for n in before if before[n] != after[n]}, {"manifest.json"}
        )
        self.assertEqual(set(before), set(after))
        self.assertEqual(list(manifest)[-2:], ["scenario_assignment", "quality_report"])
        self.assertEqual(len(manifest), 11)
        self.assertIn(
            {
                "name": COMPONENT_VALIDATOR,
                "version": VALIDATOR_VERSION,
                "sub_seed": sub_seed(self.config.seed, "validator"),
            },
            manifest["components"],
        )
        self.assertEqual(len(manifest["components"]), 7)
        self.assertEqual(load_manifest(work), manifest)

    def test_never_overwrites(self) -> None:
        work = self.copy()
        c8.generate(self.config, work)
        before = tree_digest(work)
        with self.assertRaises(pol.GeneratorError):
            c8.generate(self.config, work)
        self.assertEqual(tree_digest(work), before)
        (work / "manifest.json").unlink()
        with self.assertRaises(pol.GeneratorError):
            c8.generate(self.config, work)

    def test_a_failed_validation_writes_nothing(self) -> None:
        work = self.copy()
        rewrite(
            work, "inventory.csv", lambda rows: rows[0].update(quantity_reserved="1")
        )
        before = tree_digest(work)
        with self.assertRaises(pol.GeneratorError):
            c8.generate(self.config, work)
        self.assertEqual(tree_digest(work), before)

    def test_no_stream_of_its_own(self) -> None:
        bases = []
        original = DeterministicRandom.__init__

        def spy(instance, seed, label):
            bases.append(int(seed))
            original(instance, seed, label)

        with mock.patch.object(DeterministicRandom, "__init__", spy):
            c8.validate(self.config, self.source)
        # Only Components 3 and 6 draw, repeated to rebuild their decisions (DT-042 §2).
        self.assertEqual(
            set(bases),
            {
                sub_seed(self.config.seed, COMPONENT_DEMAND),
                sub_seed(self.config.seed, COMPONENT_SUPPLIER_BEHAVIOUR),
            },
        )
        self.assertNotIn(sub_seed(self.config.seed, COMPONENT_VALIDATOR), bases)


# =======================================================================================
# Fault injection - one family at a time (DT-042 section 4)
# =======================================================================================


class InjectionTests(Workspace):
    # --- MAN ----------------------------------------------------------------------------

    def test_manifest_identity(self) -> None:
        work = self.copy()
        manifest = load_manifest(work)
        manifest["seed"] += 1
        save_manifest(work, manifest)
        self.assert_detected(work, "MAN-02")

    def test_manifest_fields_and_components(self) -> None:
        work = self.copy()
        manifest = load_manifest(work)
        manifest["components"] = manifest["components"][:-1]
        manifest["quality_report"] = {}
        save_manifest(work, manifest)
        self.assert_detected(work, "MAN-01", "MAN-03")

    def test_manifest_digest_and_foreign_file(self) -> None:
        work = self.copy()
        (work / "notes.txt").write_text("x", encoding="utf-8")
        manifest = load_manifest(work)
        manifest["files"][0]["sha256"] = "0" * 64
        save_manifest(work, manifest)
        problems = self.assert_detected(work, "MAN-04")
        self.assertTrue(any("notes.txt" in p for p in problems))

    # --- FMT / ORG ----------------------------------------------------------------------

    def test_line_endings_and_bom(self) -> None:
        work = self.copy()
        data = (work / "suppliers.csv").read_bytes()
        rewrite_bytes(
            work, "suppliers.csv", b"\xef\xbb\xbf" + data.replace(b"\n", b"\r\n")
        )
        self.assert_detected(work, "FMT-01")

    def test_bom_alone(self) -> None:
        work = self.copy()
        rewrite_bytes(
            work,
            "suppliers.csv",
            b"\xef\xbb\xbf" + (work / "suppliers.csv").read_bytes(),
        )
        self.assert_detected(work, "FMT-01")

    def test_header(self) -> None:
        work = self.copy()
        data = (
            (work / "categories.csv").read_bytes().replace(b"parent_id", b"parent", 1)
        )
        rewrite_bytes(work, "categories.csv", data)
        self.assert_detected(work, "FMT-02")

    def test_field_count(self) -> None:
        work = self.copy()
        data = (work / "locations.csv").read_bytes().rstrip(b"\n") + b",extra\n"
        rewrite_bytes(work, "locations.csv", data)
        self.assert_detected(work, "FMT-03")

    def test_types_and_null_tokens(self) -> None:
        work = self.copy()

        def change(rows):
            rows[0]["is_active"] = "True"
            rows[1]["valid_to"] = "NULL"
            rows[2]["created_at"] = "2023-01-01T00:00:00Z"

        rewrite(work, "products.csv", change)
        problems = self.assert_detected(work, "FMT-04")
        self.assertGreaterEqual(sum("[FMT-04]" in p for p in problems), 3)

    def test_money_with_one_decimal(self) -> None:
        work = self.copy()
        rewrite(
            work, "product_suppliers.csv", lambda rows: rows[0].update(unit_cost="12.5")
        )
        self.assert_detected(work, "FMT-04")

    def test_data_origin(self) -> None:
        work = self.copy()
        rewrite(work, "demand.csv", lambda rows: rows[5].update(data_origin="REAL"))
        self.assert_detected(work, "ORG-01")

    # --- IDN / REF ----------------------------------------------------------------------

    def test_duplicate_id(self) -> None:
        work = self.copy()
        rewrite(work, "consumption.csv", lambda rows: rows[3].update(id=rows[2]["id"]))
        self.assert_detected(work, "IDN-01")

    def test_row_order(self) -> None:
        work = self.copy()

        def swap(rows):
            rows[0], rows[1] = rows[1], rows[0]
            rows[0]["id"], rows[1]["id"] = rows[1]["id"], rows[0]["id"]

        rewrite(work, "suppliers.csv", swap)
        self.assert_detected(work, "IDN-02")

    def test_receipt_numbering(self) -> None:
        work = self.copy()

        def renumber(rows):
            rows[0]["id"], rows[-1]["id"] = rows[-1]["id"], rows[0]["id"]

        rewrite(work, "purchase_order_receipts.csv", renumber)
        self.assert_detected(work, "IDN-01")

    def test_two_preferred_relations(self) -> None:
        work = self.copy()

        def second_preferred(rows):
            product = next(
                r["product_id"]
                for r in rows
                if sum(x["product_id"] == r["product_id"] for x in rows) > 1
            )
            for r in rows:
                if r["product_id"] == product:
                    r["is_preferred"], r["is_active"] = "true", "true"

        rewrite(work, "product_suppliers.csv", second_preferred)
        self.assert_detected(work, "IDN-03")

    def test_foreign_key(self) -> None:
        work = self.copy()
        rewrite(
            work,
            "product_suppliers.csv",
            lambda rows: rows[0].update(supplier_id="999"),
        )
        self.assert_detected(work, "REF-01")

    def test_receipt_movement_link(self) -> None:
        work = self.copy()

        def retarget(rows):
            receipt = next(r for r in rows if r["movement_type"] == "RECEIPT")
            receipt["reference_id"] = "999"

        rewrite(work, "inventory_movements.csv", retarget)
        self.assert_detected(work, "REF-04")

    def test_issue_movement_link(self) -> None:
        work = self.copy()

        def drop(rows):
            index = next(i for i, r in enumerate(rows) if r["movement_type"] == "ISSUE")
            del rows[index]
            for position, r in enumerate(rows, start=1):
                r["id"] = str(position)

        rewrite(work, "inventory_movements.csv", drop)
        self.assert_detected(work, "REF-05")

    def test_second_line_for_an_order(self) -> None:
        work = self.copy()

        def duplicate(rows):
            twin = dict(rows[0])
            twin["id"] = str(len(rows) + 1)
            twin["product_id"] = "12" if rows[0]["product_id"] != "12" else "11"
            rows.append(twin)

        rewrite(work, "purchase_order_items.csv", duplicate)
        self.assert_detected(work, "REF-02")

    def test_order_with_a_supplier_that_is_not_preferred(self) -> None:
        work = self.copy()
        _, suppliers = read(work, "suppliers.csv")

        def switch(rows):
            current = rows[0]["supplier_id"]
            rows[0]["supplier_id"] = next(
                s["id"] for s in suppliers if s["id"] != current
            )

        rewrite(work, "purchase_orders.csv", switch)
        self.assert_detected(work, "REF-03")

    def test_opening_balance_on_the_wrong_day(self) -> None:
        work = self.copy()

        def move(rows):
            opening = next(r for r in rows if r["movement_type"] == "ADJUSTMENT")
            opening["occurred_at"] = opening["recorded_at"] = "2023-01-02T00:00:00Z"

        rewrite(work, "inventory_movements.csv", move)
        self.assert_detected(work, "REF-06")

    def test_missing_inventory_row(self) -> None:
        work = self.copy()

        def drop(rows):
            del rows[-1]

        rewrite(work, "inventory.csv", drop)
        self.assert_detected(work, "REF-07")

    def test_relation_values(self) -> None:
        work = self.copy()
        rewrite(
            work,
            "product_suppliers.csv",
            lambda rows: rows[0].update(order_multiple="0", agreed_lead_time_days="0"),
        )
        self.assert_detected(work, "COM-01")

    def test_received_order_without_receipts(self) -> None:
        work = self.copy()
        _, orders = read(work, "purchase_orders.csv")
        received = {o["id"] for o in orders if o["status"] == "RECEIVED"}

        def drop(rows):
            index = next(
                i
                for i, r in enumerate(rows)
                if r["purchase_order_item_id"] in received
                and sum(
                    x["purchase_order_item_id"] == r["purchase_order_item_id"]
                    for x in rows
                )
                == 1
            )
            del rows[index]

        rewrite(work, "purchase_order_receipts.csv", drop)
        self.assert_detected(work, "TMP-05", "RCP-02")

    def test_consumption_movement_after_valid_to(self) -> None:
        work = self.copy()
        _, products = read(work, "products.csv")
        product = next(p for p in products if p["valid_to"])

        def late_issue(rows):
            issue = next(
                r
                for r in rows
                if r["movement_type"] == "ISSUE" and r["product_id"] == product["id"]
            )
            day = _dt.date.fromisoformat(product["valid_to"]) + _dt.timedelta(days=1)
            issue["occurred_at"] = issue["recorded_at"] = f"{day}T18:00:00Z"

        rewrite(work, "inventory_movements.csv", late_issue)
        self.assert_detected(work, "TMP-04")

    # --- COM ----------------------------------------------------------------------------

    def test_quantity_breaks_the_multiple(self) -> None:
        work = self.copy()
        _, relations = read(work, "product_suppliers.csv")
        _, orders = read(work, "purchase_orders.csv")
        order_supplier = {o["id"]: o["supplier_id"] for o in orders}
        multiples = {
            (r["product_id"], r["supplier_id"]): int(r["order_multiple"])
            for r in relations
        }

        def change(rows):
            for r in rows:
                if (
                    multiples[(r["product_id"], order_supplier[r["purchase_order_id"]])]
                    > 1
                ):
                    r["quantity_ordered"] = str(int(r["quantity_ordered"]) + 1)
                    return
            self.fail("no line with a multiple > 1")

        rewrite(work, "purchase_order_items.csv", change)
        self.assert_detected(work, "COM-02")

    def test_unit_cost(self) -> None:
        work = self.copy()
        rewrite(
            work,
            "purchase_order_items.csv",
            lambda rows: rows[0].update(unit_cost="0.01"),
        )
        self.assert_detected(work, "COM-03")

    def test_expected_at(self) -> None:
        work = self.copy()

        def shift(rows):
            day = _dt.date.fromisoformat(rows[0]["expected_at"][:10]) + _dt.timedelta(
                days=1
            )
            rows[0]["expected_at"] = f"{day}T00:00:00Z"

        rewrite(work, "purchase_orders.csv", shift)
        self.assert_detected(work, "COM-04")

    # --- RCP / CAN / ONB ----------------------------------------------------------------

    def test_partial_receipt_sum(self) -> None:
        work = self.copy()
        rewrite(
            work,
            "purchase_order_receipts.csv",
            lambda rows: rows[0].update(
                quantity_received=str(int(rows[0]["quantity_received"]) - 1)
            ),
        )
        self.assert_detected(work, "RCP-02", "REF-04")

    def test_receipt_before_issue(self) -> None:
        work = self.copy()
        rewrite(
            work,
            "purchase_order_receipts.csv",
            lambda rows: rows[0].update(received_at="2022-12-31T00:00:00Z"),
        )
        self.assert_detected(work, "RCP-01")

    def test_status(self) -> None:
        work = self.copy()

        def reopen(rows):
            order = next(r for r in rows if r["status"] == "RECEIVED")
            order["status"], order["closed_at"] = "ISSUED", ""

        rewrite(work, "purchase_orders.csv", reopen)
        self.assert_detected(work, "RCP-03")

    def test_cancelled_close(self) -> None:
        work = self.copy()

        def late_close(rows):
            order = next(r for r in rows if r["status"] == "CANCELLED")
            day = _dt.date.fromisoformat(order["closed_at"][:10]) + _dt.timedelta(
                days=1
            )
            order["closed_at"] = f"{day}T00:00:00Z"

        rewrite(work, "purchase_orders.csv", late_close)
        self.assert_detected(work, "CAN-01")

    def test_cancelled_twin_that_copies_nothing(self) -> None:
        work = self.copy()
        _, orders = read(work, "purchase_orders.csv")
        twin = next(o["id"] for o in orders if o["status"] == "CANCELLED")

        def change(rows):
            for r in rows:
                if r["purchase_order_id"] == twin:
                    r["quantity_ordered"] = str(int(r["quantity_ordered"]) * 2)

        rewrite(work, "purchase_order_items.csv", change)
        self.assert_detected(work, "CAN-02")

    def test_twin_of_an_ineligible_template(self) -> None:
        # Template and twin moved to the last day of the period: the twin's close would
        # fall on end_date, so the template is not eligible (DT-039 §5.2 point 1).
        work = self.copy()
        _, orders = read(work, "purchase_orders.csv")
        _, items = read(work, "purchase_order_items.csv")
        product = {i["purchase_order_id"]: i["product_id"] for i in items}
        twin = next(o for o in orders if o["status"] == "CANCELLED")
        key = (
            twin["issued_at"],
            twin["supplier_id"],
            product[twin["id"]],
            twin["location_id"],
        )
        template = next(
            o
            for o in orders
            if o["status"] != "CANCELLED"
            and (o["issued_at"], o["supplier_id"], product[o["id"]], o["location_id"])
            == key
        )
        last = str(self.config.period.end_date - _dt.timedelta(days=1)) + "T00:00:00Z"

        def move(rows):
            for r in rows:
                if r["id"] in (twin["id"], template["id"]):
                    r["issued_at"] = last

        rewrite(work, "purchase_orders.csv", move)
        problems = self.assert_detected(work, "CAN-02")
        self.assertTrue(any("[CAN-02]" in p and "not eligible" in p for p in problems))

    def test_one_cancelled_too_many(self) -> None:
        # A pending causal order relabelled CANCELLED: well formed as a twin, but the
        # number of cancelled orders no longer matches K, and it copies no template.
        work = self.copy()

        def cancel(rows):
            order = next(r for r in rows if r["status"] == "ISSUED")
            order["status"] = "CANCELLED"
            day = _dt.date.fromisoformat(order["issued_at"][:10]) + _dt.timedelta(
                days=1
            )
            order["closed_at"] = f"{day}T00:00:00Z"

        rewrite(work, "purchase_orders.csv", cancel)
        self.assert_detected(work, "CAN-03", "CAN-04")

    def test_order_number(self) -> None:
        work = self.copy()
        rewrite(
            work,
            "purchase_orders.csv",
            lambda rows: [
                r.update(order_number="PO-0" + r["order_number"][3:]) for r in rows
            ],
        )
        self.assert_detected(work, "ONB-01")

    def test_cancelled_are_not_required_to_be_chronological(self) -> None:
        _, orders = read(self.source, "purchase_orders.csv")
        issued = [o["issued_at"] for o in orders]
        self.assertNotEqual(issued, sorted(issued))  # the tail is not chronological...
        c8.validate(self.config, self.source)  # ...and that is valid (DT-039 §5.2)

    # --- INV / CON ----------------------------------------------------------------------

    def test_snapshot(self) -> None:
        work = self.copy()
        rewrite(
            work,
            "inventory.csv",
            lambda rows: rows[0].update(
                quantity_on_hand=str(int(rows[0]["quantity_on_hand"]) + 1)
            ),
        )
        self.assert_detected(work, "INV-03")

    def test_movement_clock_and_reason(self) -> None:
        work = self.copy()

        def change(rows):
            issue = next(r for r in rows if r["movement_type"] == "ISSUE")
            issue["occurred_at"] = issue["recorded_at"] = (
                issue["occurred_at"][:11] + "06:00:00Z"
            )
            receipt = next(r for r in rows if r["movement_type"] == "RECEIPT")
            receipt["reason_code"] = "OPENING_BALANCE"

        rewrite(work, "inventory_movements.csv", change)
        self.assert_detected(work, "INV-01")

    def test_negative_stock(self) -> None:
        work = self.copy()

        def shrink(rows):
            opening = next(r for r in rows if r["movement_type"] == "ADJUSTMENT")
            opening["quantity"] = "1"

        rewrite(work, "inventory_movements.csv", shrink)
        self.assert_detected(work, "INV-02")

    def test_transit(self) -> None:
        work = self.copy()
        rewrite(
            work,
            "inventory.csv",
            lambda rows: rows[-1].update(
                quantity_in_transit=str(int(rows[-1]["quantity_in_transit"]) + 5)
            ),
        )
        self.assert_detected(work, "INV-04")

    def test_consumption_grid(self) -> None:
        work = self.copy()

        def drop(rows):
            del rows[-1]

        rewrite(work, "consumption.csv", drop)
        self.assert_detected(work, "CON-01")

    def test_backlog_is_refused(self) -> None:
        work = self.copy()
        _, demand = read(work, "demand.csv")
        latent = {
            (d["product_id"], d["occurred_on"]): int(d["quantity"]) for d in demand
        }

        def under_serve(rows):
            row = next(
                r
                for r in rows
                if int(r["quantity"]) > 0 and r["is_stockout_affected"] == "false"
            )
            row["quantity"] = str(int(row["quantity"]) - 1)
            row["is_stockout_affected"] = "true"
            self.assertGreater(
                latent[(row["product_id"], row["occurred_on"])], int(row["quantity"])
            )

        rewrite(work, "consumption.csv", under_serve)
        self.assert_detected(work, "CON-02")

    def test_stockout_flag(self) -> None:
        work = self.copy()

        def flip(rows):
            row = next(r for r in rows if r["is_stockout_affected"] == "true")
            row["is_stockout_affected"] = "false"

        rewrite(work, "consumption.csv", flip)
        self.assert_detected(work, "CON-03")

    # --- TMP / MST ----------------------------------------------------------------------

    def test_validity_interval(self) -> None:
        work = self.copy()
        rewrite(
            work,
            "products.csv",
            lambda rows: rows[0].update(valid_to="2022-12-31"),
        )
        self.assert_detected(work, "TMP-01")

    def test_order_issued_after_valid_to(self) -> None:
        work = self.copy()
        _, items = read(work, "purchase_order_items.csv")
        _, orders = read(work, "purchase_orders.csv")
        product = items[0]["product_id"]
        issued = orders[0]["issued_at"][:10]

        def end_validity(rows):
            for r in rows:
                if r["id"] == product:
                    r["valid_to"] = str(
                        _dt.date.fromisoformat(issued) - _dt.timedelta(days=1)
                    )

        rewrite(work, "products.csv", end_validity)
        self.assert_detected(work, "TMP-03", "TMP-02")

    def test_unit_of_measure(self) -> None:
        work = self.copy()
        rewrite(
            work, "products.csv", lambda rows: rows[0].update(unit_of_measure="LITRE")
        )
        self.assert_detected(work, "MST-01")

    # --- SCN / COV / LVC ----------------------------------------------------------------

    def test_scenario_assignment_structure(self) -> None:
        work = self.copy()
        manifest = load_manifest(work)
        items = list(manifest["scenario_assignment"].items())
        manifest["scenario_assignment"] = dict(reversed(items))
        save_manifest(work, manifest)
        self.assert_detected(work, "SCN-01")

    def test_scenario_assignment_is_checked_against_the_data(self) -> None:
        work = self.copy()
        manifest = load_manifest(work)
        manifest["scenario_assignment"]["STOCKOUT"]["products"] = [1]
        save_manifest(work, manifest)
        self.assert_detected(work, "SCN-02")

    def test_required_coverage(self) -> None:
        work = self.copy()
        manifest = load_manifest(work)
        manifest["scenario_assignment"]["DELAYED_SUPPLIER"]["products"] = []
        save_manifest(work, manifest)
        self.assert_detected(work, "COV-01", "SCN-02")

    def test_coverage_follows_scenarios_required(self) -> None:
        work = self.copy()
        manifest = load_manifest(work)
        manifest["scenario_assignment"]["DELAYED_SUPPLIER"]["products"] = []
        save_manifest(work, manifest)
        narrow = make_config(**SMALL, scenarios={"required": ["STOCKOUT"]})
        with self.assertRaises(pol.GeneratorError) as caught:
            c8.validate(narrow, work)
        ids = {p[1:7] for p in caught.exception.problems if p.startswith("[")}
        self.assertNotIn("COV-01", ids)

    def test_level_c_inactive_with_history(self) -> None:
        work = self.copy()
        rewrite(
            work,
            "products.csv",
            lambda rows: [r.update(is_active="true") for r in rows],
        )
        self.assert_detected(work, "LVC-20")

    def test_level_c_checks_fail_when_nothing_shows_them(self) -> None:
        empty = sc.EmergentProperties((), (), (), ())
        with mock.patch.object(c8.sc, "emergent_properties", return_value=empty):
            ids, _ = self.failing(self.source)
        self.assertTrue({"LVC-08", "LVC-12", "LVC-18", "LVC-20"} <= ids)

    # --- accumulation -------------------------------------------------------------------

    def test_every_finding_of_every_family_in_one_error(self) -> None:
        work = self.copy()
        rewrite(work, "demand.csv", lambda rows: rows[0].update(data_origin="REAL"))
        rewrite(
            work, "inventory.csv", lambda rows: rows[0].update(quantity_reserved="7")
        )
        rewrite(
            work, "products.csv", lambda rows: rows[0].update(unit_of_measure="LITRE")
        )
        ids, problems = self.failing(work)
        self.assertTrue({"ORG-01", "INV-03", "MST-01"} <= ids)
        self.assertTrue(problems[0].startswith("Component 8 rejected the dataset"))

    def test_findings_are_capped_but_counted(self) -> None:
        work = self.copy()
        rewrite(
            work,
            "demand.csv",
            lambda rows: [r.update(data_origin="REAL") for r in rows],
        )
        _, problems = self.failing(work)
        org = [p for p in problems if p.startswith("[ORG-01]")]
        self.assertEqual(len(org), c8.DETAIL_LIMIT + 1)
        self.assertIn("more", org[-1])

    def test_a_missing_file_is_a_failure_not_a_crash(self) -> None:
        work = self.copy()
        (work / "inventory.csv").unlink()
        ids, _ = self.failing(work)
        self.assertTrue({"MAN-04", "FMT-01", "INV-03"} <= ids)


# =======================================================================================
# The DT-027 exception on the reference configuration R1
# =======================================================================================


class InFlightReceiptTests(unittest.TestCase):
    """R1 has receipts after ``valid_to`` of orders issued in force: they must pass."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config = make_config()
        cls.work = build_workspace(Path(cls._tmp.name) / "r1", cls.config)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_receipts_after_valid_to_exist_and_are_valid(self) -> None:
        _, products = read(self.work, "products.csv")
        valid_to = {p["id"]: p["valid_to"] for p in products if p["valid_to"]}
        _, items = read(self.work, "purchase_order_items.csv")
        product_of_item = {i["id"]: i["product_id"] for i in items}
        _, receipts = read(self.work, "purchase_order_receipts.csv")
        late = [
            r
            for r in receipts
            if product_of_item[r["purchase_order_item_id"]] in valid_to
            and r["received_at"][:10]
            > valid_to[product_of_item[r["purchase_order_item_id"]]]
        ]
        self.assertTrue(late)
        report = c8.validate(self.config, self.work)
        self.assertEqual(report["validations"]["failed"], 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
