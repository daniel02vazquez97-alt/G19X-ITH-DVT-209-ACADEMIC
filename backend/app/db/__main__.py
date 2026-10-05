"""``python -m app.db migrate`` — apply the pending migrations to ``DATABASE_URL``."""

from __future__ import annotations

import sys

from .connection import connect
from .migrations import apply_migrations


def main(argv: list[str]) -> int:
    if argv != ["migrate"]:
        print("usage: python -m app.db migrate", file=sys.stderr)
        return 2
    with connect() as conn:
        applied = apply_migrations(conn)
    print("applied: " + (", ".join(applied) if applied else "none (schema up to date)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
