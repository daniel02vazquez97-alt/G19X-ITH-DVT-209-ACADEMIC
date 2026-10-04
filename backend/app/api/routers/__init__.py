"""Routers of the API V1 and their shared dependencies: read-only connection and run resolution."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import psycopg
from fastapi import Request

from app.db.read import LazyReadOnlyConnection
from app.db.read import runs as runs_read

from ..errors import ApiError
from ..schemas import ErrorResponse


def connection(request: Request) -> Iterator[LazyReadOnlyConnection]:
    """One read-only connection per request (`DT-066`), opened on its first query: a request rejected by
    authentication, authorization or validation never reaches PostgreSQL."""
    conn = LazyReadOnlyConnection(request.app.state.settings.database_url)
    try:
        yield conn
    finally:
        conn.close()


def resolve_run(conn: psycopg.Connection, run_type: str, run_id: int | None) -> dict[str, Any]:
    """`DT-066`: explicit ``run_id`` must exist, be of ``run_type`` and COMPLETED; default: deterministic rule."""
    if run_id is None:
        run_id = runs_read.default_run_id(conn, run_type)
        if run_id is None:
            raise ApiError(404, "RUN_NOT_FOUND", "No hay ninguna ejecución completada.", {"run_type": run_type})
    run = runs_read.run_context(conn, run_id)
    if run is None or run["run_type"] != run_type or run["status"] != "COMPLETED":
        reason = "not_found" if run is None else ("wrong_type" if run["run_type"] != run_type else "not_completed")
        raise ApiError(404, "RUN_NOT_FOUND", "La ejecución no existe o no es consultable.",
                       {"run_id": run_id, "run_type": run_type, "reason": reason})
    return run


def errors(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI documentation of the error responses of an endpoint."""
    return {status: {"model": ErrorResponse} for status in statuses}
