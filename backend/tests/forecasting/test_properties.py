"""Leakage, reproducibility and purity of the forecasting package (`DT-046`, RML-004)."""

from __future__ import annotations

import ast
import datetime as dt
import sys
import unittest
from pathlib import Path

import app.forecasting as forecasting_package
from app.forecasting import build_request, forecast

from ._builders import A, DAY, daily_request

PACKAGE_DIR = Path(forecasting_package.__file__).parent
MODULES = sorted(PACKAGE_DIR.glob("*.py"))
ALLOWED_IMPORTS = {
    "__future__",
    "collections",
    "collections.abc",
    "dataclasses",
    "datetime",
    "decimal",
    "enum",
    "fractions",
    "types",
    "typing",
}


def _trees() -> list[tuple[Path, ast.AST]]:
    return [(path, ast.parse(path.read_text(encoding="utf-8"))) for path in MODULES]


class LeakageTest(unittest.TestCase):
    def full_series(self, future: int) -> list[tuple[dt.date, int, bool]]:
        """400 days up to A plus 30 days after A whose quantity is ``future``."""
        past = [(A - DAY * i, (i * 7) % 11, False) for i in range(400)]
        after = [(A + DAY * (i + 1), future, False) for i in range(30)]
        return past + after

    def test_rows_after_as_of_date_are_rejected(self) -> None:
        with self.assertRaises(Exception):
            build_request(1, 1, A, self.full_series(5))

    def test_changing_only_the_future_does_not_change_the_forecast(self) -> None:
        results = []
        for future in (0, 10_000):
            valid = [row for row in self.full_series(future) if row[0] <= A]
            results.append(forecast(build_request(1, 1, A, valid)))
        self.assertEqual(results[0], results[1])

    def test_an_earlier_cut_ignores_later_days(self) -> None:
        earlier = A - DAY * 50
        rows = [row for row in self.full_series(0) if row[0] <= earlier]
        changed = [(d, q if d <= earlier else 999, f) for d, q, f in self.full_series(0)]
        changed = [row for row in changed if row[0] <= earlier]
        self.assertEqual(forecast(build_request(1, 1, earlier, rows)), forecast(build_request(1, 1, earlier, changed)))


class ReproducibilityTest(unittest.TestCase):
    def test_same_input_same_result(self) -> None:
        daily = [(i * 13) % 17 for i in range(7 * 70 + 5)]
        self.assertEqual(forecast(daily_request(daily)), forecast(daily_request(list(daily))))


class PurityTest(unittest.TestCase):
    def test_only_standard_library_imports(self) -> None:
        for path, tree in _trees():
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        with self.subTest(module=path.name, imported=alias.name):
                            self.assertIn(alias.name, ALLOWED_IMPORTS)
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    with self.subTest(module=path.name, imported=node.module):
                        self.assertIn(node.module, ALLOWED_IMPORTS)
        for name in ALLOWED_IMPORTS:
            self.assertIn(name.split(".")[0], sys.stdlib_module_names | {"__future__"})

    def test_no_database_engine_or_generator_reference(self) -> None:
        for path in MODULES:
            source = path.read_text(encoding="utf-8")
            for forbidden in ("psycopg", "app.db", "supply_engine", "data.synthetic", "demand.csv"):
                with self.subTest(module=path.name, forbidden=forbidden):
                    self.assertNotIn(forbidden, source)

    def test_no_clock_randomness_or_float(self) -> None:
        for path, tree in _trees():
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, {"today", "now", "utcnow", "time", "random"}, path.name)
                if isinstance(node, ast.Constant):
                    self.assertNotIsInstance(node.value, float, path.name)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotEqual(node.func.id, "float", path.name)

    def test_no_mutable_module_state(self) -> None:
        for path, tree in _trees():
            for node in tree.body:  # type: ignore[attr-defined]
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
                        continue
                    mutable = (ast.List, ast.Set, ast.Dict, ast.ListComp, ast.SetComp, ast.DictComp)
                    with self.subTest(module=path.name, line=node.lineno):
                        self.assertNotIsInstance(node.value, mutable)


if __name__ == "__main__":
    unittest.main()
