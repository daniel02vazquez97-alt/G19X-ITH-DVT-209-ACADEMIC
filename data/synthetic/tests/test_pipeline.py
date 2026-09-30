"""Tests for W1: one complete run, published by promotion (`DT-040`).

Run from the repository root::

    python3 -m unittest discover -s data/synthetic/tests -t .

Every test runs the real pipeline C2 -> C3 -> C6 -> C4 -> C5 on a small configuration,
inside a temporary ``<base>/output`` + ``<base>/tmp`` layout, and inspects the directories
themselves - never an internal flag - with SHA-256 digests of every file.

Failures are provoked two ways: **real** failures of a component (a configuration that
C2, C3 or C4 rejects after earlier components already wrote) and **injected** ones
(``mock`` on a component's ``generate`` or on ``os.rename``) where no configuration can
reach the branch.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import tempfile
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from data.synthetic.generator import __main__ as cli
from data.synthetic.generator import orders, pipeline, validator
from data.synthetic.generator import policies as pol
from data.synthetic.generator.catalog import DEFAULT_OUTPUT_DIR
from data.synthetic.generator.pipeline import (
    COMPONENT_VERSIONS,
    DATASET_FILES,
    FILE_COLUMNS,
    run,
    verify,
)
from data.synthetic.generator.writer import GENERATOR_VERSION
from data.synthetic.tests.test_inventory import (
    BASE_CONFIG,
    FIXED_TIME,
    REPO_ROOT,
    SMALL,
    make_config,
)

CONFIG = make_config(**SMALL)

#: A second valid dataset, with another seed. Seed 1 was used before C8 existed; at the
#: 12-product, 59-day scale it leaves PARTIAL_DELIVERY without a manifestation, which C8
#: now rightly rejects (COV-01, DT-042). Seed 4 covers every required scenario.
OTHER_CONFIG = make_config(**SMALL, seed=4)


def digests(directory: Path) -> dict[str, str]:
    """Every file under ``directory`` (recursively) with its SHA-256; {} if absent."""
    if not directory.exists():
        return {}
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


class Layout(unittest.TestCase):
    """A fresh ``<base>/output`` and ``<base>/tmp`` for every test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name) / "synthetic"
        self.base.mkdir()
        self.output = self.base / "output"
        self.tmp_root = self.base / "tmp"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def publish(self, config=CONFIG) -> dict:
        return run(config, self.output, generated_at=FIXED_TIME)

    def assert_no_residue(self) -> None:
        # No workspace, no ``.anterior``, not even the tmp/ directory.
        self.assertFalse(self.tmp_root.exists(), list(self.tmp_root.rglob("*")))


# =======================================================================================
# A successful run
# =======================================================================================


class SuccessTests(Layout):
    def test_publishes_exactly_the_complete_dataset(self) -> None:
        manifest = self.publish()
        self.assertEqual({p.name for p in self.output.iterdir()}, set(DATASET_FILES))
        self.assertEqual(len(DATASET_FILES), 13)
        self.assertEqual(
            json.loads((self.output / "manifest.json").read_text()), manifest
        )
        self.assert_no_residue()

    def test_the_published_dataset_passes_the_final_verification(self) -> None:
        self.publish()
        manifest = verify(self.output)
        self.assertEqual(manifest["generator_version"], "0.4.0")
        self.assertEqual(GENERATOR_VERSION, "0.4.0")
        self.assertEqual(
            {c["name"]: c["version"] for c in manifest["components"]},
            COMPONENT_VERSIONS,
        )
        self.assertEqual(manifest["generated_at"], "2026-09-23T12:00:00Z")

    def test_the_manifest_is_complete(self) -> None:
        manifest = self.publish()
        self.assertEqual(
            list(manifest),
            [
                "dataset_version",
                "generator_version",
                "seed",
                "generated_at",
                "time_range",
                "data_origin",
                "config",
                "components",
                "files",
                "scenario_assignment",
                "quality_report",
            ],
        )
        self.assertEqual(
            [c["name"] for c in manifest["components"]],
            [
                "catalog",
                "demand",
                "inventory",
                "orders",
                "scenarios",
                "supplier_behaviour",
                "validator",
            ],
        )
        self.assertEqual(len(COMPONENT_VERSIONS), 7)
        self.assertEqual(len(manifest["scenario_assignment"]), 16)
        report = manifest["quality_report"]
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["validations"]["failed"], 0)
        self.assertEqual(report["anomalies"], [])

    def test_headers_are_the_contracts(self) -> None:
        self.publish()
        for name, columns in FILE_COLUMNS.items():
            header = (self.output / name).read_text(encoding="utf-8").split("\n")[0]
            self.assertEqual(header, ",".join(columns), name)

    def test_components_ran_inside_the_workspace_and_output_was_untouched(self) -> None:
        # Publish a first dataset, then watch the second run from inside C5: at that
        # point C2..C4 have written, and output/ must still be the first dataset.
        self.publish(OTHER_CONFIG)
        before = digests(self.output)
        seen = {}
        original = orders.generate

        def spy(config, directory, simulation):
            seen["directory"] = Path(directory)
            seen["output_during_run"] = digests(self.output)
            seen["workspace_files"] = sorted(p.name for p in Path(directory).iterdir())
            return original(config, directory, simulation)

        with mock.patch.object(pipeline.orders, "generate", spy):
            self.publish()
        self.assertEqual(seen["directory"].parent, self.tmp_root)
        self.assertEqual(seen["output_during_run"], before)
        self.assertIn("inventory_movements.csv", seen["workspace_files"])
        self.assert_no_residue()

    def test_replaces_the_previous_dataset_completely(self) -> None:
        # Dataset A (another seed), then dataset B: output/ must be exactly B, as if it
        # had been generated into an empty directory - no file of A survives.
        self.publish(OTHER_CONFIG)
        a = digests(self.output)
        self.publish()
        b = digests(self.output)
        with tempfile.TemporaryDirectory() as other:
            fresh = Path(other) / "output"
            run(CONFIG, fresh, generated_at=FIXED_TIME)
            self.assertEqual(b, digests(fresh))
        self.assertNotEqual(a, b)
        self.assert_no_residue()

    def test_replaces_a_partial_catalogue_only_dataset(self) -> None:
        # The dataset published before W1: C2 + C3 files only.
        run(CONFIG, self.output, generated_at=FIXED_TIME)
        for name in list(FILE_COLUMNS)[6:]:
            (self.output / name).unlink()
        self.publish()
        self.assertEqual({p.name for p in self.output.iterdir()}, set(DATASET_FILES))
        verify(self.output)


# =======================================================================================
# Determinism
# =======================================================================================


class DeterminismTests(unittest.TestCase):
    def test_two_runs_publish_the_same_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a" / "output", Path(tmp) / "b" / "output"
            run(CONFIG, a, generated_at=FIXED_TIME)
            run(CONFIG, b, generated_at=FIXED_TIME)
            self.assertEqual(digests(a), digests(b))

    def test_only_generated_at_differs_between_two_runs(self) -> None:
        later = FIXED_TIME + _dt.timedelta(days=3, hours=5)
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a" / "output", Path(tmp) / "b" / "output"
            first = run(CONFIG, a, generated_at=FIXED_TIME)
            second = run(CONFIG, b, generated_at=later)
            data_a = {k: v for k, v in digests(a).items() if k != "manifest.json"}
            data_b = {k: v for k, v in digests(b).items() if k != "manifest.json"}
            self.assertEqual(data_a, data_b)
            self.assertNotEqual(first["generated_at"], second["generated_at"])
            first.pop("generated_at"), second.pop("generated_at")
            self.assertEqual(first, second)
            self.assertEqual(
                json.dumps(first["quality_report"]),
                json.dumps(second["quality_report"]),
            )

    def test_the_execution_id_never_reaches_the_artefact(self) -> None:
        marker = uuid.UUID("0123456789abcdef0123456789abcdef")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            with mock.patch.object(pipeline.uuid, "uuid4", return_value=marker):
                run(CONFIG, output, generated_at=FIXED_TIME)
            for path in output.iterdir():
                self.assertNotIn(marker.hex.encode(), path.read_bytes(), path.name)
            other = Path(tmp) / "other" / "output"
            run(CONFIG, other, generated_at=FIXED_TIME)
            self.assertEqual(digests(output), digests(other))


# =======================================================================================
# Failures - output/ keeps exactly what it held; the workspace is gone
# =======================================================================================


class FailureTests(Layout):
    def setUp(self) -> None:
        super().setUp()
        self.publish(OTHER_CONFIG)
        self.before = digests(self.output)
        self.assertEqual(len(self.before), 13)

    def assert_untouched(self) -> None:
        self.assertEqual(digests(self.output), self.before)
        self.assert_no_residue()

    def fails(self, config=CONFIG) -> pol.GeneratorError:
        with self.assertRaises(pol.GeneratorError) as raised:
            self.publish(config)
        return raised.exception

    # --- real failures of a component -------------------------------------------------

    def test_c2_fails(self) -> None:
        # P-1: more categories than products. Nothing is written by anyone.
        self.fails(make_config(scale={"product_count": 4, "category_count": 5}))
        self.assert_untouched()

    def test_c3_fails_after_c2_wrote(self) -> None:
        # P-6 of C3: 5 products, six demand shapes. C2 accepts them and writes first.
        self.fails(
            make_config(
                scale={"product_count": 5, "supplier_count": 3, "category_count": 2},
                period=SMALL["period"],
            )
        )
        self.assert_untouched()

    def test_c4_fails_after_c2_c3_c6_wrote(self) -> None:
        # P-C4-2: a 20-day period. C2, C3 and C6 accept it; C4 refuses it.
        self.fails(
            make_config(
                scale=SMALL["scale"],
                period={"start_date": "2023-01-01", "end_date": "2023-01-21"},
            )
        )
        self.assert_untouched()

    # --- injected failures where no configuration reaches the branch -----------------

    def test_c6_fails(self) -> None:
        with mock.patch.object(
            pipeline.supplier_behaviour,
            "generate",
            side_effect=pol.GeneratorError(["C6 down"]),
        ):
            self.fails()
        self.assert_untouched()

    def test_c5_fails_after_everything_else_wrote(self) -> None:
        # The B2 situation of DT-039: the last component fails.
        with mock.patch.object(
            pipeline.orders,
            "generate",
            side_effect=pol.GeneratorError(["B2: no eligible template"]),
        ):
            self.fails()
        self.assert_untouched()

    def test_any_exception_still_cleans_the_workspace(self) -> None:
        with mock.patch.object(
            pipeline.inventory, "generate", side_effect=RuntimeError("unexpected")
        ):
            with self.assertRaises(RuntimeError):
                self.publish()
        self.assert_untouched()

    def test_c7_fails_after_c5_wrote(self) -> None:
        with mock.patch.object(
            pipeline.scenarios,
            "generate",
            side_effect=pol.GeneratorError(["C7: demand does not match"]),
        ):
            self.fails()
        self.assert_untouched()

    def test_c8_rejects_the_dataset(self) -> None:
        # A real C8 rejection: a CSV corrupted after C5, digests kept consistent, so
        # only the validator can notice. Nothing is published and the error names it.
        def corrupt(d: Path) -> None:
            path = d / "inventory.csv"
            lines = path.read_text().split("\n")
            fields = lines[1].split(",")
            fields[4] = "3"  # quantity_reserved, always 0
            lines[1] = ",".join(fields)
            path.write_text("\n".join(lines))
            manifest_path = d / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            for entry in manifest["files"]:
                if entry["name"] == "inventory.csv":
                    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest))

        with self.wrap_c5(corrupt):
            error = self.fails()
        self.assertTrue(any(p.startswith("[INV-03]") for p in error.problems))
        self.assert_untouched()

    # --- the final verification ------------------------------------------------------

    def wrap_c5(self, after):
        original = orders.generate

        def wrapped(config, directory, simulation):
            manifest = original(config, directory, simulation)
            after(Path(directory))
            return manifest

        return mock.patch.object(pipeline.orders, "generate", wrapped)

    def wrap_c8(self, after):
        """Tamper after the last component, so that only ``verify`` stands in the way."""
        original = validator.generate

        def wrapped(config, directory):
            manifest = original(config, directory)
            after(Path(directory))
            return manifest

        return mock.patch.object(pipeline.validator, "generate", wrapped)

    def test_verification_requires_a_passing_quality_report(self) -> None:
        for change in (
            lambda m: m.pop("quality_report"),
            lambda m: m.pop("scenario_assignment"),
            lambda m: m["quality_report"]["validations"].update(failed=1),
            lambda m: m["quality_report"].update(result="FAIL"),
        ):

            def tamper(d: Path, change=change) -> None:
                path = d / "manifest.json"
                manifest = json.loads(path.read_text())
                change(manifest)
                path.write_text(json.dumps(manifest))

            with self.subTest(change=change), self.wrap_c8(tamper):
                self.fails()
            self.assert_untouched()

    def test_verification_rejects_a_stray_file(self) -> None:
        with self.wrap_c8(lambda d: (d / "scratch.tmp").write_text("x")):
            error = self.fails()
        self.assertTrue(any("scratch.tmp" in p for p in error.problems))
        self.assert_untouched()

    def test_verification_rejects_altered_bytes(self) -> None:
        def tamper(d: Path) -> None:
            path = d / "purchase_orders.csv"
            path.write_text(path.read_text() + "extra\n")

        with self.wrap_c8(tamper):
            error = self.fails()
        self.assertTrue(any("sha256" in p for p in error.problems))
        self.assert_untouched()

    def test_verification_rejects_an_incomplete_manifest(self) -> None:
        def drop(d: Path) -> None:
            path = d / "manifest.json"
            manifest = json.loads(path.read_text())
            manifest["files"] = [
                f for f in manifest["files"] if f["name"] != "consumption.csv"
            ]
            manifest["components"] = manifest["components"][:-1]
            path.write_text(json.dumps(manifest))
            (d / "consumption.csv").unlink()

        with self.wrap_c8(drop):
            self.fails()
        self.assert_untouched()

    def test_verification_rejects_negative_stock(self) -> None:
        def negative(d: Path) -> None:
            path = d / "inventory_movements.csv"
            lines = path.read_text().split("\n")
            fields = lines[1].split(",")
            fields[4] = "-999999"
            lines[1] = ",".join(fields)
            path.write_text("\n".join(lines))
            # Keep the manifest consistent so only the stock rule can catch it.
            manifest_path = d / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            for entry in manifest["files"]:
                if entry["name"] == "inventory_movements.csv":
                    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest))

        with self.wrap_c8(negative):
            error = self.fails()
        self.assertTrue(any("negative stock" in p for p in error.problems))
        self.assert_untouched()

    # --- the promotion (DT-040 section 5) ---------------------------------------------

    def failing_rename(
        self, *, fail_b: bool = False, fail_c: bool = False, fail_a=False
    ):
        real = pipeline.os.rename

        def rename(src, dst):
            src, dst = Path(src), Path(dst)
            if fail_a and src == self.output:
                raise OSError("injected failure of (a)")
            if fail_b and dst == self.output and src.parent == self.tmp_root:
                if not src.name.endswith(pipeline.PREVIOUS_SUFFIX):
                    raise OSError("injected failure of (b)")
            if fail_c and src.name.endswith(pipeline.PREVIOUS_SUFFIX):
                raise OSError("injected failure of (c)")
            return real(src, dst)

        return mock.patch.object(pipeline.os, "rename", rename)

    def test_promotion_step_a_fails(self) -> None:
        with self.failing_rename(fail_a=True):
            self.fails()
        self.assert_untouched()

    def test_promotion_step_b_fails_and_the_previous_dataset_is_restored(self) -> None:
        with self.failing_rename(fail_b=True):
            error = self.fails()
        self.assertTrue(any("unchanged" in p for p in error.problems))
        self.assert_untouched()

    def test_steps_b_and_c_fail_and_the_previous_dataset_is_not_lost(self) -> None:
        # The double failure: output/ is absent, and the previous dataset is intact
        # where the error says. It is never deleted.
        with self.failing_rename(fail_b=True, fail_c=True):
            error = self.fails()
        self.assertFalse(self.output.exists())
        previous = [p for p in self.tmp_root.iterdir()]
        self.assertEqual(len(previous), 1)
        self.assertTrue(previous[0].name.endswith(pipeline.PREVIOUS_SUFFIX))
        self.assertEqual(digests(previous[0]), self.before)
        self.assertTrue(any(str(previous[0]) in p for p in error.problems))


# =======================================================================================
# The check of output/ before anything is created (DT-038 section 13)
# =======================================================================================


class OutputCheckTests(Layout):
    def test_missing_or_empty_output_is_fine(self) -> None:
        self.publish()
        self.assertTrue(self.output.is_dir())

    def test_foreign_file_stops_the_run_and_nothing_is_deleted(self) -> None:
        self.publish(OTHER_CONFIG)
        (self.output / "notes.txt").write_text("mine")
        before = digests(self.output)
        with self.assertRaises(pol.GeneratorError) as raised:
            self.publish()
        self.assertIn("notes.txt", str(raised.exception))
        self.assertEqual(digests(self.output), before)
        self.assert_no_residue()

    def test_sub_directory_stops_the_run(self) -> None:
        (self.output / "nested").mkdir(parents=True)
        with self.assertRaises(pol.GeneratorError):
            self.publish()
        self.assertTrue((self.output / "nested").is_dir())

    def test_output_that_is_a_file_stops_the_run(self) -> None:
        self.output.write_text("not a directory")
        with self.assertRaises(pol.GeneratorError):
            self.publish()
        self.assertEqual(self.output.read_text(), "not a directory")


# =======================================================================================
# The command line uses W1, and only W1
# =======================================================================================


class CommandLineTests(Layout):
    def config_file(self, **overrides) -> Path:
        raw = json.loads(json.dumps(BASE_CONFIG))
        raw["scale"].update(SMALL["scale"])
        raw["period"].update(SMALL["period"])
        for key, value in overrides.items():
            raw[key].update(value)
        path = self.base / "config.yaml"
        path.write_text(json.dumps(raw))  # JSON is valid YAML
        return path

    def main(self, *args: str) -> tuple[int, str]:
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = cli.main(list(args))
        return code, err.getvalue()

    def test_success(self) -> None:
        code, _ = self.main(
            "--config", str(self.config_file()), "--output", str(self.output)
        )
        self.assertEqual(code, 0)
        self.assertEqual({p.name for p in self.output.iterdir()}, set(DATASET_FILES))
        verify(self.output)
        self.assert_no_residue()

    def test_failure_leaves_output_intact(self) -> None:
        self.main("--config", str(self.config_file()), "--output", str(self.output))
        before = digests(self.output)
        bad = self.config_file(period={"end_date": "2023-01-21"})
        code, err = self.main("--config", str(bad), "--output", str(self.output))
        self.assertEqual(code, 1)
        self.assertIn("P-C4-2", err)
        self.assertEqual(digests(self.output), before)
        self.assert_no_residue()

    def test_the_command_line_calls_no_component_directly(self) -> None:
        import inspect

        source = inspect.getsource(cli)
        self.assertIn("pipeline.run", source)
        for name in ("catalog", "demand", "supplier_behaviour", "inventory", "orders"):
            self.assertNotIn(f"{name}.generate", source)
            self.assertNotIn(f"import {name}", source)


class RepositoryOutputTests(unittest.TestCase):
    def test_the_suite_never_touches_the_repository_output(self) -> None:
        before = digests(REPO_ROOT / DEFAULT_OUTPUT_DIR)
        with tempfile.TemporaryDirectory() as tmp:
            run(CONFIG, Path(tmp) / "output", generated_at=FIXED_TIME)
        self.assertEqual(digests(REPO_ROOT / DEFAULT_OUTPUT_DIR), before)
        self.assertFalse(
            (REPO_ROOT / DEFAULT_OUTPUT_DIR).parent.joinpath("tmp").exists()
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


# =======================================================================================
# R2 and R3 of DT-033, end to end: generate -> workspace -> C7 -> C8 -> verify -> promote
# =======================================================================================


class ReferenceEndToEndTests(unittest.TestCase):
    CONFIGS = {
        "R2": SMALL,
        "R3": {
            "scale": {
                "product_count": 1200,
                "supplier_count": 10,
                "category_count": 1000,
            },
            "period": SMALL["period"],
        },
    }

    def test_published_and_validated(self) -> None:
        for name, overrides in self.CONFIGS.items():
            with self.subTest(config=name), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "synthetic" / "output"
                config = make_config(**overrides)
                manifest = run(config, output, generated_at=FIXED_TIME)
                self.assertEqual(verify(output), manifest)
                self.assertFalse((output.parent / "tmp").exists())
                report = manifest["quality_report"]
                self.assertEqual(
                    (
                        report["validations"]["executed"],
                        report["validations"]["failed"],
                    ),
                    (51, 0),
                )
                self.assertTrue(
                    all(e["covered"] for e in report["scenario_distribution"].values())
                )
                self.assertTrue(
                    all(
                        x["products"] > 0
                        for x in report["validations"]["level_c"].values()
                    )
                )
