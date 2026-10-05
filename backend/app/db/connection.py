"""Database connection from the environment (`DT-055`).

The connection string is never stored in the repository (`CLAUDE.md` §9): it is read from
``DATABASE_URL``, e.g. ``postgresql://postgres@127.0.0.1:5432/inventory`` for the local container.
"""

from __future__ import annotations

import os

import psycopg

ENV_VAR = "DATABASE_URL"


def database_url(explicit: str | None = None) -> str:
    """The explicit connection string, or ``DATABASE_URL``; fails if neither is set."""
    url = explicit or os.environ.get(ENV_VAR)
    if not url:
        raise RuntimeError(f"{ENV_VAR} is not set")
    return url


def connect(url: str | None = None) -> psycopg.Connection:
    """A new autocommit connection; transactions are opened explicitly with ``conn.transaction()``."""
    return psycopg.connect(database_url(url), autocommit=True)
