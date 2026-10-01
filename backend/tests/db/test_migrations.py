"""The SQL migration runner (`DT-055`): reproducible, idempotent and guarded by sha256."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from _db_support import DatabaseTestCase

from app.db.migrations import MIGRATIONS_DIR, MigrationError, apply_migrations, discover


class MigrationsTest(DatabaseTestCase):
    migrate = False

    def _directory(self) -> Path:
        handle = tempfile.TemporaryDirectory(prefix="u2_migrations_")
        self.addCleanup(handle.cleanup)
        target = Path(handle.name)
        for path in MIGRATIONS_DIR.glob("*.sql"):
            shutil.copy(path, target / path.name)
        return target

    def test_first_run_applies_everything_and_second_is_a_no_op(self) -> None:
        self.assertEqual(apply_migrations(self.conn), ["0001_dataset_tables"])
        self.assertEqual(apply_migrations(self.conn), [])
        rows = self.conn.execute("SELECT version, sha256 FROM schema_migrations ORDER BY version").fetchall()
        self.assertEqual(rows, [(m.version, m.sha256) for m in discover()])

    def test_changed_applied_migration_is_an_error(self) -> None:
        directory = self._directory()
        apply_migrations(self.conn, directory)
        path = directory / "0001_dataset_tables.sql"
        path.write_text(path.read_text(encoding="utf-8") + "\n-- edited\n", encoding="utf-8")
        with self.assertRaises(MigrationError):
            apply_migrations(self.conn, directory)

    def test_new_migration_is_applied_in_order(self) -> None:
        directory = self._directory()
        apply_migrations(self.conn, directory)
        (directory / "0002_probe.sql").write_text("CREATE TABLE probe (id bigint);", encoding="utf-8")
        self.assertEqual(apply_migrations(self.conn, directory), ["0002_probe"])
        self.assertIsNotNone(self.conn.execute("SELECT to_regclass('probe')").fetchone()[0])

    def test_failing_migration_leaves_no_trace(self) -> None:
        directory = self._directory()
        apply_migrations(self.conn, directory)
        (directory / "0002_broken.sql").write_text(
            "CREATE TABLE half_done (id bigint); SELECT * FROM no_such_table;", encoding="utf-8"
        )
        with self.assertRaises(Exception):
            apply_migrations(self.conn, directory)
        self.assertIsNone(self.conn.execute("SELECT to_regclass('half_done')").fetchone()[0])
        versions = [r[0] for r in self.conn.execute("SELECT version FROM schema_migrations")]
        self.assertEqual(versions, ["0001_dataset_tables"])

    def test_bad_names_and_duplicate_numbers_are_rejected(self) -> None:
        directory = self._directory()
        (directory / "2_bad.sql").write_text("SELECT 1;", encoding="utf-8")
        with self.assertRaises(MigrationError):
            discover(directory)
        (directory / "2_bad.sql").unlink()
        (directory / "0001_other.sql").write_text("SELECT 1;", encoding="utf-8")
        with self.assertRaises(MigrationError):
            discover(directory)
