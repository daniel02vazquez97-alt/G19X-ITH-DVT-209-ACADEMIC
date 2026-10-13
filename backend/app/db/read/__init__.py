"""Read-only queries of the API (U5, `docs/03` §16.2, `DT-066`): hand-written SQL grouped by entity.

`read_only_connection` opens one connection per request whose transactions are ``READ ONLY``: any
``INSERT``/``UPDATE``/``DELETE`` through it fails with SQLSTATE 25006. Nothing here writes, recalculates
or reads ``demand``.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

#: Seconds libpq may spend opening a connection (TCP, TLS and authentication; libpq's minimum is 2). Without it a
#: PostgreSQL that accepts TCP but never answers (stopped in Azure, C14 2026-10-12) kept the request waiting until
#: the frontend proxy gave up with its own 504 after ~60 s; now psycopg raises OperationalError and the API answers
#: its 503 SERVICE_UNAVAILABLE (`docs/07` §7.4). Only the API's read connections: batch runs keep libpq's default.
CONNECT_TIMEOUT_SECONDS = 5


def _connect(url: str) -> psycopg.Connection:
    return psycopg.connect(url, autocommit=False, row_factory=dict_row, connect_timeout=CONNECT_TIMEOUT_SECONDS)


@contextmanager
def read_only_connection(url: str) -> Iterator[psycopg.Connection]:
    conn = _connect(url)
    try:
        conn.read_only = True  # every transaction of this connection is READ ONLY
        yield conn
    finally:
        try:
            conn.rollback()
        finally:
            conn.close()


class LazyReadOnlyConnection:
    """A read-only connection opened on the first query, so that a request rejected by authentication or
    validation never touches PostgreSQL. Exposes only ``execute``; always closed with ``close``."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._conn: psycopg.Connection | None = None

    def execute(self, query, params=None):  # noqa: ANN001 — same signature as psycopg.Connection.execute
        if self._conn is None:
            conn = _connect(self._url)
            conn.read_only = True
            self._conn = conn
        return self._conn.execute(query, params)

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.rollback()
            finally:
                self._conn.close()
                self._conn = None


def like_pattern(text: str) -> str:
    """Substring pattern for ``ILIKE … ESCAPE '\\'`` with the wildcards of ``text`` escaped."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
