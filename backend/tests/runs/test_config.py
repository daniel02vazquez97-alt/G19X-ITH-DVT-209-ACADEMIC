"""Configuration identity of a forecast execution (`DT-057` point 3), without PostgreSQL."""

from __future__ import annotations

import ast
import datetime as dt
import hashlib
import unittest
from pathlib import Path

import app.runs.config as config_module
from app.forecasting import BASELINES, MOVING_AVERAGE
from app.runs.config import (
    CATALOG_POLICY,
    canonical_json,
    config_sha256,
    lock_key,
    run_configuration,
)

A = dt.date(2025, 12, 31)


class CanonicalJsonTest(unittest.TestCase):
    def test_sorted_compact_and_utf8(self) -> None:
        self.assertEqual(canonical_json({"b": 1, "a": ["ñ", 2]}), '{"a":["ñ",2],"b":1}')


class RunConfigurationTest(unittest.TestCase):
    def test_contains_everything_that_determines_the_output(self) -> None:
        configuration = run_configuration()
        self.assertEqual(
            [(m["name"], m["version"], m["algorithm"]) for m in configuration["models"]],
            [(d.name, d.version, d.algorithm) for d in BASELINES],
        )
        self.assertEqual([m["hyperparameters"] for m in configuration["models"]], [d.hyperparameters for d in BASELINES])
        self.assertEqual(configuration["reference"], {"name": MOVING_AVERAGE.name, "version": "1.0.0"})
        self.assertEqual(configuration["primary_chain"], ["baseline.moving_average", "baseline.naive"])
        self.assertEqual(configuration["horizon_weeks"], 14)
        self.assertEqual(configuration["quantization"], {"scale": 6, "rounding": "ROUND_HALF_EVEN"})
        self.assertEqual(configuration["catalog_policy"], CATALOG_POLICY)
        self.assertEqual(configuration["confidence_level"], "0.80")

    def test_sha256_is_deterministic_and_of_the_canonical_json(self) -> None:
        expected = hashlib.sha256(canonical_json(run_configuration()).encode("utf-8")).hexdigest()
        self.assertEqual(config_sha256(), expected)
        self.assertEqual(config_sha256(), config_sha256(run_configuration()))
        self.assertRegex(config_sha256(), r"^[0-9a-f]{64}$")

    def test_any_change_of_definition_changes_the_sha256(self) -> None:
        changed = run_configuration()
        changed["models"][2]["hyperparameters"]["window_weeks"] = 8
        self.assertNotEqual(config_sha256(changed), config_sha256())
        changed = run_configuration()
        changed["models"][0]["version"] = "1.0.1"
        self.assertNotEqual(config_sha256(changed), config_sha256())

    def test_no_timestamp_or_id_enters_the_configuration(self) -> None:
        text = canonical_json(run_configuration())
        self.assertNotIn(str(dt.date.today().year) + "-", text)
        self.assertNotIn("_id", text)


class LockKeyTest(unittest.TestCase):
    def test_deterministic_signed_64_bit_and_identity_dependent(self) -> None:
        sha = config_sha256()
        key = lock_key(A, 1, sha)
        self.assertEqual(key, lock_key(A, 1, sha))
        self.assertTrue(-(2**63) <= key < 2**63)
        self.assertNotEqual(key, lock_key(A - dt.timedelta(days=1), 1, sha))
        self.assertNotEqual(key, lock_key(A, 2, sha))


class ConfigPurityTest(unittest.TestCase):
    def test_config_does_not_need_the_database_driver(self) -> None:
        tree = ast.parse(Path(config_module.__file__).read_text(encoding="utf-8"))
        imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
            a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
        }
        self.assertFalse({m for m in imported if m and (m.startswith("psycopg") or m.startswith("app.db"))})


if __name__ == "__main__":
    unittest.main()
