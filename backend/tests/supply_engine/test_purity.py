"""Structural tests of the supply engine: purity, dependencies and `V1-11`.

Run from ``backend/``::

    python3 -m unittest discover -s tests -t .

Scope: `docs/03` §16.4 rules 1 and 2 (standard library only; nothing imports ``data.synthetic``);
`docs/06` §16.1 and §16.6 (no clock, no randomness, no float); aclaración A-2 of `DT-051` (no
``abc_class`` nor ``rotation_class`` anywhere: case 11 of `DT-031` verified structurally);
`DT-043` (Python ≥ 3.11, no dependencies).
"""

from __future__ import annotations

import ast
import dataclasses
import sys
import tomllib
import unittest
from pathlib import Path

import app.supply_engine as engine_package
from app.supply_engine import (
    ConsumptionSeries,
    EvaluationInput,
    Forecast,
    Inventory,
    LeadTimeObservation,
    OpenLine,
    PolicyParameters,
    Product,
    SupplierRelation,
)

PACKAGE_DIR = Path(engine_package.__file__).parent
BACKEND_DIR = PACKAGE_DIR.parent.parent
MODULES = sorted(PACKAGE_DIR.glob("*.py"))

#: The only modules the engine may import (all from the standard library).
ALLOWED_IMPORTS = {
    "__future__",
    "collections",
    "collections.abc",
    "dataclasses",
    "datetime",
    "decimal",
    "enum",
    "fractions",
    "math",
    "typing",
}


def _trees() -> list[tuple[Path, ast.AST]]:
    return [(path, ast.parse(path.read_text(encoding="utf-8"))) for path in MODULES]


class PackageShapeTest(unittest.TestCase):
    def test_the_package_has_the_planned_modules(self) -> None:
        names = {path.name for path in MODULES}
        self.assertEqual(
            names,
            {"__init__.py", "contract.py", "engine.py", "exact.py", "rules.py", "validation.py"},
        )

    def test_pyproject_requires_python_311_and_declares_no_dependency(self) -> None:
        data = tomllib.loads((BACKEND_DIR / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["project"]["requires-python"], ">=3.11")
        self.assertEqual(data["project"]["dependencies"], [])

    def test_runs_on_python_311_or_later(self) -> None:
        self.assertGreaterEqual(sys.version_info[:2], (3, 11))


class ImportPurityTest(unittest.TestCase):
    def test_only_allowed_standard_library_imports(self) -> None:
        for path, tree in _trees():
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        with self.subTest(module=path.name, imported=alias.name):
                            self.assertIn(alias.name, ALLOWED_IMPORTS)
                elif isinstance(node, ast.ImportFrom):
                    if node.level:  # relative import inside the package
                        continue
                    with self.subTest(module=path.name, imported=node.module):
                        self.assertIn(node.module, ALLOWED_IMPORTS)

    def test_allowed_imports_are_all_standard_library(self) -> None:
        for name in ALLOWED_IMPORTS:
            with self.subTest(name=name):
                self.assertIn(name.split(".")[0], sys.stdlib_module_names | {"__future__"})

    def test_nothing_imports_the_generator(self) -> None:
        for path in MODULES:
            with self.subTest(module=path.name):
                self.assertNotIn("data.synthetic", path.read_text(encoding="utf-8"))


class DeterminismSourceTest(unittest.TestCase):
    def test_no_clock_and_no_randomness(self) -> None:
        forbidden_attributes = {"today", "now", "utcnow", "time", "random"}
        for path, tree in _trees():
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr in forbidden_attributes:
                    self.fail(f"{path.name} uses .{node.attr}")

    def test_no_float_anywhere(self) -> None:
        for path, tree in _trees():
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, float):
                    self.fail(f"{path.name} has a float literal")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotEqual(node.func.id, "float", f"{path.name} calls float()")

    def test_decimal_is_only_built_in_the_reporting_function(self) -> None:
        """B3: ``Decimal`` never takes part in a decision (`docs/06` §16.6 point 7)."""
        for path, tree in _trees():
            for function in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
                calls = [
                    n
                    for n in ast.walk(function)
                    if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name)
                    and n.func.id == "Decimal"
                ]
                if calls:
                    self.assertEqual(
                        (path.name, function.name), ("exact.py", "_correctly_rounded")
                    )


class NoSegmentAttributeTest(unittest.TestCase):
    """`V1-11` and aclaración A-2: case 11 of `DT-031`, verified structurally."""

    INPUT_TYPES = (
        EvaluationInput,
        Product,
        SupplierRelation,
        Inventory,
        OpenLine,
        LeadTimeObservation,
        ConsumptionSeries,
        Forecast,
        PolicyParameters,
    )

    def test_no_input_type_has_a_segment_attribute(self) -> None:
        for kind in self.INPUT_TYPES:
            names = {field.name for field in dataclasses.fields(kind)}
            with self.subTest(kind=kind.__name__):
                self.assertNotIn("abc_class", names)
                self.assertNotIn("rotation_class", names)

    def test_the_package_never_names_a_segment_attribute(self) -> None:
        for path in MODULES:
            text = path.read_text(encoding="utf-8")
            with self.subTest(module=path.name):
                code_names = {
                    n.id for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Name)
                } | {
                    n.attr for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Attribute)
                }
                self.assertNotIn("abc_class", code_names)
                self.assertNotIn("rotation_class", code_names)

    def test_a_segment_attribute_cannot_be_passed(self) -> None:
        with self.assertRaises(TypeError):
            Product(1, 1, True, None, None, abc_class="A")  # type: ignore[call-arg]


if __name__ == "__main__":
    unittest.main()
