"""Reading and file-level validation of a published dataset, without touching the database.

Steps 2 (identity for detection) and 3 (pre-validation) of `docs/04` §9.5: ``manifest.json`` with its
eleven fields, ``quality_report`` in ``PASS``, the set of files equal to ``files[]``, each file equal
in ``sha256`` and number of rows, and each header equal to its contract. CSV format is that of
`DT-024`: UTF-8 without BOM, comma, RFC 4180 quoting, LF line endings. Every error is accumulated.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import contract

MANIFEST = "manifest.json"


@dataclass(frozen=True)
class DataError:
    """One reason why a dataset is rejected. ``line`` is the physical CSV line (header = 1)."""

    message: str
    file: str | None = None
    line: int | None = None
    column: str | None = None

    def as_json(self) -> dict[str, Any]:
        return {"file": self.file, "line": self.line, "column": self.column, "message": self.message}

    def __str__(self) -> str:
        where = ":".join(str(p) for p in (self.file, self.line, self.column) if p is not None)
        return f"{where}: {self.message}" if where else self.message


@dataclass(frozen=True)
class Identity:
    """What detection compares with ``data_loads`` (`docs/04` §9.5, table of detection)."""

    manifest: dict[str, Any]
    manifest_sha256: str
    #: ``sha256`` of each file named in ``files[]`` as found on disk (``None`` if missing).
    file_sha256: dict[str, str | None]

    @property
    def dataset_version(self) -> str:
        return self.manifest["dataset_version"]


@dataclass(frozen=True)
class Dataset:
    """A dataset that passed pre-validation: its manifest and the data rows of each file."""

    directory: Path
    manifest: dict[str, Any]
    manifest_sha256: str
    #: File name → data rows (header excluded), in the file's order.
    rows: dict[str, list[list[str]]]


class ManifestError(ValueError):
    """``manifest.json`` cannot be read, or has no usable ``dataset_version``."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_identity(directory: Path) -> Identity:
    """The manifest and the on-disk ``sha256`` of its files; raises `ManifestError` if unusable."""
    path = directory / MANIFEST
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ManifestError(f"{MANIFEST} cannot be read: {exc.strerror}") from exc
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"{MANIFEST} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ManifestError(f"{MANIFEST} is not a JSON object")
    version = manifest.get("dataset_version")
    if not isinstance(version, str) or not version:
        raise ManifestError(f"{MANIFEST} has no dataset_version")
    file_sha256: dict[str, str | None] = {}
    for entry in manifest.get("files") or []:
        name = entry.get("name") if isinstance(entry, dict) else None
        if isinstance(name, str) and "/" not in name and "\\" not in name:
            target = directory / name
            file_sha256[name] = _sha256(target.read_bytes()) if target.is_file() else None
    return Identity(manifest, _sha256(raw), file_sha256)


def time_range(manifest: dict[str, Any]) -> tuple[_dt.date, _dt.date] | None:
    """``(start_date, end_date)`` of the manifest (end exclusive), or ``None`` if malformed."""
    value = manifest.get("time_range")
    if not isinstance(value, dict):
        return None
    try:
        start = _dt.date.fromisoformat(value["start_date"])
        end = _dt.date.fromisoformat(value["end_date"])
    except (KeyError, TypeError, ValueError):
        return None
    return (start, end) if start < end else None


def _validate_manifest(manifest: dict[str, Any]) -> list[DataError]:
    errors = []
    missing = [f for f in contract.MANIFEST_FIELDS if f not in manifest]
    unexpected = sorted(set(manifest) - set(contract.MANIFEST_FIELDS))
    if missing:
        errors.append(DataError(f"missing fields: {', '.join(missing)}", MANIFEST))
    if unexpected:
        errors.append(DataError(f"unexpected fields: {', '.join(unexpected)}", MANIFEST))
    if manifest.get("data_origin") not in contract.DATA_ORIGINS:
        errors.append(DataError("data_origin must be SYNTHETIC or REAL", MANIFEST))
    if not isinstance(manifest.get("generator_version"), str):
        errors.append(DataError("generator_version must be a string", MANIFEST))
    if "time_range" in manifest and time_range(manifest) is None:
        errors.append(DataError("time_range must hold start_date < end_date", MANIFEST))

    report = manifest.get("quality_report")
    validations = report.get("validations") if isinstance(report, dict) else None
    if not isinstance(report, dict) or report.get("result") != "PASS":
        errors.append(DataError("quality_report.result is not PASS", MANIFEST))
    if not isinstance(validations, dict) or not (
        validations.get("failed") == 0
        and isinstance(validations.get("executed"), int)
        and validations.get("executed") == validations.get("passed")
    ):
        errors.append(DataError("quality_report.validations must have failed = 0 and executed = passed", MANIFEST))
    if isinstance(report, dict) and report.get("dataset_version") not in (None, manifest.get("dataset_version")):
        errors.append(DataError("quality_report.dataset_version differs from dataset_version", MANIFEST))
    return errors


def _file_entries(manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[DataError]]:
    entries: dict[str, dict[str, Any]] = {}
    errors = []
    files = manifest.get("files")
    if not isinstance(files, list):
        return entries, [DataError("files must be a list", MANIFEST)]
    for position, entry in enumerate(files):
        if not (
            isinstance(entry, dict)
            and isinstance(entry.get("name"), str)
            and isinstance(entry.get("rows"), int)
            and isinstance(entry.get("sha256"), str)
        ):
            errors.append(DataError(f"files[{position}] needs name, rows and sha256", MANIFEST))
            continue
        if entry["name"] in entries:
            errors.append(DataError(f"files lists {entry['name']} twice", MANIFEST))
        entries[entry["name"]] = entry
    expected = set(contract.FILES)
    for name in sorted(expected - set(entries)):
        errors.append(DataError(f"files does not list {name}", MANIFEST))
    for name in sorted(set(entries) - expected):
        errors.append(DataError(f"files lists {name}, which is not in the contract", MANIFEST))
    return entries, errors


def _read_csv(path: Path, entry: dict[str, Any]) -> tuple[list[list[str]] | None, list[DataError]]:
    name = path.name
    data = path.read_bytes()
    errors = []
    if _sha256(data) != entry["sha256"]:
        errors.append(DataError("sha256 differs from the manifest", name))
    if data.startswith(b"\xef\xbb\xbf"):
        errors.append(DataError("file starts with a BOM", name))
    if b"\r" in data:
        errors.append(DataError("line endings must be LF", name))
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return None, errors + [DataError(f"not valid UTF-8: {exc}", name)]
    try:
        records = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error as exc:
        return None, errors + [DataError(f"malformed CSV: {exc}", name)]
    if not records:
        return None, errors + [DataError("file is empty: the header is missing", name)]
    if records[0] != contract.header(name):
        errors.append(
            DataError(f"header {records[0]} differs from the contract {contract.header(name)}", name, 1)
        )
    rows = records[1:]
    if len(rows) != entry["rows"]:
        errors.append(DataError(f"{len(rows)} rows, the manifest declares {entry['rows']}", name))
    width = len(contract.FILES[name])
    for offset, row in enumerate(rows):
        if len(row) != width:
            errors.append(DataError(f"{len(row)} fields, expected {width}", name, offset + 2))
    return rows, errors


def read_dataset(directory: Path) -> tuple[Dataset | None, list[DataError]]:
    """Pre-validate ``directory`` (step 3). Returns the dataset, or ``None`` with every error."""
    try:
        identity = read_identity(directory)
    except ManifestError as exc:
        return None, [DataError(str(exc), MANIFEST)]
    manifest = identity.manifest
    errors = _validate_manifest(manifest)
    entries, entry_errors = _file_entries(manifest)
    errors += entry_errors

    present = {p.name for p in directory.iterdir() if p.is_file()} - {MANIFEST}
    for name in sorted(present - set(entries)):
        errors.append(DataError("file is not listed in the manifest", name))
    rows: dict[str, list[list[str]]] = {}
    for name in contract.FILES:
        if name not in entries:
            continue
        if name not in present:
            errors.append(DataError("file listed in the manifest does not exist", name))
            continue
        file_rows, file_errors = _read_csv(directory / name, entries[name])
        errors += file_errors
        if file_rows is not None:
            rows[name] = file_rows
    if errors:
        return None, errors
    return Dataset(directory, manifest, identity.manifest_sha256, rows), []
