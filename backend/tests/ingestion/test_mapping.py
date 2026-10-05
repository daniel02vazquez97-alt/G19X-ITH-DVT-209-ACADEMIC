"""Row-by-row mapping without database (step 4 of `docs/04` §9.5, types of §9.3)."""

from __future__ import annotations

import datetime as _dt
import unittest
from decimal import Decimal
from pathlib import Path

from app.ingestion import contract
from app.ingestion.contract import Column
from app.ingestion.dataset import Dataset, read_dataset
from app.ingestion.mapping import STAMP, map_dataset, parse_value

from ._support import DATASET_AVAILABLE, DATASET_DIR, SKIP_REASON


def _empty_rows() -> dict[str, list[list[str]]]:
    return {name: [] for name in contract.FILES}


def _dataset(rows: dict[str, list[list[str]]]) -> Dataset:
    return Dataset(Path("."), {"data_origin": "SYNTHETIC"}, "0" * 64, rows)


class ParseValueTest(unittest.TestCase):
    def assertInvalid(self, column: Column, raw: str, fragment: str) -> None:
        with self.assertRaises(ValueError) as caught:
            parse_value(column, raw)
        self.assertIn(fragment, str(caught.exception))

    def test_empty_is_null_only_when_nullable(self) -> None:
        self.assertIsNone(parse_value(Column("x", "text", nullable=True), ""))
        self.assertInvalid(Column("x", "text"), "", "is required")
        self.assertInvalid(Column("x", "ref"), "", "is required")

    def test_ids_and_integers(self) -> None:
        self.assertEqual(parse_value(Column("id", "id"), "42"), 42)
        for raw in ("0", "-1", "+1", "01", "1.0", "1,000", " 1"):
            self.assertInvalid(Column("id", "id"), raw, "integer >= 1")
        self.assertEqual(parse_value(Column("x", "int"), "-3"), -3)
        self.assertInvalid(Column("x", "int"), "+3", "an integer")
        self.assertEqual(parse_value(Column("x", "int_nonneg"), "0"), 0)
        self.assertInvalid(Column("x", "int_nonneg"), "-1", "integer >= 0")

    def test_quantities_are_exact_decimals_with_their_domain(self) -> None:
        self.assertEqual(parse_value(Column("q", "qty", domain="nonneg"), "17"), Decimal(17))
        self.assertEqual(parse_value(Column("q", "qty", domain="nonneg"), "2.5"), Decimal("2.5"))
        self.assertInvalid(Column("q", "qty", domain="nonneg"), "-1", ">= 0")
        self.assertInvalid(Column("q", "qty", domain="pos"), "0", "> 0")
        self.assertInvalid(Column("q", "qty", domain="nonzero"), "0", "!= 0")
        self.assertEqual(parse_value(Column("q", "qty", domain="nonzero"), "-5"), Decimal(-5))
        self.assertEqual(parse_value(Column("q", "qty", domain="any"), "-5"), Decimal(-5))
        for raw in ("1e3", "1.", ".5", "1 000", "NaN"):
            self.assertInvalid(Column("q", "qty", domain="any"), raw, "a quantity")

    def test_money_needs_exactly_two_decimals(self) -> None:
        self.assertEqual(parse_value(Column("m", "money"), "1180.29"), Decimal("1180.29"))
        for raw in ("1180.2", "1180", "1180.290", "1,180.29"):
            self.assertInvalid(Column("m", "money"), raw, "two decimals")

    def test_booleans_dates_and_instants(self) -> None:
        self.assertIs(parse_value(Column("b", "bool"), "true"), True)
        self.assertIs(parse_value(Column("b", "bool"), "false"), False)
        self.assertInvalid(Column("b", "bool"), "True", "true or false")
        self.assertEqual(parse_value(Column("d", "date"), "2025-03-31"), _dt.date(2025, 3, 31))
        self.assertInvalid(Column("d", "date"), "2025-3-31", "YYYY-MM-DD")
        with self.assertRaises(ValueError):
            parse_value(Column("d", "date"), "2025-02-30")
        instant = parse_value(Column("t", "datetime"), "2025-12-31T18:00:00Z")
        self.assertEqual(instant, _dt.datetime(2025, 12, 31, 18, tzinfo=_dt.UTC))
        for raw in ("2025-12-31 18:00:00", "2025-12-31T18:00:00+00:00", "2025-12-31T18:00Z"):
            self.assertInvalid(Column("t", "datetime"), raw, "UTC instant")

    def test_vocabularies(self) -> None:
        self.assertEqual(parse_value(Column("o", "origin"), "REAL"), "REAL")
        self.assertInvalid(Column("o", "origin"), "synthetic", "SYNTHETIC or REAL")
        movement = Column("t", "vocab", domain=contract.MOVEMENT_TYPES)
        self.assertEqual(parse_value(movement, "SCRAP"), "SCRAP")
        self.assertInvalid(movement, "LOSS", "is not one of")

    def test_stamped_columns_must_be_empty(self) -> None:
        self.assertIs(parse_value(Column("created_at", "stamped"), ""), STAMP)
        self.assertInvalid(Column("created_at", "stamped"), "2025-01-01T00:00:00Z", "must be empty")


class RowChecksTest(unittest.TestCase):
    def test_cross_column_restrictions_and_accumulation(self) -> None:
        rows = _empty_rows()
        rows["products.csv"] = [
            ["1", "SKU-1", "P", "", "1", "UN", "true", "", "", "", "2025-02-01", "2025-01-01", "", "", "SYNTHETIC"],
        ]
        rows["product_suppliers.csv"] = [["1", "1", "1", "10", "0", "0.5", "1.00", "true", "true", "SYNTHETIC"]]
        rows["purchase_order_items.csv"] = [["1", "1", "1", "10", "11", "1.00", "", "SYNTHETIC"]]
        rows["demand.csv"] = [["1", "1", "1", "2025-01-01", "3", "REAL"]]
        rows["consumption.csv"] = [
            ["1", "1", "1", "2025-01-01", "-3", "", "maybe", "SYNTHETIC"],
            ["2", "1", "1", "2025-01-02", "3", "", "false", "SYNTHETIC"],
        ]
        mapped, errors = map_dataset(_dataset(rows))
        self.assertEqual(mapped, {})
        found = {(e.file, e.line, e.column) for e in errors}
        self.assertEqual(
            found,
            {
                ("products.csv", 2, "valid_to"),
                ("product_suppliers.csv", 2, "order_multiple"),
                ("purchase_order_items.csv", 2, "quantity_received"),
                ("demand.csv", 2, "data_origin"),
                ("consumption.csv", 2, "quantity"),
                ("consumption.csv", 2, "is_stockout_affected"),
            },
        )

    def test_valid_rows_are_typed(self) -> None:
        rows = _empty_rows()
        rows["locations.csv"] = [["1", "LOC-1", "Main", "WAREHOUSE", "true", "SYNTHETIC"]]
        mapped, errors = map_dataset(_dataset(rows))
        self.assertEqual(errors, [])
        self.assertEqual(mapped["locations.csv"], [(1, "LOC-1", "Main", "WAREHOUSE", True, "SYNTHETIC")])


@unittest.skipUnless(DATASET_AVAILABLE, SKIP_REASON)
class PublishedDatasetMappingTest(unittest.TestCase):
    def test_published_dataset_maps_without_errors(self) -> None:
        dataset, errors = read_dataset(DATASET_DIR)
        self.assertEqual(errors, [])
        mapped, errors = map_dataset(dataset)
        self.assertEqual(errors, [])
        for name, rows in mapped.items():
            self.assertEqual(len(rows), len(dataset.rows[name]), name)
        # Stamped columns are left for the load instant; quantities are exact decimals.
        supplier = mapped["suppliers.csv"][0]
        self.assertIs(supplier[6], STAMP)
        self.assertIs(supplier[7], STAMP)
        self.assertIsInstance(mapped["inventory.csv"][0][3], Decimal)


if __name__ == "__main__":
    unittest.main()
