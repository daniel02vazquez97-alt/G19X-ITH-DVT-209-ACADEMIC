"""The API V1 (U5) against PostgreSQL with the real dataset 0.4.0 (`docs/07` §7.2 and §7.4, `DT-066`,
`DT-067`).

One database is loaded, forecast (U3) and evaluated (U4) once for the whole module, at 2025-12-31; the
API only reads it. Every request goes through `starlette.testclient.TestClient` (``httpx2``, `DT-064`).
"""

from __future__ import annotations

import datetime as dt
import time
import unittest
from decimal import Decimal

import psycopg
from psycopg import errors as pg_errors
from _db_support import DATASET_DIR, TemporaryDatabase
from starlette.testclient import TestClient

from app.api.app import create_app
from app.api.auth import ADMIN, ANALYST, PLANNER, VIEWER, Identity
from app.api.settings import Settings
from app.db.migrations import apply_migrations
from app.db.read import LazyReadOnlyConnection, read_only_connection
from app.ingestion.loader import load_dataset
from app.runs.forecast import run_forecast
from app.runs.recommendation import run_recommendations
from app.runs.recommendation_inputs import OrderLineRow, map_open_lines

A = dt.date(2025, 12, 31)
TOKENS = {role: f"dev-{role.lower()}-token-integration" for role in (VIEWER, ANALYST, PLANNER, ADMIN)}
IDENTITIES = {token: Identity(f"it-{role.lower()}", frozenset({role})) for role, token in TOKENS.items()}

_DB: TemporaryDatabase | None = None
_FORECAST_RUN = _RECOMMENDATION_RUN = None


def setUpModule() -> None:
    global _DB, _FORECAST_RUN, _RECOMMENDATION_RUN
    _DB = TemporaryDatabase()
    try:
        with _DB.connect() as conn:
            apply_migrations(conn)
            load_dataset(conn, DATASET_DIR)
            _FORECAST_RUN = run_forecast(conn, A).calculation_run_id
            _RECOMMENDATION_RUN = run_recommendations(conn, A).calculation_run_id
    except BaseException:
        _DB.drop()
        raise


def tearDownModule() -> None:
    if _DB is not None:
        _DB.drop()


class ApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app(Settings("local", _DB.dsn, IDENTITIES)))
        self.conn = _DB.connect()
        self.addCleanup(self.conn.close)

    def get(self, path: str, role: str = ADMIN, expected: int = 200) -> dict:
        response = self.client.get(path, headers={"Authorization": f"Bearer {TOKENS[role]}"})
        self.assertEqual(response.status_code, expected, (path, response.text[:300]))
        return response.json()

    def one(self, query: str, params: tuple = ()):
        return self.conn.execute(query, params).fetchone()[0]


class ProductsTest(ApiTestCase):
    def test_list_pagination_is_stable_and_complete(self) -> None:
        first = self.get("/api/v1/products?page_size=60", VIEWER)
        second = self.get("/api/v1/products?page_size=60&page=2", VIEWER)
        self.assertEqual((first["total"], len(first["items"]), len(second["items"])), (100, 60, 40))
        skus = [p["sku"] for p in first["items"] + second["items"]]
        self.assertEqual(skus, sorted(skus))
        self.assertEqual(len(set(skus)), 100)
        self.assertEqual(self.get("/api/v1/products?page=9", VIEWER)["items"], [])

    def test_filters_search_and_sort(self) -> None:
        inactive = self.get("/api/v1/products?is_active=false")
        self.assertEqual(sorted(p["id"] for p in inactive["items"]), [21, 26, 37, 56, 61])
        found = self.get("/api/v1/products?search=sku-0002")  # case-insensitive substring
        self.assertEqual({p["sku"] for p in found["items"]}, {f"SKU-0002{i}" for i in range(10)})
        self.assertEqual(self.get("/api/v1/products?search=%25")["total"], 0)  # wildcard escaped
        category = self.get("/api/v1/products?category_id=1&page_size=200")
        self.assertTrue(category["items"] and all(p["category"]["id"] == 1 for p in category["items"]))
        descending = [p["id"] for p in self.get("/api/v1/products?sort=-id&page_size=3")["items"]]
        self.assertEqual(descending, [100, 99, 98])

    def test_detail_with_inventory_and_suppliers(self) -> None:
        product = self.get("/api/v1/products/21")
        self.assertEqual((product["is_active"], product["valid_to"]), (False, "2025-04-02"))
        self.assertEqual(product["inventory"]["on_hand"], str(self.one(
            "SELECT quantity_on_hand FROM inventory WHERE product_id = 21")))
        self.assertEqual([s["supplier"]["id"] for s in product["suppliers"]], [2])
        self.get("/api/v1/products/9999", expected=404)

    def test_no_demand_field_anywhere(self) -> None:
        for path in ("/api/v1/products/1", "/api/v1/inventory/1", "/api/v1/products/1/history?granularity=daily",
                     "/api/v1/forecasts?page_size=1", "/api/v1/recommendations/1"):
            with self.subTest(path):
                self.assertNotIn('"demand"', str(self.get(path)).replace("'", '"'))


class InventoryTest(ApiTestCase):
    def test_list_and_derivations(self) -> None:
        page = self.get("/api/v1/inventory?page_size=200", VIEWER)
        self.assertEqual(page["total"], 100)
        for item in page["items"]:
            on_hand, reserved, transit = (Decimal(item[k]) for k in ("on_hand", "reserved", "in_transit_total"))
            self.assertEqual(Decimal(item["available"]), on_hand - reserved)
            self.assertEqual(Decimal(item["inventory_position_accounting"]), on_hand + transit - reserved)
        top = self.get("/api/v1/inventory?sort=-on_hand&page_size=1")["items"][0]
        self.assertEqual(Decimal(top["on_hand"]), self.one("SELECT max(quantity_on_hand) FROM inventory"))
        self.assertEqual(self.get("/api/v1/inventory?product_id=5")["items"][0]["product_id"], 5)

    def test_open_lines_follow_the_u4_rule(self) -> None:
        rows = self.conn.execute(
            """
            SELECT po.id, i.id, i.product_id, po.supplier_id, po.location_id, po.status, i.quantity_ordered,
                   i.quantity_received, po.issued_at AT TIME ZONE 'UTC', po.expected_at AT TIME ZONE 'UTC',
                   i.expected_at AT TIME ZONE 'UTC', NULL::timestamp
            FROM purchase_order_items i JOIN purchase_orders po ON po.id = i.purchase_order_id
            """
        ).fetchall()
        lines = [OrderLineRow(*r) for r in rows]
        total = 0
        for product in range(1, 101):
            expected = map_open_lines(lines, product, 1)
            got = self.get(f"/api/v1/inventory/{product}")["open_lines"]
            total += len(got)
            self.assertEqual([(g["expected_on"], Decimal(g["quantity_pending"]), g["supplier"]["id"]) for g in got],
                             [(e.expected_on.isoformat(), e.quantity_pending, e.supplier_id) for e in expected])
        self.assertEqual(total, 89)
        self.get("/api/v1/inventory/9999", expected=404)


class HistoryTest(ApiTestCase):
    def test_comes_from_consumption_not_demand(self) -> None:
        product = self.one(
            """
            SELECT c.product_id FROM consumption c JOIN demand d USING (product_id, location_id, occurred_on)
            WHERE c.quantity <> d.quantity ORDER BY c.product_id LIMIT 1
            """
        )
        body = self.get(f"/api/v1/products/{product}/history?granularity=daily&date_from=2023-01-01&date_to=2025-12-31",
                        ANALYST)
        consumption = self.one("SELECT sum(quantity) FROM consumption WHERE product_id = %s", (product,))
        demand = self.one("SELECT sum(quantity) FROM demand WHERE product_id = %s", (product,))
        self.assertNotEqual(consumption, demand)
        self.assertEqual(sum(Decimal(p["quantity"]) for p in body["periods"]), consumption)
        self.assertEqual(sum(p["stockout_days"] for p in body["periods"]),
                         self.one("SELECT count(*) FROM consumption WHERE product_id = %s AND is_stockout_affected", (product,)))

    def test_defaults_weekly_and_population_statistics(self) -> None:
        body = self.get("/api/v1/products/1/history", PLANNER)
        self.assertEqual((body["granularity"], body["date_from"], body["date_to"]), ("weekly", "2023-01-01", "2025-12-31"))
        complete = [Decimal(p["quantity"]) for p in body["periods"] if p["complete"]]
        n = len(complete)
        mean = sum(complete) / n
        population = (sum((q - mean) ** 2 for q in complete) / n).sqrt()
        self.assertEqual(body["statistics"]["periods_used"], n)
        self.assertEqual(set(body["statistics"]), {"periods_used", "mean", "std_dev", "cv", "zero_periods"})
        self.assertEqual(Decimal(body["statistics"]["std_dev"]), population.quantize(Decimal("0.000001")))
        self.assertFalse(body["periods"][0]["complete"])  # 2023-01-01 is a Sunday: partial ISO week

    def test_validation_and_errors(self) -> None:
        self.get("/api/v1/products/1/history?date_from=2025-02-01&date_to=2025-01-01", ANALYST, 400)
        self.get("/api/v1/products/1/history?granularity=yearly", ANALYST, 422)
        self.get("/api/v1/products/9999/history", ANALYST, 404)
        self.get("/api/v1/products/1/history", VIEWER, 403)
        empty = self.get("/api/v1/products/1/history?date_from=2030-01-01&date_to=2030-01-31", ANALYST)
        self.assertEqual(empty["statistics"]["periods_used"], 0)
        self.assertTrue(all(not p["complete"] for p in empty["periods"]))


class ForecastsTest(ApiTestCase):
    def test_primary_series_of_the_default_run_with_provenance(self) -> None:
        page = self.get("/api/v1/forecasts?page_size=200", VIEWER)
        self.assertEqual(page["total"], 95)
        self.assertEqual(len(page["items"]), 95)
        self.assertTrue(all(len(s["periods"]) == 14 for s in page["items"]))
        primary = self.one("SELECT count(*) FROM forecasts WHERE calculation_run_id = %s AND is_primary", (_FORECAST_RUN,))
        self.assertEqual(sum(len(s["periods"]) for s in page["items"]), primary)
        provenance = page["provenance"]
        self.assertEqual(provenance["run_id"], _FORECAST_RUN)
        self.assertEqual((provenance["dataset_version"], provenance["data_origin"], provenance["as_of_date"]),
                         ("ds-6c8ad65b4999", "SYNTHETIC", "2025-12-31"))
        self.assertEqual(provenance["model_version"], {"name": "baseline.moving_average", "version": "1.0.0"})
        self.assertEqual(provenance["notices"], ["SYNTHETIC_DATA"])

    def test_pagination_by_series_and_filters(self) -> None:
        page = self.get("/api/v1/forecasts?page_size=10&page=2")
        expected = [row[0] for row in self.conn.execute(
            "SELECT DISTINCT product_id FROM forecasts WHERE calculation_run_id = %s AND is_primary ORDER BY product_id "
            "LIMIT 10 OFFSET 10", (_FORECAST_RUN,)).fetchall()]
        self.assertEqual([s["product"]["id"] for s in page["items"]], expected)
        self.assertEqual(page["total"], self.one(
            "SELECT count(DISTINCT product_id) FROM forecasts WHERE calculation_run_id = %s AND is_primary", (_FORECAST_RUN,)))
        self.assertEqual(self.get("/api/v1/forecasts?product_id=1")["total"], 1)
        self.assertEqual(self.get(f"/api/v1/forecasts?run_id={_RECOMMENDATION_RUN}", expected=404)["error"]["code"],
                         "RUN_NOT_FOUND")

    def test_product_forecast(self) -> None:
        series = self.get("/api/v1/products/1/forecast")
        self.assertEqual(series["periods"][0]["period_start"], "2026-01-01")
        self.assertEqual(self.get("/api/v1/products/21/forecast", expected=404)["error"]["code"], "FORECAST_NOT_FOUND")
        self.assertEqual(self.get("/api/v1/products/9999/forecast", expected=404)["error"]["code"], "PRODUCT_NOT_FOUND")


class RecommendationsTest(ApiTestCase):
    def test_three_outcomes_with_provenance(self) -> None:
        counts = dict(self.conn.execute(
            "SELECT outcome, count(*) FROM recommendations WHERE calculation_run_id = %s GROUP BY outcome",
            (_RECOMMENDATION_RUN,)).fetchall())
        for outcome in ("RECOMMEND", "NO_NEED", "NOT_CALCULABLE"):
            with self.subTest(outcome):
                page = self.get(f"/api/v1/recommendations?outcome={outcome}&page_size=200", VIEWER)
                self.assertEqual(page["total"], counts[outcome])
                self.assertTrue(all(i["outcome"] == outcome for i in page["items"]))
        default = self.get("/api/v1/recommendations?page_size=200")
        self.assertEqual(default["total"], counts["RECOMMEND"])
        provenance = default["provenance"]
        self.assertEqual((provenance["run_id"], provenance["forecast_run_id"], provenance["policy_set"],
                          provenance["engine_version"]), (_RECOMMENDATION_RUN, _FORECAST_RUN, "V1_PROVISIONAL", "0.1.0"))
        self.assertEqual(provenance["notices"], ["SYNTHETIC_DATA", "V1_PROVISIONAL_POLICY"])

    def test_sort_and_filters(self) -> None:
        quantities = [Decimal(i["recommended_quantity"]) for i in
                      self.get("/api/v1/recommendations?sort=-recommended_quantity&page_size=200")["items"]]
        self.assertEqual(quantities, sorted(quantities, reverse=True))
        supplier = self.one("SELECT suggested_supplier_id FROM recommendations WHERE outcome = 'RECOMMEND' LIMIT 1")
        filtered = self.get(f"/api/v1/recommendations?supplier_id={supplier}&page_size=200")["items"]
        self.assertTrue(filtered and all(i["supplier"]["id"] == supplier for i in filtered))
        self.assertEqual(self.get("/api/v1/recommendations?product_id=21&outcome=NOT_CALCULABLE")["total"], 1)

    def test_detail_keeps_the_stored_evaluation(self) -> None:
        stored = self.conn.execute(
            "SELECT id, calculation_inputs, policy_snapshot, raw_quantity FROM recommendations "
            "WHERE outcome = 'RECOMMEND' ORDER BY id LIMIT 1").fetchone()
        detail = self.get(f"/api/v1/recommendations/{stored[0]}")
        self.assertEqual(detail["calculation_inputs"], stored[1])
        self.assertEqual(detail["policy_snapshot"], stored[2])
        self.assertEqual(detail["raw_quantity"], str(stored[3]))
        self.assertEqual(len(detail["calculation_inputs"]["forecast"]["weekly_quantities"]), 14)
        self.get("/api/v1/recommendations/999999", expected=404)

    def test_product_recommendation_for_any_outcome(self) -> None:
        no_need = self.one("SELECT product_id FROM recommendations WHERE outcome = 'NO_NEED' ORDER BY product_id LIMIT 1")
        self.assertEqual(self.get(f"/api/v1/products/{no_need}/recommendation")["raw_quantity"], "0")
        not_calculable = self.get("/api/v1/products/21/recommendation")
        self.assertEqual((not_calculable["outcome"], not_calculable["reasons"], not_calculable["forecast_id"]),
                         ("NOT_CALCULABLE", ["PRODUCT_INACTIVE", "PRODUCT_OUT_OF_VALIDITY", "FORECAST_MISSING"], None))
        self.assertEqual(self.get("/api/v1/products/3/recommendation")["reasons"], ["NO_ACTIVE_PREFERRED_SUPPLIER"])
        self.assertEqual(self.get("/api/v1/products/9999/recommendation", expected=404)["error"]["code"],
                         "PRODUCT_NOT_FOUND")
        self.assertEqual(self.get(f"/api/v1/products/1/recommendation?run_id={_FORECAST_RUN}", expected=404)
                         ["error"]["details"]["reason"], "wrong_type")


class RunsTest(ApiTestCase):
    def test_run_detail_for_planner_and_admin_only(self) -> None:
        run = self.get(f"/api/v1/runs/{_RECOMMENDATION_RUN}", PLANNER)
        self.assertEqual((run["run_type"], run["status"], run["versions"]["forecast_run_id"], run["counts"]["evaluated"]),
                         ("RECOMMENDATION", "COMPLETED", _FORECAST_RUN, 100))
        forecast = self.get(f"/api/v1/runs/{_FORECAST_RUN}", ADMIN)
        self.assertEqual((forecast["counts"]["forecast_rows"], forecast["versions"]["reference_model_version"]["name"]),
                         (3990, "baseline.moving_average"))
        self.get(f"/api/v1/runs/{_FORECAST_RUN}", VIEWER, 403)
        self.get(f"/api/v1/runs/{_FORECAST_RUN}", ANALYST, 403)
        self.get("/api/v1/runs/999999", PLANNER, 404)


class RoleMatrixOnRealDataTest(ApiTestCase):
    PATHS = {
        "/api/v1/me": {VIEWER, ANALYST, PLANNER, ADMIN},
        "/api/v1/products": {VIEWER, ANALYST, PLANNER, ADMIN},
        "/api/v1/products/1": {VIEWER, ANALYST, PLANNER, ADMIN},
        "/api/v1/products/1/history": {ANALYST, PLANNER, ADMIN},
        "/api/v1/inventory": {VIEWER, ANALYST, PLANNER, ADMIN},
        "/api/v1/inventory/1": {VIEWER, ANALYST, PLANNER, ADMIN},
        "/api/v1/forecasts": {VIEWER, ANALYST, PLANNER, ADMIN},
        "/api/v1/products/1/forecast": {VIEWER, ANALYST, PLANNER, ADMIN},
        "/api/v1/recommendations": {VIEWER, ANALYST, PLANNER, ADMIN},
        "/api/v1/recommendations/1": {VIEWER, ANALYST, PLANNER, ADMIN},
        "/api/v1/products/1/recommendation": {VIEWER, ANALYST, PLANNER, ADMIN},
    }

    def test_allowed_200_denied_403(self) -> None:
        paths = dict(self.PATHS, **{f"/api/v1/runs/{_FORECAST_RUN}": {PLANNER, ADMIN}})
        for path, allowed in paths.items():
            for role in (VIEWER, ANALYST, PLANNER, ADMIN):
                with self.subTest(path=path, role=role):
                    self.get(path, role, 200 if role in allowed else 403)


class ReadOnlyTest(ApiTestCase):
    ENDPOINTS = ["/health", "/api/v1/me", "/api/v1/products", "/api/v1/products/1", "/api/v1/products/1/history",
                 "/api/v1/inventory", "/api/v1/inventory/1", "/api/v1/forecasts", "/api/v1/products/1/forecast",
                 "/api/v1/recommendations", "/api/v1/recommendations/1", "/api/v1/products/1/recommendation",
                 "/api/v1/runs/1"]

    def snapshot(self) -> tuple:
        time.sleep(1.2)  # API backends are closed after each request and flush their statistics on exit
        self.conn.execute("SELECT pg_stat_force_next_flush()")
        writes = self.one("SELECT coalesce(sum(n_tup_ins + n_tup_upd + n_tup_del), 0) FROM pg_stat_user_tables")
        tables = [r[0] for r in self.conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")]
        counts = tuple(self.one(f'SELECT count(*) FROM "{t}"') for t in tables)
        return writes, counts

    def test_no_endpoint_writes(self) -> None:
        before = self.snapshot()
        for path in self.ENDPOINTS:
            self.client.get(path, headers={"Authorization": f"Bearer {TOKENS[ADMIN]}"})
        self.assertEqual(self.snapshot(), before)

    def test_writes_through_the_read_connections_are_rejected(self) -> None:
        with read_only_connection(_DB.dsn) as conn:
            with self.assertRaises(pg_errors.ReadOnlySqlTransaction) as caught:
                conn.execute("DELETE FROM consumption WHERE product_id = 1")
        self.assertEqual(caught.exception.diag.sqlstate, "25006")
        lazy = LazyReadOnlyConnection(_DB.dsn)
        try:
            with self.assertRaises(pg_errors.ReadOnlySqlTransaction):
                lazy.execute("INSERT INTO categories (code, name, is_active, data_origin) VALUES ('X', 'X', true, 'SYNTHETIC')")
        finally:
            lazy.close()
        self.assertEqual(self.one("SELECT count(*) FROM consumption WHERE product_id = 1"), 1096)


class DemandIsolationTest(ApiTestCase):
    def test_history_works_without_the_demand_table(self) -> None:
        self.conn.execute("ALTER TABLE demand RENAME TO demand_hidden")
        try:
            body = self.get("/api/v1/products/1/history?granularity=monthly", ANALYST)
            self.assertEqual(len(body["periods"]), 36)
            for path in ("/api/v1/products/1", "/api/v1/inventory/1", "/api/v1/forecasts", "/api/v1/recommendations/1"):
                self.get(path)
        finally:
            self.conn.execute("ALTER TABLE demand_hidden RENAME TO demand")


if __name__ == "__main__":
    unittest.main()
