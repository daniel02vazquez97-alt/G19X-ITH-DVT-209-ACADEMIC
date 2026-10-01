"""Shared helpers of the ingestion tests: the published dataset and altered temporary copies.

The dataset is never modified: every alteration happens on a copy in a temporary directory, and the
manifest of the copy is rewritten so that only the intended defect remains.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
DATASET_DIR = Path(os.environ.get("U2_DATASET_DIR", REPO_DIR / "data" / "synthetic" / "output"))
DATASET_AVAILABLE = (DATASET_DIR / "manifest.json").is_file()
SKIP_REASON = f"dataset 0.4.0 not found in {DATASET_DIR} (set U2_DATASET_DIR)"


def copy_dataset() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    """A temporary copy of the dataset; the caller must clean up the returned handle."""
    handle = tempfile.TemporaryDirectory(prefix="u2_dataset_")
    target = Path(handle.name) / "output"
    shutil.copytree(DATASET_DIR, target)
    return handle, target


def read_manifest(directory: Path) -> dict:
    return json.loads((directory / "manifest.json").read_text(encoding="utf-8"))


def write_manifest(directory: Path, manifest: dict) -> None:
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    (directory / "manifest.json").write_text(text, encoding="utf-8", newline="\n")


def edit_manifest(directory: Path, change: Callable[[dict], None]) -> None:
    manifest = read_manifest(directory)
    change(manifest)
    write_manifest(directory, manifest)


def rewrite_csv(
    directory: Path,
    name: str,
    change: Callable[[list[list[str]]], None],
    update_manifest: bool = True,
) -> None:
    """Apply ``change`` to the records (header first) of ``name``; refresh its manifest entry."""
    path = directory / name
    with path.open(encoding="utf-8", newline="") as handle:
        records = list(csv.reader(handle))
    change(records)
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows(records)
    data = buffer.getvalue().encode("utf-8")
    path.write_bytes(data)
    if update_manifest:
        refresh_entry(directory, name)


def refresh_entry(directory: Path, name: str) -> None:
    """Make the manifest entry of ``name`` match the file on disk (sha256 and rows)."""
    data = (directory / name).read_bytes()
    rows = data.count(b"\n") - 1

    def change(manifest: dict) -> None:
        for entry in manifest["files"]:
            if entry["name"] == name:
                entry["sha256"] = hashlib.sha256(data).hexdigest()
                entry["rows"] = rows

    edit_manifest(directory, change)


def set_field(records: list[list[str]], row_id: str, column: str, value: str) -> None:
    """Set ``column`` of the data row whose ``id`` is ``row_id``."""
    index = records[0].index(column)
    for record in records[1:]:
        if record[0] == row_id:
            record[index] = value
            return
    raise KeyError(row_id)
