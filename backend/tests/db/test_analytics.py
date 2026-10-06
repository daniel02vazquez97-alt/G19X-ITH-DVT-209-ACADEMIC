"""Migration 0004 (U9, `DT-097`): the read-only analytics layer — views, role and migration.

Integration suite (real PostgreSQL, `docs/13` §14). Four groups:

* migration: from scratch, over 0001–0003 with data, idempotent, and in a second database of the same
  cluster (the role is cluster-wide);
* schema: exactly the expected views, with their columns and types;
* values: a small fixture with hand-computed results, and the real dataset 0.4.0 with forecast and
  recommendations, checked against the operational tables and against U4 and U5;
* the role ``analytics_reader``: reads the views and nothing else, and cannot write or change anything.
"""

from __future__ import annotations

import datetime as dt
import shutil
import tempfile
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg import errors as pg_errors
from psycopg.rows import dict_row
from _db_support import DATASET_DIR, DatabaseTestCase, TemporaryDatabase

from app.db.migrations import MIGRATIONS_DIR, apply_migrations, discover
from app.db.read.inventory import list_inventory
from app.ingestion.loader import load_dataset
from app.runs.forecast import run_forecast
from app.runs.recommendation import read_context, run_recommendations
from app.runs.recommendation_inputs import map_lead_time_observations

A = dt.date(2025, 12, 31)
READER = "analytics_reader"

#: Every view of the analytics schema, with its columns in order and their information_schema types.
EXPECTED_VIEWS: dict[str, list[tuple[str, str]]] = {
    "data_load": [
        ("data_load_id", "bigint"), ("dataset_version", "text"), ("generator_version", "text"),
        ("data_origin", "text"), ("period_start", "date"), ("cut_date", "date"),
        ("loaded_at", "timestamp with time zone"),
    ],
    "dim_date": [
        ("calendar_date", "date"), ("year", "integer"), ("quarter", "integer"), ("month", "integer"),
        ("day_of_month", "integer"), ("iso_year", "integer"), ("iso_week", "integer"),
        ("iso_day_of_week", "integer"),
    ],
    "dim_product": [
        ("product_id", "bigint"), ("sku", "text"), ("name", "text"), ("category_id", "bigint"),
        ("unit_of_measure", "text"), ("abc_class", "text"), ("rotation_class", "text"), ("is_active", "boolean"),
        ("valid_from", "date"), ("valid_to", "date"), ("data_origin", "text"),
    ],
    "dim_category": [
        ("category_id", "bigint"), ("code", "text"), ("name", "text"), ("parent_id", "bigint"),
        ("is_active", "boolean"), ("data_origin", "text"),
    ],
    "dim_supplier": [
        ("supplier_id", "bigint"), ("code", "text"), ("name", "text"), ("currency", "text"),
        ("is_active", "boolean"), ("data_origin", "text"),
    ],
    "dim_location": [
        ("location_id", "bigint"), ("code", "text"), ("name", "text"), ("type", "text"),
        ("is_active", "boolean"), ("data_origin", "text"),
    ],
    "dim_model_version": [
        ("model_version_id", "bigint"), ("name", "text"), ("version", "text"), ("algorithm", "text"),
        ("is_baseline", "boolean"), ("status", "text"),
    ],
    "fact_consumption": [
        ("product_id", "bigint"), ("location_id", "bigint"), ("occurred_on", "date"),
        ("consumed_quantity", "numeric"), ("is_stockout_affected", "boolean"),
        ("latent_demand_quantity", "numeric"), ("data_origin", "text"),
    ],
    "fact_inventory_current": [
        ("product_id", "bigint"), ("location_id", "bigint"), ("as_of_date", "date"),
        ("quantity_on_hand", "numeric"), ("quantity_reserved", "numeric"), ("quantity_in_transit", "numeric"),
        ("accounting_position", "numeric"), ("last_movement_at", "timestamp with time zone"),
        ("data_origin", "text"),
    ],
    "fact_inventory_daily": [
        ("product_id", "bigint"), ("location_id", "bigint"), ("calendar_date", "date"),
        ("net_movement_quantity", "numeric"), ("on_hand_end_of_day", "numeric"),
    ],
    "fact_purchase_order_line": [
        ("purchase_order_item_id", "bigint"), ("purchase_order_id", "bigint"), ("order_number", "text"),
        ("product_id", "bigint"), ("supplier_id", "bigint"), ("location_id", "bigint"),
        ("order_status", "text"), ("currency", "text"), ("issued_on", "date"), ("expected_on", "date"),
        ("closed_on", "date"), ("quantity_ordered", "numeric"), ("quantity_received", "numeric"),
        ("quantity_pending", "numeric"), ("is_open", "boolean"), ("unit_cost", "numeric"),
        ("agreed_lead_time_days", "integer"), ("last_received_on", "date"), ("receipt_count", "bigint"),
        ("is_fully_received", "boolean"), ("observed_lead_time_days", "integer"), ("is_on_time", "boolean"),
        ("open_age_days_at_cut", "integer"), ("data_origin", "text"),
    ],
    "fact_forecast": [
        ("forecast_id", "bigint"), ("calculation_run_id", "bigint"), ("as_of_date", "date"),
        ("product_id", "bigint"), ("location_id", "bigint"), ("model_version_id", "bigint"),
        ("period_start", "date"), ("period_end", "date"), ("granularity", "text"),
        ("predicted_quantity", "numeric"), ("lower_bound", "numeric"), ("upper_bound", "numeric"),
        ("confidence_level", "numeric"), ("method_used", "text"), ("confidence_flag", "text"),
        ("is_primary", "boolean"),
    ],
    "fact_recommendation": [
        ("recommendation_id", "bigint"), ("calculation_run_id", "bigint"), ("forecast_run_id", "bigint"),
        ("as_of_date", "date"), ("product_id", "bigint"), ("location_id", "bigint"), ("outcome", "text"),
        ("reasons", "text"), ("flags", "text"), ("missing_policy_parameters", "text"),
        ("forecast_id", "bigint"), ("suggested_supplier_id", "bigint"), ("suggested_order_date", "date"),
        ("recommended_quantity", "numeric"), ("raw_quantity", "numeric"), ("reorder_point", "numeric"),
        ("safety_stock", "numeric"), ("lead_time_used_days", "integer"), ("demand_during_lead_time", "numeric"),
        ("inventory_position_at_calc", "numeric"), ("policy_set", "text"), ("engine_version", "text"),
        ("generated_at", "timestamp with time zone"),
    ],
}

#: The grain of every fact view: no two rows may share these columns.
GRAINS = {
    "fact_consumption": ("product_id", "location_id", "occurred_on"),
    "fact_inventory_current": ("product_id", "location_id"),
    "fact_inventory_daily": ("product_id", "location_id", "calendar_date"),
    "fact_purchase_order_line": ("purchase_order_item_id",),
    "fact_forecast": ("calculation_run_id", "model_version_id", "product_id", "location_id", "period_start"),
    "fact_recommendation": ("calculation_run_id", "product_id", "location_id"),
    "dim_date": ("calendar_date",),
}


def analytics_views(conn: psycopg.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT table_name FROM information_schema.views WHERE table_schema = 'analytics'")}


def insert_fixture(conn: psycopg.Connection) -> None:
    """A tiny load with hand-computable results (period 2025-01-01 … 2025-01-10, cut 2025-01-10)."""
    now = "2025-01-11T00:00:00Z"
    conn.execute(
        """INSERT INTO data_loads (id, dataset_version, generator_version, data_origin, time_range, manifest,
               manifest_sha256, files, status, outcome, started_at, finished_at)
           VALUES (1, 'fixture', '0.0.0', 'SYNTHETIC', daterange('2025-01-01', '2025-01-11'), '{}', 'x', '[]',
                   'COMPLETED', 'COMPLETED', %s, %s)""",
        (now, now),
    )
    conn.execute("INSERT INTO categories VALUES (1, 'C1', 'Category 1', NULL, true, 'SYNTHETIC')")
    conn.execute("INSERT INTO locations VALUES (1, 'L1', 'Location 1', 'WAREHOUSE', true, 'SYNTHETIC')")
    conn.execute("INSERT INTO suppliers VALUES (1, 'S1', 'Supplier 1', 'contact', true, 'MXN', %s, %s, 'SYNTHETIC')",
                 (now, now))
    for pid in (1, 2):
        conn.execute(
            """INSERT INTO products VALUES (%s, %s, %s, NULL, 1, 'UNIT', true, 'A', 'HIGH', NULL, '2024-01-01',
                   NULL, %s, %s, 'SYNTHETIC')""",
            (pid, f"SKU-{pid}", f"Product {pid}", now, now),
        )
    conn.execute("INSERT INTO product_suppliers VALUES (1, 1, 1, 7, 0, 1, 2.5, true, true, 'SYNTHETIC')")
    for day, quantity, stockout, demand in (("2025-01-01", 3, False, 3), ("2025-01-02", 0, True, 5)):
        conn.execute("INSERT INTO consumption (product_id, location_id, occurred_on, quantity, is_stockout_affected,"
                     " data_origin) VALUES (1, 1, %s, %s, %s, 'SYNTHETIC')", (day, quantity, stockout))
        conn.execute("INSERT INTO demand (product_id, location_id, occurred_on, quantity, data_origin)"
                     " VALUES (1, 1, %s, %s, 'SYNTHETIC')", (day, demand))
    movements = (
        ("2024-12-31T12:00:00Z", "ADJUSTMENT", 10),   # before the period: opening balance
        ("2025-01-01T10:00:00Z", "ISSUE", -3),
        ("2025-01-03T05:30:00Z", "RECEIPT", 20),
        ("2025-01-03T20:00:00Z", "ISSUE", -4),        # same UTC day
        ("2025-01-04T23:30:00-06:00", "ISSUE", -1),   # 2025-01-05 in UTC
    )
    for occurred_at, kind, quantity in movements:
        conn.execute(
            """INSERT INTO inventory_movements (product_id, location_id, movement_type, quantity, occurred_at,
                   recorded_at, reference_type, data_origin) VALUES (1, 1, %s, %s, %s, %s, 'FIXTURE', 'SYNTHETIC')""",
            (kind, quantity, occurred_at, occurred_at),
        )
    conn.execute("INSERT INTO inventory (product_id, location_id, quantity_on_hand, quantity_reserved,"
                 " quantity_in_transit, updated_at, data_origin) VALUES (1, 1, 22, 2, 5, %s, 'SYNTHETIC')", (now,))
    conn.execute("INSERT INTO inventory (product_id, location_id, quantity_on_hand, quantity_reserved,"
                 " quantity_in_transit, updated_at, data_origin) VALUES (2, 1, 0, 0, 0, %s, 'SYNTHETIC')", (now,))
    orders = (
        (1, "PO-1", "RECEIVED", "2025-01-01T08:00:00Z", "2025-01-08T00:00:00Z"),
        (2, "PO-2", "PARTIALLY_RECEIVED", "2025-01-02T08:00:00Z", "2025-01-05T00:00:00Z"),
        (3, "PO-3", "CANCELLED", "2025-01-03T08:00:00Z", "2025-01-09T00:00:00Z"),
        (4, "PO-4", "RECEIVED", "2025-01-01T23:30:00-06:00", "2025-01-03T00:00:00Z"),
    )
    for oid, number, status, issued, expected in orders:
        conn.execute(
            """INSERT INTO purchase_orders (id, order_number, supplier_id, location_id, status, issued_at, expected_at,
                   currency, created_at, updated_at, data_origin) VALUES (%s, %s, 1, 1, %s, %s, %s, 'MXN', %s, %s,
                   'SYNTHETIC')""",
            (oid, number, status, issued, expected, now, now),
        )
    items = (
        (11, 1, 1, 20, 20, None),
        (21, 2, 1, 10, 4, "2025-01-12T00:00:00Z"),  # the line's date overrides the header's
        (31, 3, 2, 8, 0, None),
        (41, 4, 2, 5, 5, None),
    )
    for iid, oid, pid, ordered, received, expected in items:
        conn.execute(
            """INSERT INTO purchase_order_items (id, purchase_order_id, product_id, quantity_ordered, quantity_received,
                   unit_cost, expected_at, data_origin) VALUES (%s, %s, %s, %s, %s, 2.5, %s, 'SYNTHETIC')""",
            (iid, oid, pid, ordered, received, expected),
        )
    for iid, received_at, quantity in ((11, "2025-01-03T05:30:00Z", 15), (11, "2025-01-06T12:00:00Z", 5),
                                       (21, "2025-01-04T09:00:00Z", 4), (41, "2025-01-07T00:00:00Z", 5)):
        conn.execute("INSERT INTO purchase_order_receipts (purchase_order_item_id, received_at, quantity_received,"
                     " data_origin) VALUES (%s, %s, %s, 'SYNTHETIC')", (iid, received_at, quantity))


class AnalyticsMigrationTest(DatabaseTestCase):
    migrate = False

    def _only(self, *names: str) -> Path:
        handle = tempfile.TemporaryDirectory(prefix="u9_migrations_")
        self.addCleanup(handle.cleanup)
        for name in names:
            shutil.copy(MIGRATIONS_DIR / name, Path(handle.name))
        return Path(handle.name)

    def test_from_scratch_the_four_migrations_apply_in_order_and_once(self) -> None:
        self.assertEqual(
            apply_migrations(self.conn),
            ["0001_dataset_tables", "0002_forecast_tables", "0003_recommendation_tables", "0004_analytics_views"],
        )
        self.assertEqual(apply_migrations(self.conn), [])
        self.assertEqual(analytics_views(self.conn), set(EXPECTED_VIEWS))
        for view in EXPECTED_VIEWS:  # an empty database gives empty views, not errors
            self.assertEqual(self.conn.execute(f"SELECT count(*) FROM analytics.{view}").fetchone()[0], 0, view)

    def test_over_0003_with_data_changes_nothing_operational(self) -> None:
        apply_migrations(self.conn, self._only(
            "0001_dataset_tables.sql", "0002_forecast_tables.sql", "0003_recommendation_tables.sql"))
        load_dataset(self.conn, DATASET_DIR)
        run_forecast(self.conn, A)
        run_recommendations(self.conn, A)
        tables = ("products", "consumption", "inventory", "inventory_movements", "purchase_order_items",
                  "calculation_runs", "forecasts", "recommendations", "data_loads")
        before = {t: self.count(t) for t in tables}
        self.assertEqual(apply_migrations(self.conn), ["0004_analytics_views"])
        self.assertEqual({t: self.count(t) for t in tables}, before)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM analytics.fact_recommendation").fetchone()[0], 100)
        # The operational flow still works after 0004: a repeated run is recognised, not rewritten.
        self.assertEqual(run_recommendations(self.conn, A).outcome.value, "ALREADY_COMPUTED")

    def test_a_second_database_of_the_same_cluster_reuses_the_role(self) -> None:
        apply_migrations(self.conn)
        other = TemporaryDatabase()
        self.addCleanup(other.drop)
        with other.connect() as conn:
            self.assertIn("0004_analytics_views", apply_migrations(conn))
            self.assertEqual(analytics_views(conn), set(EXPECTED_VIEWS))
            self.assertTrue(conn.execute(
                "SELECT has_schema_privilege(%s, 'analytics', 'USAGE')", (READER,)).fetchone()[0])


class AnalyticsSchemaTest(DatabaseTestCase):
    def test_views_columns_and_types(self) -> None:
        self.assertEqual(analytics_views(self.conn), set(EXPECTED_VIEWS))
        for view, columns in EXPECTED_VIEWS.items():
            actual = self.conn.execute(
                """SELECT column_name, data_type FROM information_schema.columns
                   WHERE table_schema = 'analytics' AND table_name = %s ORDER BY ordinal_position""",
                (view,),
            ).fetchall()
            self.assertEqual(actual, columns, view)

    def test_no_table_and_no_materialized_view_in_analytics(self) -> None:
        kinds = self.conn.execute(
            """SELECT c.relkind, count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = 'analytics' GROUP BY c.relkind"""
        ).fetchall()
        self.assertEqual(kinds, [("v", len(EXPECTED_VIEWS))])

    def test_public_keeps_the_operational_tables_only(self) -> None:
        views = self.conn.execute("SELECT count(*) FROM information_schema.views WHERE table_schema = 'public'")
        self.assertEqual(views.fetchone()[0], 0)


class AnalyticsFixtureTest(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        insert_fixture(self.conn)

    def rows(self, query: str) -> list[dict]:
        with self.conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(query).fetchall()

    def test_data_load_and_calendar(self) -> None:
        load = self.rows("SELECT * FROM analytics.data_load")
        self.assertEqual([(r["period_start"], r["cut_date"]) for r in load], [(dt.date(2025, 1, 1), dt.date(2025, 1, 10))])
        days = self.rows("SELECT * FROM analytics.dim_date ORDER BY calendar_date")
        self.assertEqual([d["calendar_date"] for d in days],
                         [dt.date(2025, 1, 1) + dt.timedelta(days=n) for n in range(10)])
        first = days[0]
        self.assertEqual((first["year"], first["quarter"], first["month"], first["day_of_month"], first["iso_year"],
                          first["iso_week"], first["iso_day_of_week"]), (2025, 1, 1, 1, 2025, 1, 3))

    def test_consumption_with_latent_demand(self) -> None:
        rows = self.rows("SELECT occurred_on, consumed_quantity, is_stockout_affected, latent_demand_quantity"
                         " FROM analytics.fact_consumption ORDER BY occurred_on")
        self.assertEqual([tuple(r.values()) for r in rows], [
            (dt.date(2025, 1, 1), Decimal(3), False, Decimal(3)),
            (dt.date(2025, 1, 2), Decimal(0), True, Decimal(5)),
        ])
        fill_rate = self.conn.execute("SELECT sum(consumed_quantity) / sum(latent_demand_quantity)"
                                      " FROM analytics.fact_consumption").fetchone()[0]
        self.assertEqual(fill_rate, Decimal("0.375"))

    def test_current_inventory_and_accounting_position(self) -> None:
        rows = self.rows("SELECT product_id, as_of_date, accounting_position FROM analytics.fact_inventory_current"
                         " ORDER BY product_id")
        self.assertEqual([tuple(r.values()) for r in rows],
                         [(1, dt.date(2025, 1, 10), Decimal(25)), (2, dt.date(2025, 1, 10), Decimal(0))])

    def test_daily_inventory_is_the_running_sum_of_movements_in_utc_days(self) -> None:
        rows = self.rows("SELECT product_id, calendar_date, net_movement_quantity, on_hand_end_of_day"
                         " FROM analytics.fact_inventory_daily ORDER BY product_id, calendar_date")
        self.assertEqual(len(rows), 20)  # 2 inventory pairs × 10 days
        product_1 = {r["calendar_date"].day: (r["net_movement_quantity"], r["on_hand_end_of_day"])
                     for r in rows if r["product_id"] == 1}
        expected = {1: (-3, 7), 2: (0, 7), 3: (16, 23), 4: (0, 23), 5: (-1, 22)}
        expected.update({day: (0, 22) for day in range(6, 11)})
        self.assertEqual(product_1, {d: (Decimal(n), Decimal(o)) for d, (n, o) in expected.items()})
        self.assertEqual({r["on_hand_end_of_day"] for r in rows if r["product_id"] == 2}, {Decimal(0)})

    def test_purchase_order_lines(self) -> None:
        rows = {r["purchase_order_item_id"]: r for r in self.rows("SELECT * FROM analytics.fact_purchase_order_line")}
        fields = ("issued_on", "expected_on", "quantity_pending", "is_open", "agreed_lead_time_days", "last_received_on",
                  "receipt_count", "is_fully_received", "observed_lead_time_days", "is_on_time", "open_age_days_at_cut")
        d = dt.date
        expected = {
            11: (d(2025, 1, 1), d(2025, 1, 8), 0, False, 7, d(2025, 1, 6), 2, True, 5, True, None),
            21: (d(2025, 1, 2), d(2025, 1, 12), 6, True, 7, d(2025, 1, 4), 1, False, None, None, 8),
            31: (d(2025, 1, 3), d(2025, 1, 9), 0, False, None, None, 0, False, None, None, None),
            41: (d(2025, 1, 2), d(2025, 1, 3), 0, False, None, d(2025, 1, 7), 1, True, 5, False, None),
        }
        self.assertEqual(set(rows), set(expected))
        for item, values in expected.items():
            with self.subTest(item=item):
                self.assertEqual(tuple(rows[item][f] for f in fields), values)


class AnalyticsDatasetTest(unittest.TestCase):
    """The real dataset 0.4.0 with the forecast and the recommendations of U3 and U4 at 2025-12-31."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.database = TemporaryDatabase()
        cls.conn = cls.database.connect()
        apply_migrations(cls.conn)
        load_dataset(cls.conn, DATASET_DIR)
        cls.forecast_run = run_forecast(cls.conn, A).calculation_run_id
        run_recommendations(cls.conn, A)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()
        cls.database.drop()

    def scalar(self, query: str):
        return self.conn.execute(query).fetchone()[0]

    def test_no_duplicates_at_the_declared_grain(self) -> None:
        for view, grain in GRAINS.items():
            with self.subTest(view=view):
                columns = ", ".join(grain)
                self.assertEqual(self.scalar(
                    f"SELECT count(*) FROM (SELECT {columns} FROM analytics.{view} GROUP BY {columns}"
                    f" HAVING count(*) > 1) d"), 0)

    def test_row_counts_match_the_operational_tables(self) -> None:
        self.assertEqual(self.scalar("SELECT count(*) FROM analytics.fact_consumption"),
                         self.scalar("SELECT count(*) FROM consumption"))
        self.assertEqual(self.scalar("SELECT count(*) FROM analytics.fact_purchase_order_line"), 3705)
        self.assertEqual(self.scalar("SELECT count(*) FROM analytics.fact_inventory_daily"), 100 * 1096)
        self.assertEqual(self.scalar("SELECT count(*) FROM analytics.fact_forecast"), 3990)
        self.assertEqual(self.scalar("SELECT count(*) FROM analytics.fact_forecast WHERE is_primary"), 1330)
        outcomes = dict(self.conn.execute(
            "SELECT outcome, count(*) FROM analytics.fact_recommendation GROUP BY outcome").fetchall())
        self.assertEqual(outcomes, {"RECOMMEND": 50, "NO_NEED": 40, "NOT_CALCULABLE": 10})

    def test_calendar_and_cut(self) -> None:
        self.assertEqual(self.conn.execute("SELECT dataset_version, cut_date FROM analytics.data_load").fetchall(),
                         [("ds-6c8ad65b4999", A)])
        first, last = self.conn.execute("SELECT min(calendar_date), max(calendar_date) FROM analytics.dim_date").fetchone()
        self.assertEqual(first, dt.date(2023, 1, 1))
        self.assertEqual(last, self.scalar("SELECT max(period_end) - 1 FROM forecasts"))

    def test_daily_inventory_reconciles_with_the_snapshot_on_every_pair(self) -> None:
        self.assertEqual(self.scalar(
            """SELECT count(*) FROM analytics.fact_inventory_current c
               JOIN analytics.fact_inventory_daily d USING (product_id, location_id)
               WHERE d.calendar_date = c.as_of_date AND d.on_hand_end_of_day = c.quantity_on_hand"""), 100)
        self.assertEqual(self.scalar("SELECT count(*) FROM analytics.fact_inventory_daily WHERE on_hand_end_of_day < 0"), 0)

    def test_recommendations_are_the_persisted_values(self) -> None:
        self.assertEqual(self.scalar(
            """SELECT count(*) FROM analytics.fact_recommendation v JOIN recommendations r ON r.id = v.recommendation_id
               WHERE v.recommended_quantity IS NOT DISTINCT FROM r.recommended_quantity
                 AND v.reorder_point IS NOT DISTINCT FROM r.reorder_point
                 AND v.safety_stock IS NOT DISTINCT FROM r.safety_stock
                 AND v.inventory_position_at_calc IS NOT DISTINCT FROM r.inventory_position_at_calc
                 AND v.reasons = array_to_string(r.reasons, ',') AND v.flags = array_to_string(r.flags, ',')"""), 100)
        self.assertEqual(self.scalar("SELECT count(DISTINCT forecast_run_id) FROM analytics.fact_recommendation"), 1)

    def test_accounting_position_is_the_one_of_the_api(self) -> None:
        with psycopg.connect(self.database.dsn, autocommit=True, row_factory=dict_row) as conn:
            _, api = list_inventory(conn, product_id=None, category_id=None, sort="sku", descending=False,
                                    limit=1000, offset=0)
        view = dict(((p, l), v) for p, l, v in self.conn.execute(
            "SELECT product_id, location_id, accounting_position FROM analytics.fact_inventory_current"))
        self.assertEqual({(r["product_id"], r["location_id"]): r["inventory_position_accounting"] for r in api}, view)

    def test_lead_time_observations_are_the_ones_of_u4(self) -> None:
        context = read_context(self.conn, A, self.forecast_run)
        suppliers = {r.supplier_id for r in context.order_lines}
        u4 = Counter((o.supplier_id, o.issued_on, o.completed_on)
                     for o in map_lead_time_observations(context.order_lines, suppliers))
        view = Counter(self.conn.execute(
            "SELECT supplier_id, issued_on, last_received_on FROM analytics.fact_purchase_order_line"
            " WHERE is_fully_received").fetchall())
        self.assertEqual(view, u4)
        self.assertEqual(self.scalar(
            "SELECT count(*) FROM analytics.fact_purchase_order_line"
            " WHERE is_fully_received AND observed_lead_time_days <> last_received_on - issued_on"), 0)


class AnalyticsReaderTest(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        insert_fixture(self.conn)
        self.addCleanup(self.conn.execute, "RESET ROLE")

    def as_reader(self) -> None:
        self.conn.execute(f"SET ROLE {READER}")

    def assert_denied(self, statement: str) -> None:
        with self.assertRaises(pg_errors.InsufficientPrivilege, msg=statement):
            self.conn.execute(statement)

    def test_role_attributes_and_memberships(self) -> None:
        row = self.conn.execute(
            """SELECT rolsuper, rolcreatedb, rolcreaterole, rolcanlogin, rolreplication, rolbypassrls
               FROM pg_roles WHERE rolname = %s""", (READER,)).fetchone()
        self.assertEqual(row, (False, False, False, False, False, False))
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid = m.member WHERE r.rolname = %s",
            (READER,)).fetchone()[0], 0)

    def test_reads_every_view(self) -> None:
        self.as_reader()
        for view in EXPECTED_VIEWS:
            with self.subTest(view=view):
                self.conn.execute(f"SELECT * FROM analytics.{view}").fetchall()
        self.assertEqual(self.conn.execute("SELECT count(*) FROM analytics.fact_purchase_order_line").fetchone()[0], 4)

    def test_cannot_read_operational_tables(self) -> None:
        self.as_reader()
        for table in ("products", "consumption", "demand", "inventory", "purchase_orders", "recommendations",
                      "calculation_runs", "data_loads", "schema_migrations"):
            with self.subTest(table=table):
                self.assert_denied(f"SELECT 1 FROM public.{table} LIMIT 1")

    def test_cannot_write_through_the_views(self) -> None:
        self.as_reader()
        self.assert_denied("INSERT INTO analytics.dim_location (location_id, code, name, type, is_active, data_origin)"
                           " VALUES (9, 'X', 'X', 'X', true, 'SYNTHETIC')")
        self.assert_denied("UPDATE analytics.dim_product SET name = 'x'")
        self.assert_denied("DELETE FROM analytics.dim_category")
        self.assert_denied("TRUNCATE public.products")
        self.assert_denied("INSERT INTO public.products (sku) VALUES ('x')")

    def test_cannot_change_the_schema(self) -> None:
        self.as_reader()
        self.assert_denied("CREATE TABLE analytics.reader_table (x int)")
        self.assert_denied("CREATE VIEW analytics.reader_view AS SELECT 1 AS x")
        self.assert_denied("CREATE TABLE public.reader_table (x int)")
        self.assert_denied("CREATE SCHEMA reader_schema")
        self.assert_denied("DROP VIEW analytics.dim_date")
        self.assert_denied("ALTER VIEW analytics.dim_date RENAME TO renamed")
        self.assert_denied(f"GRANT SELECT ON public.products TO {READER}")

    def test_cannot_run_the_migrations(self) -> None:
        self.as_reader()
        with self.assertRaises(pg_errors.InsufficientPrivilege):
            apply_migrations(self.conn)

    def test_later_views_in_analytics_are_readable_and_later_tables_in_public_are_not(self) -> None:
        self.conn.execute("CREATE VIEW analytics.u9_probe AS SELECT 1 AS x")
        self.conn.execute("CREATE TABLE public.u9_probe_table (x int)")
        self.as_reader()
        self.assertEqual(self.conn.execute("SELECT x FROM analytics.u9_probe").fetchone()[0], 1)
        self.assert_denied("SELECT x FROM public.u9_probe_table")


if __name__ == "__main__":
    unittest.main()
