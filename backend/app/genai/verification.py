"""Figure verification (`DT-069` points 3–5, RS-010).

A narrative figure is every maximal match of ``-?\\d+(?:\\.\\d+)?`` in the final text. It is valid if and
only if it is equal, as a string, to the ``display`` of some fact: no tolerance, no conversion to a
number.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .errors import UnverifiedFigureError
from .types import Fact

FIGURE = re.compile(r"-?\d+(?:\.\d+)?")


def figures(text: str) -> tuple[str, ...]:
    return tuple(match.group() for match in FIGURE.finditer(text))


def verify(text: str, facts: Iterable[Fact]) -> None:
    """Raise ``UnverifiedFigureError`` with the figures of ``text`` that are not a fact's ``display``."""
    allowed = {fact.display for fact in facts}
    unknown = tuple(figure for figure in figures(text) if figure not in allowed)
    if unknown:
        raise UnverifiedFigureError(unknown)
