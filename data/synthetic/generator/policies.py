"""Synthetic generation policies of the dataset generator.

Phase 1 - Data. One home for every synthetic parameter, so that replacing them when
real data arrives is a single file to read:

* **Component 2** - `DT-028` (generation policies) and the scope limits of `DT-029`.
* **Component 3** - `DT-035` (demand generation policies), from the banner near the
  bottom of this module onwards.
* **Component 4** - `DT-036` (synthetic inventory and replenishment policies), in its
  own banner.
* **Component 5** - `DT-039` section 5.2 (synthetic ``CANCELLED`` orders), in its own
  banner.
* **Component 6** - `DT-037` section 2 (synthetic supplier behaviour profiles), in the
  last banner of this module.

.. warning::

   **Every numeric value, set and range in this module is a synthetic generation
   parameter.** They are not commercial policies of the organisation, not costs, not
   MOQs, not order multiples and not lead times agreed with any real supplier. They
   exist for one reason: so the synthetic dataset can contain the technical scenarios
   that ``knowledge/dataset-specification.md`` requires. Its section 3.5 authorises
   exactly this, provided the values are identified as synthetic - which `DT-028` and
   this docstring do.

   The real business parameters remain pending in ``knowledge/business-rules.md``
   section 3. None of them is fixed here.

None of these values is configurable in this version (`DT-028` section 8, which
`DT-035` adopts unchanged): ``DatasetConfig`` is not extended. They are constants of
their component, and the contract for making any of them configurable later is written
in that same section.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from ..config.config import DatasetConfig

__all__ = [
    "GeneratorError",
    "MOQ_VALUES",
    "MOQ_NO_MINIMUM_VALUES",
    "MOQ_WITH_MINIMUM_VALUES",
    "ORDER_MULTIPLE_VALUES",
    "ORDER_MULTIPLE_LARGE_THRESHOLD",
    "UNIT_COST_MIN_CENTS",
    "UNIT_COST_MAX_CENTS",
    "AGREED_LEAD_TIME_MIN",
    "AGREED_LEAD_TIME_MAX",
    "UNIT_OF_MEASURE_VALUES",
    "LOCATION_TYPE_VALUES",
    "DATA_ORIGIN",
    "CODE_PATTERNS",
    "ClassSplit",
    "class_split",
    "category_distribution",
    "inactive_product_count",
    "inactive_valid_to_offset",
    "code_width",
    "check_preconditions",
    # Component 3 - DT-035
    "DEMAND_SHAPES",
    "DEMAND_ROTATIONS",
    "DEMAND_SHAPE_MIX",
    "DEMAND_ROTATION_MIX",
    "DEMAND_BASE_LEVEL",
    "DEMAND_NOISE_PERMILLE",
    "DEMAND_TREND_PERMILLE",
    "DEMAND_SEASON_AMPLITUDE_PERMILLE",
    "DEMAND_SEASON_PERIOD_DAYS",
    "DEMAND_INTERMITTENT_EVENT_PERMILLE",
    "DEMAND_INTERMITTENT_EVENT_MULTIPLIER",
    "DEMAND_QUANTITY_IS_INTEGER",
    "DEMAND_MIN_PRODUCTS",
    "demand_mix_counts",
    "seasonal_factor_permille",
    "trend_factor_permille",
    # Component 4 - DT-036
    "INVENTORY_WINDOW_DAYS",
    "INVENTORY_OPENING_MARGIN_DAYS",
    "INVENTORY_ORDER_COVERAGE_DAYS",
    "INVENTORY_OPENING_PROFILES",
    "INVENTORY_OPENING_FACTOR_PERMILLE",
    "INVENTORY_OPENING_MIX",
    # Component 5 - DT-039
    "ORDERS_CANCELLED_PERMILLE",
    "ORDERS_CANCELLED_CLOSE_LAG_DAYS",
    # Component 6 - DT-037
    "SUPPLIER_PUNCTUALITY_PROFILES",
    "SUPPLIER_ON_TIME_PERMILLE",
    "SUPPLIER_DELAY_DAYS",
    "SUPPLIER_PUNCTUALITY_MIX",
    "SUPPLIER_INTEGRITY_PROFILES",
    "SUPPLIER_PARTIAL_PERMILLE",
    "SUPPLIER_SPLIT_RANGE",
    "SUPPLIER_COMPLETION_LAG_DAYS",
    "SUPPLIER_INTEGRITY_MIX",
    "SUPPLIER_BEHAVIOUR_MIN_SUPPLIERS",
]


class GeneratorError(RuntimeError):
    """Raised when the generator cannot produce a valid dataset.

    Carries every problem found, like ``ConfigError`` does for the configuration, so a
    configuration that violates three preconditions is corrected in one pass.

    It is deliberately **not** a ``ConfigError``: the configuration may be perfectly
    valid and still be one this version of the generator cannot serve (`DT-028`
    section 8). Conflating the two would put the limitation in the wrong layer.
    """

    def __init__(self, problems: list[str]) -> None:
        self.problems = list(problems)
        joined = "\n".join(f"  - {p}" for p in self.problems)
        super().__init__(f"Cannot generate the catalogue:\n{joined}")


# ---------------------------------------------------------------------------------------
# 1. Commercial values of ProductSupplier - DT-028 section 1
# ---------------------------------------------------------------------------------------

#: `DT-028` section 1.1. Tuple, not a set, because the draw must be reproducible and set
#: iteration order is not part of any contract.
MOQ_VALUES: tuple[int, ...] = (0, 1, 5, 10, 25, 50, 100, 250)

#: "No significant MOQ" (specification section 16, first case).
MOQ_NO_MINIMUM_VALUES: tuple[int, ...] = (0, 1)

#: "Products with MOQ" (specification section 16, second case).
MOQ_WITH_MINIMUM_VALUES: tuple[int, ...] = (5, 10, 25, 50, 100, 250)

#: `DT-028` section 1.2.
ORDER_MULTIPLE_VALUES: tuple[int, ...] = (1, 5, 10, 12, 24, 48, 100)

#: `DT-028` section 1.2 requires at least one relation at or above this value.
ORDER_MULTIPLE_LARGE_THRESHOLD = 48

#: `DT-028` section 1.3: [0.50, 2500.00] with exactly two decimals. Held in cents so the
#: draw is integer arithmetic; `docs/04` section 7 forbids floating point for monetary
#: values and a float draw would reintroduce it through the back door.
UNIT_COST_MIN_CENTS = 50
UNIT_COST_MAX_CENTS = 250_000

#: `DT-028` section 1.4: [1, 45] natural days. The lower bound is 1, not 0, and section
#: 1.6 explains why: an agreed lead time of zero represents nothing. The "zero lead time"
#: edge case of specification section 26 is an *observed* lead time and belongs to
#: Components 5 and 6.
AGREED_LEAD_TIME_MIN = 1
AGREED_LEAD_TIME_MAX = 45

# ---------------------------------------------------------------------------------------
# 4-6. Vocabularies - DT-028 sections 4, 5 and 6
# ---------------------------------------------------------------------------------------

#: `DT-028` section 5. Closed set of three, one per example in `docs/04` section 3.2.
UNIT_OF_MEASURE_VALUES: tuple[str, ...] = ("EACH", "BOX", "KG")

#: `DT-028` section 6. Closed set of **one**: the current scope is a single operating
#: location. Adding BRANCH or STORE would be designing multi-warehouse support, which is
#: `DT-P09` and deliberately deferred.
LOCATION_TYPE_VALUES: tuple[str, ...] = ("MAIN_WAREHOUSE",)

#: `DT-026`. Constant in every row of every master entity.
DATA_ORIGIN = "SYNTHETIC"

#: `DT-028` section 4: neutral patterns, zero-padded to a fixed width. The width matters
#: beyond looks - it makes the lexicographic order of the business key agree with the
#: numeric one, which is what lets `DT-024` order rows by code (CAT-002 before CAT-010).
#:
#: The widths here are the ones the ADR tabulates, for the scale it tabulates them at.
#: They are a *minimum*, not a cap - see :func:`code_width`.
CODE_PATTERNS: dict[str, tuple[str, int]] = {
    "category": ("CAT", 3),
    "product": ("SKU", 5),
    "supplier": ("SUP", 3),
    "location": ("LOC", 3),
}


def code_width(kind: str, count: int) -> int:
    """Padding width for a set of ``count`` codes of this kind (`DT-028` section 4).

    The ADR fixes widths of 3 and 5 **and** says what to do when they run out: "if the
    fixed width falls short for a larger scale, it is widened". So the width is the
    tabulated one, or as many digits as the largest number needs, whichever is greater.

    Widening is not cosmetic. `DT-024` orders rows by business key and justifies it with
    "since the codes are zero-padded to a fixed width, the lexicographic order of the
    business key agrees with the numeric one". Overflow breaks exactly that: with 1000
    categories and a width of 3, ``CAT-1000`` sorts *before* ``CAT-999``, so the file
    would come out unordered - and silently, since every row would still be present and
    unique. Widening keeps the padding uniform within a dataset, which is what the
    equivalence actually needs.

    Codes are not comparable between datasets of different scales, and `DT-028` section 4
    already says so: identifiers are not reused between runs with different configurations.
    """
    if count < 1:
        raise GeneratorError([f"count must be positive, got {count}"])
    return max(CODE_PATTERNS[kind][1], len(str(count)))


# ---------------------------------------------------------------------------------------
# 2.2 Product classes - DT-028 section 2.2
# ---------------------------------------------------------------------------------------

#: Proportions of `DT-028` section 2.2, as exact fractions. Floats would make the floor
#: depend on binary rounding: 0.05 * 100 is 5.000000000000001 in binary floating point,
#: which floors to 5 by luck rather than by rule.
_CLASS_B_SHARE = Fraction(10, 100)
_CLASS_C_SHARE = Fraction(5, 100)
_CLASS_D_SHARE = Fraction(5, 100)

#: `DT-028` section 7: 5 % of products inactive, floor of 1.
_INACTIVE_SHARE = Fraction(5, 100)

#: `DT-028` section 7.1: an inactive product's validity ends at 75 % of the window.
_INACTIVE_VALID_TO_SHARE = Fraction(75, 100)


@dataclass(frozen=True)
class ClassSplit:
    """How many products fall in each supplier-assignment class (`DT-028` section 2.2)."""

    class_a: int  # 1 supplier, active relation
    class_b: int  # 2 suppliers, both active
    class_c: int  # 3 suppliers, all active
    class_d: int  # 1 supplier, relation inactive -> "product with no active supplier"

    @property
    def relation_count(self) -> int:
        """``R`` in `DT-028` section 2.3: total number of ProductSupplier rows."""
        return self.class_a + 2 * self.class_b + 3 * self.class_c + self.class_d

    @property
    def product_count(self) -> int:
        return self.class_a + self.class_b + self.class_c + self.class_d


def class_split(product_count: int) -> ClassSplit:
    """Split the catalogue into the four classes of `DT-028` section 2.2.

    B, C and D take their share with a floor of one product each; A takes the rest. With
    ``product_count = 100`` this gives 80 / 10 / 5 / 5 and ``R = 120``, the figures the
    ADR states.

    Class A is never empty: for ``product_count >= 4`` (precondition P-2) the three
    floors take at most three products, leaving at least one.
    """
    if product_count < 4:
        raise GeneratorError(
            [
                "product_count must be at least 4 for the four-class split "
                f"(DT-028 section 2.2, precondition P-2); got {product_count}"
            ]
        )
    n_b = max(1, int(_CLASS_B_SHARE * product_count))
    n_c = max(1, int(_CLASS_C_SHARE * product_count))
    n_d = max(1, int(_CLASS_D_SHARE * product_count))
    n_a = product_count - n_b - n_c - n_d
    return ClassSplit(class_a=n_a, class_b=n_b, class_c=n_c, class_d=n_d)


def inactive_product_count(product_count: int) -> int:
    """How many products carry ``is_active = false`` (`DT-028` section 7)."""
    return max(1, int(_INACTIVE_SHARE * product_count))


def inactive_valid_to_offset(period_days: int) -> int:
    """Days from ``valid_from`` to ``valid_to`` for an inactive product.

    ``floor(0.75 * period.days)`` (`DT-028` section 7.1). Precondition P-5 keeps this
    from collapsing to zero.
    """
    return int(_INACTIVE_VALID_TO_SHARE * period_days)


# ---------------------------------------------------------------------------------------
# 3. Weighted distribution of products per category - DT-028 section 3
# ---------------------------------------------------------------------------------------


def category_distribution(category_count: int, product_count: int) -> list[int]:
    """Products per category: Zipf(1) weights, largest remainder, floor of one.

    This is a pure function of its two arguments - the seed decides *which* product goes
    to a category, never *how many* (`DT-028` section 3.4).

    The weights are handled as exact fractions, because the ADR requires the
    normalisation to sum to exactly 1 and forbids comparing floats for equality.

    The donor of the floor loop is **recomputed on every transfer**. `DT-028` section 3.2
    is emphatic about this, and with reason: fixing the donor once produces a different
    algorithm that aborts - with ``category_count = product_count = 10`` the base split
    is ``[3,2,1,1,1,1,1,0,0,0]`` and a fixed donor reaches zero before the three empty
    categories are filled.

    Ties - equal remainders, or equal counts when picking the donor - go to the lower
    index, so the result is a total function of the two arguments and does not depend on
    iteration order.
    """
    if category_count < 1:
        raise GeneratorError([f"category_count must be positive, got {category_count}"])
    if product_count < category_count:
        raise GeneratorError(
            [
                "product_count must be at least category_count for the floor of one "
                "product per category (DT-028 section 3.2, precondition P-1); got "
                f"product_count={product_count}, category_count={category_count}"
            ]
        )

    weights = [Fraction(1, i) for i in range(1, category_count + 1)]
    total = sum(weights)
    shares = [w / total for w in weights]
    # The ADR asks for this to be validated, not assumed.
    if sum(shares) != 1:
        raise GeneratorError(
            ["the normalised Zipf weights do not sum to exactly 1 (DT-028 section 3.2)"]
        )

    exact = [share * product_count for share in shares]
    counts = [int(value) for value in exact]  # floor: every value is non-negative
    remainders = [value - int(value) for value in exact]

    # Largest remainder, lower index wins a tie.
    shortfall = product_count - sum(counts)
    order = sorted(range(category_count), key=lambda i: (-remainders[i], i))
    for index in order[:shortfall]:
        counts[index] += 1

    # Floor of one product per category. Safe: whenever some count is zero, the maximum
    # is at least 2, because the counts sum to product_count >= category_count. So the
    # donor never drops below 1 and the loop runs at most category_count times.
    for _ in range(category_count):
        smallest = min(range(category_count), key=lambda i: (counts[i], i))
        if counts[smallest] >= 1:
            break
        donor = max(range(category_count), key=lambda i: (counts[i], -i))
        counts[donor] -= 1
        counts[smallest] += 1

    if min(counts) < 1 or sum(counts) != product_count:
        raise GeneratorError(
            [
                "the category distribution is inconsistent: "
                f"counts={counts}, sum={sum(counts)}, expected {product_count}"
            ]
        )
    return counts


# ---------------------------------------------------------------------------------------
# Preconditions - DT-028 section 8 and DT-029
# ---------------------------------------------------------------------------------------


def check_preconditions(config: DatasetConfig) -> None:
    """Check every precondition this version of Component 2 requires.

    P-1 to P-5 come from `DT-028` section 8; the single-location limit comes from
    `DT-029`. None of them lives in ``config.py``, and that is deliberate: a
    configuration with two locations is a valid configuration that *this generator*
    cannot serve. The restriction belongs where the limitation is.

    All problems are reported together, and the generator never produces a degraded
    dataset in silence.

    Raises:
        GeneratorError: if any precondition fails.
    """
    problems: list[str] = []
    scale = config.scale
    days = config.period.days

    if scale.product_count < scale.category_count:
        problems.append(
            "P-1: product_count must be at least category_count so no category is empty "
            f"(DT-028 section 3.2); got product_count={scale.product_count}, "
            f"category_count={scale.category_count}"
        )
    if scale.product_count < 4:
        problems.append(
            "P-2: product_count must be at least 4, one per supplier-assignment class "
            f"(DT-028 section 2.2); got {scale.product_count}"
        )
    if scale.supplier_count < 3:
        problems.append(
            "P-3: supplier_count must be at least 3, because class C needs three "
            f"distinct suppliers for one product (DT-028 section 2.3); got "
            f"{scale.supplier_count}"
        )

    # P-4 needs R, which needs the class split, which needs P-2. Only evaluate it when
    # the split is computable; otherwise the message would be about a number the reader
    # cannot check.
    if scale.product_count >= 4:
        relations = class_split(scale.product_count).relation_count
        if scale.supplier_count >= relations:
            problems.append(
                "P-4: supplier_count must be strictly below the total number of "
                "product-supplier relations, so that no supplier is left without rows "
                "and at least one supplies several products (DT-028 section 2.3); got "
                f"supplier_count={scale.supplier_count}, relations={relations}"
            )

    if days < 2:
        problems.append(
            "P-5: period.days must be at least 2, so an inactive product keeps some "
            f"history (DT-028 section 7.1); got {days}"
        )

    if scale.location_count != 1:
        problems.append(
            "this version of Component 2 generates exactly one location; multi-location "
            "support is DT-P09 and is deferred (DT-029); got "
            f"location_count={scale.location_count}"
        )

    if problems:
        raise GeneratorError(problems)


# =======================================================================================
# COMPONENT 3 - Demand Generator
#
# Everything below belongs to `DT-035` (synthetic demand generation policies) and is as
# synthetic as everything above it: these are `synthetic generation parameters`, not
# demand figures, sales volumes or rotation classes of any organisation. Specification
# section 3.5 authorises them provided they are identified as such, which `DT-035` and
# this banner do.
#
# Section 8 of the specification describes the six demand shapes **qualitatively** -
# "ascending trend", "high variability", "numerous zero periods" - and fixes no formula
# and no number. `DT-035` supplies them, with the same status the MOQ values of
# `DT-028` have: a technical choice that can be replaced without touching any rule.
# =======================================================================================

#: The six **shapes** a demand series can take (specification section 8). Every product
#: receives exactly one.
DEMAND_SHAPES: tuple[str, ...] = (
    "STABLE_DEMAND",
    "GROWING_DEMAND",
    "DECLINING_DEMAND",
    "SEASONAL_DEMAND",
    "INTERMITTENT_DEMAND",
    "ERRATIC_DEMAND",
)

#: The two **rotation levels** (`DT-023` section 7.2). Every product receives one, in
#: addition to its shape.
DEMAND_ROTATIONS: tuple[str, ...] = ("HIGH_ROTATION", "LOW_ROTATION")

#: Shape mix, in per cent. Sums to 100 and is validated at import time.
#:
#: Stable is the largest slice because it is the baseline every model is compared
#: against (section 8.1); intermittent and erratic are the smallest because they are the
#: hardest cases, not the common ones. No claim is made that a real catalogue looks like
#: this - the mix exists so the dataset contains all six shapes in usable numbers.
DEMAND_SHAPE_MIX: dict[str, int] = {
    "STABLE_DEMAND": 30,
    "GROWING_DEMAND": 15,
    "DECLINING_DEMAND": 15,
    "SEASONAL_DEMAND": 20,
    "INTERMITTENT_DEMAND": 10,
    "ERRATIC_DEMAND": 10,
}

#: Rotation mix, in per cent. Sums to 100.
DEMAND_ROTATION_MIX: dict[str, int] = {
    "HIGH_ROTATION": 30,
    "LOW_ROTATION": 70,
}

#: Base demand level per day, by rotation class, as an inclusive integer range.
#:
#: This is the parameter the specification never names and without which there is no
#: series at all: how much a product moves on an ordinary day. The two ranges are
#: disjoint and an order of magnitude apart, which is what makes `HIGH_ROTATION` and
#: `LOW_ROTATION` distinguishable by inspection rather than by label.
DEMAND_BASE_LEVEL: dict[str, tuple[int, int]] = {
    "HIGH_ROTATION": (20, 60),
    "LOW_ROTATION": (1, 5),
}

#: Day-to-day relative variability, in per mille of the level, by shape.
#:
#: `ERRATIC_DEMAND` is four times the others: section 8.6 asks it to be distinguishable
#: "by its variability, not by having a different mean level", so the level ranges are
#: shared and only this number changes.
DEMAND_NOISE_PERMILLE: dict[str, int] = {
    "STABLE_DEMAND": 150,
    "GROWING_DEMAND": 150,
    "DECLINING_DEMAND": 150,
    "SEASONAL_DEMAND": 150,
    "INTERMITTENT_DEMAND": 150,
    "ERRATIC_DEMAND": 600,
}

#: Total relative change across the **whole** period, in per mille (sections 8.2, 8.3).
#:
#: 600 means a growing series ends at 1.6x its starting level and a declining one at
#: 0.4x. The declining figure is the binding one: it must stay comfortably above zero,
#: because a level that reaches zero would turn a declining product into an intermittent
#: one and make the two shapes indistinguishable.
DEMAND_TREND_PERMILLE = 600

#: Relative amplitude of the seasonal wave, in per mille (section 8.4).
DEMAND_SEASON_AMPLITUDE_PERMILLE = 400

#: Seasonal period, in days. Annual, as section 8.4 requires; the configured window of
#: 1096 days holds three complete cycles.
DEMAND_SEASON_PERIOD_DAYS = 365

#: Probability, in per mille, that an intermittent product has any demand on a given day
#: (section 8.5). 150 leaves roughly 85 % of days at zero.
DEMAND_INTERMITTENT_EVENT_PERMILLE = 150

#: When an intermittent product does move, it moves in a lump: the base level times a
#: factor drawn from this inclusive range. Without it, an intermittent series would just
#: be a stable series with holes, and the annual total would collapse.
DEMAND_INTERMITTENT_EVENT_MULTIPLIER: tuple[int, int] = (2, 6)

#: `DT-035`: quantities are integers in V1, for every unit of measure. Declared as a
#: constant rather than left implicit because `DT-024` explicitly does **not** cover
#: non-monetary decimals, and `docs/04` section 7 leaves fractional quantities open
#: "to be decided per unit of measure". V1 decides: integers. This is a property of the
#: synthetic dataset, not a claim that real products come in whole units.
DEMAND_QUANTITY_IS_INTEGER = True

#: Minimum products C3 needs, one per shape, so that no shape is missing from the
#: dataset. Precondition **P-6**; the same spirit as P-2 for C2's four classes.
DEMAND_MIN_PRODUCTS = len(DEMAND_SHAPES)


def _validate_mix(name: str, mix: dict[str, int], members: tuple[str, ...]) -> None:
    """A mix must cover exactly its members and sum to 100. Checked at import."""
    if set(mix) != set(members):
        raise GeneratorError(
            [f"{name} must cover exactly {sorted(members)}, got {sorted(mix)}"]
        )
    if sum(mix.values()) != 100:
        raise GeneratorError([f"{name} must sum to 100, got {sum(mix.values())}"])


_validate_mix("DEMAND_SHAPE_MIX", DEMAND_SHAPE_MIX, DEMAND_SHAPES)
_validate_mix("DEMAND_ROTATION_MIX", DEMAND_ROTATION_MIX, DEMAND_ROTATIONS)


def demand_mix_counts(
    mix: dict[str, int], members: tuple[str, ...], total: int
) -> dict[str, int]:
    """Split ``total`` products across ``members`` following ``mix``, floor of one each.

    Largest remainder with exact fractions, ties to the lower index - the same method
    `DT-028` section 3.2 fixes for the category distribution, and for the same reason:
    the result must be a total function of its arguments, not of iteration order.

    The floor of one is what makes the coverage guarantee a construction rather than a
    probability. `DT-028` section 1.5 already learned that lesson at small scale.
    """
    if total < len(members):
        raise GeneratorError(
            [
                f"cannot give every one of {len(members)} classes at least one product "
                f"out of {total} (DT-035, precondition P-6)"
            ]
        )
    exact = [Fraction(mix[name] * total, 100) for name in members]
    counts = [int(value) for value in exact]
    remainders = [value - int(value) for value in exact]
    shortfall = total - sum(counts)
    order = sorted(range(len(members)), key=lambda i: (-remainders[i], i))
    for index in order[:shortfall]:
        counts[index] += 1

    # Floor of one, donor recomputed on every transfer (DT-028 section 3.2).
    for _ in range(len(members)):
        smallest = min(range(len(members)), key=lambda i: (counts[i], i))
        if counts[smallest] >= 1:
            break
        donor = max(range(len(members)), key=lambda i: (counts[i], -i))
        counts[donor] -= 1
        counts[smallest] += 1

    result = {name: counts[i] for i, name in enumerate(members)}
    if min(result.values()) < 1 or sum(result.values()) != total:
        raise GeneratorError([f"inconsistent mix split: {result}, expected {total}"])
    return result


def seasonal_factor_permille(day_index: int, phase: int) -> int:
    """Seasonal multiplier for one day, in per mille, as an exact integer.

    A **triangular** wave, not a sine, and the reason is reproducibility rather than
    taste: ``math.sin`` is computed by the platform's libm, whose last bits are not
    guaranteed to match across versions or architectures. `DT-032` exists to make the
    dataset byte-identical everywhere, and a single float from libm would undo that for
    every seasonal product. A triangle is exact integer arithmetic and satisfies section
    8.4 just as well, which asks for "a clearly defined and reproducible periodicity",
    not for a sinusoid.

    Returns a value in ``[1000 - A, 1000 + A]`` with ``A`` the amplitude in per mille.
    """
    period = DEMAND_SEASON_PERIOD_DAYS
    half = period // 2
    position = (day_index + phase) % period
    if position < half:
        triangle = -1000 + (2000 * position) // half
    else:
        triangle = 1000 - (2000 * (position - half)) // (period - half)
    return 1000 + (DEMAND_SEASON_AMPLITUDE_PERMILLE * triangle) // 1000


def trend_factor_permille(shape: str, day_index: int, total_days: int) -> int:
    """Trend multiplier for one day, in per mille (sections 8.2 and 8.3).

    Linear in the day index: the simplest mechanism that produces a monotone global
    trend, and the one easiest to falsify in a test. Shapes other than the two trend
    shapes return exactly 1000, so trend and seasonality stay separable terms rather
    than a single blended curve.
    """
    if shape not in ("GROWING_DEMAND", "DECLINING_DEMAND"):
        return 1000
    span = max(1, total_days - 1)
    progress = (DEMAND_TREND_PERMILLE * day_index) // span
    return 1000 + progress if shape == "GROWING_DEMAND" else 1000 - progress


# =======================================================================================
# Component 4 - Inventory Simulator: synthetic inventory policies (DT-036)
# =======================================================================================
#
# **Synthetic simulation parameters, not inventory policy.** None of these is a reorder
# point, a safety stock, a service level, a review period or a coverage target of any
# organisation. `DT-036` states the non-equivalences in its reading warning:
#
#     s != ROP     Q != recommendation     C != target_coverage_days
#
# They drive a generator of plausible history and nothing else. Changing any of them
# changes the published artefact and therefore requires a `generator_version` bump under
# the rule of `DT-033`.

#: `W` - width, in days, of the demand window behind both the opening balance (`DT-036`
#: section 1) and the recent demand of the replenishment trigger (section 5). The window
#: is always **exactly** this wide; it is never shortened (decision D-C4-2).
INVENTORY_WINDOW_DAYS = 28

#: `M` - margin, in days, **added to the agreed lead time to size the opening balance**
#: (`DT-036` section 1). It is not a review period: the trigger is evaluated every day
#: (`DT-038` section 3, decision D-C4-3), and the engine's `R_v1` plays no part here.
INVENTORY_OPENING_MARGIN_DAYS = 7

#: `C` - coverage, in days, of the synthetic order quantity `Q = ceil(d_recent x C)`
#: (`DT-036` section 4). Not `target_coverage_days`: this generator writes no
#: `InventoryPolicy`.
INVENTORY_ORDER_COVERAGE_DAYS = 21

#: `DT-036` section 2: the three opening profiles, in canonical order.
INVENTORY_OPENING_PROFILES: tuple[str, ...] = ("AJUSTADO", "NORMAL", "HOLGADO")

#: `DT-036` section 2: opening factor of each profile, in **per mille**. Integers on
#: purpose - 0.75 as a float would bring back the binary rounding `DT-028` avoids with
#: `Fraction`, and `DT-032` forbids floats in the generator.
INVENTORY_OPENING_FACTOR_PERMILLE: dict[str, int] = {
    "AJUSTADO": 750,
    "NORMAL": 1000,
    "HOLGADO": 1500,
}

#: `DT-036` section 2: share of product-location pairs per opening profile, summing to
#: 100, split by largest remainder with a floor of one (`DT-028` section 3.2).
INVENTORY_OPENING_MIX: dict[str, int] = {
    "AJUSTADO": 30,
    "NORMAL": 40,
    "HOLGADO": 30,
}

_validate_mix(
    "INVENTORY_OPENING_MIX", INVENTORY_OPENING_MIX, INVENTORY_OPENING_PROFILES
)
if set(INVENTORY_OPENING_FACTOR_PERMILLE) != set(INVENTORY_OPENING_PROFILES):
    raise GeneratorError(
        ["INVENTORY_OPENING_FACTOR_PERMILLE must define exactly the opening profiles"]
    )


# =======================================================================================
# Component 5 - Purchase Order Generator: synthetic CANCELLED orders (DT-039 §5.2)
# =======================================================================================
#
# **Synthetic coverage parameters, not a cancellation rate.** Approved on 2026-09-26 so
# that the dataset holds at least one cancelled order, as section 14 of the specification
# requires. Neither is a cancellation rate of any organisation, a business requirement or
# a measurement: they must not be quoted as business information. Changing either
# changes the published artefact and therefore requires a `generator_version` bump under
# the rule of `DT-033` (`DT-039` section 12).

#: `DT-039` section 5.2, point 2: per mille of the **causal** orders turned into
#: cancelled twins, with a floor of one: ``K = max(1, ceil(N x 20 / 1000))``.
ORDERS_CANCELLED_PERMILLE = 20

#: `DT-039` section 5.2, points 1 and 4: days between the issue of a cancelled twin and
#: its ``closed_at``. Also the offset of the planned close that decides eligibility.
ORDERS_CANCELLED_CLOSE_LAG_DAYS = 1

if not 0 <= ORDERS_CANCELLED_PERMILLE <= 1000:
    raise GeneratorError(["ORDERS_CANCELLED_PERMILLE must be in [0, 1000]"])
if ORDERS_CANCELLED_CLOSE_LAG_DAYS < 1:
    # DT-039 section 5.2: a cancelled order with issued_at == closed_at cannot exist.
    raise GeneratorError(["ORDERS_CANCELLED_CLOSE_LAG_DAYS must be at least 1"])


# =======================================================================================
# Component 6 - Supplier Behaviour Generator: synthetic supplier profiles (DT-037 §2)
# =======================================================================================
#
# **Synthetic generation parameters, not supplier ratings.** None of these values is a
# service level, a commercial agreement, an on-time rate or a characteristic of any real
# supplier, and none may be used to evaluate or negotiate with one (`DT-037`, reading
# warning). They exist so the dataset contains reliable, delayed and partial deliveries.
# Every value of a profile is a **constant of the profile**, not a draw (`DT-037` §4):
# what distinguishes two suppliers is which profile they belong to.

#: Axis 1 - punctuality, canonical order of `DT-037` section 2.
SUPPLIER_PUNCTUALITY_PROFILES: tuple[str, ...] = ("PUNCTUAL", "IRREGULAR", "LATE")

#: Probability, per mille, that a receipt arrives on its expected date.
SUPPLIER_ON_TIME_PERMILLE: dict[str, int] = {
    "PUNCTUAL": 900,
    "IRREGULAR": 650,
    "LATE": 250,
}

#: Range of the delay, in calendar days, when a receipt is not on time. Both ends included.
SUPPLIER_DELAY_DAYS: dict[str, tuple[int, int]] = {
    "PUNCTUAL": (1, 3),
    "IRREGULAR": (1, 7),
    "LATE": (3, 14),
}

#: Share of suppliers per punctuality profile, summing to 100; largest remainder with a
#: floor of one (`DT-028` section 3.2). 4 / 4 / 2 with the current 10 suppliers.
SUPPLIER_PUNCTUALITY_MIX: dict[str, int] = {"PUNCTUAL": 40, "IRREGULAR": 40, "LATE": 20}

#: Axis 2 - integrity, canonical order of `DT-037` section 2.
SUPPLIER_INTEGRITY_PROFILES: tuple[str, ...] = ("COMPLETE", "SPLIT")

#: Probability, per mille and per order, of splitting the delivery in two receipts.
SUPPLIER_PARTIAL_PERMILLE: dict[str, int] = {"COMPLETE": 0, "SPLIT": 250}

#: Share, per mille, of the first receipt of a split delivery. **None** for ``COMPLETE``
#: (`DT-037` section 3: null, not zero and not omitted).
SUPPLIER_SPLIT_RANGE: dict[str, tuple[int, int] | None] = {
    "COMPLETE": None,
    "SPLIT": (400, 800),
}

#: Days between the first and the second receipt of a split delivery. **None** for
#: ``COMPLETE``.
SUPPLIER_COMPLETION_LAG_DAYS: dict[str, tuple[int, int] | None] = {
    "COMPLETE": None,
    "SPLIT": (1, 10),
}

#: Share of suppliers per integrity profile, summing to 100. 7 / 3 with 10 suppliers.
SUPPLIER_INTEGRITY_MIX: dict[str, int] = {"COMPLETE": 70, "SPLIT": 30}

#: Precondition **P-C6-1** (`DT-037` section 2): one supplier per punctuality profile.
SUPPLIER_BEHAVIOUR_MIN_SUPPLIERS = len(SUPPLIER_PUNCTUALITY_PROFILES)

_validate_mix(
    "SUPPLIER_PUNCTUALITY_MIX", SUPPLIER_PUNCTUALITY_MIX, SUPPLIER_PUNCTUALITY_PROFILES
)
_validate_mix(
    "SUPPLIER_INTEGRITY_MIX", SUPPLIER_INTEGRITY_MIX, SUPPLIER_INTEGRITY_PROFILES
)
for _table in (SUPPLIER_ON_TIME_PERMILLE, SUPPLIER_DELAY_DAYS):
    if set(_table) != set(SUPPLIER_PUNCTUALITY_PROFILES):
        raise GeneratorError(["a punctuality table must cover exactly its profiles"])
for _table in (
    SUPPLIER_PARTIAL_PERMILLE,
    SUPPLIER_SPLIT_RANGE,
    SUPPLIER_COMPLETION_LAG_DAYS,
):
    if set(_table) != set(SUPPLIER_INTEGRITY_PROFILES):
        raise GeneratorError(["an integrity table must cover exactly its profiles"])
del _table
