"""Migration 0002 (U3, `DT-057`): from scratch, over an existing 0001, idempotent and sha-guarded."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from _db_support import DatabaseTestCase

from app.db.migrations import MIGRATIONS_DIR, apply_migrations, discover

U3_TABLES = {"model_versions", "calculation_runs", "forecasts"}


class ForecastMigrationTest(DatabaseTestCase):
    migrate = False

    def tables(self) -> set[str]:
        return {
            r[0]
            for r in self.conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
        }

    def test_from_scratch_both_migrations_apply_in_order_and_once(self) -> None:
        self.assertEqual(apply_migrations(self.conn), ["0001_dataset_tables", "0002_forecast_tables"])
        self.assertEqual(apply_migrations(self.conn), [])
        self.assertTrue(U3_TABLES <= self.tables())
        stored = dict(self.conn.execute("SELECT version, sha256 FROM schema_migrations").fetchall())
        self.assertEqual(stored, {m.version: m.sha256 for m in discover()})

    def test_over_an_existing_0001(self) -> None:
        handle = tempfile.TemporaryDirectory(prefix="u3_migrations_")
        self.addCleanup(handle.cleanup)
        only_0001 = Path(handle.name)
        shutil.copy(MIGRATIONS_DIR / "0001_dataset_tables.sql", only_0001)
        self.assertEqual(apply_migrations(self.conn, only_0001), ["0001_dataset_tables"])
        self.assertFalse(U3_TABLES & self.tables())
        self.assertEqual(apply_migrations(self.conn), ["0002_forecast_tables"])
        self.assertTrue(U3_TABLES <= self.tables())

    def test_foreign_keys_of_the_u3_tables(self) -> None:
        apply_migrations(self.conn)
        rows = self.conn.execute(
            """
            SELECT c.conrelid::regclass::text, a.attname, c.confrelid::regclass::text
            FROM pg_constraint c
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
            WHERE c.contype = 'f' AND c.conrelid::regclass::text = ANY (%s)
            """,
            (sorted(U3_TABLES),),
        ).fetchall()
        self.assertEqual(
            {(t, c): r for t, c, r in rows},
            {
                ("calculation_runs", "data_load_id"): "data_loads",
                ("calculation_runs", "reference_model_version_id"): "model_versions",
                ("forecasts", "calculation_run_id"): "calculation_runs",
                ("forecasts", "product_id"): "products",
                ("forecasts", "location_id"): "locations",
                ("forecasts", "model_version_id"): "model_versions",
            },
        )

    def test_indexes_and_triggers(self) -> None:
        apply_migrations(self.conn)
        indexes = dict(
            self.conn.execute("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public'").fetchall()
        )
        self.assertIn("WHERE (status = 'COMPLETED'", indexes["calculation_runs_completed_ux"])
        self.assertIn("WHERE is_primary", indexes["forecasts_primary_ux"])
        self.assertIn("UNIQUE", indexes["forecasts_run_series_period_uk"])
        self.assertIn("UNIQUE", indexes["model_versions_name_version_uk"])
        triggers = {
            r[0]
            for r in self.conn.execute(
                "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal"
            )
        }
        self.assertEqual(triggers, {"calculation_runs_immutable", "forecasts_immutable"})
