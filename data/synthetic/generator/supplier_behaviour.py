"""Component 6 - Supplier Behaviour Generator: one deterministic profile per supplier.

Phase 1 - Data.

    suppliers.csv (Component 2)
        -> build_supplier_profiles() -> tuple[SupplierProfile, ...] (in memory)
            -> consumed by Component 4 (`DT-038` section 1)
        -> generate() also adds this component to manifest.json - and writes nothing else

Execution order of the approved pipeline (`DT-040` section 4)::

    C2 -> C3 -> C6 -> C4 -> C5

**What it does** (`DT-037`): gives every supplier - active or not - one profile on each
of two orthogonal axes, punctuality and integrity. The share of each profile is fixed by
a mix with a floor of one (largest remainder, `DT-028` section 3.2, the helper shared with
Components 3 and 4); which supplier gets which slot is decided by a seeded permutation per
axis, exactly as Component 3 assigns demand shapes to products. The values of a profile
are constants of `DT-037` section 2, never draws.

**What it does not do.** It writes **no data file**: a ``supplier_behaviour.csv`` would be
generation metadata inside a business entity, which specification section 42.1 forbids.
Its only persistent trace is its entry in ``manifest.components`` (decision A1,
2026-09-28). It knows nothing about orders, receipts, inventory or dates: applying a
profile to a concrete order is Component 4's job.

**Contract with Component 4.** The profiles are instances of
:class:`~.inventory.SupplierProfile`, the type Component 4 declared as the contract it
consumes (decision A2, 2026-09-28). Only that dataclass is imported: no function of
Component 4 is called.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ..config.config import DatasetConfig
from . import policies as pol
from .inventory import SupplierProfile  # the data contract only (decision A2)
from .rng import COMPONENT_SUPPLIER_BEHAVIOUR, DeterministicRandom, sub_seed
from .writer import SUPPLIER_BEHAVIOUR_VERSION, extend_manifest, write_manifest

__all__ = [
    "SUPPLIERS_FILE",
    "PUNCTUALITY_STREAM",
    "INTEGRITY_STREAM",
    "build_supplier_profiles",
    "generate",
]

SUPPLIERS_FILE = "suppliers.csv"
MANIFEST_FILE = "manifest.json"

#: `DT-037` section 4: the two streams, and only these two, both on
#: ``sub_seed(seed, "supplier_behaviour")``.
PUNCTUALITY_STREAM = "punctuality-assignment"
INTEGRITY_STREAM = "integrity-assignment"


def _read_supplier_ids(input_dir: Path) -> list[int]:
    """Every supplier id of ``suppliers.csv``, ascending. ``is_active`` is not read:
    inactive suppliers get a profile too (`DT-037` section 4)."""
    path = input_dir / SUPPLIERS_FILE
    if not path.is_file():
        raise pol.GeneratorError(
            [
                f"{SUPPLIERS_FILE} not found in {input_dir}; Component 6 reads the "
                "catalogue Component 2 writes, which must be generated first"
            ]
        )
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if "id" not in (reader.fieldnames or []):
            raise pol.GeneratorError([f"{SUPPLIERS_FILE} has no 'id' column"])
        ids = [int(row["id"]) for row in reader]
    if len(set(ids)) != len(ids):
        raise pol.GeneratorError([f"{SUPPLIERS_FILE} repeats a supplier id"])
    return sorted(ids)


def _slots(mix: dict[str, int], members: tuple[str, ...], total: int) -> list[str]:
    """The quota of each profile, laid out in canonical order (`DT-028` section 3.2)."""
    counts = pol.demand_mix_counts(mix, members, total)
    slots: list[str] = []
    for name in members:
        slots.extend([name] * counts[name])
    return slots


def build_supplier_profiles(
    config: DatasetConfig, input_dir: Path | str
) -> tuple[SupplierProfile, ...]:
    """One profile per supplier of ``suppliers.csv``, ordered by ``supplier_id``.

    Reads ``input_dir``; writes nothing.

    Raises:
        GeneratorError: if ``suppliers.csv`` is missing or malformed, or if there are
            fewer than three suppliers (precondition P-C6-1): with fewer, the floor of
            one of the punctuality axis cannot hold, and the run fails instead of
            silently producing a dataset without one of the behaviours of section 12.
    """
    ids = _read_supplier_ids(Path(input_dir))
    if len(ids) < pol.SUPPLIER_BEHAVIOUR_MIN_SUPPLIERS:
        raise pol.GeneratorError(
            [
                f"P-C6-1: at least {pol.SUPPLIER_BEHAVIOUR_MIN_SUPPLIERS} suppliers are "
                f"needed, one per punctuality profile (DT-037 section 2); found {len(ids)}"
            ]
        )

    count = len(ids)
    punctuality_slots = _slots(
        pol.SUPPLIER_PUNCTUALITY_MIX, pol.SUPPLIER_PUNCTUALITY_PROFILES, count
    )
    integrity_slots = _slots(
        pol.SUPPLIER_INTEGRITY_MIX, pol.SUPPLIER_INTEGRITY_PROFILES, count
    )

    # Two independent streams: a change in one axis never shifts the other (DT-032).
    base = sub_seed(config.seed, COMPONENT_SUPPLIER_BEHAVIOUR)
    punctuality_order = DeterministicRandom(base, PUNCTUALITY_STREAM).permutation(count)
    integrity_order = DeterministicRandom(base, INTEGRITY_STREAM).permutation(count)

    profiles = []
    for position, supplier_id in enumerate(ids):
        punctuality = punctuality_slots[punctuality_order[position]]
        integrity = integrity_slots[integrity_order[position]]
        profiles.append(
            SupplierProfile(
                supplier_id=supplier_id,
                punctuality=punctuality,
                integrity=integrity,
                on_time_permille=pol.SUPPLIER_ON_TIME_PERMILLE[punctuality],
                delay_days=pol.SUPPLIER_DELAY_DAYS[punctuality],
                partial_permille=pol.SUPPLIER_PARTIAL_PERMILLE[integrity],
                split_range=pol.SUPPLIER_SPLIT_RANGE[integrity],
                completion_lag_days=pol.SUPPLIER_COMPLETION_LAG_DAYS[integrity],
            )
        )
    return tuple(profiles)


def generate(
    config: DatasetConfig, output_dir: Path | str
) -> tuple[dict[str, Any], tuple[SupplierProfile, ...]]:
    """Build the profiles and add this component to ``manifest.json`` in ``output_dir``.

    ``output_dir`` is **required**: the workspace of the run (`DT-040`), which already
    holds Component 2's output. The manifest is the only file touched, and only to add
    ``{name, version, sub_seed}`` to ``components``; ``files`` gains nothing, because this
    component writes no data file (`DT-037` section 1, decision A1).

    Returns:
        The extended manifest, already written, and the profiles for Component 4.

    Raises:
        GeneratorError: see :func:`build_supplier_profiles`; also if ``manifest.json``
            is missing. Nothing is written in either case.
        ValueError: if the manifest already records this component.
    """
    target = Path(output_dir)
    profiles = build_supplier_profiles(config, target)

    manifest_path = target / MANIFEST_FILE
    if not manifest_path.is_file():
        raise pol.GeneratorError(
            [f"{MANIFEST_FILE} not found in {target}; Component 2 writes it first"]
        )
    manifest = extend_manifest(
        json.loads(manifest_path.read_text(encoding="utf-8")),
        component={
            "name": COMPONENT_SUPPLIER_BEHAVIOUR,
            "version": SUPPLIER_BEHAVIOUR_VERSION,
            "sub_seed": sub_seed(config.seed, COMPONENT_SUPPLIER_BEHAVIOUR),
        },
        files=[],
    )
    write_manifest(manifest_path, manifest)
    return manifest, profiles
