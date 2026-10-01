"""Minimal runner for the versioned SQL migrations (`DT-043`, `DT-055`).

Files ``NNNN_name.sql`` in ``backend/db/migrations`` are applied in order, each in its own
transaction, and recorded in ``schema_migrations`` with their ``sha256``. Applying again is a no-op;
an applied migration whose file has changed is an error, so the schema is reproducible.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"
_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    text        PRIMARY KEY,
    sha256     text        NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
)
"""


class MigrationError(RuntimeError):
    """A migration file is malformed, or an applied one no longer matches its file."""


@dataclass(frozen=True)
class Migration:
    version: str
    path: Path
    sha256: str


def discover(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    """Every migration file, ordered by version; rejects unexpected names and duplicates."""
    found: dict[str, Migration] = {}
    for path in sorted(directory.glob("*.sql")):
        match = _NAME.match(path.name)
        if match is None:
            raise MigrationError(f"unexpected migration file name: {path.name}")
        version = path.stem
        if match.group(1) in {v[:4] for v in found}:
            raise MigrationError(f"duplicate migration number: {path.name}")
        found[version] = Migration(version, path, hashlib.sha256(path.read_bytes()).hexdigest())
    return [found[v] for v in sorted(found)]


def apply_migrations(conn: psycopg.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply the pending migrations; return the versions applied now."""
    conn.execute(_CREATE_TABLE)
    applied = dict(conn.execute("SELECT version, sha256 FROM schema_migrations").fetchall())
    newly_applied = []
    for migration in discover(directory):
        if migration.version in applied:
            if applied[migration.version] != migration.sha256:
                raise MigrationError(f"applied migration {migration.version} has changed on disk")
            continue
        with conn.transaction():
            conn.execute(migration.path.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO schema_migrations (version, sha256) VALUES (%s, %s)",
                (migration.version, migration.sha256),
            )
        newly_applied.append(migration.version)
    return newly_applied
