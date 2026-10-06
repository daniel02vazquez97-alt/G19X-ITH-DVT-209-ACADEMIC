"""No ``float`` crosses into U1 or U3 (`DT-074`) and `ml` depends only on the allowed packages."""

from __future__ import annotations

import ast
import datetime as _dt
import sys
import unittest
from pathlib import Path
from unittest import mock

import app.forecasting as forecasting_pkg
from app.supply_engine import rules
from ml import backtest, models
from ml.backtest import comparison_tables, run_backtest
from ml.config import F5aConfig
from ml.data import load_dataset
from ml.tests.fixtures import TempDataset

ML_DIR = Path(__file__).resolve().parents[1]


def _floats(value, path="arg"):
    if isinstance(value, float):
        yield path
    elif isinstance(value, (list, tuple, set, frozenset)):
        for i, item in enumerate(value):
            yield from _floats(item, f"{path}[{i}]")
    elif isinstance(value, dict):
        for k, item in value.items():
            yield from _floats(item, f"{path}.{k}")
    elif hasattr(value, "__dataclass_fields__"):
        for name in value.__dataclass_fields__:
            yield from _floats(getattr(value, name), f"{path}.{name}")


def _guard(function, calls):
    def wrapper(*args, **kwargs):
        found = list(_floats(list(args) + list(kwargs.values())))
        if found:
            raise AssertionError(f"float passed to {function.__name__}: {found[:3]}")
        calls.append(function.__name__)
        return function(*args, **kwargs)

    return wrapper


class NoFloatAcrossTheBoundaryTest(unittest.TestCase):
    def test_every_call_into_u1_and_u3_is_float_free(self) -> None:
        calls: list[str] = []
        patches = [
            mock.patch.object(backtest, "build_request", _guard(backtest.build_request, calls)),
            mock.patch.object(models, "forecast", _guard(models.forecast, calls)),
            mock.patch.object(backtest, "weekly_totals", _guard(backtest.weekly_totals, calls)),
        ] + [
            mock.patch.object(rules, name, _guard(getattr(rules, name), calls))
            for name in ("select_supplier", "observed_lead_time", "cap_lead_time", "coverage_horizon", "demand_over_horizon")
        ]
        with TempDataset() as path:
            ds = load_dataset(path)
            for p in patches:
                p.start()
            try:
                result = run_backtest(ds, F5aConfig(), [_dt.date(2024, 3, 27), _dt.date(2024, 8, 14)])
                comparison_tables(result, F5aConfig())
            finally:
                mock.patch.stopall()
        for name in ("build_request", "forecast", "weekly_totals", "observed_lead_time", "demand_over_horizon"):
            self.assertIn(name, calls)

    def test_baseline_output_is_decimal(self) -> None:
        with TempDataset() as path:
            ds = load_dataset(path)
        sc = backtest.run_series_cut(ds, (1, 1), _dt.date(2024, 3, 27), F5aConfig())
        for fc in sc.forecasts.values():
            self.assertFalse(list(_floats(fc.points + fc.lowers + fc.uppers)))


class DependencyRulesTest(unittest.TestCase):
    ALLOWED_APP = ("app.forecasting", "app.supply_engine")
    #: The only allowed import of app.runs: the pure U4 adapter, in the parity test of the lead-time rule
    #: (docs/13 §14). The ml package itself never imports app.runs (docs/03 §16.2).
    RUNS_EXCEPTION = ("tests/test_data.py", "app.runs.recommendation_inputs")

    def _imports(self, source: Path) -> list[str]:
        names = []
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names.append(node.module or "")
        return names

    def test_app_runs_only_in_the_parity_test(self) -> None:
        found = []
        for source in sorted(ML_DIR.rglob("*.py")):
            relative = source.relative_to(ML_DIR).as_posix()
            for name in self._imports(source):
                if name == "app.runs" or name.startswith("app.runs."):
                    found.append((relative, name))
        self.assertEqual(found, [self.RUNS_EXCEPTION])

    def test_ml_imports_only_stdlib_and_the_two_libraries(self) -> None:
        stdlib = set(sys.stdlib_module_names)
        for source in sorted(ML_DIR.rglob("*.py")):
            if source.relative_to(ML_DIR).as_posix() == self.RUNS_EXCEPTION[0]:
                continue
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    top = name.split(".")[0]
                    ok = top in stdlib or name.startswith(self.ALLOWED_APP) or top == "ml"
                    self.assertTrue(ok, f"{source.name} imports {name}")

    def test_u3_package_is_untouched_by_ml(self) -> None:
        # The provider used by ml is the U3 one, not a copy.
        self.assertIs(models.forecast, forecasting_pkg.forecast)


if __name__ == "__main__":
    unittest.main()
