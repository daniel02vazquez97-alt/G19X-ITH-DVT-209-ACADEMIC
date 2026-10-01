"""``python -m app.ingestion <dataset_dir>`` — load a published dataset into ``DATABASE_URL``.

Exit status 0 for ``COMPLETED`` and ``ALREADY_LOADED``, 1 for any rejection or failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.db.connection import connect

from .loader import load_dataset


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m app.ingestion <dataset_dir>", file=sys.stderr)
        return 2
    with connect() as conn:
        result = load_dataset(conn, Path(argv[0]))
    print(f"{result.outcome}: dataset {result.dataset_version}, data_loads.id {result.data_load_id}")
    for table, count in result.rows.items():
        print(f"  {table}: {count}")
    for error in result.errors[:50]:
        print(f"  {error}", file=sys.stderr)
    if len(result.errors) > 50:
        print(f"  … {len(result.errors) - 50} more errors", file=sys.stderr)
    return 0 if result.outcome.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
