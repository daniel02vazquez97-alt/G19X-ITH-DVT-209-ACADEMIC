"""The column contract of the ingestion against the published dataset 0.4.0 (`docs/04` §9.1, §9.5)."""

from __future__ import annotations

import csv
import unittest

from app.ingestion import contract

from ._support import DATASET_AVAILABLE, DATASET_DIR, SKIP_REASON, read_manifest

LOAD_ORDER = [
    "locations",
    "categories",
    "suppliers",
    "products",
    "product_suppliers",
    "purchase_orders",
    "purchase_order_items",
    "purchase_order_receipts",
    "demand",
    "consumption",
    "inventory_movements",
    "inventory",
]


class ContractTest(unittest.TestCase):
    def test_files_are_the_twelve_tables_in_load_order(self) -> None:
        self.assertEqual([contract.table_name(n) for n in contract.FILES], LOAD_ORDER)

    def test_every_column_kind_is_known_and_domains_are_set(self) -> None:
        kinds = {"id", "ref", "int", "int_nonneg", "qty", "money", "text", "bool", "date", "datetime",
                 "origin", "vocab", "stamped"}
        for name, columns in contract.FILES.items():
            self.assertEqual(columns[0].name, "id", name)
            self.assertIn("data_origin", [c.name for c in columns], name)
            for column in columns:
                self.assertIn(column.kind, kinds, (name, column.name))
                if column.kind == "qty":
                    self.assertIn(column.domain, ("nonneg", "pos", "nonzero", "any"), (name, column.name))
                if column.kind == "vocab":
                    self.assertTrue(column.domain, (name, column.name))

    def test_closed_vocabularies_are_those_of_the_model(self) -> None:
        self.assertEqual(contract.DATA_ORIGINS, ("SYNTHETIC", "REAL"))
        self.assertEqual(len(contract.MOVEMENT_TYPES), 7)
        self.assertEqual(
            contract.ORDER_STATUSES, ("DRAFT", "ISSUED", "PARTIALLY_RECEIVED", "RECEIVED", "CANCELLED")
        )


@unittest.skipUnless(DATASET_AVAILABLE, SKIP_REASON)
class ContractAgainstDatasetTest(unittest.TestCase):
    def test_headers_match_the_published_files(self) -> None:
        for name in contract.FILES:
            with (DATASET_DIR / name).open(encoding="utf-8", newline="") as handle:
                self.assertEqual(next(csv.reader(handle)), contract.header(name), name)

    def test_manifest_has_the_eleven_fields_and_lists_the_twelve_files(self) -> None:
        manifest = read_manifest(DATASET_DIR)
        self.assertEqual(sorted(manifest), sorted(contract.MANIFEST_FIELDS))
        self.assertEqual(sorted(e["name"] for e in manifest["files"]), sorted(contract.FILES))

    def test_dataset_is_0_4_0(self) -> None:
        manifest = read_manifest(DATASET_DIR)
        self.assertEqual(manifest["dataset_version"], "ds-6c8ad65b4999")
        self.assertEqual(manifest["generator_version"], "0.4.0")
        self.assertEqual(manifest["data_origin"], "SYNTHETIC")


if __name__ == "__main__":
    unittest.main()
