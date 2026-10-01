"""The load of dataset 0.4.0 (`docs/04` §9.5): first load, reconciliations, idempotence, conflicts.

One database is loaded once for the whole module (a full load takes seconds); every test either only
reads it, or changes it inside a transaction that is always rolled back, or only adds ``FAILED`` rows
to ``data_loads`` and compares counts before and after.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
import unittest
from decimal import Decimal

import psycopg
from psycopg import errors as pg_errors
from _db_support import (
    DATASET_DIR,
    TemporaryDatabase,
    copy_dataset,
    edit_manifest,
    read_manifest,
    rewrite_csv,
    set_field,
)

from app.db.migrations import apply_migrations
from app.ingestion import contract
from app.ingestion.loader import LOCK_KEY, LoadOutcome, load_dataset, post_validate

_DB: TemporaryDatabase | None = None
_FIRST = None
#: table → (max id, sequence last_value) right after the load: sequences are not transactional, so
#: later tests that insert (and roll back) would advance them.
_SEQUENCES: dict[str, tuple[int, int | None]] = {}


def setUpModule() -> None:
    global _DB, _FIRST
    _DB = TemporaryDatabase()
    try:
        with _DB.connect() as conn:
            apply_migrations(conn)
            _FIRST = load_dataset(conn, DATASET_DIR)
            for name in contract.FILES:
                table = contract.table_name(name)
                _SEQUENCES[table] = (
                    conn.execute(f"SELECT max(id) FROM {table}").fetchone()[0],
                    # NULL until used: setval(max, true) must have been called.
                    conn.execute(
                        "SELECT last_value FROM pg_sequences WHERE sequencename = %s", (f"{table}_id_seq",)
                    ).fetchone()[0],
                )
    except BaseException:
        _DB.drop()
        raise


def tearDownModule() -> None:
    if _DB is not None:
        _DB.drop()


class LoadedTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = _DB.connect()
        self.addCleanup(self.conn.close)
        self.manifest = read_manifest(DATASET_DIR)

    def counts(self) -> dict[str, int]:
        tables = [contract.table_name(n) for n in contract.FILES] + ["data_loads"]
        return {t: self.conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}

    def dataset_copy(self):
        handle, directory = copy_dataset()
        self.addCleanup(handle.cleanup)
        return directory


class FirstLoadTest(LoadedTestCase):
    def test_first_load_is_completed(self) -> None:
        self.assertIs(_FIRST.outcome, LoadOutcome.COMPLETED)
        self.assertEqual(_FIRST.dataset_version, "ds-6c8ad65b4999")
        self.assertEqual(_FIRST.errors, ())

    def test_rows_per_table_equal_the_manifest(self) -> None:
        declared = {contract.table_name(e["name"]): e["rows"] for e in self.manifest["files"]}
        self.assertEqual(_FIRST.rows, declared)
        counts = self.counts()
        for table, rows in declared.items():
            self.assertEqual(counts[table], rows, table)

    def test_data_loads_records_the_load(self) -> None:
        row = self.conn.execute(
            """
            SELECT id, dataset_version, generator_version, data_origin, lower(time_range),
                   upper(time_range), manifest, manifest_sha256, files, status, outcome, errors,
                   started_at <= finished_at
            FROM data_loads WHERE status = 'COMPLETED'
            """
        ).fetchone()
        raw = (DATASET_DIR / "manifest.json").read_bytes()
        self.assertEqual(row[0], _FIRST.data_load_id)
        self.assertEqual(row[1:4], ("ds-6c8ad65b4999", "0.4.0", "SYNTHETIC"))
        self.assertEqual(row[4:6], (_dt.date(2023, 1, 1), _dt.date(2026, 1, 1)))
        self.assertEqual(row[6], json.loads(raw))
        self.assertEqual(row[7], hashlib.sha256(raw).hexdigest())
        self.assertEqual(row[8], self.manifest["files"])
        self.assertEqual(row[9:12], ("COMPLETED", "COMPLETED", []))
        self.assertTrue(row[12])

    def test_post_validation_holds_on_the_loaded_data(self) -> None:
        self.assertEqual(post_validate(self.conn, self.manifest), [])

    def test_on_hand_equals_the_sum_of_movements_recomputed_from_the_csv(self) -> None:
        totals: dict[tuple[int, int], Decimal] = {}
        with (DATASET_DIR / "inventory_movements.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                key = (int(row["product_id"]), int(row["location_id"]))
                totals[key] = totals.get(key, Decimal(0)) + Decimal(row["quantity"])
        stored = {
            (p, l): q
            for p, l, q in self.conn.execute("SELECT product_id, location_id, quantity_on_hand FROM inventory")
        }
        self.assertEqual(stored, totals)

    def test_ids_are_kept_and_sequences_continue_after_them(self) -> None:
        # Receipts are not in id order in the file: the id of the dataset is kept, not renumbered.
        self.assertEqual(
            self.conn.execute("SELECT purchase_order_item_id FROM purchase_order_receipts WHERE id = 76").fetchone(),
            (1,),
        )
        for table, (maximum, last) in _SEQUENCES.items():
            self.assertEqual(last, maximum, table)

    def test_technical_stamps_are_the_load_instant(self) -> None:
        stamps = set()
        for table, column in (("suppliers", "created_at"), ("suppliers", "updated_at"), ("products", "created_at"),
                              ("products", "updated_at"), ("purchase_orders", "created_at"),
                              ("purchase_orders", "updated_at"), ("inventory", "updated_at")):
            stamps |= {r[0] for r in self.conn.execute(f"SELECT DISTINCT {column} FROM {table}")}
        self.assertEqual(len(stamps), 1)
        started, finished = self.conn.execute(
            "SELECT started_at, finished_at FROM data_loads WHERE status = 'COMPLETED'"
        ).fetchone()
        self.assertTrue(started <= stamps.pop() <= finished)

    def test_quantities_are_numeric_and_nulls_are_null(self) -> None:
        on_hand = self.conn.execute("SELECT quantity_on_hand FROM inventory WHERE id = 2").fetchone()[0]
        self.assertEqual(on_hand, Decimal(215))
        self.assertEqual(self.conn.execute("SELECT count(*) FROM purchase_orders WHERE currency = ''").fetchone()[0], 0)
        self.assertEqual(
            self.conn.execute("SELECT count(*) FROM inventory_movements WHERE reference_type = 'INITIAL_INVENTORY' "
                              "AND reference_id IS NULL").fetchone()[0],
            100,
        )

    def test_the_advisory_lock_is_released(self) -> None:
        held = self.conn.execute(
            "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND objid = %s",
            (LOCK_KEY & 0xFFFFFFFF,),
        ).fetchone()[0]
        self.assertEqual(held, 0)


class IdempotenceTest(LoadedTestCase):
    def test_same_dataset_again_is_already_loaded_and_writes_nothing(self) -> None:
        before = self.counts()
        result = load_dataset(self.conn, DATASET_DIR)
        self.assertIs(result.outcome, LoadOutcome.ALREADY_LOADED)
        self.assertEqual(result.data_load_id, _FIRST.data_load_id)
        self.assertEqual(self.counts(), before)

    def test_identical_copy_elsewhere_is_already_loaded(self) -> None:
        before = self.counts()
        result = load_dataset(self.conn, self.dataset_copy())
        self.assertIs(result.outcome, LoadOutcome.ALREADY_LOADED)
        self.assertEqual(self.counts(), before)

    def _assert_rejected(self, directory, outcome: LoadOutcome, version: str) -> None:
        before = self.counts()
        result = load_dataset(self.conn, directory)
        self.assertIs(result.outcome, outcome)
        after = self.counts()
        self.assertEqual(after["data_loads"], before["data_loads"] + 1)
        self.assertEqual({k: v for k, v in after.items() if k != "data_loads"},
                         {k: v for k, v in before.items() if k != "data_loads"})
        status, recorded, errors = self.conn.execute(
            "SELECT status, outcome, errors FROM data_loads WHERE id = %s", (result.data_load_id,)
        ).fetchone()
        self.assertEqual((status, recorded), ("FAILED", outcome.value))
        self.assertTrue(errors)
        self.assertEqual(result.dataset_version, version)

    def test_same_version_with_other_content_is_an_integrity_conflict(self) -> None:
        directory = self.dataset_copy()
        rewrite_csv(directory, "suppliers.csv", lambda r: set_field(r, "1", "name", "Renamed supplier"))
        self._assert_rejected(directory, LoadOutcome.INTEGRITY_CONFLICT, "ds-6c8ad65b4999")

    def test_altered_file_under_the_same_manifest_is_an_integrity_conflict(self) -> None:
        directory = self.dataset_copy()
        rewrite_csv(directory, "suppliers.csv", lambda r: set_field(r, "1", "name", "X"), update_manifest=False)
        self._assert_rejected(directory, LoadOutcome.INTEGRITY_CONFLICT, "ds-6c8ad65b4999")

    def test_other_dataset_version_is_a_lineage_conflict(self) -> None:
        directory = self.dataset_copy()
        edit_manifest(directory, lambda m: m.update(dataset_version="ds-000000000000"))
        self._assert_rejected(directory, LoadOutcome.LINEAGE_CONFLICT, "ds-000000000000")

    def test_a_second_completed_load_is_impossible(self) -> None:
        with self.assertRaises(pg_errors.UniqueViolation), self.conn.transaction():
            self.conn.execute(
                """
                INSERT INTO data_loads (dataset_version, manifest, manifest_sha256, files, status, outcome,
                                        started_at, finished_at)
                VALUES ('x', '{}', 'x', '[]', 'COMPLETED', 'COMPLETED', now(), now())
                """
            )


class ConstraintTest(LoadedTestCase):
    """Every restriction of `docs/04` §9.3 rejects its violation (inside rolled-back transactions)."""

    def assertViolates(self, error: type[Exception], statement: str) -> None:
        with self.conn.transaction(force_rollback=True):
            with self.assertRaises(error, msg=statement), self.conn.transaction():
                self.conn.execute(statement)

    def assertAccepts(self, statement: str) -> None:
        with self.conn.transaction(force_rollback=True):
            self.conn.execute(statement)

    def test_check_constraints(self) -> None:
        check = pg_errors.CheckViolation
        self.assertViolates(check, "UPDATE products SET valid_to = valid_from - 1 WHERE id = 1")
        self.assertViolates(check, "UPDATE product_suppliers SET moq = -1 WHERE id = 1")
        self.assertViolates(check, "UPDATE product_suppliers SET order_multiple = 0.5 WHERE id = 1")
        self.assertViolates(check, "UPDATE inventory_movements SET quantity = 0 WHERE id = 1")
        self.assertViolates(check, "UPDATE inventory_movements SET movement_type = 'LOSS' WHERE id = 1")
        self.assertViolates(check, "UPDATE purchase_order_items SET quantity_ordered = 0, quantity_received = 0 "
                                   "WHERE id = 1")
        self.assertViolates(check, "UPDATE purchase_order_items SET quantity_received = quantity_ordered + 1 "
                                   "WHERE id = 1")
        self.assertViolates(check, "UPDATE purchase_order_items SET quantity_received = -1 WHERE id = 1")
        self.assertViolates(check, "UPDATE inventory SET quantity_on_hand = -1 WHERE id = 1")
        self.assertViolates(check, "UPDATE demand SET data_origin = 'REAL' WHERE id = 1")
        self.assertViolates(check, "UPDATE locations SET data_origin = 'MIXED' WHERE id = 1")
        self.assertViolates(check, "UPDATE purchase_orders SET status = 'OPEN' WHERE id = 1")
        self.assertViolates(check, "UPDATE data_loads SET outcome = 'LOAD_FAILED' WHERE status = 'COMPLETED'")

    def test_not_null_data_origin(self) -> None:
        for table in (contract.table_name(n) for n in contract.FILES):
            self.assertViolates(pg_errors.NotNullViolation, f"UPDATE {table} SET data_origin = NULL WHERE id = "
                                                            f"(SELECT min(id) FROM {table})")

    def test_unique_business_keys(self) -> None:
        unique = pg_errors.UniqueViolation
        self.assertViolates(unique, "UPDATE suppliers SET code = (SELECT code FROM suppliers WHERE id = 2) WHERE id = 1")
        self.assertViolates(unique, "UPDATE products SET sku = (SELECT sku FROM products WHERE id = 2) WHERE id = 1")
        self.assertViolates(unique, "INSERT INTO product_suppliers (product_id, supplier_id, agreed_lead_time_days, moq, "
                                    "order_multiple, unit_cost, is_preferred, is_active, data_origin) "
                                    "SELECT product_id, supplier_id, 1, 0, 1, 1, false, false, 'SYNTHETIC' "
                                    "FROM product_suppliers WHERE id = 1")
        # NULLS NOT DISTINCT: a second INITIAL_INVENTORY of the same pair and instant is a duplicate.
        self.assertViolates(unique, "INSERT INTO inventory_movements (product_id, location_id, movement_type, quantity, "
                                    "occurred_at, recorded_at, reference_type, reference_id, data_origin) "
                                    "SELECT product_id, location_id, movement_type, quantity, occurred_at, recorded_at, "
                                    "reference_type, reference_id, data_origin FROM inventory_movements "
                                    "WHERE reference_type = 'INITIAL_INVENTORY' LIMIT 1")

    def test_one_active_preferred_supplier_per_product(self) -> None:
        product = self.conn.execute(
            "SELECT product_id FROM product_suppliers GROUP BY product_id HAVING count(*) > 1 LIMIT 1"
        ).fetchone()[0]
        self.assertViolates(
            pg_errors.UniqueViolation,
            f"UPDATE product_suppliers SET is_preferred = true, is_active = true WHERE product_id = {product}",
        )

    def test_foreign_keys(self) -> None:
        fk = pg_errors.ForeignKeyViolation
        self.assertViolates(fk, "UPDATE products SET category_id = 999999 WHERE id = 1")
        self.assertViolates(fk, "UPDATE purchase_order_receipts SET purchase_order_item_id = 999999 WHERE id = 76")
        self.assertViolates(fk, "UPDATE inventory SET location_id = 999999 WHERE id = 1")
        self.assertViolates(fk, "DELETE FROM locations")

    def test_model_vocabulary_and_fractional_quantities_are_accepted(self) -> None:
        # The CHECK holds the vocabulary of the model, not only what 0.4.0 emits (docs/04 §9.3).
        self.assertAccepts("UPDATE inventory_movements SET movement_type = 'SCRAP' WHERE id = 1")
        self.assertAccepts("UPDATE purchase_orders SET status = 'DRAFT' WHERE id = 1")
        # numeric without fixed precision (DT-044).
        with self.conn.transaction(force_rollback=True):
            self.conn.execute("UPDATE inventory SET quantity_on_hand = 2.375 WHERE id = 1")
            value = self.conn.execute("SELECT quantity_on_hand FROM inventory WHERE id = 1").fetchone()[0]
            self.assertEqual(value, Decimal("2.375"))

    def test_polymorphic_references_have_no_fk_and_post_validation_catches_them(self) -> None:
        with self.conn.transaction(force_rollback=True):
            self.conn.execute("UPDATE inventory_movements SET reference_id = 999999999 "
                              "WHERE id = (SELECT min(id) FROM inventory_movements WHERE reference_type = 'CONSUMPTION')")
            errors = post_validate(self.conn, self.manifest)
        self.assertEqual([e.column for e in errors], ["reference_id"])


if __name__ == "__main__":
    unittest.main()
