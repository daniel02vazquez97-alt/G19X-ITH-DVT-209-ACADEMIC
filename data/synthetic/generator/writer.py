"""Output contract of the synthetic dataset: CSV files and ``manifest.json``.

Phase 1 - Data. Implements `DT-024` (one CSV per entity, format conventions) and
`DT-025` (manifest), plus the versioning scheme `DT-025` rule 5 defers to the generator
(`DT-033`).

The format conventions are **part of the contract**, not implementation detail: without
them "CSV" restricts nothing. They are applied in exactly one place - :func:`format_value`
- so the validator (Component 8) checks the same rules the writer produced.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..config.config import DatasetConfig

__all__ = [
    "GENERATOR_VERSION",
    "CATALOG_VERSION",
    "DEMAND_VERSION",
    "INVENTORY_VERSION",
    "ORDERS_VERSION",
    "SUPPLIER_BEHAVIOUR_VERSION",
    "SCENARIOS_VERSION",
    "VALIDATOR_VERSION",
    "add_manifest_field",
    "extend_manifest",
    "format_value",
    "format_cents",
    "render_csv",
    "write_csv",
    "dataset_version",
    "build_manifest",
    "write_manifest",
    "file_entry",
    "to_utc",
]

#: Version of the generator that produced a dataset (`DT-025`, `DT-033`).
#:
#: Semantic versioning over the *observable output*: the minor number rises when the
#: generator produces different data for the same configuration and seed - a new
#: component, a changed policy, a changed draw order. It is written into
#: ``manifest.json`` and is part of the reproducibility invariant of section 44 of the
#: specification: same configuration + same seed + **same generator version** -> byte
#: identical data files.
#:
#: ``0.3.0`` (2026-09-29): the batch C6 + C4 + C5 enters the published artefact through
#: W1 (`DT-036` section 8, `DT-040`), in a single increment. With the same number the new
#: artefact would share ``dataset_version`` with the C2 + C3 one it replaces (`DT-033`).
#:
#: ``0.4.0`` (2026-09-29): C7 and C8 enter the published artefact through W1 in a single
#: increment (decision C7/C8-11, `DT-042` section 9). The manifest gains
#: ``scenario_assignment``, ``quality_report`` and two components; the twelve CSV files
#: are byte for byte those of 0.3.0 for the same configuration.
GENERATOR_VERSION = "0.4.0"

#: Version of Component 2 itself, recorded in ``manifest.json`` under
#: ``components[].version``. `DT-028` section 8 uses that field to trace which synthetic
#: policies produced a dataset, which is a question about *this component*, not about the
#: generator as a whole. Keeping them separate is what stops them from being conflated
#: now that there is more than one component.
CATALOG_VERSION = "0.1.0"

#: Version of Component 3 (Demand Generator), recorded the same way. Independent of
#: ``CATALOG_VERSION``: a change to the demand policies of `DT-035` moves this number and
#: not the catalogue's, which is precisely what `DT-028` section 8 wants the field for.
DEMAND_VERSION = "0.1.0"

#: Version of Component 4 (Inventory Simulator), recorded under ``components[].version``
#: when the component extends the manifest (`DT-038` section 15). Its own number, for the
#: same reason as the two above.
INVENTORY_VERSION = "0.1.0"

#: Version of Component 5 (Purchase Order Generator), recorded under
#: ``components[].version`` when the component extends the manifest (`DT-039` section 9).
#: Its own number, for the same reason as the three above.
ORDERS_VERSION = "0.1.0"

#: Version of Component 6 (Supplier Behaviour Generator), recorded under
#: ``components[].version`` when the component extends the manifest (`DT-037` section 1).
#: The component writes no data file; this entry is its only trace in the manifest.
SUPPLIER_BEHAVIOUR_VERSION = "0.1.0"

#: Version of Component 7 (Scenario Assignment), recorded under ``components[].version``
#: when the component extends the manifest (`DT-041` section 2). The component writes no
#: data file; it adds its entry and the ``scenario_assignment`` field.
SCENARIOS_VERSION = "0.1.0"

#: Version of Component 8 (Dataset Validator + quality report), recorded under
#: ``components[].version`` when the component extends the manifest (`DT-042` section 2).
#: The component writes no data file; it adds its entry and the ``quality_report`` field.
VALIDATOR_VERSION = "0.1.0"

#: RFC 4180 says a field must be quoted when it contains the delimiter, a quote or a
#: line break. `DT-024` asks for minimal quoting, which is exactly that set.
_MUST_QUOTE = (",", '"', "\n", "\r")


def format_value(value: Any) -> str:
    """Render one value as the CSV contract of `DT-024` requires.

    ======================  ==================================================
    ``None``                empty field - never ``NULL``, ``None`` or ``NaN``
    ``bool``                ``true`` / ``false``, lowercase
    ``int``                 plain digits, no thousands separator, no ``+``
    ``datetime.date``       ``YYYY-MM-DD``
    ``datetime.datetime``   ``YYYY-MM-DDTHH:MM:SSZ``, converted to UTC
    ``str``                 as is
    ======================  ==================================================

    ``bool`` is checked before ``int`` on purpose: in Python ``True`` *is* an ``int``,
    and the obvious ordering would silently write ``1`` where the contract says ``true``.

    Monetary values do not appear here as floats. `docs/04` section 7 forbids floating
    point for money, so the generator carries amounts in integer cents and formats them
    with :func:`format_cents`; letting a float through this function would reintroduce
    the problem the model rules out.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, _dt.datetime):
        return to_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise TypeError(
        f"{type(value).__name__} has no CSV representation in the DT-024 contract: "
        f"{value!r}"
    )


def to_utc(moment: _dt.datetime) -> _dt.datetime:
    """Convert an aware timestamp to UTC, refusing a naive one.

    `DT-024` and `DT-025` both say **UTC** and the trailing ``Z`` asserts it. Stamping
    that ``Z`` on whatever the caller passed would turn a local time into a false
    instant, which is worse than no timestamp at all: it looks authoritative. A naive
    datetime carries no offset to convert, so it is refused rather than guessed.
    """
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError(
            "a timestamp must carry a timezone so it can be converted to UTC; "
            f"got the naive value {moment!r}"
        )
    return moment.astimezone(_dt.timezone.utc)


def format_cents(cents: int) -> str:
    """Render an amount held in integer cents with exactly two decimals (`DT-024`)."""
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise TypeError(f"an amount must be an integer number of cents, got {cents!r}")
    sign = "-" if cents < 0 else ""
    units, remainder = divmod(abs(cents), 100)
    return f"{sign}{units}.{remainder:02d}"


def _escape(field: str) -> str:
    if any(ch in field for ch in _MUST_QUOTE):
        return '"' + field.replace('"', '""') + '"'
    return field


def render_csv(header: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    """Render a whole CSV file as text, following `DT-024`.

    Written by hand rather than with :mod:`csv` for one reason: ``csv.writer`` emits
    ``\\r\\n`` by default and its quoting policy is configured rather than stated. The
    contract asks for LF endings and minimal RFC 4180 quoting on every platform, and
    twelve lines that say so are easier to check against the ADR than a set of dialect
    flags.
    """
    lines = [",".join(_escape(name) for name in header)]
    for row in rows:
        if len(row) != len(header):
            raise ValueError(
                f"row has {len(row)} fields but the header declares {len(header)}: {row!r}"
            )
        lines.append(",".join(_escape(format_value(value)) for value in row))
    return "\n".join(lines) + "\n"


def write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    """Write a CSV file and return its text.

    UTF-8 without BOM, LF line endings - ``newline=""`` keeps Python from translating
    the LF to CRLF on Windows, which would break the byte-identity invariant of
    section 44 across platforms.
    """
    text = render_csv(header, rows)
    path.write_text(text, encoding="utf-8", newline="")
    return text


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dataset_version(config: DatasetConfig, generator_version: str) -> str:
    """Identifier of the dataset a configuration and generator version produce (`DT-033`).

    Derived, not assigned: ``ds-`` followed by the first 12 hex characters of
    ``sha256(canonical_config_json + "|" + generator_version)``.

    Two properties motivate this over a hand-maintained counter. It is **reproducible** -
    regenerating the same dataset yields the same identifier, so the field can be
    compared - and it **changes exactly when the data changes**, because its two inputs
    are precisely the two terms of the reproducibility invariant. A manual version number
    has neither property: nothing forces anyone to bump it.

    It deliberately does **not** include ``generated_at``: the identifier names the
    dataset, not the run.
    """
    canonical = json.dumps(config.to_dict(), sort_keys=True, separators=(",", ":"))
    digest = _sha256(f"{canonical}|{generator_version}")
    return f"ds-{digest[:12]}"


def build_manifest(
    *,
    config: DatasetConfig,
    generated_at: _dt.datetime,
    components: Sequence[dict[str, Any]],
    files: Sequence[dict[str, Any]],
    generator_version: str = GENERATOR_VERSION,
) -> dict[str, Any]:
    """Assemble the manifest described by `DT-025`.

    The nine mandatory fields are all present. ``scenario_assignment`` and
    ``quality_report`` are **absent**, which `DT-025` states explicitly: they are
    contributed by Components 7 and 8, and a Component 2 manifest that lacks them is not
    an invalid manifest.
    """
    return {
        "dataset_version": dataset_version(config, generator_version),
        "generator_version": generator_version,
        "seed": config.seed,
        "generated_at": to_utc(generated_at).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "time_range": config.period.to_dict(),
        "data_origin": "SYNTHETIC",
        "config": config.to_dict(),
        "components": [dict(entry) for entry in components],
        "files": [dict(entry) for entry in files],
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> str:
    """Write ``manifest.json``: UTF-8, two-space indent, LF, trailing newline."""
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="")
    return text


def file_entry(name: str, entity: str, rows: int, text: str) -> dict[str, Any]:
    """One record of the manifest's ``files`` list (`DT-025`).

    The digest is taken over the file's exact bytes, which is what makes it possible to
    detect a directory holding files from two different runs.
    """
    return {"name": name, "entity": entity, "rows": rows, "sha256": _sha256(text)}


def extend_manifest(
    manifest: dict[str, Any],
    *,
    component: dict[str, Any],
    files: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Add one component and its files to an existing manifest (`DT-025`).

    Returns a new dictionary; the argument is not mutated.

    This is what lets a run stay a single manifest describing a single execution, as
    `DT-025` rule 1 requires, while each component still writes only its own files. Both
    lists are re-sorted - ``files`` by name, ``components`` by name - so the manifest does
    not depend on the order in which the components happened to run, which is exactly the
    independence `DT-030` set out to obtain.

    ``dataset_version`` is not recomputed: `DT-033` derives it from the configuration and
    the generator version, neither of which a component contributes to.
    """
    if any(entry["name"] == component["name"] for entry in manifest["components"]):
        raise ValueError(
            f"component {component['name']!r} is already in the manifest; "
            "a run writes each component once"
        )
    known = {entry["name"] for entry in manifest["files"]}
    clashes = sorted(entry["name"] for entry in files if entry["name"] in known)
    if clashes:
        raise ValueError(f"these files are already in the manifest: {clashes}")

    extended = dict(manifest)
    extended["components"] = sorted(
        [dict(entry) for entry in manifest["components"]] + [dict(component)],
        key=lambda entry: entry["name"],
    )
    extended["files"] = sorted(
        [dict(entry) for entry in manifest["files"]] + [dict(entry) for entry in files],
        key=lambda entry: entry["name"],
    )
    return extended


def add_manifest_field(
    manifest: dict[str, Any], key: str, value: Any
) -> dict[str, Any]:
    """Add one field contributed by a later component, such as ``scenario_assignment``.

    `DT-025` declares ``scenario_assignment`` and ``quality_report`` as fields that
    Components 7 and 8 contribute. A field is written once: if the key is already
    present - either one of the nine mandatory fields or a field a component already
    added - this raises instead of overwriting it silently (`DT-041` section 11).

    Returns a new dictionary with the field appended; the argument is not mutated.
    """
    if key in manifest:
        raise ValueError(
            f"manifest already has a {key!r} field; it is never overwritten"
        )
    extended = dict(manifest)
    extended[key] = value
    return extended
