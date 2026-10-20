"""Migration 0005 (U14, `DT-104`): the reference baseline points to its Azure ML registry entry.

Integration suite (real PostgreSQL, `docs/13` §14): from scratch the forecast run creates the row with the reference,
and on a database built before 0005 the migration fills it in place without touching anything else.
"""

from __future__ import annotations

import datetime as dt
import shutil
import tempfile
from pathlib import Path

from _db_support import DATASET_DIR, DatabaseTestCase

from app.db.migrations import MIGRATIONS_DIR, apply_migrations
from app.forecasting.baselines import AZUREML_REFERENCE_MODEL, MOVING_AVERAGE, NAIVE, SEASONAL_NAIVE
from app.ingestion.loader import load_dataset
from app.runs.forecast import ForecastRunError, register_model_versions, run_forecast

A = dt.date(2025, 12, 31)
MIGRATION = "0005_model_registry_ref"


class RegistryMigrationTest(DatabaseTestCase):
    migrate = False

    def _before_0005(self) -> Path:
        handle = tempfile.TemporaryDirectory(prefix="u14_migrations_")
        self.addCleanup(handle.cleanup)
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if not path.name.startswith("0005"):
                shutil.copy(path, Path(handle.name))
        return Path(handle.name)

    def refs(self) -> dict[str, str | None]:
        return dict(self.conn.execute("SELECT name, external_ref FROM model_versions").fetchall())

    def test_from_scratch_the_forecast_run_records_the_reference(self) -> None:
        self.assertIn(MIGRATION, apply_migrations(self.conn))
        self.assertEqual(self.refs(), {})  # empty database: the migration changes nothing
        load_dataset(self.conn, DATASET_DIR)
        run_forecast(self.conn, A)
        self.assertEqual(self.refs(), {NAIVE.name: None, SEASONAL_NAIVE.name: None,
                                       MOVING_AVERAGE.name: AZUREML_REFERENCE_MODEL})

    def test_over_an_existing_database_it_fills_only_the_reference_baseline(self) -> None:
        self.assertNotIn(MIGRATION, apply_migrations(self.conn, self._before_0005()))
        load_dataset(self.conn, DATASET_DIR)
        run_forecast(self.conn, A)
        # A database created before 0005 has the three baselines without registry reference.
        self.conn.execute("UPDATE model_versions SET external_ref = NULL")
        tables = ("calculation_runs", "forecasts", "model_versions", "data_loads")
        before = {t: self.count(t) for t in tables}
        self.assertEqual(apply_migrations(self.conn), [MIGRATION])
        self.assertEqual(self.refs(), {NAIVE.name: None, SEASONAL_NAIVE.name: None,
                                       MOVING_AVERAGE.name: AZUREML_REFERENCE_MODEL})
        self.assertEqual({t: self.count(t) for t in tables}, before)
        self.assertEqual(apply_migrations(self.conn), [])
        # The run is recognised, not rewritten: the rows match their definitions again.
        self.assertEqual(run_forecast(self.conn, A).outcome.value, "ALREADY_COMPUTED")

    def test_a_different_reference_is_never_overwritten(self) -> None:
        apply_migrations(self.conn, self._before_0005())
        load_dataset(self.conn, DATASET_DIR)
        run_forecast(self.conn, A)
        self.conn.execute("UPDATE model_versions SET external_ref = 'azureml:otro:9' WHERE name = %s",
                          (MOVING_AVERAGE.name,))
        apply_migrations(self.conn)
        self.assertEqual(self.refs()[MOVING_AVERAGE.name], "azureml:otro:9")
        with self.assertRaises(ForecastRunError):
            register_model_versions(self.conn)
