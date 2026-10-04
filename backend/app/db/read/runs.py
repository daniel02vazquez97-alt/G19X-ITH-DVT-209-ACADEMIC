"""Calculation runs and their provenance context (`DT-066`)."""

from __future__ import annotations

from typing import Any

import psycopg

_CONTEXT = """
    SELECT r.id, r.run_type, r.status, r.as_of_date, r.data_load_id, r.config_sha256, r.summary, r.error,
           r.started_at, r.finished_at, r.forecast_run_id, r.engine_version,
           d.dataset_version, d.generator_version, d.data_origin,
           m.name AS reference_model_name, m.version AS reference_model_version
    FROM calculation_runs r
    JOIN data_loads d ON d.id = r.data_load_id
    LEFT JOIN model_versions m ON m.id = r.reference_model_version_id
"""


def default_run_id(conn: psycopg.Connection, run_type: str) -> int | None:
    """`DT-066`: the single COMPLETED load → its COMPLETED runs of ``run_type`` → max ``as_of_date`` → max ``id``."""
    row = conn.execute(
        """
        SELECT r.id
        FROM calculation_runs r
        JOIN data_loads d ON d.id = r.data_load_id AND d.status = 'COMPLETED'
        WHERE r.run_type = %s AND r.status = 'COMPLETED'
        ORDER BY r.as_of_date DESC, r.id DESC
        LIMIT 1
        """,
        (run_type,),
    ).fetchone()
    return None if row is None else row["id"]


def run_context(conn: psycopg.Connection, run_id: int) -> dict[str, Any] | None:
    return conn.execute(_CONTEXT + " WHERE r.id = %s", (run_id,)).fetchone()
