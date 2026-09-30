"""Component 3 - Demand Generator: the latent demand history.

Phase 1 - Data.

    products.csv + locations.csv -> build_demand() -> Demand -> generate() -> demand.csv

**What "latent" means, and why it is the whole point of this component.**

``demand.csv`` holds the quantity that *would have been demanded* had stock never run
out. It is not what was sold. During a stockout the two diverge, and the dataset has to
keep both if the difference is ever to be measured:

    latent demand (C3, demand.csv) = 100
    stock available (C4)           =  70
    satisfied demand (C4, consumption.csv) = 70, is_stockout_affected = true

`docs/04` section 3.8 states the problem this separation solves: what a consumption
record holds is "**satisfied** demand", so "during a stockout the real demand was higher
than the one recorded", and a model trained on it "learns that demand fell" precisely
where the product was most critical. Keeping the latent series is what makes that bias
measurable rather than merely acknowledged. See `DT-034`.

**C3 does not write ``consumption.csv``, and does not know what stock is.** It has no
inventory, no stockouts, no ``is_stockout_affected`` column, no orders and no receipts.
Turning latent demand into satisfied demand is Component 4's responsibility and its
alone - if both components generated stockouts, neither would own the truth.

Contracts implemented here:

* `DT-034` - ``Demand`` as a persistent entity, and the column contract of ``demand.csv``.
* `DT-035` - the synthetic demand generation policies (in :mod:`.policies`).
* `DT-024` - the CSV format conventions, unchanged.
* `DT-025` - the component's entry in ``manifest.json``.
* `DT-026` - ``data_origin = SYNTHETIC`` on every row.
* `DT-027` - a product's series lives inside ``[valid_from, valid_to]``.
* `DT-030` / `DT-032` - determinism, under the canonical identifier ``demand``.

**Every generated quantity is synthetic.** The levels, trends, amplitudes and event
frequencies come from `DT-035` and describe nothing about any real organisation.
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

from ..config.config import DatasetConfig
from . import policies as pol
from .rng import COMPONENT_DEMAND, DeterministicRandom, sub_seed
from .writer import (
    DEMAND_VERSION,
    extend_manifest,
    file_entry,
    write_csv,
    write_manifest,
)

__all__ = [
    "Demand",
    "DemandProfile",
    "build_demand",
    "generate",
    "DEMAND_COLUMNS",
    "DEMAND_FILE",
    "MANIFEST_FILE",
]

#: `DT-034`: the file this component writes. Plural and ``snake_case`` like every other
#: entity file of `DT-024`.
DEMAND_FILE = "demand.csv"

MANIFEST_FILE = "manifest.json"

#: Files this component reads. C3 consumes C2 through its **published output**, not
#: through an in-memory object: the dependency in the architecture is
#: ``C2 -> products.csv/locations.csv -> C3``, and reading the files is what makes that
#: dependency real instead of a convention two functions happen to share.
PRODUCTS_FILE = "products.csv"
LOCATIONS_FILE = "locations.csv"

#: `DT-034`: the column contract. Six columns, no more.
#:
#: Deliberately absent, each for its own reason:
#: ``is_stockout_affected`` belongs to ``consumption.csv`` and to Component 4 - putting
#: it here would be C3 claiming knowledge of stock it does not have; ``scenario`` is
#: forbidden on every entity by `DT-025`; ``channel`` exists on ``Consumption`` and is
#: optional there, and latent demand has no channel to speak of.
DEMAND_COLUMNS = (
    "id",
    "product_id",
    "location_id",
    "occurred_on",
    "quantity",
    "data_origin",
)


@dataclass(frozen=True)
class DemandProfile:
    """How one product behaves, decided once and applied to every one of its days.

    The profile is **not written to the dataset**. `DT-025` forbids a ``scenario``
    column on any entity, and Component 7 is the one that records which product received
    which axis. C3 needs the profile to generate; it does not need to publish it.
    """

    product_id: int
    shape: str
    rotation: str
    base_level: int
    season_phase: int


@dataclass(frozen=True)
class Demand:
    """The latent demand series, one row per product, location and day."""

    rows: list[dict[str, Any]] = field(default_factory=list)
    profiles: list[DemandProfile] = field(default_factory=list)


# ---------------------------------------------------------------------------------------
# Reading Component 2's output
# ---------------------------------------------------------------------------------------


def _parse_bool(value: str, column: str) -> bool:
    """Read a boolean as `DT-024` writes it: lowercase ``true`` / ``false``."""
    if value == "true":
        return True
    if value == "false":
        return False
    raise pol.GeneratorError(
        [f"{column} must be 'true' or 'false' as DT-024 requires, got {value!r}"]
    )


def _parse_date(value: str, column: str) -> _dt.date:
    try:
        return _dt.date.fromisoformat(value)
    except ValueError as exc:
        raise pol.GeneratorError(
            [f"{column} is not an ISO date (YYYY-MM-DD) as DT-024 requires: {value!r}"]
        ) from exc


def _read_rows(path: Path, expected: Sequence[str]) -> list[dict[str, str]]:
    """Read one of Component 2's CSV files, checking its header against the contract."""
    if not path.is_file():
        raise pol.GeneratorError(
            [
                f"{path.name} not found in {path.parent}; Component 3 consumes the "
                "output of Component 2, so the catalogue must be generated first"
            ]
        )
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        missing = [name for name in expected if name not in header]
        if missing:
            raise pol.GeneratorError(
                [
                    f"{path.name} is missing the column(s) {missing}; expected {list(expected)}"
                ]
            )
        return list(reader)


def read_catalog_inputs(
    output_dir: Path,
) -> tuple[list[dict[str, Any]], list[int]]:
    """Load the two things C3 needs from Component 2, and nothing else.

    From ``products.csv``: the identity and the validity window, because a product's
    series must live inside ``[valid_from, valid_to]`` (`DT-027`, specification section
    34). From ``locations.csv``: the identifiers.

    ``categories.csv``, ``suppliers.csv`` and ``product_suppliers.csv`` are **not read**.
    No document makes demand depend on a category or on who supplies the product, and
    reading a file the component does not need would invent a dependency.

    Products are returned in ascending ``id`` order regardless of how the file was
    ordered, so nothing downstream depends on file order.
    """
    products = []
    for raw in _read_rows(
        output_dir / PRODUCTS_FILE, ("id", "is_active", "valid_from", "valid_to")
    ):
        valid_to = raw["valid_to"].strip()
        products.append(
            {
                "id": int(raw["id"]),
                "is_active": _parse_bool(raw["is_active"], "products.is_active"),
                "valid_from": _parse_date(raw["valid_from"], "products.valid_from"),
                # Empty means "in force with no end date" (`DT-027`).
                "valid_to": (
                    _parse_date(valid_to, "products.valid_to") if valid_to else None
                ),
            }
        )
    products.sort(key=lambda row: row["id"])

    locations = sorted(
        int(raw["id"]) for raw in _read_rows(output_dir / LOCATIONS_FILE, ("id",))
    )

    problems = []
    if not products:
        problems.append(f"{PRODUCTS_FILE} has no rows")
    if not locations:
        problems.append(f"{LOCATIONS_FILE} has no rows")
    if problems:
        raise pol.GeneratorError(problems)
    return products, locations


# ---------------------------------------------------------------------------------------
# The calendar
# ---------------------------------------------------------------------------------------


def period_days(config: DatasetConfig) -> Iterator[_dt.date]:
    """Every day of the configured window, as a **half-open** interval.

    ``[start_date, end_date)``: the start is included, the end is not. With
    2023-01-01 -> 2026-01-01 the last day generated is 2025-12-31, and 2026-01-01 never
    appears. This is the reading ``Period.days`` already implied - it returns
    ``(end - start).days``, which is the cardinality of the half-open interval - and it
    is now fixed explicitly (`DT-034`) rather than left to each component to guess.
    """
    current = config.period.start_date
    end = config.period.end_date
    while current < end:
        yield current
        current += _dt.timedelta(days=1)


def _product_days(
    product: dict[str, Any], calendar: Sequence[_dt.date]
) -> list[_dt.date]:
    """The days of the calendar a product is in force for.

    ``[valid_from, valid_to]`` with **both ends included** (`DT-027` as corrected), and
    open on the right when ``valid_to`` is empty. Specification section 34 requires every
    event of a product to fall inside that interval, and section 18 requires an inactive
    product to keep the history it had - which is why an inactive product gets a series
    that stops at ``valid_to`` rather than no series at all.
    """
    valid_from = product["valid_from"]
    valid_to = product["valid_to"]
    return [
        day
        for day in calendar
        if day >= valid_from and (valid_to is None or day <= valid_to)
    ]


# ---------------------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------------------


def _assign_profiles(
    products: Sequence[dict[str, Any]], base: int
) -> list[DemandProfile]:
    """Give every product a shape, a rotation class, a base level and a seasonal phase.

    **Two orthogonal axes, not one list of eight.** A product gets one of the six shapes
    of specification section 8 *and* one of the two rotation classes. Collapsing them
    into a single eight-way choice would make "high rotation" mutually exclusive with
    "seasonal", which is nonsense: rotation is how much a product moves, shape is how
    that movement is distributed over time. `DT-023` section 7.2 already treats rotation
    as a separate axis backed by its own sections, not as a seventh demand pattern.

    Each axis has its own mix summing to 100 % and its own floor of one product, so both
    axes are present by construction at any admissible scale (`DT-035`).

    Three independent streams, so that changing the number of draws in one does not
    shift the others - the property `DT-032` labels exist for.
    """
    count = len(products)
    shape_counts = pol.demand_mix_counts(pol.DEMAND_SHAPE_MIX, pol.DEMAND_SHAPES, count)
    rotation_counts = pol.demand_mix_counts(
        pol.DEMAND_ROTATION_MIX, pol.DEMAND_ROTATIONS, count
    )

    shape_slots: list[str] = []
    for name in pol.DEMAND_SHAPES:
        shape_slots.extend([name] * shape_counts[name])
    rotation_slots: list[str] = []
    for name in pol.DEMAND_ROTATIONS:
        rotation_slots.extend([name] * rotation_counts[name])

    shape_order = DeterministicRandom(base, "shape-assignment").permutation(count)
    rotation_order = DeterministicRandom(base, "rotation-assignment").permutation(count)
    level_rng = DeterministicRandom(base, "base-level")
    phase_rng = DeterministicRandom(base, "season-phase")

    profiles = []
    for position, product in enumerate(products):
        shape = shape_slots[shape_order[position]]
        rotation = rotation_slots[rotation_order[position]]
        low, high = pol.DEMAND_BASE_LEVEL[rotation]
        profiles.append(
            DemandProfile(
                product_id=product["id"],
                shape=shape,
                rotation=rotation,
                base_level=level_rng.between(low, high),
                # Drawn for every product, not only the seasonal ones: keeping the draw
                # count independent of the shape assignment means a later change to the
                # shape mix cannot shift anybody's level.
                season_phase=phase_rng.below(pol.DEMAND_SEASON_PERIOD_DAYS),
            )
        )
    return profiles


# ---------------------------------------------------------------------------------------
# The series
# ---------------------------------------------------------------------------------------

#: Everything below is integer arithmetic in per mille. Not a style preference: a single
#: float would put the byte-identity of `DT-032` at the mercy of the platform's libm.
_MILLE = 1000


def _round_div(numerator: int, denominator: int) -> int:
    """Integer division rounding half away from zero. Exact and platform-independent."""
    if numerator >= 0:
        return (numerator + denominator // 2) // denominator
    return -((-numerator + denominator // 2) // denominator)


def _quantity(
    profile: DemandProfile,
    day_index: int,
    total_days: int,
    noise_rng: DeterministicRandom,
    event_rng: DeterministicRandom,
) -> int:
    """Latent demand of one product on one day, as a non-negative integer.

    Intermittent demand takes a different route on purpose. Its zeros are not a small
    level rounding down - they are days with no demand event at all - and its positive
    days are lumps, not the ordinary level. Section 8.5 asks for "numerous zero periods
    and separated consumption events"; a series that merely rounded to zero would be a
    low-volume stable series wearing an intermittent label, and the two would be
    indistinguishable by inspection, which is the one thing section 8.5 wants to avoid.
    """
    if profile.shape == "INTERMITTENT_DEMAND":
        if event_rng.below(_MILLE) >= pol.DEMAND_INTERMITTENT_EVENT_PERMILLE:
            return 0
        low, high = pol.DEMAND_INTERMITTENT_EVENT_MULTIPLIER
        return profile.base_level * event_rng.between(low, high)

    trend = pol.trend_factor_permille(profile.shape, day_index, total_days)
    season = (
        pol.seasonal_factor_permille(day_index, profile.season_phase)
        if profile.shape == "SEASONAL_DEMAND"
        else _MILLE
    )
    spread = pol.DEMAND_NOISE_PERMILLE[profile.shape]
    noise = _MILLE + noise_rng.between(-spread, spread)

    scaled = profile.base_level * trend * season * noise
    return max(0, _round_div(scaled, _MILLE**3))


def build_demand(config: DatasetConfig, output_dir: Path | str) -> Demand:
    """Build the latent demand series from Component 2's published catalogue.

    Dense by construction: every product in force on a day has a row for that day, with
    ``quantity = 0`` when there was no demand. Section 8.5 requires that "a large number
    of zeros is not automatically interpreted as absence of product" - and if the zero
    days were simply omitted, absence and zero would be the same thing on disk and that
    requirement would be unverifiable.

    Rows come out in the order `DT-024` requires, ascending by the business key
    ``(product_id, location_id, occurred_on)``, and ``id`` follows that order.

    Raises:
        GeneratorError: if Component 2's output is missing or malformed, or if the scale
            cannot give every demand shape at least one product.
    """
    target = Path(output_dir)
    products, locations = read_catalog_inputs(target)

    if len(products) < pol.DEMAND_MIN_PRODUCTS:
        raise pol.GeneratorError(
            [
                f"P-6: at least {pol.DEMAND_MIN_PRODUCTS} products are needed, one per "
                f"demand shape (DT-035); products.csv has {len(products)}"
            ]
        )

    calendar = list(period_days(config))
    if not calendar:
        raise pol.GeneratorError(
            [
                "the configured period contains no day; [start_date, end_date) is "
                f"empty for {config.period.to_dict()}"
            ]
        )

    base = sub_seed(config.seed, COMPONENT_DEMAND)
    profiles = _assign_profiles(products, base)
    by_product = {profile.product_id: profile for profile in profiles}

    # One pair of streams per product and location, labelled by their ids. The series of
    # product 7 is then the same whatever else the generator does: adding a product to
    # the catalogue, or a location, cannot shift the demand of the ones already there.
    rows: list[dict[str, Any]] = []
    total_days = len(calendar)
    first_day = calendar[0]
    for product in products:
        profile = by_product[product["id"]]
        days = _product_days(product, calendar)
        for location_id in locations:
            noise_rng = DeterministicRandom(
                base, f"noise:{product['id']}:{location_id}"
            )
            event_rng = DeterministicRandom(
                base, f"event:{product['id']}:{location_id}"
            )
            for day in days:
                rows.append(
                    {
                        "id": 0,  # assigned below, in business-key order
                        "product_id": product["id"],
                        "location_id": location_id,
                        "occurred_on": day,
                        # The day index is measured from the start of the period, not
                        # from the product's own first day: a trend or a season must be
                        # anchored to the calendar, or two products with different
                        # validity windows would peak on different dates.
                        "quantity": _quantity(
                            profile,
                            (day - first_day).days,
                            total_days,
                            noise_rng,
                            event_rng,
                        ),
                        "data_origin": pol.DATA_ORIGIN,
                    }
                )

    rows.sort(
        key=lambda row: (row["product_id"], row["location_id"], row["occurred_on"])
    )
    for index, row in enumerate(rows, start=1):
        row["id"] = index

    _check_demand(rows, profiles, products, locations, config)
    return Demand(rows=rows, profiles=profiles)


def _check_demand(
    rows: Sequence[dict[str, Any]],
    profiles: Sequence[DemandProfile],
    products: Sequence[dict[str, Any]],
    locations: Sequence[int],
    config: DatasetConfig,
) -> None:
    """Verify what the policies promise, before a single byte is written.

    The same posture as Component 2's coverage check: restate the guarantees rather than
    trust the construction, so that a future change to the draw order fails here, loudly,
    instead of shipping a dataset that quietly misses a required behaviour.
    """
    problems: list[str] = []

    shapes_present = {profile.shape for profile in profiles}
    missing_shapes = sorted(set(pol.DEMAND_SHAPES) - shapes_present)
    if missing_shapes:
        problems.append(
            f"these demand shapes got no product: {missing_shapes} "
            "(specification section 8, DT-035)"
        )
    rotations_present = {profile.rotation for profile in profiles}
    missing_rotations = sorted(set(pol.DEMAND_ROTATIONS) - rotations_present)
    if missing_rotations:
        problems.append(
            f"these rotation classes got no product: {missing_rotations} (DT-023 section 7.2)"
        )

    if any(row["quantity"] < 0 for row in rows):
        problems.append(
            "a latent demand quantity is negative (specification section 34)"
        )
    if any(not isinstance(row["quantity"], int) for row in rows):
        problems.append("a latent demand quantity is not an integer (DT-035)")

    keys = {(row["product_id"], row["location_id"], row["occurred_on"]) for row in rows}
    if len(keys) != len(rows):
        problems.append(
            f"the business key is not unique: {len(rows)} rows, {len(keys)} distinct keys"
        )

    start, end = config.period.start_date, config.period.end_date
    outside = [row for row in rows if not (start <= row["occurred_on"] < end)]
    if outside:
        problems.append(
            f"{len(outside)} rows fall outside the half-open period [{start}, {end})"
        )

    validity = {product["id"]: product for product in products}
    breaches = [
        row
        for row in rows
        if row["occurred_on"] < validity[row["product_id"]]["valid_from"]
        or (
            validity[row["product_id"]]["valid_to"] is not None
            and row["occurred_on"] > validity[row["product_id"]]["valid_to"]
        )
    ]
    if breaches:
        problems.append(
            f"{len(breaches)} rows fall outside their product's validity window "
            "(DT-027, specification section 34)"
        )

    calendar = list(period_days(config))
    expected = sum(
        len(_product_days(product, calendar)) * len(locations) for product in products
    )
    if len(rows) != expected:
        problems.append(
            f"the series is not dense: {len(rows)} rows, expected {expected} "
            "(one per product, location and day in force)"
        )

    if problems:
        raise pol.GeneratorError(problems)


# ---------------------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------------------


def generate(
    config: DatasetConfig,
    output_dir: Path | str,
    *,
    generated_at: _dt.datetime | None = None,
) -> dict[str, Any]:
    """Build the latent demand series and write ``demand.csv`` into ``output_dir``.

    The manifest of the run is extended in place: this component's entry is added to
    ``components`` and ``demand.csv`` to ``files``, so one directory keeps one manifest
    describing one execution (`DT-025` rule 1).

    Args:
        config: a validated :class:`DatasetConfig`.
        output_dir: the directory Component 2 already wrote its catalogue into.
        generated_at: unused for the data and accepted only so a caller can keep the
            manifest's timestamp fixed. **No generated value depends on it** - that is
            the invariant of specification section 44.

    Returns:
        The extended manifest, already written to disk.

    Raises:
        GeneratorError: if the catalogue is missing, or a precondition or guarantee
            fails. Nothing is written in that case.
    """
    target = Path(output_dir)
    demand = build_demand(config, target)

    manifest_path = target / MANIFEST_FILE
    if not manifest_path.is_file():
        raise pol.GeneratorError(
            [
                f"{MANIFEST_FILE} not found in {target}; Component 2 writes it and "
                "Component 3 extends it"
            ]
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    text = write_csv(
        target / DEMAND_FILE,
        DEMAND_COLUMNS,
        [[row[name] for name in DEMAND_COLUMNS] for row in demand.rows],
    )

    manifest = extend_manifest(
        manifest,
        component={
            "name": COMPONENT_DEMAND,
            "version": DEMAND_VERSION,
            "sub_seed": sub_seed(config.seed, COMPONENT_DEMAND),
        },
        files=[file_entry(DEMAND_FILE, "Demand", len(demand.rows), text)],
    )
    write_manifest(manifest_path, manifest)
    return manifest
