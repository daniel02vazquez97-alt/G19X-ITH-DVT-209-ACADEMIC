"""Atomic, idempotent and traceable load of a dataset into PostgreSQL (`DT-044`, `docs/04` §9.5).

1. advisory lock: one load at a time per database;
2. detection against ``data_loads`` → ``ALREADY_LOADED`` (writes nothing) or a conflict;
3. pre-validation and 4. mapping, without touching the database, accumulating every error;
5. load in ONE transaction, in foreign-key order, keeping the dataset ``id``;
6. post-validation inside that transaction → rollback if any invariant fails;
7. commit with ``data_loads`` ``COMPLETED``; on any failure, rollback and ``data_loads`` ``FAILED``
   in a separate transaction. A load never leaves partial rows and never deletes anything.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from psycopg.types.range import Range

from . import contract
from .dataset import DataError, Identity, ManifestError, read_dataset, read_identity, time_range
from .mapping import STAMP, map_dataset

#: Key of the session advisory lock that serialises loads on a database.
LOCK_KEY = 4_405_190_002

#: At most this many errors are stored in ``data_loads.errors``; the result keeps them all.
MAX_RECORDED_ERRORS = 1000

#: At most this many offending rows are reported per post-validation check.
_SAMPLE = 20


class LoadOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    ALREADY_LOADED = "ALREADY_LOADED"
    INTEGRITY_CONFLICT = "INTEGRITY_CONFLICT"
    LINEAGE_CONFLICT = "LINEAGE_CONFLICT"
    INVALID_DATASET = "INVALID_DATASET"
    LOAD_FAILED = "LOAD_FAILED"
    POST_VALIDATION_FAILED = "POST_VALIDATION_FAILED"

    @property
    def ok(self) -> bool:
        return self in (LoadOutcome.COMPLETED, LoadOutcome.ALREADY_LOADED)


@dataclass(frozen=True)
class LoadResult:
    outcome: LoadOutcome
    dataset_version: str | None
    #: The ``data_loads`` row written by this attempt, or the existing one for ``ALREADY_LOADED``.
    data_load_id: int | None
    errors: tuple[DataError, ...] = ()
    #: Rows loaded per table (only for ``COMPLETED``).
    rows: dict[str, int] = field(default_factory=dict)


class SchemaMissingError(RuntimeError):
    """The database has no ``data_loads``: the migrations have not been applied."""


class _PostValidationFailed(Exception):
    def __init__(self, errors: list[DataError]) -> None:
        super().__init__(f"{len(errors)} post-validation errors")
        self.errors = errors


def load_dataset(conn: psycopg.Connection, directory: Path) -> LoadResult:
    """Load the dataset published in ``directory`` into the database of ``conn``.

    ``conn`` must be in autocommit mode: this function opens its own transactions.
    """
    if not conn.autocommit:
        raise ValueError("load_dataset needs an autocommit connection")
    if conn.execute("SELECT to_regclass('data_loads')").fetchone()[0] is None:
        raise SchemaMissingError("schema missing: run `python -m app.db migrate` first")
    started_at = _now(conn)
    try:
        identity = read_identity(directory)
    except ManifestError as exc:
        # Without a dataset_version there is nothing to attribute the attempt to: no row.
        return LoadResult(LoadOutcome.INVALID_DATASET, None, None, (DataError(str(exc), "manifest.json"),))

    conn.execute("SELECT pg_advisory_lock(%s)", (LOCK_KEY,))
    try:
        return _load_locked(conn, directory, identity, started_at)
    finally:
        conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))


def _load_locked(
    conn: psycopg.Connection, directory: Path, identity: Identity, started_at: _dt.datetime
) -> LoadResult:
    # --- 2. detection ---------------------------------------------------------------------------
    completed = conn.execute(
        "SELECT id, dataset_version, manifest_sha256, files FROM data_loads WHERE status = 'COMPLETED'"
    ).fetchone()
    if completed is not None:
        load_id, version, manifest_sha256, files = completed
        if version != identity.dataset_version:
            message = f"the database already holds dataset {version}: another dataset needs another database"
            return _fail(conn, identity, started_at, LoadOutcome.LINEAGE_CONFLICT, [DataError(message)])
        stored = {entry["name"]: entry["sha256"] for entry in files}
        if manifest_sha256 == identity.manifest_sha256 and stored == identity.file_sha256:
            return LoadResult(LoadOutcome.ALREADY_LOADED, version, load_id)
        message = f"dataset {version} is already loaded with different content (sha256)"
        return _fail(conn, identity, started_at, LoadOutcome.INTEGRITY_CONFLICT, [DataError(message)])

    # --- 3. pre-validation and 4. mapping, without touching the database -------------------------
    dataset, errors = read_dataset(directory)
    if dataset is None:
        return _fail(conn, identity, started_at, LoadOutcome.INVALID_DATASET, errors)
    rows, errors = map_dataset(dataset)
    if errors:
        return _fail(conn, identity, started_at, LoadOutcome.INVALID_DATASET, errors)

    # --- 5. load, 6. post-validation and 7. commit, in ONE transaction ---------------------------
    try:
        with conn.transaction():
            stamp = conn.execute("SELECT transaction_timestamp()").fetchone()[0]
            for name, typed_rows in rows.items():
                _copy(conn, name, typed_rows, stamp)
                _reset_sequence(conn, contract.table_name(name))
            post_errors = post_validate(conn, dataset.manifest)
            if post_errors:
                raise _PostValidationFailed(post_errors)
            load_id = _record(conn, identity, started_at, LoadOutcome.COMPLETED, [])
    except _PostValidationFailed as exc:
        return _fail(conn, identity, started_at, LoadOutcome.POST_VALIDATION_FAILED, exc.errors)
    except psycopg.Error as exc:
        return _fail(conn, identity, started_at, LoadOutcome.LOAD_FAILED, [_database_error(exc)])
    loaded = {contract.table_name(name): len(r) for name, r in rows.items()}
    return LoadResult(LoadOutcome.COMPLETED, identity.dataset_version, load_id, (), loaded)


def _now(conn: psycopg.Connection) -> _dt.datetime:
    return conn.execute("SELECT clock_timestamp()").fetchone()[0]


def _copy(conn: psycopg.Connection, name: str, rows: list[tuple[Any, ...]], stamp: _dt.datetime) -> None:
    columns = contract.header(name)
    statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier(contract.table_name(name)), sql.SQL(", ").join(map(sql.Identifier, columns))
    )
    with conn.cursor() as cur, cur.copy(statement) as copy:
        for row in rows:
            copy.write_row([stamp if value is STAMP else value for value in row])


def _reset_sequence(conn: psycopg.Connection, table: str) -> None:
    """Next generated ``id`` = max loaded ``id`` + 1 (or 1 for an empty table)."""
    conn.execute(
        sql.SQL(
            "SELECT setval(pg_get_serial_sequence({}, 'id'), COALESCE(max(id), 1), count(*) > 0) FROM {}"
        ).format(sql.Literal(table), sql.Identifier(table))
    )


def _database_error(exc: psycopg.Error) -> DataError:
    diag = exc.diag
    detail = f" ({diag.message_detail})" if diag.message_detail else ""
    return DataError(
        f"{diag.sqlstate or ''} {diag.message_primary or exc}{detail}".strip(),
        file=f"{diag.table_name}.csv" if diag.table_name else None,
        column=diag.column_name or diag.constraint_name,
    )


def _record(
    conn: psycopg.Connection,
    identity: Identity,
    started_at: _dt.datetime,
    outcome: LoadOutcome,
    errors: list[DataError],
) -> int:
    manifest = identity.manifest
    origin = manifest.get("data_origin")
    period = time_range(manifest)
    files = manifest.get("files") if isinstance(manifest.get("files"), list) else []
    recorded = [e.as_json() for e in errors[:MAX_RECORDED_ERRORS]]
    if len(errors) > MAX_RECORDED_ERRORS:
        recorded.append(DataError(f"{len(errors) - MAX_RECORDED_ERRORS} more errors not recorded").as_json())
    generator_version = manifest.get("generator_version")
    return conn.execute(
        """
        INSERT INTO data_loads (dataset_version, generator_version, data_origin, time_range, manifest,
                                manifest_sha256, files, status, outcome, errors, started_at, finished_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, clock_timestamp())
        RETURNING id
        """,
        (
            identity.dataset_version,
            generator_version if isinstance(generator_version, str) else None,
            origin if origin in contract.DATA_ORIGINS else None,
            None if period is None else Range(period[0], period[1], "[)"),
            Jsonb(manifest),
            identity.manifest_sha256,
            Jsonb(files),
            "COMPLETED" if outcome is LoadOutcome.COMPLETED else "FAILED",
            outcome.value,
            Jsonb(recorded),
            started_at,
        ),
    ).fetchone()[0]


def _fail(
    conn: psycopg.Connection,
    identity: Identity,
    started_at: _dt.datetime,
    outcome: LoadOutcome,
    errors: list[DataError],
) -> LoadResult:
    with conn.transaction():
        load_id = _record(conn, identity, started_at, outcome, errors)
    return LoadResult(outcome, identity.dataset_version, load_id, tuple(errors))


# --- 6. post-validation ------------------------------------------------------------------------


def post_validate(conn: psycopg.Connection, manifest: dict[str, Any]) -> list[DataError]:
    """The six invariants of `docs/04` §9.5 step 6, over the rows of the current transaction."""
    errors: list[DataError] = []

    # 1. rows per table = files[].rows
    declared = {entry["name"]: entry["rows"] for entry in manifest["files"]}
    for name in contract.FILES:
        table = contract.table_name(name)
        count = conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]
        if count != declared[name]:
            errors.append(DataError(f"{count} rows in {table}, the manifest declares {declared[name]}", name))

    # 2. quantity_on_hand = Σ movements of the pair
    for product, location, on_hand, total in conn.execute(
        """
        SELECT product_id, location_id, i.quantity_on_hand, COALESCE(m.total, 0)
        FROM inventory i
        FULL JOIN (SELECT product_id, location_id, sum(quantity) AS total
                   FROM inventory_movements GROUP BY product_id, location_id) m
            USING (product_id, location_id)
        WHERE i.quantity_on_hand IS DISTINCT FROM COALESCE(m.total, 0)
        ORDER BY product_id, location_id LIMIT %s
        """,
        (_SAMPLE,),
    ):
        errors.append(
            DataError(
                f"product {product} at location {location}: quantity_on_hand {on_hand}, Σ movements {total}",
                "inventory.csv",
                column="quantity_on_hand",
            )
        )

    # 3. quantity_in_transit = Σ pending of the ISSUED / PARTIALLY_RECEIVED lines
    for product, location, in_transit, pending in conn.execute(
        """
        SELECT product_id, location_id, i.quantity_in_transit, COALESCE(p.pending, 0)
        FROM inventory i
        FULL JOIN (SELECT it.product_id, po.location_id,
                          sum(it.quantity_ordered - it.quantity_received) AS pending
                   FROM purchase_order_items it
                   JOIN purchase_orders po ON po.id = it.purchase_order_id
                   WHERE po.status IN ('ISSUED', 'PARTIALLY_RECEIVED')
                   GROUP BY it.product_id, po.location_id) p
            USING (product_id, location_id)
        WHERE i.quantity_in_transit IS DISTINCT FROM COALESCE(p.pending, 0)
        ORDER BY product_id, location_id LIMIT %s
        """,
        (_SAMPLE,),
    ):
        errors.append(
            DataError(
                f"product {product} at location {location}: quantity_in_transit {in_transit}, "
                f"Σ pending of open lines {pending}",
                "inventory.csv",
                column="quantity_in_transit",
            )
        )

    # 4. purchase_order_items.quantity_received = Σ receipts
    for item, received, total in conn.execute(
        """
        SELECT it.id, it.quantity_received, COALESCE(sum(r.quantity_received), 0)
        FROM purchase_order_items it
        LEFT JOIN purchase_order_receipts r ON r.purchase_order_item_id = it.id
        GROUP BY it.id
        HAVING it.quantity_received <> COALESCE(sum(r.quantity_received), 0)
        ORDER BY it.id LIMIT %s
        """,
        (_SAMPLE,),
    ):
        errors.append(
            DataError(
                f"item {item}: quantity_received {received}, Σ receipts {total}",
                "purchase_order_items.csv",
                column="quantity_received",
            )
        )

    # 5. every polymorphic reference resolves (DT-038 §5.2)
    for movement, reference_type, reference_id in conn.execute(
        """
        SELECT m.id, m.reference_type, m.reference_id
        FROM inventory_movements m
        WHERE NOT (
            (m.reference_type = 'INITIAL_INVENTORY' AND m.reference_id IS NULL)
            OR (m.reference_type = 'CONSUMPTION'
                AND EXISTS (SELECT 1 FROM consumption c WHERE c.id = m.reference_id))
            OR (m.reference_type = 'PURCHASE_ORDER_RECEIPT'
                AND EXISTS (SELECT 1 FROM purchase_order_receipts r WHERE r.id = m.reference_id))
        )
        ORDER BY m.id LIMIT %s
        """,
        (_SAMPLE,),
    ):
        errors.append(
            DataError(
                f"movement {movement}: reference {reference_type} {reference_id} does not resolve",
                "inventory_movements.csv",
                column="reference_id",
            )
        )

    # 6. data_origin of every row = that of the load
    origin = manifest["data_origin"]
    for name in contract.FILES:
        table = contract.table_name(name)
        count = conn.execute(
            sql.SQL("SELECT count(*) FROM {} WHERE data_origin <> %s").format(sql.Identifier(table)), (origin,)
        ).fetchone()[0]
        if count:
            errors.append(DataError(f"{count} rows with data_origin other than {origin}", name, column="data_origin"))
    return errors
