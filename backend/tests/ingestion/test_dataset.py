"""Pre-validation without database (step 3 of `docs/04` §9.5), on the dataset and altered copies."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from app.ingestion import contract
from app.ingestion.dataset import ManifestError, read_dataset, read_identity

from ._support import (
    DATASET_AVAILABLE,
    DATASET_DIR,
    SKIP_REASON,
    copy_dataset,
    edit_manifest,
    read_manifest,
    refresh_entry,
    rewrite_csv,
    set_field,
)


def _messages(errors: list) -> list[str]:
    return [str(e) for e in errors]


@unittest.skipUnless(DATASET_AVAILABLE, SKIP_REASON)
class PublishedDatasetTest(unittest.TestCase):
    def test_published_dataset_passes_prevalidation(self) -> None:
        dataset, errors = read_dataset(DATASET_DIR)
        self.assertEqual(errors, [])
        manifest = read_manifest(DATASET_DIR)
        declared = {e["name"]: e["rows"] for e in manifest["files"]}
        self.assertEqual(list(dataset.rows), list(contract.FILES))
        for name, rows in dataset.rows.items():
            self.assertEqual(len(rows), declared[name], name)
        self.assertEqual(
            dataset.manifest_sha256, hashlib.sha256((DATASET_DIR / "manifest.json").read_bytes()).hexdigest()
        )

    def test_identity_holds_version_and_on_disk_sha256(self) -> None:
        identity = read_identity(DATASET_DIR)
        self.assertEqual(identity.dataset_version, "ds-6c8ad65b4999")
        manifest = read_manifest(DATASET_DIR)
        self.assertEqual(identity.file_sha256, {e["name"]: e["sha256"] for e in manifest["files"]})


@unittest.skipUnless(DATASET_AVAILABLE, SKIP_REASON)
class AlteredCopyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.handle, self.dir = copy_dataset()
        self.addCleanup(self.handle.cleanup)

    def assertRejected(self, fragment: str, file: str | None = None) -> list:
        dataset, errors = read_dataset(self.dir)
        self.assertIsNone(dataset)
        matching = [e for e in errors if fragment in e.message and (file is None or e.file == file)]
        self.assertTrue(matching, f"{fragment!r} not in {_messages(errors)}")
        return errors

    def test_unaltered_copy_passes(self) -> None:
        self.assertEqual(read_dataset(self.dir)[1], [])

    def test_sha256_mismatch(self) -> None:
        rewrite_csv(self.dir, "suppliers.csv", lambda r: set_field(r, "1", "name", "Changed"), update_manifest=False)
        self.assertRejected("sha256 differs", "suppliers.csv")

    def test_missing_file(self) -> None:
        (self.dir / "consumption.csv").unlink()
        self.assertRejected("does not exist", "consumption.csv")

    def test_unlisted_file(self) -> None:
        (self.dir / "extra.csv").write_text("id\n", encoding="utf-8")
        self.assertRejected("not listed in the manifest", "extra.csv")

    def test_file_missing_from_manifest(self) -> None:
        edit_manifest(self.dir, lambda m: m.update(files=[e for e in m["files"] if e["name"] != "demand.csv"]))
        errors = self.assertRejected("does not list demand.csv", "manifest.json")
        self.assertIn("demand.csv: file is not listed in the manifest", _messages(errors))

    def test_header_differs_from_contract(self) -> None:
        def rename(records: list[list[str]]) -> None:
            records[0][1] = "sku_code"

        rewrite_csv(self.dir, "products.csv", rename)
        self.assertRejected("differs from the contract", "products.csv")

    def test_column_order_differs_from_contract(self) -> None:
        def swap(records: list[list[str]]) -> None:
            for record in records:
                record[1], record[2] = record[2], record[1]

        rewrite_csv(self.dir, "locations.csv", swap)
        self.assertRejected("differs from the contract", "locations.csv")

    def test_row_count_differs_from_manifest(self) -> None:
        def drop_last(records: list[list[str]]) -> None:
            records.pop()

        rewrite_csv(self.dir, "inventory.csv", drop_last)
        edit_manifest(self.dir, lambda m: [e.update(rows=100) for e in m["files"] if e["name"] == "inventory.csv"])
        self.assertRejected("99 rows, the manifest declares 100", "inventory.csv")

    def test_quality_report_not_pass(self) -> None:
        def fail(manifest: dict) -> None:
            manifest["quality_report"]["result"] = "FAIL"
            manifest["quality_report"]["validations"]["failed"] = 1

        edit_manifest(self.dir, fail)
        errors = self.assertRejected("quality_report.result is not PASS")
        self.assertIn("failed = 0", " ".join(_messages(errors)))

    def test_manifest_field_missing_and_unexpected(self) -> None:
        def change(manifest: dict) -> None:
            del manifest["seed"]
            manifest["comment"] = "x"

        edit_manifest(self.dir, change)
        self.assertRejected("missing fields: seed")
        self.assertRejected("unexpected fields: comment")

    def test_invalid_data_origin_and_time_range(self) -> None:
        def change(manifest: dict) -> None:
            manifest["data_origin"] = "MIXED"
            manifest["time_range"] = {"start_date": "2026-01-01", "end_date": "2023-01-01"}

        edit_manifest(self.dir, change)
        self.assertRejected("data_origin must be SYNTHETIC or REAL")
        self.assertRejected("time_range")

    def test_bom_and_crlf(self) -> None:
        path = self.dir / "categories.csv"
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes().replace(b"\n", b"\r\n"))
        refresh_entry(self.dir, "categories.csv")
        self.assertRejected("BOM", "categories.csv")
        self.assertRejected("LF", "categories.csv")

    def test_wrong_number_of_fields(self) -> None:
        def widen(records: list[list[str]]) -> None:
            records[3].append("extra")

        rewrite_csv(self.dir, "categories.csv", widen)
        errors = self.assertRejected("7 fields, expected 6", "categories.csv")
        self.assertEqual([e.line for e in errors if e.file == "categories.csv"], [4])

    def test_errors_are_accumulated(self) -> None:
        (self.dir / "demand.csv").unlink()
        rewrite_csv(self.dir, "suppliers.csv", lambda r: set_field(r, "1", "name", "X"), update_manifest=False)
        edit_manifest(self.dir, lambda m: m["quality_report"].update(result="FAIL"))
        errors = read_dataset(self.dir)[1]
        files = {e.file for e in errors}
        self.assertTrue({"demand.csv", "suppliers.csv", "manifest.json"} <= files, _messages(errors))

    def test_unreadable_manifest(self) -> None:
        (self.dir / "manifest.json").write_text("{not json", encoding="utf-8")
        with self.assertRaises(ManifestError):
            read_identity(self.dir)
        dataset, errors = read_dataset(self.dir)
        self.assertIsNone(dataset)
        self.assertIn("not valid UTF-8 JSON", errors[0].message)

    def test_manifest_without_dataset_version(self) -> None:
        edit_manifest(self.dir, lambda m: m.pop("dataset_version"))
        with self.assertRaises(ManifestError):
            read_identity(self.dir)

    def test_missing_directory(self) -> None:
        dataset, errors = read_dataset(Path(self.dir) / "nowhere")
        self.assertIsNone(dataset)
        self.assertIn("cannot be read", errors[0].message)


if __name__ == "__main__":
    unittest.main()
