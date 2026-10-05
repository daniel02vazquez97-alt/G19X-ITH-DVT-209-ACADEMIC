"""`docs/03` §16.4 and `DT-068` point 12: ``genai`` uses only the standard library, never the database,
the engine, the API or any AI/network library; ``api`` → ``genai`` only."""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

GENAI_DIR = Path(__file__).resolve().parents[2] / "app" / "genai"
FORBIDDEN = ("app.api", "app.db", "app.supply_engine", "app.forecasting", "app.runs", "app.ingestion", "psycopg",
             "openai", "azure", "httpx", "httpx2", "requests", "urllib", "http", "socket", "fastapi", "pydantic",
             "jinja2")


def imports(path: Path) -> list[tuple[str, int]]:
    result = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            result += [(alias.name, 0) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            result.append((node.module or "", node.level))
    return result


class IsolationTest(unittest.TestCase):
    def test_only_standard_library_and_own_package(self) -> None:
        files = sorted(GENAI_DIR.glob("*.py"))
        self.assertGreater(len(files), 5)
        for path in files:
            for name, level in imports(path):
                with self.subTest(path=path.name, name=name):
                    if level:  # relative: inside app.genai
                        continue
                    self.assertFalse(any(name == f or name.startswith(f + ".") for f in FORBIDDEN))
                    top = name.split(".")[0]
                    self.assertTrue(top in sys.stdlib_module_names or top == "__future__", name)

    def test_no_sql_and_no_demand(self) -> None:
        for path in GENAI_DIR.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotRegex(source, r"\bSELECT\b|\bINSERT\b|\bUPDATE\b")
            self.assertNotIn("demand", source.replace("demand_over_horizon", "").replace("demanda", ""))

    def test_the_engine_is_never_loaded(self) -> None:
        from tests.genai._genai_fixtures import RECOMMEND_ROW, context_of

        from app.genai import explain

        before = {m for m in sys.modules if m.startswith(("app.supply_engine", "app.runs", "app.forecasting"))}
        explain(context_of(RECOMMEND_ROW))
        after = {m for m in sys.modules if m.startswith(("app.supply_engine", "app.runs", "app.forecasting"))}
        self.assertEqual(after - before, set())


if __name__ == "__main__":
    unittest.main()
