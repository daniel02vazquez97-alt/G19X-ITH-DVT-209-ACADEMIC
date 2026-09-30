"""Component 2 - Catalog Generator: the five master entities of the synthetic dataset.

Phase 1 - Data.

    DatasetConfig -> build_catalog() -> Catalog -> generate() -> 5 CSV + manifest.json

What this component produces, and nothing else: ``Category``, ``Product``, ``Supplier``,
``ProductSupplier`` and ``Location``. No demand, no inventory, no purchase orders, no
scenario assignment, no validation. Those are Components 3 to 8.

Contracts implemented here:

* `DT-024` - one CSV per entity, column contract, rows ordered by business key.
* `DT-025` - ``manifest.json`` beside them.
* `DT-026` - ``data_origin = SYNTHETIC`` on every row.
* `DT-027` - ``valid_from`` / ``valid_to`` on ``Product``.
* `DT-028` - the synthetic generation policies.
* `DT-029` - the fields this component deliberately leaves empty.
* `DT-030` / `DT-032` - determinism.

**Every generated value is synthetic.** The commercial-looking columns - ``moq``,
``order_multiple``, ``unit_cost``, ``agreed_lead_time_days`` - come from the parameters
of `DT-028`, which exist to build technical test scenarios. They are not policies,
prices or agreements of any organisation.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from ..config.config import DatasetConfig
from . import policies as pol
from .rng import COMPONENT_CATALOG, DeterministicRandom, sub_seed
from .writer import (
    CATALOG_VERSION,
    GENERATOR_VERSION,
    build_manifest,
    file_entry,
    format_cents,
    write_csv,
    write_manifest,
)

__all__ = [
    "Catalog",
    "build_catalog",
    "generate",
    "DEFAULT_OUTPUT_DIR",
    "CATEGORY_COLUMNS",
    "PRODUCT_COLUMNS",
    "SUPPLIER_COLUMNS",
    "PRODUCT_SUPPLIER_COLUMNS",
    "LOCATION_COLUMNS",
]

#: `DT-024`: default output directory. Not versioned - `CLAUDE.md` section 13.7 keeps
#: datasets out of the repository.
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"

# Column contracts of `DT-024`. Order is fixed and is part of the contract.
CATEGORY_COLUMNS = ("id", "code", "name", "parent_id", "is_active", "data_origin")
PRODUCT_COLUMNS = (
    "id",
    "sku",
    "name",
    "description",
    "category_id",
    "unit_of_measure",
    "is_active",
    "abc_class",
    "rotation_class",
    "shelf_life_days",
    "valid_from",
    "valid_to",
    "created_at",
    "updated_at",
    "data_origin",
)
SUPPLIER_COLUMNS = (
    "id",
    "code",
    "name",
    "contact_info",
    "is_active",
    "currency",
    "created_at",
    "updated_at",
    "data_origin",
)
PRODUCT_SUPPLIER_COLUMNS = (
    "id",
    "product_id",
    "supplier_id",
    "agreed_lead_time_days",
    "moq",
    "order_multiple",
    "unit_cost",
    "is_preferred",
    "is_active",
    "data_origin",
)
LOCATION_COLUMNS = ("id", "code", "name", "type", "is_active", "data_origin")

#: How many ProductSupplier rows each class gets (`DT-028` section 2.2).
_SUPPLIERS_PER_CLASS = {"A": 1, "B": 2, "C": 3, "D": 1}


def _code(kind: str, number: int, width: int) -> str:
    """Zero-padded business key, e.g. ``SKU-00007`` (`DT-028` section 4).

    The width comes from :func:`policies.code_width`, which widens beyond the tabulated
    value when the scale needs it. Padding must be uniform across one dataset, or the
    row order of `DT-024` stops agreeing with the numeric order of the key.
    """
    prefix = pol.CODE_PATTERNS[kind][0]
    return f"{prefix}-{number:0{width}d}"


@dataclass(frozen=True)
class Catalog:
    """The five master entities, as rows keyed by column name.

    Rows are already in the order `DT-024` requires - ascending by business key - and
    their ``id`` is assigned following that same order.
    """

    categories: list[dict[str, Any]] = field(default_factory=list)
    products: list[dict[str, Any]] = field(default_factory=list)
    suppliers: list[dict[str, Any]] = field(default_factory=list)
    product_suppliers: list[dict[str, Any]] = field(default_factory=list)
    locations: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------------------


def build_catalog(config: DatasetConfig) -> Catalog:
    """Build the five master entities from a validated configuration.

    Pure in the sense that matters: the same configuration always yields the same
    catalogue. Nothing is read from the clock, the environment or the filesystem.

    Raises:
        GeneratorError: if a precondition of `DT-028` section 8 or `DT-029` fails, or if
            a coverage guarantee could not be met. The generator never emits a dataset
            that quietly misses a scenario the specification requires.
    """
    pol.check_preconditions(config)

    scale = config.scale
    base = sub_seed(config.seed, COMPONENT_CATALOG)

    categories = _build_categories(scale.category_count)
    suppliers = _build_suppliers(scale.supplier_count)
    locations = _build_locations(scale.location_count)
    products, product_classes = _build_products(config, base)
    relations = _build_product_suppliers(
        base=base,
        products=products,
        product_classes=product_classes,
        supplier_count=scale.supplier_count,
    )

    _check_coverage(
        categories=categories,
        products=products,
        suppliers=suppliers,
        locations=locations,
        relations=relations,
        supplier_count=scale.supplier_count,
    )

    return Catalog(
        categories=categories,
        products=products,
        suppliers=suppliers,
        product_suppliers=relations,
        locations=locations,
    )


def _build_categories(count: int) -> list[dict[str, Any]]:
    """Categories: flat hierarchy, all active (`DT-028` sections 4 and 7)."""
    width = pol.code_width("category", count)
    return [
        {
            "id": i,
            "code": _code("category", i, width),
            "name": f"Category {_code('category', i, width)}",
            # `ASSUMPTION-009`: one level only, so no category has a parent.
            "parent_id": None,
            "is_active": True,
            "data_origin": pol.DATA_ORIGIN,
        }
        for i in range(1, count + 1)
    ]


def _build_suppliers(count: int) -> list[dict[str, Any]]:
    """Suppliers: all active (`DT-028` section 7).

    The "no active supplier" case is materialised on the *relation*, not on the
    supplier: deactivating a whole supplier would affect all of its products at once and
    make the dataset less controllable (`DT-028` section 2.5).

    ``contact_info`` and ``currency`` stay empty by `DT-029` - the first because
    `CLAUDE.md` section 9.7 forbids supplier data in development, the second because
    multi-currency is an open question in `docs/04` section 8.5.
    """
    width = pol.code_width("supplier", count)
    return [
        {
            "id": i,
            "code": _code("supplier", i, width),
            "name": f"Supplier {_code('supplier', i, width)}",
            "contact_info": None,
            "is_active": True,
            "currency": None,
            "created_at": None,
            "updated_at": None,
            "data_origin": pol.DATA_ORIGIN,
        }
        for i in range(1, count + 1)
    ]


def _build_locations(count: int) -> list[dict[str, Any]]:
    """Locations: exactly one in this version (`DT-029`, checked as a precondition)."""
    location_type = pol.LOCATION_TYPE_VALUES[0]
    width = pol.code_width("location", count)
    return [
        {
            "id": i,
            "code": _code("location", i, width),
            "name": f"Location {_code('location', i, width)}",
            "type": location_type,
            "is_active": True,
            "data_origin": pol.DATA_ORIGIN,
        }
        for i in range(1, count + 1)
    ]


def _build_products(
    config: DatasetConfig, base: int
) -> tuple[list[dict[str, Any]], dict[int, str]]:
    """Products, plus the class (A-D) each one belongs to.

    Three independent decisions, each with its own stream so that changing one does not
    reshuffle the others:

    * which category a product belongs to - the *counts* come from the Zipf distribution
      of `DT-028` section 3 and are not random at all; only the assignment is;
    * which class (A-D) it belongs to, for supplier assignment;
    * whether it is active.

    Class D and the inactive products are kept **disjoint**: `DT-028` section 7.1 calls
    them independent sets chosen separately, because overlapping them would merge two
    distinct test cases - "product with no active supplier" and "inactive product that
    keeps its history" - into one product and leave each case untested on its own.
    """
    scale = config.scale
    count = scale.product_count
    split = pol.class_split(count)

    # -- category assignment ---------------------------------------------------------
    per_category = pol.category_distribution(scale.category_count, count)
    slots: list[int] = []
    for index, amount in enumerate(per_category, start=1):
        slots.extend([index] * amount)
    order = DeterministicRandom(base, "category-assignment").permutation(count)
    category_of = {position: slots[slot] for position, slot in enumerate(order)}

    # -- classes A-D -----------------------------------------------------------------
    role_order = DeterministicRandom(base, "product-class").permutation(count)
    classes: dict[int, str] = {}
    cursor = 0
    for label in ("D", "C", "B"):
        amount = getattr(split, f"class_{label.lower()}")
        for position in role_order[cursor : cursor + amount]:
            classes[position] = label
        cursor += amount
    for position in role_order[cursor:]:
        classes[position] = "A"

    # -- active / inactive ------------------------------------------------------------
    inactive_count = pol.inactive_product_count(count)
    eligible = [position for position in role_order if classes[position] != "D"]
    if inactive_count > len(eligible):
        raise pol.GeneratorError(
            [
                f"cannot pick {inactive_count} inactive products disjoint from the "
                f"{split.class_d} class-D products out of {count} (DT-028 section 7.1)"
            ]
        )
    shuffled = DeterministicRandom(base, "product-active").permutation(len(eligible))
    inactive = {eligible[i] for i in shuffled[:inactive_count]}

    # -- rows -------------------------------------------------------------------------
    unit_rng = DeterministicRandom(base, "unit-of-measure")
    valid_from = config.period.start_date
    valid_to_inactive = valid_from + _dt.timedelta(
        days=pol.inactive_valid_to_offset(config.period.days)
    )

    sku_width = pol.code_width("product", count)
    products: list[dict[str, Any]] = []
    for position in range(count):
        number = position + 1
        sku = _code("product", number, sku_width)
        is_active = position not in inactive
        products.append(
            {
                "id": number,
                "sku": sku,
                "name": f"Product {sku}",
                # `DT-029`: section 7.2 of the specification asks for "name **or**
                # description"; name is enough, so description stays empty.
                "description": None,
                "category_id": category_of[position],
                "unit_of_measure": unit_rng.choice(pol.UNIT_OF_MEASURE_VALUES),
                "is_active": is_active,
                # Derived from consumption, which does not exist yet (`DT-029`).
                "abc_class": None,
                "rotation_class": None,
                "shelf_life_days": None,
                "valid_from": valid_from,
                # `DT-027`: empty means "in force with no end date".
                "valid_to": None if is_active else valid_to_inactive,
                # Technical audit fields: set by ingestion, not by the generator.
                "created_at": None,
                "updated_at": None,
                "data_origin": pol.DATA_ORIGIN,
            }
        )

    # Products are created in ascending SKU order, which is the business key, so the list
    # already satisfies the row order of `DT-024`.
    return products, {position + 1: classes[position] for position in range(count)}


def _build_product_suppliers(
    *,
    base: int,
    products: Sequence[dict[str, Any]],
    product_classes: dict[int, str],
    supplier_count: int,
) -> list[dict[str, Any]]:
    """ProductSupplier rows: deterministic rotation plus synthetic commercial values.

    The rotation of `DT-028` section 2.3: start at an offset derived from the sub-seed,
    advance one position per relation, and skip to the next supplier if the pair already
    exists for this product. Three lines that make the pair unique without retries, give
    every supplier at least one relation (precondition P-4 guarantees there are more
    relations than suppliers) and keep the split independent of generation order.
    """
    offset = DeterministicRandom(base, "supplier-rotation").below(supplier_count)

    rows: list[dict[str, Any]] = []
    cursor = 0
    for product in products:
        product_id = product["id"]
        label = product_classes[product_id]
        needed = _SUPPLIERS_PER_CLASS[label]
        assigned: list[int] = []
        while len(assigned) < needed:
            supplier_id = (offset + cursor) % supplier_count + 1
            cursor += 1
            if supplier_id in assigned:
                continue  # skip to the next: the pair already exists
            assigned.append(supplier_id)
        for rank, supplier_id in enumerate(assigned):
            active = label != "D"
            rows.append(
                {
                    "id": 0,  # assigned below, once the rows are in business-key order
                    "product_id": product_id,
                    "supplier_id": supplier_id,
                    "agreed_lead_time_days": 0,  # drawn below
                    "moq": 0,
                    "order_multiple": 1,
                    "unit_cost": "",
                    # `DT-028` section 2.4: the first supplier the rotation assigns.
                    # No selection criterion and no scoring - `BR-X05` is pending.
                    # Class D has none: its only relation is inactive, and `docs/04`
                    # section 3.4 allows at most one preferred *active* supplier.
                    "is_preferred": active and rank == 0,
                    "is_active": active,
                    "data_origin": pol.DATA_ORIGIN,
                }
            )

    # `DT-024`: ascending by business key, which for this entity is the pair
    # (product_id, supplier_id). The rotation produces them product-major but not sorted
    # by supplier within a product, so the sort is not a no-op.
    rows.sort(key=lambda row: (row["product_id"], row["supplier_id"]))
    for index, row in enumerate(rows, start=1):
        row["id"] = index

    _draw_commercial_values(base, rows)
    return rows


def _draw_commercial_values(base: int, rows: list[dict[str, Any]]) -> None:
    """Fill ``moq``, ``order_multiple``, ``unit_cost`` and ``agreed_lead_time_days``.

    Values are drawn in file order, so they depend on the configuration and seed alone.

    Then the **witness relations** are forced. `DT-028` section 1.5 is explicit that the
    coverage guarantees cannot be left to the draw: with few relations a uniform seeded
    draw misses at least one of them with appreciable probability. Coverage here is a
    construction, not an expected outcome.
    """
    moq_rng = DeterministicRandom(base, "moq")
    multiple_rng = DeterministicRandom(base, "order-multiple")
    cost_rng = DeterministicRandom(base, "unit-cost")
    lead_rng = DeterministicRandom(base, "agreed-lead-time")

    for row in rows:
        row["moq"] = moq_rng.choice(pol.MOQ_VALUES)
        row["order_multiple"] = multiple_rng.choice(pol.ORDER_MULTIPLE_VALUES)
        row["unit_cost"] = format_cents(
            cost_rng.between(pol.UNIT_COST_MIN_CENTS, pol.UNIT_COST_MAX_CENTS)
        )
        row["agreed_lead_time_days"] = lead_rng.between(
            pol.AGREED_LEAD_TIME_MIN, pol.AGREED_LEAD_TIME_MAX
        )

    _force_witnesses(rows)
    _ensure_lead_time_variety(rows)
    _ensure_non_weekly_lead_time(rows)


def _force_witnesses(rows: list[dict[str, Any]]) -> None:
    """Pin the relations that carry the mandatory coverage cases (`DT-028` section 1).

    Witnesses are taken from the **active** relations, in file order, because an
    inactive relation is not a convincing witness of "a product the buyer can order at
    no minimum".

    ``moq = 1`` would satisfy section 1.1 on its face, but section 1.1 also requires the
    first witness to carry ``order_multiple = 1``: a relation with ``moq = 1`` and
    ``order_multiple = 100`` has a real minimum order of 100 units, because the engine
    computes ``ceil(Q/M)*M``. Without that condition the guarantee would be empty.
    """
    active = [row for row in rows if row["is_active"]]
    if len(active) < 4:
        raise pol.GeneratorError(
            [
                f"need at least 4 active product-supplier relations to place the "
                f"coverage witnesses of DT-028 section 1; got {len(active)}"
            ]
        )
    # 1. No significant MOQ, and genuinely orderable in any quantity.
    active[0]["moq"] = 0
    active[0]["order_multiple"] = 1
    # 2. A product with a real minimum order quantity.
    active[1]["moq"] = pol.MOQ_WITH_MINIMUM_VALUES[-1]
    # 3. A large order multiple - the edge case of specification section 26.
    active[2]["order_multiple"] = pol.ORDER_MULTIPLE_VALUES[-1]
    # The fourth guarantee - a lead time that is not a multiple of seven days, which is
    # what exercises the weekly-to-daily conversion of `DT-019` - is handled by
    # _ensure_non_weekly_lead_time() rather than by pinning a value here. Pinning one
    # would introduce a number that appears nowhere in `DT-028`, and the ADR asks for
    # every synthetic parameter to live in that one document.


def _ensure_lead_time_variety(rows: list[dict[str, Any]]) -> None:
    """Give every multi-supplier product two different lead times.

    `DT-028` section 1.6, condition 3: this is what gives the ``MULTIPLE_LEAD_TIMES``
    axis content. Drawing independently makes a collision unlikely but not impossible,
    and "unlikely" is not a guarantee - so when a product's relations all share one lead
    time, the second is nudged by a day. Deterministic, and it never leaves the
    ``[1, 45]`` range of `DT-028` section 1.4.
    """
    by_product: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_product.setdefault(row["product_id"], []).append(row)

    for group in by_product.values():
        if len(group) < 2:
            continue
        if len({row["agreed_lead_time_days"] for row in group}) > 1:
            continue
        target = group[1]
        current = target["agreed_lead_time_days"]
        target["agreed_lead_time_days"] = (
            current + 1 if current < pol.AGREED_LEAD_TIME_MAX else current - 1
        )


def _ensure_non_weekly_lead_time(rows: list[dict[str, Any]]) -> None:
    """Guarantee at least one lead time that is not a multiple of seven days.

    `DT-028` section 1.6, condition 2, via specification section 26. Like the variety
    rule above, this adjusts rather than pins: adding one day to the first offending
    relation introduces no value that is not already reachable inside the declared
    ``[1, 45]`` range, whereas writing a literal would put a number in the code that
    `DT-028` does not contain.

    Almost always a no-op: six sevenths of the range already satisfy the condition.
    """
    if any(row["agreed_lead_time_days"] % 7 != 0 for row in rows):
        return
    target = rows[0]
    current = target["agreed_lead_time_days"]
    target["agreed_lead_time_days"] = (
        current + 1 if current < pol.AGREED_LEAD_TIME_MAX else current - 1
    )


def _check_coverage(
    *,
    categories: Sequence[dict[str, Any]],
    products: Sequence[dict[str, Any]],
    suppliers: Sequence[dict[str, Any]],
    locations: Sequence[dict[str, Any]],
    relations: Sequence[dict[str, Any]],
    supplier_count: int,
) -> None:
    """Verify every guarantee the policies promise, before anything is written.

    `DT-028` section 8 is explicit: the generator "fails with an explicit error" rather
    than producing a degraded dataset in silence. These checks are that sentence in
    code. They restate the guarantees instead of trusting the construction, which is the
    point - a future change to the draw order should fail here, loudly, not ship a
    dataset that quietly misses a required scenario.
    """
    problems: list[str] = []
    active = [row for row in relations if row["is_active"]]

    if not any(
        row["moq"] in pol.MOQ_NO_MINIMUM_VALUES and row["order_multiple"] == 1
        for row in active
    ):
        problems.append(
            "no active relation represents 'no significant MOQ' with order_multiple = 1 "
            "(DT-028 section 1.1)"
        )
    if not any(row["moq"] in pol.MOQ_WITH_MINIMUM_VALUES for row in active):
        problems.append("no active relation carries a real MOQ (DT-028 section 1.1)")
    if not any(row["order_multiple"] == 1 for row in active):
        problems.append(
            "no active relation has order_multiple = 1 (DT-028 section 1.2)"
        )
    if not any(
        row["order_multiple"] >= pol.ORDER_MULTIPLE_LARGE_THRESHOLD for row in active
    ):
        problems.append(
            "no active relation has a large order multiple "
            f"(>= {pol.ORDER_MULTIPLE_LARGE_THRESHOLD}, DT-028 section 1.2)"
        )
    if not any(row["agreed_lead_time_days"] % 7 != 0 for row in relations):
        problems.append(
            "no relation has a lead time that is not a multiple of seven days "
            "(DT-028 section 1.6, specification section 26)"
        )
    if len({row["agreed_lead_time_days"] for row in relations}) < 2:
        problems.append(
            "lead times show no variation between suppliers (DT-028 section 1.6)"
        )

    by_product: dict[int, list[dict[str, Any]]] = {}
    for row in relations:
        by_product.setdefault(row["product_id"], []).append(row)

    multi = [group for group in by_product.values() if len(group) > 1]
    if not multi:
        problems.append(
            "no product has more than one supplier (specification section 25, row 21)"
        )
    single_lead_time = [
        group[0]["product_id"]
        for group in multi
        if len({row["agreed_lead_time_days"] for row in group}) < 2
    ]
    if single_lead_time:
        problems.append(
            "these products have several suppliers but a single lead time: "
            f"{sorted(single_lead_time)[:10]} (DT-028 section 1.6, condition 3)"
        )

    covered = {row["supplier_id"] for row in relations}
    if len(covered) != supplier_count:
        orphans = sorted(set(range(1, supplier_count + 1)) - covered)
        problems.append(
            f"these suppliers have no relation at all: {orphans} "
            "(DT-028 section 2.3, precondition P-4)"
        )
    if not any(len(group) > 1 for group in _by_supplier(relations).values()):
        problems.append(
            "no supplier serves more than one product (specification section 7.4)"
        )

    if not any(row["is_preferred"] for row in relations):
        problems.append(
            "no preferred supplier in the whole catalogue (DT-028 section 2.4)"
        )
    # `DT-028` section 2.4 in both directions: exactly one preferred supplier on every
    # product that has an active relation, and never more than one anywhere. Checking
    # only the upper bound would pass a catalogue with a single preferred row in total.
    too_many = [
        product_id
        for product_id, group in by_product.items()
        if len([row for row in group if row["is_preferred"]]) > 1
    ]
    if too_many:
        problems.append(
            f"these products have more than one preferred supplier: {sorted(too_many)[:10]}; "
            "docs/04 section 3.4 allows at most one active"
        )
    missing_preferred = [
        product_id
        for product_id, group in by_product.items()
        if any(row["is_active"] for row in group)
        and not any(row["is_preferred"] for row in group)
    ]
    if missing_preferred:
        problems.append(
            "these products have active suppliers but none preferred: "
            f"{sorted(missing_preferred)[:10]} (DT-028 section 2.4)"
        )
    preferred_inactive = [
        row["id"] for row in relations if row["is_preferred"] and not row["is_active"]
    ]
    if preferred_inactive:
        problems.append(
            f"these relations are preferred but inactive: {sorted(preferred_inactive)[:10]}; "
            "docs/04 section 3.4 speaks of the preferred *active* supplier"
        )
    if not any(
        all(not row["is_active"] for row in group) for group in by_product.values()
    ):
        problems.append(
            "no product has all of its supplier relations inactive, so the "
            "'product with no active supplier' case is missing "
            "(DT-028 section 2.5, specification section 26)"
        )

    states = {product["is_active"] for product in products}
    if states != {True, False}:
        problems.append(
            "the catalogue must contain both active and inactive products "
            "(specification section 25, rows 19 and 20)"
        )

    # `DT-028` section 7, the rest of the table: the "no active supplier" case lives on
    # the relation, so these three entities are active without exception. Checked rather
    # than assumed, for the same reason as everything else in this function.
    for label, rows in (
        ("categories", categories),
        ("suppliers", suppliers),
        ("locations", locations),
    ):
        inactive = [row["code"] for row in rows if not row["is_active"]]
        if inactive:
            problems.append(
                f"DT-028 section 7 requires every row of {label} to be active; "
                f"these are not: {sorted(inactive)[:10]}"
            )

    if problems:
        raise pol.GeneratorError(problems)


def _by_supplier(
    relations: Sequence[dict[str, Any]],
) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in relations:
        grouped.setdefault(row["supplier_id"], []).append(row)
    return grouped


# ---------------------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------------------

_FILES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("categories.csv", "Category", "categories", CATEGORY_COLUMNS),
    ("locations.csv", "Location", "locations", LOCATION_COLUMNS),
    (
        "product_suppliers.csv",
        "ProductSupplier",
        "product_suppliers",
        PRODUCT_SUPPLIER_COLUMNS,
    ),
    ("products.csv", "Product", "products", PRODUCT_COLUMNS),
    ("suppliers.csv", "Supplier", "suppliers", SUPPLIER_COLUMNS),
)


def generate(
    config: DatasetConfig,
    output_dir: Path | str | None = None,
    *,
    generated_at: _dt.datetime | None = None,
) -> dict[str, Any]:
    """Build the catalogue and write it to ``output_dir``.

    Args:
        config: a validated :class:`DatasetConfig`.
        output_dir: where to write. Defaults to ``data/synthetic/output/``.
        generated_at: the timestamp recorded in the manifest. Defaults to now, in UTC.
            It is a parameter so that a test can pin it: it is the one field the
            reproducibility invariant of section 44 excludes, and leaving it to the
            clock would make the manifest untestable.

    Returns:
        The manifest as a dictionary, already written to disk.

    Raises:
        GeneratorError: if a precondition or a coverage guarantee fails. Nothing is
            written in that case - the checks run before the first file is opened.
    """
    catalog = build_catalog(config)

    target = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    target.mkdir(parents=True, exist_ok=True)

    entries = []
    for filename, entity, attribute, columns in _FILES:
        rows = getattr(catalog, attribute)
        text = write_csv(
            target / filename,
            columns,
            [[row[name] for name in columns] for row in rows],
        )
        entries.append(file_entry(filename, entity, len(rows), text))

    manifest = build_manifest(
        config=config,
        generated_at=generated_at or _dt.datetime.now(_dt.timezone.utc),
        components=[
            {
                "name": COMPONENT_CATALOG,
                # The component's own version, not the generator's: `DT-028` section 8
                # leans on this field to record which policies produced the data, and
                # once Component 3 exists the two numbers stop coinciding.
                "version": CATALOG_VERSION,
                "sub_seed": sub_seed(config.seed, COMPONENT_CATALOG),
            }
        ],
        files=entries,
    )
    write_manifest(target / "manifest.json", manifest)
    return manifest
