"""Failed loads (`docs/04` §9.5): rejection before touching the data, rollback, and retry.

Each test uses its own fresh database. A failed load leaves no row in any of the twelve tables and
records exactly one ``FAILED`` row in ``data_loads``; a later load of the good dataset succeeds.
"""

from __future__ import annotations

import unittest

from _db_support import DATASET_DIR, DatabaseTestCase, edit_manifest, rewrite_csv, set_field

from app.ingestion import contract
from app.ingestion.loader import LoadOutcome, SchemaMissingError, load_dataset

TABLES = [contract.table_name(n) for n in contract.FILES]


class FailedLoadTest(DatabaseTestCase):
    def assertNothingLoaded(self) -> None:
        for table in TABLES:
            self.assertEqual(self.count(table), 0, table)

    def assertFailed(self, directory, outcome: LoadOutcome, file: str | None = None, column: str | None = None):
        result = load_dataset(self.conn, directory)
        self.assertIs(result.outcome, outcome, [str(e) for e in result.errors])
        self.assertFalse(result.outcome.ok)
        self.assertTrue(result.errors)
        if file is not None:
            self.assertIn(file, {e.file for e in result.errors}, [str(e) for e in result.errors])
        if column is not None:
            self.assertIn(column, {e.column for e in result.errors}, [str(e) for e in result.errors])
        self.assertNothingLoaded()
        rows = self.conn.execute("SELECT id, status, outcome, errors FROM data_loads").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][:3], (result.data_load_id, "FAILED", outcome.value))
        self.assertEqual(len(rows[0][3]), len(result.errors))
        return result

    def assertRetrySucceeds(self) -> None:
        result = load_dataset(self.conn, DATASET_DIR)
        self.assertIs(result.outcome, LoadOutcome.COMPLETED, [str(e) for e in result.errors])
        statuses = [r[0] for r in self.conn.execute("SELECT status FROM data_loads ORDER BY id")]
        self.assertEqual(statuses, ["FAILED", "COMPLETED"])
        self.assertEqual(self.count("demand"), 108235)

    # --- before touching the data -------------------------------------------------------------

    def test_quality_report_fail_is_rejected_before_loading(self) -> None:
        directory = self.dataset_copy()
        edit_manifest(directory, lambda m: m["quality_report"].update(result="FAIL"))
        self.assertFailed(directory, LoadOutcome.INVALID_DATASET, "manifest.json")

    def test_mapping_errors_are_all_reported_with_their_line(self) -> None:
        directory = self.dataset_copy()

        def corrupt(records: list[list[str]]) -> None:
            set_field(records, "10", "quantity", "-4")
            set_field(records, "20", "occurred_on", "2024/01/01")

        rewrite_csv(directory, "consumption.csv", corrupt)
        result = self.assertFailed(directory, LoadOutcome.INVALID_DATASET, "consumption.csv")
        self.assertEqual({(e.column) for e in result.errors}, {"quantity", "occurred_on"})
        self.assertTrue(all(e.line is not None for e in result.errors))

    def test_unreadable_manifest_writes_no_row(self) -> None:
        directory = self.dataset_copy()
        (directory / "manifest.json").write_text("[]", encoding="utf-8")
        result = load_dataset(self.conn, directory)
        self.assertIs(result.outcome, LoadOutcome.INVALID_DATASET)
        self.assertIsNone(result.data_load_id)
        self.assertEqual(self.count("data_loads"), 0)

    def test_missing_schema_is_reported(self) -> None:
        self.conn.execute("DROP TABLE data_loads")
        with self.assertRaises(SchemaMissingError):
            load_dataset(self.conn, DATASET_DIR)

    # --- rollback -----------------------------------------------------------------------------

    def test_database_error_rolls_back_everything_loaded_before_it(self) -> None:
        directory = self.dataset_copy()
        rewrite_csv(directory, "products.csv", lambda r: set_field(r, "5", "category_id", "999"))
        result = self.assertFailed(directory, LoadOutcome.LOAD_FAILED, "products.csv")
        self.assertIn("23503", str(result.errors[0]))  # foreign_key_violation
        self.assertRetrySucceeds()

    def test_on_hand_not_reconciled_rolls_back_and_retry_succeeds(self) -> None:
        directory = self.dataset_copy()
        rewrite_csv(directory, "inventory.csv", lambda r: set_field(r, "2", "quantity_on_hand", "216"))
        result = self.assertFailed(directory, LoadOutcome.POST_VALIDATION_FAILED, "inventory.csv", "quantity_on_hand")
        self.assertEqual(len(result.errors), 1)
        self.assertRetrySucceeds()

    def test_in_transit_not_reconciled(self) -> None:
        directory = self.dataset_copy()
        rewrite_csv(directory, "inventory.csv", lambda r: set_field(r, "1", "quantity_in_transit", "1"))
        self.assertFailed(directory, LoadOutcome.POST_VALIDATION_FAILED, "inventory.csv", "quantity_in_transit")

    def test_received_not_equal_to_receipts(self) -> None:
        directory = self.dataset_copy()
        rewrite_csv(directory, "purchase_order_receipts.csv", lambda r: set_field(r, "76", "quantity_received", "95"))
        self.assertFailed(
            directory, LoadOutcome.POST_VALIDATION_FAILED, "purchase_order_items.csv", "quantity_received"
        )

    def test_unresolved_polymorphic_reference(self) -> None:
        directory = self.dataset_copy()

        def dangle(records: list[list[str]]) -> None:
            column = records[0].index("reference_type")
            first = next(r for r in records[1:] if r[column] == "PURCHASE_ORDER_RECEIPT")
            set_field(records, first[0], "reference_id", "99999999")

        rewrite_csv(directory, "inventory_movements.csv", dangle)
        self.assertFailed(directory, LoadOutcome.POST_VALIDATION_FAILED, "inventory_movements.csv", "reference_id")

    def test_mixed_data_origin(self) -> None:
        directory = self.dataset_copy()
        rewrite_csv(directory, "consumption.csv", lambda r: set_field(r, "1", "data_origin", "REAL"))
        result = self.assertFailed(directory, LoadOutcome.POST_VALIDATION_FAILED, "consumption.csv", "data_origin")
        self.assertEqual([e.column for e in result.errors], ["data_origin"])
        self.assertRetrySucceeds()


if __name__ == "__main__":
    unittest.main()
