"""Tests for Component 6: the Supplier Behaviour Generator.

Run from the repository root::

    python3 -m unittest discover -s data/synthetic/tests -t .

Standard library ``unittest``, like the other components (`docs/13-testing.md`).

Scope: `DT-037` - one deterministic profile per supplier on two orthogonal axes, the
mixes with a floor of one, the two assignment streams, precondition P-C6-1, no data
file, and the component's entry in ``manifest.components`` (decision A1). Then the
pipeline in its approved order, C2 -> C3 -> **C6** -> C4 -> C5, checked with the
independent audits of Components 4 and 5.

The table of `DT-037` section 2 and the split of `DT-028` section 3.2 are written out here
as literals and as an independent oracle: the tests do not read the values they check
from the module under test.
"""

from __future__ import annotations

import ast
import collections
import inspect
import json
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

from data.synthetic.generator import policies as pol
from data.synthetic.generator import supplier_behaviour as sb
from data.synthetic.generator.catalog import DEFAULT_OUTPUT_DIR
from data.synthetic.generator.inventory import SupplierProfile
from data.synthetic.generator.inventory import generate as generate_inventory
from data.synthetic.generator.orders import generate as generate_orders
from data.synthetic.generator.rng import (
    COMPONENT_SUPPLIER_BEHAVIOUR,
    DeterministicRandom,
    sub_seed,
)
from data.synthetic.generator.supplier_behaviour import (
    build_supplier_profiles,
    generate,
)
from data.synthetic.generator.writer import (
    GENERATOR_VERSION,
    SUPPLIER_BEHAVIOUR_VERSION,
    build_manifest,
    write_manifest,
)
from data.synthetic.tests import test_inventory as c4_tests
from data.synthetic.tests import test_orders as c5_tests
from data.synthetic.tests.test_inventory import (
    FIXED_TIME,
    REPO_ROOT,
    SMALL,
    build_pipeline,
    make_config,
    read_rows,
    tree_digest,
)

CONFIG = make_config(**SMALL)

#: `DT-037` section 2, written out.
PUNCTUALITY = {
    "PUNCTUAL": (900, (1, 3)),
    "IRREGULAR": (650, (1, 7)),
    "LATE": (250, (3, 14)),
}
INTEGRITY = {
    "COMPLETE": (0, None, None),
    "SPLIT": (250, (400, 800), (1, 10)),
}
PUNCTUALITY_MIX = (("PUNCTUAL", 40), ("IRREGULAR", 40), ("LATE", 20))
INTEGRITY_MIX = (("COMPLETE", 70), ("SPLIT", 30))


def oracle_split(mix: tuple[tuple[str, int], ...], total: int) -> dict[str, int]:
    """Largest remainder with a floor of one, as `DT-028` section 3.2 describes it.

    Exact fractions; ties to the lower index; the donor of each floor transfer is the
    current maximum, recomputed every time. Written independently of ``policies.py``.
    """
    exact = [Fraction(share * total, 100) for _, share in mix]
    counts = [value.numerator // value.denominator for value in exact]
    remainders = [value - count for value, count in zip(exact, counts)]
    for index in sorted(range(len(mix)), key=lambda i: (-remainders[i], i))[
        : total - sum(counts)
    ]:
        counts[index] += 1
    while min(counts) < 1:
        smallest = counts.index(min(counts))
        donor = counts.index(max(counts))
        counts[donor] -= 1
        counts[smallest] += 1
    return {name: counts[i] for i, (name, _) in enumerate(mix)}


def workspace(
    tmp: str,
    suppliers: list[tuple[int, bool]],
    *,
    name: str = "work",
    manifest: bool = True,
) -> Path:
    """A ``suppliers.csv`` - rows in the order given - and, optionally, a manifest."""
    directory = Path(tmp) / name
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "suppliers.csv").open("w", encoding="utf-8", newline="") as h:
        h.write("id,code,is_active\n")
        for supplier_id, active in suppliers:
            h.write(f"{supplier_id},SUP-{supplier_id:03d},{str(active).lower()}\n")
    if manifest:
        write_manifest(
            directory / "manifest.json",
            build_manifest(
                config=CONFIG, generated_at=FIXED_TIME, components=[], files=[]
            ),
        )
    return directory


def active(count: int) -> list[tuple[int, bool]]:
    return [(i, True) for i in range(1, count + 1)]


# =======================================================================================
# Rules - DT-037 section 2
# =======================================================================================


class ParameterTests(unittest.TestCase):
    def test_policy_tables_are_dt037(self) -> None:
        self.assertEqual(pol.SUPPLIER_PUNCTUALITY_PROFILES, tuple(PUNCTUALITY))
        self.assertEqual(pol.SUPPLIER_INTEGRITY_PROFILES, tuple(INTEGRITY))
        self.assertEqual(pol.SUPPLIER_PUNCTUALITY_MIX, dict(PUNCTUALITY_MIX))
        self.assertEqual(pol.SUPPLIER_INTEGRITY_MIX, dict(INTEGRITY_MIX))
        self.assertEqual(pol.SUPPLIER_BEHAVIOUR_MIN_SUPPLIERS, 3)

    def test_versions(self) -> None:
        self.assertEqual(SUPPLIER_BEHAVIOUR_VERSION, "0.1.0")
        # One bump for the batch C6 + C4 + C5 (DT-036 section 8), applied with W1.
        self.assertEqual(GENERATOR_VERSION, "0.4.0")


class ProfileValueTests(unittest.TestCase):
    """Every generated profile carries exactly the constants of its two profiles."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.profiles = build_supplier_profiles(
            CONFIG, workspace(cls._tmp.name, active(40))
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def check(self, punctuality: str) -> None:
        on_time, delay = PUNCTUALITY[punctuality]
        chosen = [p for p in self.profiles if p.punctuality == punctuality]
        self.assertTrue(chosen)
        for profile in chosen:
            self.assertEqual(
                (profile.on_time_permille, profile.delay_days), (on_time, delay)
            )

    def check_integrity(self, integrity: str) -> None:
        partial, split, lag = INTEGRITY[integrity]
        chosen = [p for p in self.profiles if p.integrity == integrity]
        self.assertTrue(chosen)
        for profile in chosen:
            self.assertEqual(
                (
                    profile.partial_permille,
                    profile.split_range,
                    profile.completion_lag_days,
                ),
                (partial, split, lag),
            )

    def test_punctual(self) -> None:
        self.check("PUNCTUAL")

    def test_irregular(self) -> None:
        self.check("IRREGULAR")

    def test_late(self) -> None:
        self.check("LATE")

    def test_complete_has_null_split_fields(self) -> None:
        self.check_integrity("COMPLETE")
        for profile in self.profiles:
            if profile.integrity == "COMPLETE":
                self.assertIsNone(profile.split_range)
                self.assertIsNone(profile.completion_lag_days)

    def test_split(self) -> None:
        self.check_integrity("SPLIT")

    def test_every_combination_exists_at_scale(self) -> None:
        combos = {(p.punctuality, p.integrity) for p in self.profiles}
        self.assertEqual(combos, {(a, b) for a in PUNCTUALITY for b in INTEGRITY})

    def test_values_are_constants_not_draws(self) -> None:
        # Two suppliers of the same profile are indistinguishable except for their id.
        by_profile = collections.defaultdict(set)
        for p in self.profiles:
            by_profile[(p.punctuality, p.integrity)].add(
                (
                    p.on_time_permille,
                    p.delay_days,
                    p.partial_permille,
                    p.split_range,
                    p.completion_lag_days,
                )
            )
        self.assertTrue(all(len(values) == 1 for values in by_profile.values()))


# =======================================================================================
# Split - DT-028 section 3.2, against an independent oracle
# =======================================================================================


class SplitTests(unittest.TestCase):
    def counts(self, n: int) -> tuple[dict[str, int], dict[str, int]]:
        with tempfile.TemporaryDirectory() as tmp:
            profiles = build_supplier_profiles(CONFIG, workspace(tmp, active(n)))
        return (
            dict(collections.Counter(p.punctuality for p in profiles)),
            dict(collections.Counter(p.integrity for p in profiles)),
        )

    def test_three_suppliers(self) -> None:
        self.assertEqual(
            self.counts(3),
            ({"PUNCTUAL": 1, "IRREGULAR": 1, "LATE": 1}, {"COMPLETE": 2, "SPLIT": 1}),
        )

    def test_ten_suppliers(self) -> None:
        self.assertEqual(
            self.counts(10),
            ({"PUNCTUAL": 4, "IRREGULAR": 4, "LATE": 2}, {"COMPLETE": 7, "SPLIT": 3}),
        )

    def test_119_suppliers(self) -> None:
        punctuality, integrity = self.counts(119)
        self.assertEqual(punctuality, oracle_split(PUNCTUALITY_MIX, 119))
        self.assertEqual(integrity, oracle_split(INTEGRITY_MIX, 119))

    def test_every_admissible_scale_matches_the_oracle(self) -> None:
        # The admissible range of the catalogue is supplier_count in [3, 119] (DT-028).
        for n in range(3, 120):
            with self.subTest(n=n):
                punctuality, integrity = self.counts(n)
                self.assertEqual(punctuality, oracle_split(PUNCTUALITY_MIX, n))
                self.assertEqual(integrity, oracle_split(INTEGRITY_MIX, n))
                self.assertEqual(len(punctuality), 3)  # floor of one
                self.assertEqual(len(integrity), 2)

    def test_oracle_sanity(self) -> None:
        self.assertEqual(
            oracle_split(PUNCTUALITY_MIX, 10),
            {"PUNCTUAL": 4, "IRREGULAR": 4, "LATE": 2},
        )
        self.assertEqual(
            oracle_split(PUNCTUALITY_MIX, 4), {"PUNCTUAL": 2, "IRREGULAR": 1, "LATE": 1}
        )


# =======================================================================================
# Coverage, precondition and integrity
# =======================================================================================


class CoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_one_profile_per_supplier_including_inactive(self) -> None:
        suppliers = [(7, True), (2, False), (5, True), (9, False), (1, True)]
        profiles = build_supplier_profiles(CONFIG, workspace(self.tmp, suppliers))
        self.assertEqual([p.supplier_id for p in profiles], [1, 2, 5, 7, 9])
        self.assertIsInstance(profiles, tuple)
        self.assertTrue(all(isinstance(p, SupplierProfile) for p in profiles))

    def test_inactivity_does_not_change_the_assignment(self) -> None:
        a = build_supplier_profiles(CONFIG, workspace(self.tmp, active(6), name="a"))
        b = build_supplier_profiles(
            CONFIG,
            workspace(self.tmp, [(i, i % 2 == 0) for i in range(1, 7)], name="b"),
        )
        self.assertEqual(a, b)

    def test_row_order_of_the_file_does_not_matter(self) -> None:
        a = build_supplier_profiles(CONFIG, workspace(self.tmp, active(8), name="a"))
        b = build_supplier_profiles(
            CONFIG, workspace(self.tmp, list(reversed(active(8))), name="b")
        )
        self.assertEqual(a, b)

    def test_duplicated_supplier_is_refused(self) -> None:
        with self.assertRaises(pol.GeneratorError):
            build_supplier_profiles(
                CONFIG,
                workspace(self.tmp, [(1, True), (2, True), (2, True), (3, True)]),
            )

    def test_every_profile_passes_component_4s_validation(self) -> None:
        for n in (3, 4, 10, 57, 119):
            with self.subTest(n=n):
                profiles = build_supplier_profiles(
                    CONFIG, workspace(self.tmp, active(n), name=f"n{n}")
                )
                self.assertEqual([q for p in profiles for q in p.problems()], [])


class PreconditionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_two_suppliers_fail(self) -> None:
        with self.assertRaises(pol.GeneratorError) as raised:
            build_supplier_profiles(CONFIG, workspace(self.tmp, active(2)))
        self.assertTrue(any(p.startswith("P-C6-1") for p in raised.exception.problems))

    def test_no_supplier_fails(self) -> None:
        with self.assertRaises(pol.GeneratorError):
            build_supplier_profiles(CONFIG, workspace(self.tmp, []))

    def test_three_suppliers_pass(self) -> None:
        self.assertEqual(
            len(build_supplier_profiles(CONFIG, workspace(self.tmp, active(3)))), 3
        )

    def test_missing_file_fails(self) -> None:
        with self.assertRaises(pol.GeneratorError):
            build_supplier_profiles(CONFIG, Path(self.tmp))

    def test_a_failed_precondition_writes_nothing(self) -> None:
        work = workspace(self.tmp, active(2))
        before = tree_digest(work)
        with self.assertRaises(pol.GeneratorError):
            generate(CONFIG, work)
        self.assertEqual(tree_digest(work), before)


# =======================================================================================
# Determinism - DT-030, DT-032, DT-037 section 4
# =======================================================================================


class DeterminismTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.work = workspace(self._tmp.name, active(10))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def config(self, seed: int):
        return make_config(**SMALL, seed=seed)

    def test_same_seed_same_profiles(self) -> None:
        self.assertEqual(
            build_supplier_profiles(CONFIG, self.work),
            build_supplier_profiles(CONFIG, self.work),
        )

    def test_the_seed_drives_the_assignment(self) -> None:
        results = {build_supplier_profiles(self.config(s), self.work) for s in range(6)}
        self.assertGreater(len(results), 1)

    def test_assignment_follows_the_documented_streams(self) -> None:
        # Recompute DT-037 section 4 from the labels: sub_seed(seed, "supplier_behaviour"),
        # one permutation per axis, applied to the suppliers ordered by id.
        for seed in (0, 7, 20260913):
            with self.subTest(seed=seed):
                base = sub_seed(seed, "supplier_behaviour")
                p_slots = [
                    n
                    for n, c in oracle_split(PUNCTUALITY_MIX, 10).items()
                    for _ in range(c)
                ]
                i_slots = [
                    n
                    for n, c in oracle_split(INTEGRITY_MIX, 10).items()
                    for _ in range(c)
                ]
                p_order = DeterministicRandom(
                    base, "punctuality-assignment"
                ).permutation(10)
                i_order = DeterministicRandom(base, "integrity-assignment").permutation(
                    10
                )
                expected = [
                    (i + 1, p_slots[p_order[i]], i_slots[i_order[i]]) for i in range(10)
                ]
                got = [
                    (p.supplier_id, p.punctuality, p.integrity)
                    for p in build_supplier_profiles(self.config(seed), self.work)
                ]
                self.assertEqual(got, expected)

    def test_axes_are_independent(self) -> None:
        reference = build_supplier_profiles(CONFIG, self.work)
        with mock.patch.dict(pol.SUPPLIER_INTEGRITY_MIX, {"COMPLETE": 50, "SPLIT": 50}):
            other = build_supplier_profiles(CONFIG, self.work)
        self.assertEqual(
            [p.punctuality for p in reference], [p.punctuality for p in other]
        )
        self.assertNotEqual(
            [p.integrity for p in reference], [p.integrity for p in other]
        )
        with mock.patch.dict(
            pol.SUPPLIER_PUNCTUALITY_MIX, {"PUNCTUAL": 20, "IRREGULAR": 40, "LATE": 40}
        ):
            other = build_supplier_profiles(CONFIG, self.work)
        self.assertEqual([p.integrity for p in reference], [p.integrity for p in other])
        self.assertNotEqual(
            [p.punctuality for p in reference], [p.punctuality for p in other]
        )

    def test_exactly_two_streams_and_no_other_randomness(self) -> None:
        source = inspect.getsource(sb)
        tree = ast.parse(source)
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "DeterministicRandom"
        ]
        self.assertEqual(len(calls), 2)
        self.assertEqual(sb.PUNCTUALITY_STREAM, "punctuality-assignment")
        self.assertEqual(sb.INTEGRITY_STREAM, "integrity-assignment")
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("random", imported)


# =======================================================================================
# Manifest and files - DT-037 section 1, decision A1
# =======================================================================================


class ManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.work = workspace(self._tmp.name, active(10))
        self.before = tree_digest(self.work)
        self.manifest_before = json.loads((self.work / "manifest.json").read_text())
        self.manifest, self.profiles = generate(CONFIG, self.work)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_component_entry(self) -> None:
        self.assertEqual(
            self.manifest["components"],
            [
                {
                    "name": COMPONENT_SUPPLIER_BEHAVIOUR,
                    "version": SUPPLIER_BEHAVIOUR_VERSION,
                    "sub_seed": sub_seed(CONFIG.seed, COMPONENT_SUPPLIER_BEHAVIOUR),
                }
            ],
        )
        self.assertEqual(COMPONENT_SUPPLIER_BEHAVIOUR, "supplier_behaviour")

    def test_zero_files(self) -> None:
        self.assertEqual(self.manifest["files"], self.manifest_before["files"])

    def test_only_the_manifest_changes(self) -> None:
        after = tree_digest(self.work)
        self.assertEqual(sorted(after), sorted(self.before))
        changed = [name for name in after if after[name] != self.before[name]]
        self.assertEqual(changed, ["manifest.json"])
        self.assertEqual(
            json.loads((self.work / "manifest.json").read_text()), self.manifest
        )

    def test_returns_the_same_profiles_as_build(self) -> None:
        self.assertEqual(self.profiles, build_supplier_profiles(CONFIG, self.work))

    def test_a_second_run_writes_nothing(self) -> None:
        snapshot = tree_digest(self.work)
        with self.assertRaises(ValueError):
            generate(CONFIG, self.work)
        self.assertEqual(tree_digest(self.work), snapshot)

    def test_missing_manifest_writes_nothing(self) -> None:
        work = workspace(self._tmp.name, active(5), name="nomanifest", manifest=False)
        before = tree_digest(work)
        with self.assertRaises(pol.GeneratorError):
            generate(CONFIG, work)
        self.assertEqual(tree_digest(work), before)


class BoundaryTests(unittest.TestCase):
    """C6 uses Component 4's type and nothing else of it; it is reached only through W1."""

    def test_only_the_supplier_profile_type_comes_from_component_4(self) -> None:
        tree = ast.parse(inspect.getsource(sb))
        from_inventory = [
            alias.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "inventory"
            for alias in node.names
        ]
        self.assertEqual(from_inventory, ["SupplierProfile"])
        self.assertIs(sb.SupplierProfile, SupplierProfile)

    def test_no_default_output_and_reached_only_through_w1(self) -> None:
        signature = inspect.signature(generate)
        self.assertIs(
            signature.parameters["output_dir"].default, inspect.Parameter.empty
        )
        self.assertNotIn("DEFAULT_OUTPUT_DIR", inspect.getsource(sb))
        from data.synthetic.generator import __main__ as cli
        from data.synthetic.generator import pipeline

        self.assertNotIn("supplier_behaviour", inspect.getsource(cli))
        self.assertIn("supplier_behaviour.generate", inspect.getsource(pipeline))


# =======================================================================================
# The pipeline in its approved order: C2 -> C3 -> C6 -> C4 -> C5
# =======================================================================================


def run_pipeline(directory: Path, config):
    build_pipeline(directory, config)
    _, profiles = generate(config, directory)
    _, simulation = generate_inventory(config, directory, profiles)
    manifest = generate_orders(config, directory, simulation)
    return profiles, simulation, manifest


class PipelineTests(unittest.TestCase):
    def check(self, config) -> None:
        output_before = tree_digest(REPO_ROOT / DEFAULT_OUTPUT_DIR)
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "work"
            profiles, simulation, manifest = run_pipeline(work, config)
            suppliers = [int(r["id"]) for r in read_rows(work, "suppliers.csv")]
            self.assertEqual([p.supplier_id for p in profiles], sorted(suppliers))
            self.assertEqual(c4_tests.audit(work, config, simulation)[:20], [])
            self.assertEqual(c5_tests.audit(work, config, simulation), [])
            self.assertEqual(
                sorted(c["name"] for c in manifest["components"]),
                ["catalog", "demand", "inventory", "orders", "supplier_behaviour"],
            )
            listed = {f["name"] for f in manifest["files"]} | {"manifest.json"}
            self.assertEqual(set(tree_digest(work)), listed)
            self.assertNotIn("supplier_behaviour.csv", listed)
            self.assertEqual(manifest["generator_version"], "0.4.0")
            # The receipts reflect the profiles: C4 applied what C6 gave it.
            profile_of = {p.supplier_id: p for p in profiles}
            for order in simulation.orders:
                if len(order.receipts) == 2:
                    self.assertEqual(profile_of[order.supplier_id].integrity, "SPLIT")
                for receipt in order.receipts[:1]:
                    if receipt.received_on > order.expected_on:
                        self.assertLess(
                            profile_of[order.supplier_id].on_time_permille, 1000
                        )
        self.assertEqual(tree_digest(REPO_ROOT / DEFAULT_OUTPUT_DIR), output_before)
        return profiles

    def test_small(self) -> None:
        self.check(make_config(**SMALL))

    def test_full_scale(self) -> None:
        profiles = self.check(make_config())
        self.assertEqual(
            dict(collections.Counter(p.punctuality for p in profiles)),
            {"PUNCTUAL": 4, "IRREGULAR": 4, "LATE": 2},
        )
        self.assertEqual(
            dict(collections.Counter(p.integrity for p in profiles)),
            {"COMPLETE": 7, "SPLIT": 3},
        )

    def test_pipeline_is_deterministic(self) -> None:
        config = make_config(**SMALL)
        with tempfile.TemporaryDirectory() as tmp:
            run_pipeline(Path(tmp) / "a", config)
            run_pipeline(Path(tmp) / "b", config)
            self.assertEqual(tree_digest(Path(tmp) / "a"), tree_digest(Path(tmp) / "b"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
