"""Row-by-row mapping of the CSV text to typed values (step 4 of `docs/04` §9.5).

Types of `docs/04` §9.3 and formats of `DT-024`; the row-level restrictions the schema also declares
are checked here so that the report lists every rejected row with its reason (RF-022, `US-011`).
Keys, foreign keys and uniqueness are left to the database. All or nothing: any error rejects the
whole dataset, and every error is accumulated.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from . import contract
from .dataset import DataError, Dataset

#: A technical column: the ingestion writes the load instant in its place (`docs/04` §9.3).
STAMP = object()

_POSITIVE_INT = re.compile(r"[1-9][0-9]*")
_INT = re.compile(r"-?(0|[1-9][0-9]*)")
_NONNEG_INT = re.compile(r"0|[1-9][0-9]*")
_QUANTITY = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?")
_MONEY = re.compile(r"-?(0|[1-9][0-9]*)\.[0-9]{2}")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_DATETIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")

_QUANTITY_DOMAINS: dict[str, tuple[Callable[[Decimal], bool], str]] = {
    "nonneg": (lambda q: q >= 0, "must be >= 0"),
    "pos": (lambda q: q > 0, "must be > 0"),
    "nonzero": (lambda q: q != 0, "must be != 0"),
    "any": (lambda q: True, ""),
}


def _match(pattern: re.Pattern[str], raw: str, what: str) -> None:
    if pattern.fullmatch(raw) is None:
        raise ValueError(f"{raw!r} is not {what}")


def parse_value(column: contract.Column, raw: str) -> Any:
    """The typed value of one field; raises ``ValueError`` with the reason."""
    if column.kind == "stamped":
        if raw != "":
            raise ValueError("must be empty: the ingestion sets it")
        return STAMP
    if raw == "":
        if column.nullable:
            return None
        raise ValueError("is required")
    kind = column.kind
    if kind in ("id", "ref"):
        _match(_POSITIVE_INT, raw, "an integer >= 1")
        return int(raw)
    if kind == "int":
        _match(_INT, raw, "an integer")
        return int(raw)
    if kind == "int_nonneg":
        _match(_NONNEG_INT, raw, "an integer >= 0")
        return int(raw)
    if kind == "qty":
        _match(_QUANTITY, raw, "a quantity")
        value = Decimal(raw)
        check, reason = _QUANTITY_DOMAINS[column.domain]
        if not check(value):
            raise ValueError(f"{raw} {reason}")
        return value
    if kind == "money":
        _match(_MONEY, raw, "an amount with two decimals")
        return Decimal(raw)
    if kind == "text":
        return raw
    if kind == "bool":
        if raw not in ("true", "false"):
            raise ValueError(f"{raw!r} is not true or false")
        return raw == "true"
    if kind == "date":
        _match(_DATE, raw, "a date YYYY-MM-DD")
        return _dt.date.fromisoformat(raw)
    if kind == "datetime":
        _match(_DATETIME, raw, "a UTC instant YYYY-MM-DDTHH:MM:SSZ")
        return _dt.datetime.fromisoformat(raw[:-1]).replace(tzinfo=_dt.UTC)
    if kind == "origin":
        if raw not in contract.DATA_ORIGINS:
            raise ValueError(f"{raw!r} is not SYNTHETIC or REAL")
        return raw
    if kind == "vocab":
        if raw not in column.domain:
            raise ValueError(f"{raw!r} is not one of {', '.join(column.domain)}")
        return raw
    raise AssertionError(f"unknown column kind {kind}")


def _row_checks(name: str, record: dict[str, Any]) -> list[tuple[str, str]]:
    """Cross-column restrictions of `docs/04` §9.3, as ``(column, reason)``."""
    problems = []
    if name == "products.csv":
        if record["valid_to"] is not None and record["valid_from"] > record["valid_to"]:
            problems.append(("valid_to", "valid_from must be <= valid_to"))
    elif name == "product_suppliers.csv":
        if record["order_multiple"] < 1:
            problems.append(("order_multiple", "must be >= 1"))
    elif name == "purchase_order_items.csv":
        if record["quantity_received"] > record["quantity_ordered"]:
            problems.append(("quantity_received", "must be <= quantity_ordered"))
    elif name == "demand.csv":
        if record["data_origin"] != "SYNTHETIC":
            problems.append(("data_origin", "demand only exists in synthetic data"))
    return problems


def map_dataset(dataset: Dataset) -> tuple[dict[str, list[tuple[Any, ...]]], list[DataError]]:
    """Typed rows of every file, in load order, or every error found."""
    mapped: dict[str, list[tuple[Any, ...]]] = {}
    errors: list[DataError] = []
    for name, columns in contract.FILES.items():
        typed_rows = []
        for offset, row in enumerate(dataset.rows[name]):
            line = offset + 2
            values = []
            row_ok = True
            for column, raw in zip(columns, row, strict=True):
                try:
                    values.append(parse_value(column, raw))
                except ValueError as exc:
                    errors.append(DataError(str(exc), name, line, column.name))
                    row_ok = False
            if not row_ok:
                continue
            record = dict(zip((c.name for c in columns), values, strict=True))
            problems = _row_checks(name, record)
            for column_name, reason in problems:
                errors.append(DataError(reason, name, line, column_name))
            if not problems:
                typed_rows.append(tuple(values))
        mapped[name] = typed_rows
    if errors:
        return {}, errors
    return mapped, []
