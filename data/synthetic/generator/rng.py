"""Deterministic pseudo-random stream for the synthetic dataset generator.

Phase 1 - Data. Implements `DT-030` (sub-seeds) and `DT-032` (stream algorithm).

Two things live here, and only these two:

* :func:`sub_seed` - the sub-seed derivation fixed by `DT-030`, so that adding a
  component never changes the data produced by the existing ones.
* :class:`DeterministicRandom` - the concrete pseudo-random algorithm, which `DT-030`
  and section 44 of ``knowledge/dataset-specification.md`` explicitly leave to
  Component 2.

**Why not** ``random.Random``. Section 44 records a known limit: the sub-seed is stable
across Python versions and platforms because it only depends on SHA-256, but "the
pseudo-random stream derived from it is not necessarily stable, because the standard
library implementation may change between versions". A counter-based SHA-256 stream has
no such caveat: every draw is a pure function of ``(seed, label, counter)``, so the same
configuration produces the same bytes on any Python 3.11+, on any platform, forever.
That closes the limit instead of documenting it. See `DT-032`.

This module is **not** a general-purpose random source. It offers exactly the three
draws the generator needs, it is not thread-safe, and it must never be used for anything
security-related: SHA-256 in counter mode is deterministic and fully predictable from the
seed, which is the whole point here.
"""

from __future__ import annotations

import hashlib
from typing import Sequence, TypeVar

__all__ = [
    "sub_seed",
    "DeterministicRandom",
    "COMPONENT_IDS",
    "COMPONENT_CATALOG",
    "COMPONENT_DEMAND",
    "COMPONENT_INVENTORY",
    "COMPONENT_ORDERS",
    "COMPONENT_SUPPLIER_BEHAVIOUR",
    "COMPONENT_SCENARIOS",
    "COMPONENT_VALIDATOR",
]

T = TypeVar("T")

# ---------------------------------------------------------------------------------------
# Canonical component identifiers - DT-030
#
# Each is a short, lowercase, stable ASCII string, deliberately **distinct from the
# component number**. That distinction is the whole point: the sub-seed is a function of
# the identifier, so an identifier derived from the number would make the data change if
# the components were ever renumbered, and inserting a component in the middle would
# silently rewrite every dataset after it.
#
# Fixed by the responsible party on 2026-09-21, before Component 3 draws anything. Only
# `catalog` was in use before that date, and it does not change - Component 2's output is
# unaffected.
#
# Component 1 (`DatasetConfig`) has no identifier on purpose: it validates configuration
# and draws nothing from the pseudo-random stream, so it has no sub-seed to derive.
# ---------------------------------------------------------------------------------------

#: Component 2 - Catalog Generator. In use since 2026-09-21; recorded in `DT-030`.
COMPONENT_CATALOG = "catalog"

#: Component 3 - Demand Generator.
COMPONENT_DEMAND = "demand"

#: Component 4 - Inventory Simulator.
COMPONENT_INVENTORY = "inventory"

#: Component 5 - Purchase Order Generator. Named for what it produces, not for the
#: entity: `purchase_orders` would be the file, and `DT-030` asks the identifier to be
#: independent of file names.
COMPONENT_ORDERS = "orders"

#: Component 6 - Supplier Behaviour Generator. The only identifier with an underscore:
#: `supplier` alone would collide in meaning with the master entity Component 2 already
#: generates, and `behaviour` alone says nothing about whose.
COMPONENT_SUPPLIER_BEHAVIOUR = "supplier_behaviour"

#: Component 7 - Scenario Assignment (`DT-023`, Level A axes).
COMPONENT_SCENARIOS = "scenarios"

#: Component 8 - Dataset Validator, including the quality report of specification
#: section 35. The report is **part of this component**, not a ninth one: `DT-023` and
#: `DT-025` both assign it to Component 8.
COMPONENT_VALIDATOR = "validator"

#: The canonical table `DT-030` requires, keyed by component number.
#:
#: The mapping exists so the table has one home instead of seven scattered constants; the
#: **identifiers**, not the numbers, are what the sub-seed depends on. The number is here
#: for readers, and changing it would not change a single byte of any dataset - which is
#: exactly the property `DT-030` was written to obtain.
COMPONENT_IDS: dict[int, str] = {
    2: COMPONENT_CATALOG,
    3: COMPONENT_DEMAND,
    4: COMPONENT_INVENTORY,
    5: COMPONENT_ORDERS,
    6: COMPONENT_SUPPLIER_BEHAVIOUR,
    7: COMPONENT_SCENARIOS,
    8: COMPONENT_VALIDATOR,
}

#: 2**64, the size of the raw draw space. Named because it appears in the rejection
#: bound below and an inline literal there would be unreadable.
_RAW_SPACE = 1 << 64


def sub_seed(seed: int, component_id: str) -> int:
    """Derive a component's sub-seed from the shared seed (`DT-030`).

    ``sub_seed(id) = int.from_bytes(sha256(f"{seed}:{id}").digest()[:8], "big")``

    The seed is serialised as a base-10 integer with no padding, exactly as `DT-030`
    states, so the value does not depend on how the caller formats it.

    Args:
        seed: ``DatasetConfig.seed``. Must be a non-negative integer.
        component_id: the component's canonical identifier, e.g. ``"catalog"``.

    Returns:
        A 64-bit unsigned integer.

    Raises:
        ValueError: if the seed is negative or the identifier is empty.
    """
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(f"seed must be an integer, got {seed!r}")
    if seed < 0:
        raise ValueError(f"seed must be zero or positive, got {seed}")
    if not component_id:
        raise ValueError("component_id must be a non-empty string")

    digest = hashlib.sha256(f"{seed}:{component_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


class DeterministicRandom:
    """Counter-based SHA-256 stream (`DT-032`).

    Each draw hashes ``"<seed>:<label>:<counter>"`` and reads 8 bytes from the digest.
    The counter advances on every draw, so the sequence is reproducible and independent
    of any library implementation detail.

    The ``label`` separates independent streams within one component. Two streams with
    different labels never overlap, which means the values drawn for, say, unit costs do
    not shift when the number of lead-time draws changes. That property is what keeps a
    change in one part of the generator from silently reshuffling another.
    """

    __slots__ = ("_seed", "_label", "_counter")

    def __init__(self, seed: int, label: str) -> None:
        if not label:
            raise ValueError("label must be a non-empty string")
        self._seed = int(seed)
        self._label = label
        self._counter = 0

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"DeterministicRandom(label={self._label!r}, counter={self._counter})"

    # -- primitive -------------------------------------------------------------------

    def _next_raw(self) -> int:
        """Next 64-bit draw. The only place the counter advances."""
        payload = f"{self._seed}:{self._label}:{self._counter}".encode("utf-8")
        self._counter += 1
        return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")

    # -- draws -----------------------------------------------------------------------

    def _next_wide(self, words: int) -> int:
        """Next draw of ``words`` * 64 bits, big-endian."""
        value = 0
        for _ in range(words):
            value = (value << 64) | self._next_raw()
        return value

    def below(self, bound: int) -> int:
        """Uniform integer in ``[0, bound)``.

        Uses rejection sampling rather than a modulo, so the distribution is exactly
        uniform. Taking ``raw % bound`` would over-represent the low values whenever
        ``bound`` does not divide the draw space - a bias that is small but real, and
        avoidable for the cost of one loop.

        A bound larger than 2**64 draws as many 64-bit words as it needs. Without that,
        the rejection limit would be zero and the loop would never terminate: the
        generator never asks for such a bound today, but a method documented as total
        should be total.

        The loop terminates with probability 1, and on its first pass unless the draw
        lands in the rejection tail - at most one part in 2**64 of the space per word.
        """
        if bound <= 0:
            raise ValueError(f"bound must be positive, got {bound}")
        words = 1
        space = _RAW_SPACE
        while space < bound:
            words += 1
            space <<= 64
        limit = space - (space % bound)
        while True:
            raw = self._next_wide(words)
            if raw < limit:
                return raw % bound

    def between(self, low: int, high: int) -> int:
        """Uniform integer in the closed interval ``[low, high]``."""
        if low > high:
            raise ValueError(f"low must not exceed high, got low={low}, high={high}")
        return low + self.below(high - low + 1)

    def choice(self, options: Sequence[T]) -> T:
        """Uniform choice from a non-empty sequence."""
        if not options:
            raise ValueError("options must not be empty")
        return options[self.below(len(options))]

    def permutation(self, count: int) -> list[int]:
        """A permutation of ``range(count)``.

        Fisher-Yates, written out rather than delegated to ``random.shuffle``: the
        standard library's shuffle is not guaranteed to produce the same permutation
        across Python versions, which is precisely the guarantee this module exists to
        provide.
        """
        if count < 0:
            raise ValueError(f"count must not be negative, got {count}")
        items = list(range(count))
        for i in range(count - 1, 0, -1):
            j = self.below(i + 1)
            items[i], items[j] = items[j], items[i]
        return items
