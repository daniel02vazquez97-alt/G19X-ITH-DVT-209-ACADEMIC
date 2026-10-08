"""Print the pinned requirements of ``backend/pyproject.toml`` for the given groups (U8, `DT-096`).

    python infra/ci/backend_requirements.py db api test > requirements.txt

``pyproject.toml`` stays the single source of versions (`DT-055`, `DT-064`): this prints
``dependencies`` plus the optional groups asked for, in that order, and fails on an unknown group or
on a requirement that is not pinned with ``==``. It exists because ``pip install -e "backend[...]"``
does not build with current setuptools (flat layout with ``app`` and ``db``; see `DT-096`).
Standard library only (``tomllib``, Python 3.11+).
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[2] / "backend" / "pyproject.toml"
PINNED = re.compile(r"^[A-Za-z0-9_.\[\]-]+==[0-9][A-Za-z0-9.]*$")


def requirements(groups: list[str], pyproject: Path = PYPROJECT) -> list[str]:
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
    optional = project.get("optional-dependencies", {})
    unknown = [group for group in groups if group not in optional]
    if unknown:
        raise SystemExit(f"unknown group(s): {', '.join(unknown)}; known: {', '.join(sorted(optional))}")
    result = list(project.get("dependencies", []))
    for group in groups:
        result.extend(optional[group])
    loose = [requirement for requirement in result if not PINNED.match(requirement)]
    if loose:
        raise SystemExit(f"requirement(s) not pinned with ==: {', '.join(loose)}")
    return result


if __name__ == "__main__":
    print("\n".join(requirements(sys.argv[1:])))
