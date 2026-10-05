"""Transversal contract of the API V1 (`DT-066`, `docs/07` §1 and §7.4): correlation id, errors, health,
OpenAPI, public routes, CORS, numbers, pagination, provenance notices and architecture rules."""

from __future__ import annotations

import ast
import re
import tomllib
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from unittest import mock

from _api_support import BACKEND_DIR, ENDPOINTS, TOKENS, auth, client, settings

import app.api as api_package
from app.api.app import create_app
from app.api.auth import ADMIN, VIEWER
from app.api.errors import ApiError
from app.api.pagination import parse_sort
from app.api.provenance import notices
from app.api.schemas import InventoryItem
from starlette.testclient import TestClient

API_DIR = BACKEND_DIR / "app" / "api"
READ_DIR = BACKEND_DIR / "app" / "db" / "read"


class CorrelationIdTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = client()

    def test_valid_header_is_kept(self) -> None:
        response = self.client.get("/health", headers={"X-Correlation-ID": "req-2026.10_03-abc"})
        self.assertEqual(response.headers["X-Correlation-ID"], "req-2026.10_03-abc")

    def test_invalid_header_is_replaced_by_a_uuid4(self) -> None:
        for value in ("short", "has space in it", "x" * 65, "bad/char/123"):
            with self.subTest(value=value):
                response = self.client.get("/health", headers={"X-Correlation-ID": value})
                generated = response.headers["X-Correlation-ID"]
                self.assertNotEqual(generated, value)
                self.assertEqual(uuid.UUID(generated).version, 4)

    def test_absent_header_is_generated(self) -> None:
        self.assertEqual(uuid.UUID(self.client.get("/health").headers["X-Correlation-ID"]).version, 4)

    def test_errors_carry_the_same_id_in_body_and_header(self) -> None:
        response = self.client.get("/api/v1/me", headers={"X-Correlation-ID": "abcdefgh-1"})
        self.assertEqual(response.json()["error"]["correlation_id"], "abcdefgh-1")
        self.assertEqual(response.headers["X-Correlation-ID"], "abcdefgh-1")


class ErrorContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = client()

    def assert_error(self, response, status: int, code: str) -> dict:
        self.assertEqual(response.status_code, status)
        body = response.json()
        self.assertEqual(set(body), {"error"})
        self.assertEqual(set(body["error"]), {"code", "message", "details", "correlation_id"})
        self.assertEqual(body["error"]["code"], code)
        self.assertEqual(body["error"]["correlation_id"], response.headers["X-Correlation-ID"])
        return body["error"]

    def test_unknown_route_and_method(self) -> None:
        self.assert_error(self.client.get("/api/v1/unknown"), 404, "NOT_FOUND")
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method):
                self.assert_error(getattr(self.client, method)("/api/v1/products", headers=auth(ADMIN)), 405,
                                  "METHOD_NOT_ALLOWED")

    def test_validation_errors_do_not_echo_values(self) -> None:
        error = self.assert_error(self.client.get("/api/v1/products?page_size=999&page=secret", headers=auth(VIEWER)),
                                  422, "VALIDATION_ERROR")
        self.assertEqual({d["field"] for d in error["details"]}, {"page", "page_size"})
        self.assertNotIn("secret", str(error))
        self.assertNotIn("999", str(error))

    def test_invalid_sort_and_date_range(self) -> None:
        self.assert_error(self.client.get("/api/v1/products?sort=-price", headers=auth(VIEWER)), 400, "INVALID_SORT")
        self.assert_error(self.client.get("/api/v1/recommendations?sort=urgency", headers=auth(VIEWER)), 400, "INVALID_SORT")
        self.assert_error(self.client.get("/api/v1/inventory?sort=coverage_days", headers=auth(VIEWER)), 400, "INVALID_SORT")

    def test_database_unavailable_is_503(self) -> None:
        self.assert_error(self.client.get("/api/v1/products", headers=auth(VIEWER)), 503, "SERVICE_UNAVAILABLE")

    def test_unhandled_error_is_a_generic_500_without_internals(self) -> None:
        app = create_app(settings())

        @app.get("/boom")
        def boom() -> None:
            raise RuntimeError("SELECT secret FROM internal_table at db-host-01")

        with self.assertLogs("app.api", level="ERROR"):
            response = TestClient(app, raise_server_exceptions=False).get("/boom")
        error = self.assert_error(response, 500, "INTERNAL_ERROR")
        self.assertNotIn("secret", response.text)
        self.assertNotIn("Traceback", response.text)
        self.assertEqual(error["details"], {})

    def test_documented_statuses_have_a_code(self) -> None:
        from app.api.errors import STATUS_ERRORS

        self.assertEqual(set(STATUS_ERRORS), {400, 401, 403, 404, 405, 409, 422, 429, 500, 503})
        app = create_app(settings())

        @app.get("/conflict")
        def conflict() -> None:
            raise ApiError(409, "CONFLICT", "x")

        self.assert_error(TestClient(app).get("/conflict"), 409, "CONFLICT")


class HealthTest(unittest.TestCase):
    def test_public_and_without_database(self) -> None:
        with mock.patch("psycopg.connect", side_effect=AssertionError("/health touched the database")):
            response = client().get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "version": api_package.__version__})

    def test_version_equals_pyproject(self) -> None:
        project = tomllib.loads((BACKEND_DIR / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(api_package.__version__, project["project"]["version"])


class OpenApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = client()
        self.schema = self.client.get("/openapi.json").json()

    def test_public_docs_and_no_redoc(self) -> None:
        self.assertEqual(self.client.get("/docs").status_code, 200)
        self.assertEqual(self.client.get("/redoc").status_code, 404)
        self.assertEqual(self.client.get("/docs/oauth2-redirect").status_code, 404)

    def test_exactly_the_fourteen_endpoints_all_get(self) -> None:
        # U5 = 13 endpoints; U6 adds the 14th, the explanation (`DT-068`).
        self.assertEqual(
            set(self.schema["paths"]),
            {"/health", "/api/v1/me", "/api/v1/products", "/api/v1/products/{product_id}",
             "/api/v1/products/{product_id}/history", "/api/v1/inventory", "/api/v1/inventory/{product_id}",
             "/api/v1/forecasts", "/api/v1/products/{product_id}/forecast", "/api/v1/recommendations",
             "/api/v1/recommendations/{recommendation_id}", "/api/v1/products/{product_id}/recommendation",
             "/api/v1/runs/{run_id}", "/api/v1/recommendations/{recommendation_id}/explanation"},
        )
        for path, operations in self.schema["paths"].items():
            self.assertEqual(set(operations), {"get"}, path)

    def test_bearer_security_and_error_models(self) -> None:
        schemes = self.schema["components"]["securitySchemes"]
        self.assertEqual([s["scheme"] for s in schemes.values()], ["bearer"])
        for path, operations in self.schema["paths"].items():
            operation = operations["get"]
            if path == "/health":
                self.assertNotIn("security", operation)
                continue
            self.assertIn("security", operation, path)
            self.assertIn("401", operation["responses"], path)
        self.assertEqual(self.schema["info"]["version"], api_package.__version__)

    def test_no_route_answers_without_token_except_the_public_ones(self) -> None:
        public = {"/health", "/docs", "/openapi.json"}
        for path, _ in ENDPOINTS:
            if path in public:
                continue
            with self.subTest(path):
                self.assertEqual(self.client.get(path).status_code, 401)
        concrete = {re.sub(r"\{[^}]+\}", "1", p) for p in self.schema["paths"]}
        for path in concrete - public:
            self.assertEqual(self.client.get(path).status_code, 401, path)


class CorsTest(unittest.TestCase):
    def test_no_cors_headers(self) -> None:
        response = client().get("/health", headers={"Origin": "https://evil.example"})
        self.assertNotIn("access-control-allow-origin", {k.lower() for k in response.headers})
        preflight = client().options("/api/v1/products", headers={"Origin": "https://evil.example",
                                                                   "Access-Control-Request-Method": "GET"})
        self.assertNotIn("access-control-allow-origin", {k.lower() for k in preflight.headers})


class NumbersAndHelpersTest(unittest.TestCase):
    def test_decimal_is_a_json_string_never_a_float(self) -> None:
        item = InventoryItem(product_id=1, sku="S", on_hand=Decimal("1.50"), reserved=Decimal("0"), available=Decimal("1.5"),
                             in_transit_total=Decimal("0"), inventory_position_accounting=Decimal("2623.500600092591729239380374"),
                             last_movement_at=None, data_origin="SYNTHETIC")
        dumped = item.model_dump(mode="json")
        self.assertEqual(dumped["on_hand"], "1.50")
        self.assertEqual(dumped["inventory_position_accounting"], "2623.500600092591729239380374")

    def test_sort_parsing(self) -> None:
        self.assertEqual(parse_sort(None, ("sku", "name"), "sku").field, "sku")
        parsed = parse_sort("-name", ("sku", "name"), "sku")
        self.assertEqual((parsed.field, parsed.descending), ("name", True))
        with self.assertRaises(ApiError):
            parse_sort("--name", ("sku", "name"), "sku")

    def test_provenance_notices(self) -> None:
        self.assertEqual(notices("SYNTHETIC", "V1_PROVISIONAL"), ["SYNTHETIC_DATA", "V1_PROVISIONAL_POLICY"])
        self.assertEqual(notices("SYNTHETIC"), ["SYNTHETIC_DATA"])
        self.assertEqual(notices("REAL", "V1_PROVISIONAL"), ["V1_PROVISIONAL_POLICY"])
        self.assertEqual(notices("REAL", "OTHER"), [])
        self.assertEqual(notices(None), [])


class ArchitectureTest(unittest.TestCase):
    """`docs/03` §16.4: the API never recalculates and never writes; nothing reads ``demand``."""

    def modules(self, directory: Path) -> dict[Path, str]:
        return {p: p.read_text(encoding="utf-8") for p in directory.rglob("*.py")}

    def test_forbidden_imports(self) -> None:
        forbidden = ("app.supply_engine", "app.forecasting", "app.runs", "data")
        for path, source in {**self.modules(API_DIR), **self.modules(READ_DIR)}.items():
            for node in ast.walk(ast.parse(source)):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module or ""]
                for name in names:
                    with self.subTest(path=path.name, name=name):
                        self.assertFalse(any(name == f or name.startswith(f + ".") for f in forbidden))

    def test_read_layer_has_no_writes_and_no_demand(self) -> None:
        for path, source in self.modules(READ_DIR).items():
            with self.subTest(path.name):
                upper = source.upper()
                for keyword in ("INSERT ", "UPDATE ", "DELETE ", "TRUNCATE", "ALTER ", "CREATE ", "DROP "):
                    self.assertNotIn(keyword, upper)
                self.assertIsNone(re.search(r"\b(FROM|JOIN)\s+demand\b", source, re.IGNORECASE))

    def test_api_layer_has_no_sql(self) -> None:
        for path, source in self.modules(API_DIR).items():
            with self.subTest(path.name):
                self.assertIsNone(re.search(r"\bSELECT\b.+\bFROM\b", source))


if __name__ == "__main__":
    unittest.main()
