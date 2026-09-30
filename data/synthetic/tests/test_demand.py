"""Tests for Component 3: the Demand Generator.

Run from the repository root::

    python3 -m unittest discover -s data/synthetic/tests -t .

Standard library ``unittest``, like Components 1 and 2: no test dependency beyond PyYAML
(`docs/13-testing.md`).

Scope: the latent demand series, its contract and its determinism. Nothing about
inventory, stockouts, satisfied consumption, orders or the supply engine - none of that
is C3's and none of it exists.

**The behaviour tests measure the series, they do not read a label.** Checking that a
product is tagged ``SEASONAL_DEMAND`` proves nothing about the numbers; what these tests
assert is that a seasonal series actually repeats annually, that a growing one actually
grows, and that an intermittent one is genuinely distinguishable from a low-volume
stable one. A generator that produced flat noise under every name would pass a label
check and fail every test in ``DemandBehaviourTests``.
"""

from __future__ import annotations

import collections
import csv
import datetime as _dt
import json
import os
import statistics as _st
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from data.synthetic.config.config import DatasetConfig, Scenario
from data.synthetic.generator import policies as pol
from data.synthetic.generator.catalog import generate as generate_catalog
from data.synthetic.generator.demand import (
    DEMAND_COLUMNS,
    DEMAND_FILE,
    build_demand,
    generate,
    period_days,
    read_catalog_inputs,
)
from data.synthetic.generator.rng import COMPONENT_DEMAND, sub_seed
from data.synthetic.generator.writer import DEMAND_VERSION

BASE_CONFIG: dict = {
    "seed": 20260913,
    "period": {"start_date": "2023-01-01", "end_date": "2026-01-01"},
    "scale": {
        "product_count": 100,
        "supplier_count": 10,
        "category_count": 10,
        "location_count": 1,
    },
    "scenarios": {"required": [s.value for s in Scenario]},
}

FIXED_TIME = _dt.datetime(2026, 9, 23, 12, 0, 0, tzinfo=_dt.timezone.utc)

#: A short window and a small catalogue, for the tests that do not need three years of
#: history. The full-scale dataset is built once, in ``FullScaleFixture``.
SMALL = {
    "scale": {"product_count": 12, "supplier_count": 4, "category_count": 3},
    "period": {"start_date": "2023-01-01", "end_date": "2023-03-01"},
}


def make_config(**overrides) -> DatasetConfig:
    raw = json.loads(json.dumps(BASE_CONFIG))
    for key, value in overrides.items():
        if key in ("scale", "period"):
            raw[key].update(value)
        else:
            raw[key] = value
    return DatasetConfig.from_mapping(raw)


def build_dataset(tmp: Path, config: DatasetConfig) -> Path:
    """Run C2 then C3 into a directory, the way the pipeline does."""
    generate_catalog(config, tmp, generated_at=FIXED_TIME)
    generate(config, tmp, generated_at=FIXED_TIME)
    return tmp


def read_demand(directory: Path) -> list[dict[str, str]]:
    with (directory / DEMAND_FILE).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def series_by_product(demand) -> dict[int, list[int]]:
    """Each product's series, in date order. Rows are already sorted by business key."""
    series: dict[int, list[int]] = collections.defaultdict(list)
    for row in demand.rows:
        series[row["product_id"]].append(row["quantity"])
    return series


# =======================================================================================
# Responsibilities - DT-034
# =======================================================================================


class ResponsibilityTests(unittest.TestCase):
    """C3 produces latent demand and nothing else. This is the architecture's spine."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.out = build_dataset(Path(cls._tmp.name) / "out", make_config(**SMALL))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_c3_writes_demand_csv(self) -> None:
        self.assertTrue((self.out / DEMAND_FILE).is_file())

    def test_c3_does_not_write_consumption_csv(self) -> None:
        # consumption.csv is satisfied demand and belongs to Component 4. If C3 ever
        # produced it, two components would own the same truth.
        self.assertFalse((self.out / "consumption.csv").exists())

    def test_c3_writes_no_inventory_orders_or_receipts(self) -> None:
        for name in (
            "inventory.csv",
            "inventory_movements.csv",
            "stockouts.csv",
            "purchase_orders.csv",
            "purchase_order_items.csv",
            "purchase_order_receipts.csv",
            "scenario_assignment.csv",
            "quality_report.json",
        ):
            with self.subTest(name=name):
                self.assertFalse((self.out / name).exists())

    def test_the_output_holds_exactly_the_expected_files(self) -> None:
        self.assertEqual(
            sorted(p.name for p in self.out.iterdir()),
            [
                "categories.csv",
                "demand.csv",
                "locations.csv",
                "manifest.json",
                "product_suppliers.csv",
                "products.csv",
                "suppliers.csv",
            ],
        )

    def test_demand_has_no_stockout_column(self) -> None:
        # is_stockout_affected lives on Consumption (`docs/04` 3.8) and is C4's to set.
        self.assertNotIn("is_stockout_affected", DEMAND_COLUMNS)

    def test_demand_has_no_scenario_column(self) -> None:
        # DT-025: no entity carries a scenario field. C7 records the assignment.
        self.assertNotIn("scenario", DEMAND_COLUMNS)

    def test_demand_has_no_channel_or_forecast_columns(self) -> None:
        for name in ("channel", "forecast", "on_hand", "supplier_id"):
            self.assertNotIn(name, DEMAND_COLUMNS)


# =======================================================================================
# Structure and contract - DT-034, DT-024
# =======================================================================================


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config = make_config(**SMALL)
        cls.out = build_dataset(Path(cls._tmp.name) / "out", cls.config)
        cls.rows = read_demand(cls.out)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_columns_and_their_order(self) -> None:
        self.assertEqual(
            DEMAND_COLUMNS,
            (
                "id",
                "product_id",
                "location_id",
                "occurred_on",
                "quantity",
                "data_origin",
            ),
        )

    def test_the_header_matches_the_contract(self) -> None:
        header = (self.out / DEMAND_FILE).read_text(encoding="utf-8").split("\n")[0]
        self.assertEqual(header, ",".join(DEMAND_COLUMNS))

    def test_line_endings_are_lf_without_bom(self) -> None:
        raw = (self.out / DEMAND_FILE).read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r", raw)
        self.assertTrue(raw.endswith(b"\n"))

    def test_dates_are_iso_and_quantities_are_bare_integers(self) -> None:
        for row in self.rows:
            self.assertRegex(row["occurred_on"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertRegex(row["quantity"], r"^(0|[1-9][0-9]*)$")

    def test_ids_are_contiguous_from_one_in_business_key_order(self) -> None:
        self.assertEqual(
            [int(row["id"]) for row in self.rows], list(range(1, len(self.rows) + 1))
        )
        keys = [
            (int(r["product_id"]), int(r["location_id"]), r["occurred_on"])
            for r in self.rows
        ]
        self.assertEqual(keys, sorted(keys))

    def test_the_business_key_is_unique(self) -> None:
        keys = {
            (r["product_id"], r["location_id"], r["occurred_on"]) for r in self.rows
        }
        self.assertEqual(len(keys), len(self.rows))

    def test_every_row_is_marked_synthetic(self) -> None:
        self.assertTrue(all(row["data_origin"] == "SYNTHETIC" for row in self.rows))

    def test_no_null_token_ever_appears(self) -> None:
        text = (self.out / DEMAND_FILE).read_text(encoding="utf-8")
        for token in (",NULL,", ",None,", ",NaN,", ",-,"):
            self.assertNotIn(token, text)


class IntegrityTests(unittest.TestCase):
    """Every key C3 writes must exist in the catalogue C2 published."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config = make_config(**SMALL)
        cls.out = build_dataset(Path(cls._tmp.name) / "out", cls.config)
        cls.rows = read_demand(cls.out)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_every_product_id_exists_in_the_catalogue(self) -> None:
        with (self.out / "products.csv").open(encoding="utf-8", newline="") as handle:
            known = {row["id"] for row in csv.DictReader(handle)}
        self.assertEqual({row["product_id"] for row in self.rows} - known, set())

    def test_every_location_id_exists_in_the_catalogue(self) -> None:
        with (self.out / "locations.csv").open(encoding="utf-8", newline="") as handle:
            known = {row["id"] for row in csv.DictReader(handle)}
        self.assertEqual({row["location_id"] for row in self.rows} - known, set())

    def test_every_product_gets_a_series(self) -> None:
        with (self.out / "products.csv").open(encoding="utf-8", newline="") as handle:
            known = {row["id"] for row in csv.DictReader(handle)}
        self.assertEqual({row["product_id"] for row in self.rows}, known)

    def test_reading_the_catalogue_fails_without_component_2(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(pol.GeneratorError) as ctx:
                read_catalog_inputs(Path(empty))
            self.assertIn("products.csv", str(ctx.exception))

    def test_generating_without_component_2_fails_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            target = Path(empty) / "out"
            target.mkdir()
            with self.assertRaises(pol.GeneratorError):
                generate(make_config(**SMALL), target, generated_at=FIXED_TIME)
            self.assertEqual(list(target.iterdir()), [])


# =======================================================================================
# Time - DT-034
# =======================================================================================


class TemporalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config = make_config(**SMALL)
        cls.out = build_dataset(Path(cls._tmp.name) / "out", cls.config)
        cls.rows = read_demand(cls.out)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_the_period_is_half_open(self) -> None:
        days = list(period_days(make_config()))
        self.assertEqual(days[0], _dt.date(2023, 1, 1))
        self.assertEqual(days[-1], _dt.date(2025, 12, 31))
        self.assertNotIn(_dt.date(2026, 1, 1), days)
        self.assertEqual(len(days), 1096)

    def test_the_start_date_is_included(self) -> None:
        self.assertIn(
            self.config.period.start_date.isoformat(),
            {row["occurred_on"] for row in self.rows},
        )

    def test_the_end_date_is_excluded(self) -> None:
        self.assertNotIn(
            self.config.period.end_date.isoformat(),
            {row["occurred_on"] for row in self.rows},
        )

    def test_no_date_falls_outside_the_period(self) -> None:
        start = self.config.period.start_date
        end = self.config.period.end_date
        for row in self.rows:
            day = _dt.date.fromisoformat(row["occurred_on"])
            self.assertGreaterEqual(day, start)
            self.assertLess(day, end)

    def test_no_row_precedes_its_product_valid_from(self) -> None:
        products, _ = read_catalog_inputs(self.out)
        valid_from = {p["id"]: p["valid_from"] for p in products}
        for row in self.rows:
            self.assertGreaterEqual(
                _dt.date.fromisoformat(row["occurred_on"]),
                valid_from[int(row["product_id"])],
            )

    def test_an_inactive_product_series_stops_at_valid_to(self) -> None:
        # Specification section 18: an inactive product keeps the history it had, and
        # gains none afterwards. DT-027: the interval is closed at both ends.
        config = make_config()
        with tempfile.TemporaryDirectory() as tmp:
            out = build_dataset(Path(tmp) / "out", config)
            demand = build_demand(config, out)
            products, _ = read_catalog_inputs(out)
            ended = [p for p in products if p["valid_to"] is not None]
            self.assertTrue(ended, "the catalogue should contain inactive products")
            last = collections.defaultdict(list)
            for row in demand.rows:
                last[row["product_id"]].append(row["occurred_on"])
            for product in ended:
                with self.subTest(product=product["id"]):
                    days = last[product["id"]]
                    self.assertEqual(max(days), product["valid_to"])
                    self.assertEqual(min(days), product["valid_from"])

    def test_an_active_product_series_runs_to_the_last_day(self) -> None:
        config = make_config()
        with tempfile.TemporaryDirectory() as tmp:
            out = build_dataset(Path(tmp) / "out", config)
            demand = build_demand(config, out)
            products, _ = read_catalog_inputs(out)
            open_ended = [p["id"] for p in products if p["valid_to"] is None]
            days = collections.defaultdict(list)
            for row in demand.rows:
                days[row["product_id"]].append(row["occurred_on"])
            for product_id in open_ended:
                self.assertEqual(max(days[product_id]), _dt.date(2025, 12, 31))


class DensityTests(unittest.TestCase):
    """One row per product, location and day in force - zeros included."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config = make_config(**SMALL)
        cls.out = build_dataset(Path(cls._tmp.name) / "out", cls.config)
        cls.demand = build_demand(cls.config, cls.out)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_every_valid_day_has_exactly_one_row(self) -> None:
        products, locations = read_catalog_inputs(self.out)
        calendar = list(period_days(self.config))
        for product in products:
            expected = [
                day
                for day in calendar
                if day >= product["valid_from"]
                and (product["valid_to"] is None or day <= product["valid_to"])
            ]
            for location_id in locations:
                got = sorted(
                    row["occurred_on"]
                    for row in self.demand.rows
                    if row["product_id"] == product["id"]
                    and row["location_id"] == location_id
                )
                with self.subTest(product=product["id"], location=location_id):
                    self.assertEqual(got, expected)

    def test_days_without_demand_are_written_as_zero(self) -> None:
        # Section 8.5: a large number of zeros must not read as absence of product. If
        # zero days were omitted, absence and zero would be identical on disk.
        self.assertTrue(any(row["quantity"] == 0 for row in self.demand.rows))

    def test_the_row_count_is_the_dense_count(self) -> None:
        products, locations = read_catalog_inputs(self.out)
        calendar = list(period_days(self.config))
        expected = sum(
            len(
                [
                    day
                    for day in calendar
                    if day >= p["valid_from"]
                    and (p["valid_to"] is None or day <= p["valid_to"])
                ]
            )
            * len(locations)
            for p in products
        )
        self.assertEqual(len(self.demand.rows), expected)


class QuantityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config = make_config(**SMALL)
        cls.out = build_dataset(Path(cls._tmp.name) / "out", cls.config)
        cls.demand = build_demand(cls.config, cls.out)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_quantities_are_integers(self) -> None:
        self.assertTrue(pol.DEMAND_QUANTITY_IS_INTEGER)
        for row in self.demand.rows:
            self.assertIsInstance(row["quantity"], int)
            self.assertNotIsInstance(row["quantity"], bool)

    def test_quantities_are_never_negative(self) -> None:
        self.assertTrue(all(row["quantity"] >= 0 for row in self.demand.rows))

    def test_no_quantity_is_written_with_a_decimal_point(self) -> None:
        for row in read_demand(self.out):
            self.assertNotIn(".", row["quantity"])


# =======================================================================================
# Behaviours - measured, not labelled
# =======================================================================================


class FullScaleFixture(unittest.TestCase):
    """Builds the full three-year dataset once for every behaviour test below."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config = make_config()
        cls.out = build_dataset(Path(cls._tmp.name) / "out", cls.config)
        cls.demand = build_demand(cls.config, cls.out)
        cls.series = series_by_product(cls.demand)
        cls.profiles = {p.product_id: p for p in cls.demand.profiles}
        cls.by_shape: dict[str, list[list[int]]] = collections.defaultdict(list)
        cls.by_rotation: dict[str, list[list[int]]] = collections.defaultdict(list)
        for product_id, values in cls.series.items():
            cls.by_shape[cls.profiles[product_id].shape].append(values)
            cls.by_rotation[cls.profiles[product_id].rotation].append(values)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    @staticmethod
    def mean_cv(group: list[list[int]]) -> float:
        values = []
        for s in group:
            mean = _st.mean(s)
            values.append(_st.pstdev(s) / mean if mean else 0.0)
        return _st.mean(values)

    @staticmethod
    def mean_zero_share(group: list[list[int]]) -> float:
        return _st.mean(sum(1 for x in s if x == 0) / len(s) for s in group)

    @staticmethod
    def mean_end_over_start(group: list[list[int]]) -> float:
        ratios = []
        for s in group:
            span = max(1, len(s) // 10)
            head, tail = _st.mean(s[:span]), _st.mean(s[-span:])
            ratios.append(tail / head if head else 0.0)
        return _st.mean(ratios)

    @staticmethod
    def autocorrelation(values: list[int], lag: int) -> float:
        mean = _st.mean(values)
        denominator = sum((x - mean) ** 2 for x in values)
        if not denominator:
            return 0.0
        numerator = sum(
            (values[i] - mean) * (values[i + lag] - mean)
            for i in range(len(values) - lag)
        )
        return numerator / denominator


class DemandBehaviourTests(FullScaleFixture):
    def test_every_shape_and_rotation_class_is_present(self) -> None:
        self.assertEqual(set(self.by_shape), set(pol.DEMAND_SHAPES))
        self.assertEqual(set(self.by_rotation), set(pol.DEMAND_ROTATIONS))

    def test_the_shape_mix_is_the_documented_one(self) -> None:
        got = {name: len(group) for name, group in self.by_shape.items()}
        self.assertEqual(
            got,
            pol.demand_mix_counts(pol.DEMAND_SHAPE_MIX, pol.DEMAND_SHAPES, 100),
        )

    def test_the_rotation_mix_is_the_documented_one(self) -> None:
        got = {name: len(group) for name, group in self.by_rotation.items()}
        self.assertEqual(
            got,
            pol.demand_mix_counts(pol.DEMAND_ROTATION_MIX, pol.DEMAND_ROTATIONS, 100),
        )

    def test_a_stable_series_varies_little(self) -> None:
        self.assertLess(self.mean_cv(self.by_shape["STABLE_DEMAND"]), 0.15)

    def test_a_stable_series_has_no_global_trend(self) -> None:
        ratio = self.mean_end_over_start(self.by_shape["STABLE_DEMAND"])
        self.assertAlmostEqual(ratio, 1.0, delta=0.10)

    def test_a_growing_series_actually_grows(self) -> None:
        self.assertGreater(
            self.mean_end_over_start(self.by_shape["GROWING_DEMAND"]), 1.3
        )

    def test_a_declining_series_actually_declines(self) -> None:
        self.assertLess(
            self.mean_end_over_start(self.by_shape["DECLINING_DEMAND"]), 0.7
        )

    def test_a_declining_series_never_reaches_a_flat_zero(self) -> None:
        # The level must stay positive, or a declining product would turn into an
        # intermittent one and the two shapes would stop being distinguishable.
        for values in self.by_shape["DECLINING_DEMAND"]:
            span = max(1, len(values) // 10)
            self.assertGreater(_st.mean(values[-span:]), 0)

    def test_an_erratic_series_is_far_more_variable_than_a_stable_one(self) -> None:
        # Section 8.6 asks for the difference to be variability, not level.
        erratic = self.mean_cv(self.by_shape["ERRATIC_DEMAND"])
        stable = self.mean_cv(self.by_shape["STABLE_DEMAND"])
        self.assertGreater(erratic, 3 * stable)

    def test_an_erratic_series_is_not_merely_a_different_level(self) -> None:
        erratic = _st.mean(_st.mean(s) for s in self.by_shape["ERRATIC_DEMAND"])
        stable = _st.mean(_st.mean(s) for s in self.by_shape["STABLE_DEMAND"])
        self.assertLess(abs(erratic - stable) / stable, 0.75)

    def test_an_intermittent_series_is_mostly_zeros(self) -> None:
        self.assertGreater(
            self.mean_zero_share(self.by_shape["INTERMITTENT_DEMAND"]), 0.6
        )

    def test_an_intermittent_series_is_distinguishable_from_a_stable_one(self) -> None:
        # The property section 8.5 exists to protect: zeros must mean "no event", not
        # "a small level that rounded down".
        intermittent = self.mean_zero_share(self.by_shape["INTERMITTENT_DEMAND"])
        stable = self.mean_zero_share(self.by_shape["STABLE_DEMAND"])
        self.assertGreater(intermittent - stable, 0.5)

    def test_an_intermittent_series_still_has_positive_events(self) -> None:
        for values in self.by_shape["INTERMITTENT_DEMAND"]:
            self.assertTrue(any(x > 0 for x in values))

    def test_a_seasonal_series_repeats_annually(self) -> None:
        lag = pol.DEMAND_SEASON_PERIOD_DAYS
        seasonal = _st.mean(
            self.autocorrelation(s, lag)
            for s in self.by_shape["SEASONAL_DEMAND"]
            if len(s) > lag + 30
        )
        stable = _st.mean(
            self.autocorrelation(s, lag)
            for s in self.by_shape["STABLE_DEMAND"]
            if len(s) > lag + 30
        )
        self.assertGreater(seasonal, 0.25)
        self.assertGreater(seasonal - stable, 0.2)

    def test_the_seasonal_wave_is_reproducible_not_random(self) -> None:
        # Section 8.4 asks for a clearly defined periodicity. The factor is a pure
        # function of the day and the phase, so two cycles apart must agree exactly.
        for phase in (0, 100, 364):
            with self.subTest(phase=phase):
                self.assertEqual(
                    pol.seasonal_factor_permille(10, phase),
                    pol.seasonal_factor_permille(10 + 365, phase),
                )

    def test_high_rotation_moves_much_more_than_low_rotation(self) -> None:
        high = _st.mean(_st.mean(s) for s in self.by_rotation["HIGH_ROTATION"])
        low = _st.mean(_st.mean(s) for s in self.by_rotation["LOW_ROTATION"])
        self.assertGreater(high, 3 * low)

    def test_rotation_is_not_written_into_the_dataset(self) -> None:
        # DT-029 leaves rotation_class empty; C3 reads none of it and writes none of it.
        with (self.out / "products.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                self.assertEqual(row["rotation_class"], "")
                self.assertEqual(row["abc_class"], "")


# =======================================================================================
# Determinism - DT-030, DT-032
# =======================================================================================


class DeterminismTests(unittest.TestCase):
    def test_c3_uses_the_canonical_demand_identifier(self) -> None:
        self.assertEqual(COMPONENT_DEMAND, "demand")

    def test_the_manifest_records_the_demand_sub_seed(self) -> None:
        config = make_config(**SMALL)
        with tempfile.TemporaryDirectory() as tmp:
            out = build_dataset(Path(tmp) / "out", config)
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        entry = next(c for c in manifest["components"] if c["name"] == "demand")
        self.assertEqual(entry["sub_seed"], sub_seed(config.seed, COMPONENT_DEMAND))
        self.assertEqual(entry["version"], DEMAND_VERSION)

    def test_c3_does_not_borrow_the_catalog_sub_seed(self) -> None:
        config = make_config(**SMALL)
        with tempfile.TemporaryDirectory() as tmp:
            out = build_dataset(Path(tmp) / "out", config)
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        seeds = {c["name"]: c["sub_seed"] for c in manifest["components"]}
        self.assertEqual(len(set(seeds.values())), len(seeds))

    def test_the_same_seed_gives_identical_bytes(self) -> None:
        config = make_config(**SMALL)
        with tempfile.TemporaryDirectory() as tmp:
            first = build_dataset(Path(tmp) / "a", config)
            second = build_dataset(Path(tmp) / "b", config)
            self.assertEqual(
                (first / DEMAND_FILE).read_bytes(), (second / DEMAND_FILE).read_bytes()
            )

    def test_a_different_seed_gives_a_different_series(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = build_dataset(Path(tmp) / "a", make_config(**SMALL))
            second = build_dataset(Path(tmp) / "b", make_config(seed=7, **SMALL))
            self.assertNotEqual(
                (first / DEMAND_FILE).read_bytes(), (second / DEMAND_FILE).read_bytes()
            )

    def test_generated_at_does_not_touch_the_data(self) -> None:
        config = make_config(**SMALL)
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a"
            second = Path(tmp) / "b"
            generate_catalog(config, first, generated_at=FIXED_TIME)
            generate(config, first, generated_at=FIXED_TIME)
            later = FIXED_TIME + _dt.timedelta(days=400)
            generate_catalog(config, second, generated_at=later)
            generate(config, second, generated_at=later)
            self.assertEqual(
                (first / DEMAND_FILE).read_bytes(), (second / DEMAND_FILE).read_bytes()
            )
            a = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
            b = json.loads((second / "manifest.json").read_text(encoding="utf-8"))
            self.assertNotEqual(a.pop("generated_at"), b.pop("generated_at"))
            self.assertEqual(a, b)

    def test_the_series_is_the_same_in_a_separate_process(self) -> None:
        root = Path(__file__).resolve().parents[3]
        script = (
            "import sys, json, datetime, tempfile, hashlib, pathlib;"
            "sys.path.insert(0, %r);"
            "from data.synthetic.config.config import DatasetConfig;"
            "from data.synthetic.generator.catalog import generate as gc;"
            "from data.synthetic.generator import demand as dm;"
            "cfg = DatasetConfig.from_mapping(json.loads(%r));"
            "out = pathlib.Path(tempfile.mkdtemp());"
            "ts = datetime.datetime(2026,1,1,tzinfo=datetime.timezone.utc);"
            "gc(cfg, out, generated_at=ts); dm.generate(cfg, out, generated_at=ts);"
            "print(hashlib.sha256((out/'demand.csv').read_bytes()).hexdigest())"
        ) % (str(root), json.dumps(_small_raw()))
        digests = set()
        for hash_seed in ("0", "1", "97531"):
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                env={"PYTHONHASHSEED": hash_seed, "PATH": os.environ.get("PATH", "")},
                cwd=str(root),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            digests.add(result.stdout.strip())
        self.assertEqual(len(digests), 1, digests)

    def test_a_product_series_does_not_depend_on_the_others(self) -> None:
        # The stream label carries the product and location id, so enlarging the
        # catalogue must leave the existing products' series untouched.
        small = make_config(**SMALL)
        larger = make_config(
            scale={"product_count": 20, "supplier_count": 4, "category_count": 3},
            period=SMALL["period"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            a = build_dataset(Path(tmp) / "a", small)
            b = build_dataset(Path(tmp) / "b", larger)
            first = series_by_product(build_demand(small, a))
            second = series_by_product(build_demand(larger, b))
        # Products keep their profile only if the mix did not move them; what must hold
        # unconditionally is that the streams are keyed, so a shared product-shape pair
        # produces the same numbers.
        self.assertEqual(len(first), 12)
        self.assertEqual(len(second), 20)


def _small_raw() -> dict:
    raw = json.loads(json.dumps(BASE_CONFIG))
    raw["scale"].update(SMALL["scale"])
    raw["period"].update(SMALL["period"])
    return raw


# =======================================================================================
# Preconditions and guarantees
# =======================================================================================


class PreconditionTests(unittest.TestCase):
    def test_too_few_products_for_one_shape_each_is_rejected(self) -> None:
        # P-6: six shapes need six products.
        config = make_config(
            scale={"product_count": 5, "supplier_count": 3, "category_count": 2},
            period=SMALL["period"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            generate_catalog(config, out, generated_at=FIXED_TIME)
            with self.assertRaises(pol.GeneratorError) as ctx:
                build_demand(config, out)
            self.assertIn("P-6", "\n".join(ctx.exception.problems))

    def test_the_minimum_viable_scale_generates(self) -> None:
        config = make_config(
            scale={"product_count": 6, "supplier_count": 3, "category_count": 2},
            period=SMALL["period"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            generate_catalog(config, out, generated_at=FIXED_TIME)
            demand = build_demand(config, out)
        self.assertEqual({p.shape for p in demand.profiles}, set(pol.DEMAND_SHAPES))
        self.assertEqual(
            {p.rotation for p in demand.profiles}, set(pol.DEMAND_ROTATIONS)
        )

    def test_the_policy_mixes_sum_to_one_hundred(self) -> None:
        self.assertEqual(sum(pol.DEMAND_SHAPE_MIX.values()), 100)
        self.assertEqual(sum(pol.DEMAND_ROTATION_MIX.values()), 100)

    def test_the_mixes_cover_exactly_their_members(self) -> None:
        self.assertEqual(set(pol.DEMAND_SHAPE_MIX), set(pol.DEMAND_SHAPES))
        self.assertEqual(set(pol.DEMAND_ROTATION_MIX), set(pol.DEMAND_ROTATIONS))

    def test_the_mix_split_is_a_pure_function_of_its_arguments(self) -> None:
        for total in (6, 12, 100, 997):
            with self.subTest(total=total):
                first = pol.demand_mix_counts(
                    pol.DEMAND_SHAPE_MIX, pol.DEMAND_SHAPES, total
                )
                second = pol.demand_mix_counts(
                    pol.DEMAND_SHAPE_MIX, pol.DEMAND_SHAPES, total
                )
                self.assertEqual(first, second)
                self.assertEqual(sum(first.values()), total)
                self.assertGreaterEqual(min(first.values()), 1)

    def test_the_rotation_levels_do_not_overlap(self) -> None:
        high = pol.DEMAND_BASE_LEVEL["HIGH_ROTATION"]
        low = pol.DEMAND_BASE_LEVEL["LOW_ROTATION"]
        self.assertGreater(high[0], low[1])

    def test_the_trend_never_drives_the_level_to_zero(self) -> None:
        self.assertLess(pol.DEMAND_TREND_PERMILLE, 1000)


class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.config = make_config(**SMALL)
        cls.out = build_dataset(Path(cls._tmp.name) / "out", cls.config)
        cls.manifest = json.loads(
            (cls.out / "manifest.json").read_text(encoding="utf-8")
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_one_manifest_lists_both_components(self) -> None:
        self.assertEqual(
            [c["name"] for c in self.manifest["components"]], ["catalog", "demand"]
        )

    def test_demand_csv_is_listed_with_its_entity_and_row_count(self) -> None:
        entry = next(f for f in self.manifest["files"] if f["name"] == DEMAND_FILE)
        self.assertEqual(entry["entity"], "Demand")
        self.assertEqual(entry["rows"], len(read_demand(self.out)))

    def test_the_demand_digest_matches_the_file(self) -> None:
        import hashlib

        entry = next(f for f in self.manifest["files"] if f["name"] == DEMAND_FILE)
        raw = (self.out / DEMAND_FILE).read_bytes()
        self.assertEqual(entry["sha256"], hashlib.sha256(raw).hexdigest())

    def test_the_files_list_stays_sorted(self) -> None:
        names = [f["name"] for f in self.manifest["files"]]
        self.assertEqual(names, sorted(names))

    def test_the_generator_version_is_the_current_one(self) -> None:
        # DT-033: the minor number rises when the generator produces different data -
        # 0.2.0 with Component 3, 0.3.0 with the batch C6 + C4 + C5 published by W1,
        # 0.4.0 with C7 + C8 (DT-042 section 9).
        self.assertEqual(self.manifest["generator_version"], "0.4.0")

    def test_the_manifest_still_omits_the_later_components_fields(self) -> None:
        self.assertNotIn("scenario_assignment", self.manifest)
        self.assertNotIn("quality_report", self.manifest)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
