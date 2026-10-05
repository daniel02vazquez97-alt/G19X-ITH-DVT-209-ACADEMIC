"""Shared helpers of the PostgreSQL integration suite (U2, `DT-055`).

This suite is separate from the default one and runs against a REAL PostgreSQL, from ``backend/``::

    U2_TEST_ADMIN_DSN=postgresql://postgres@127.0.0.1:5432/postgres \\
        python3 -m unittest discover -s tests/db -t tests/db

``U2_TEST_ADMIN_DSN`` must allow ``CREATE DATABASE``: every test works on its own temporary database
``u2_test_<random>``, dropped afterwards. Without it the suite fails instead of skipping, so that a
green run always means the integration was exercised. The dataset is read from ``U2_DATASET_DIR``
(default ``data/synthetic/output``) and only ever altered in temporary copies.
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid
from pathlib import Path

import psycopg
from psycopg.conninfo import make_conninfo

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:  # the suite is discovered with -t tests/db
    sys.path.insert(0, str(BACKEND_DIR))
if str(BACKEND_DIR / "tests") not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR / "tests"))

from app.db.migrations import apply_migrations  # noqa: E402
from ingestion._support import (  # noqa: E402,F401
    DATASET_AVAILABLE,
    DATASET_DIR,
    copy_dataset,
    edit_manifest,
    read_manifest,
    rewrite_csv,
    set_field,
)

ADMIN_ENV = "U2_TEST_ADMIN_DSN"


def admin_dsn() -> str:
    dsn = os.environ.get(ADMIN_ENV)
    if not dsn:
        raise RuntimeError(f"{ADMIN_ENV} is not set: the integration suite needs a real PostgreSQL")
    if not DATASET_AVAILABLE:
        raise RuntimeError(f"dataset 0.4.0 not found in {DATASET_DIR} (set U2_DATASET_DIR)")
    return dsn


class TemporaryDatabase:
    """A new empty database; ``drop()`` removes it even with open sessions."""

    def __init__(self) -> None:
        self.admin = admin_dsn()
        self.name = f"u2_test_{uuid.uuid4().hex[:12]}"
        with psycopg.connect(self.admin, autocommit=True) as conn:
            conn.execute(f'CREATE DATABASE "{self.name}"')
        self.dsn = make_conninfo(self.admin, dbname=self.name)

    def connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, autocommit=True)

    def drop(self) -> None:
        with psycopg.connect(self.admin, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{self.name}" WITH (FORCE)')


class DatabaseTestCase(unittest.TestCase):
    """One fresh database per test, migrated unless ``migrate = False``."""

    migrate = True

    def setUp(self) -> None:
        self.database = TemporaryDatabase()
        self.addCleanup(self.database.drop)
        self.conn = self.database.connect()
        self.addCleanup(self.conn.close)
        if self.migrate:
            apply_migrations(self.conn)

    def count(self, table: str) -> int:
        return self.conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

    def dataset_copy(self) -> Path:
        handle, directory = copy_dataset()
        self.addCleanup(handle.cleanup)
        return directory
