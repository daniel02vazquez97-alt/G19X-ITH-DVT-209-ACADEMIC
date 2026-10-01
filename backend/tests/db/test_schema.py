"""The physical model of `docs/04` §9 (`DT-044`): tables, column order, types and foreign keys."""

from __future__ import annotations

from _db_support import DatabaseTestCase

from app.ingestion import contract

EXPECTED_TABLES = {contract.table_name(n) for n in contract.FILES} | {"data_loads", "schema_migrations"}

#: (table, column) → referenced table, exactly the documented foreign keys.
EXPECTED_FKS = {
    ("products", "category_id"): "categories",
    ("product_suppliers", "product_id"): "products",
    ("product_suppliers", "supplier_id"): "suppliers",
    ("purchase_orders", "supplier_id"): "suppliers",
    ("purchase_orders", "location_id"): "locations",
    ("purchase_order_items", "purchase_order_id"): "purchase_orders",
    ("purchase_order_items", "product_id"): "products",
    ("purchase_order_receipts", "purchase_order_item_id"): "purchase_order_items",
    ("demand", "product_id"): "products",
    ("demand", "location_id"): "locations",
    ("consumption", "product_id"): "products",
    ("consumption", "location_id"): "locations",
    ("inventory_movements", "product_id"): "products",
    ("inventory_movements", "location_id"): "locations",
    ("inventory", "product_id"): "products",
    ("inventory", "location_id"): "locations",
}

_SQL_TYPES = {
    "id": "bigint",
    "ref": "bigint",
    "int": "integer",
    "int_nonneg": "integer",
    "qty": "numeric",
    "money": "numeric",
    "text": "text",
    "vocab": "text",
    "origin": "text",
    "bool": "boolean",
    "date": "date",
    "datetime": "timestamp with time zone",
    "stamped": "timestamp with time zone",
}


class SchemaTest(DatabaseTestCase):
    def _columns(self, table: str) -> list[tuple[str, str, str, int | None]]:
        return self.conn.execute(
            """
            SELECT column_name, data_type, is_nullable, numeric_precision
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        ).fetchall()

    def test_exactly_the_twelve_tables_plus_data_loads(self) -> None:
        tables = {
            r[0]
            for r in self.conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
        }
        self.assertEqual(tables, EXPECTED_TABLES)
        for deferred in ("model_versions", "calculation_runs", "forecasts", "recommendations",
                         "inventory_policies", "risk_assessments", "supplier_performance", "audit_log",
                         "app_users"):
            self.assertNotIn(deferred, tables)

    def test_columns_follow_the_contract_name_order_type_and_nullability(self) -> None:
        for name, columns in contract.FILES.items():
            actual = self._columns(contract.table_name(name))
            self.assertEqual([c[0] for c in actual], [c.name for c in columns], name)
            for column, (_, data_type, nullable, precision) in zip(columns, actual, strict=True):
                self.assertEqual(data_type, _SQL_TYPES[column.kind], (name, column.name))
                self.assertEqual(nullable == "YES", column.nullable, (name, column.name))
                if data_type == "numeric":
                    self.assertIsNone(precision, f"{name}.{column.name}: numeric without fixed precision")

    def test_ids_are_identity_primary_keys(self) -> None:
        for name in contract.FILES:
            table = contract.table_name(name)
            identity, pk = self.conn.execute(
                """
                SELECT c.is_identity, (SELECT array_agg(a.attname) FROM pg_index i
                        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY (i.indkey)
                        WHERE i.indrelid = %s::regclass AND i.indisprimary)
                FROM information_schema.columns c
                WHERE c.table_name = %s AND c.column_name = 'id'
                """,
                (table, table),
            ).fetchone()
            self.assertEqual(identity, "YES", table)
            self.assertEqual(pk, ["id"], table)

    def test_foreign_keys_are_exactly_the_documented_ones(self) -> None:
        rows = self.conn.execute(
            """
            SELECT c.conrelid::regclass::text, a.attname, c.confrelid::regclass::text
            FROM pg_constraint c
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
            WHERE c.contype = 'f'
            """
        ).fetchall()
        self.assertEqual({(t, c): r for t, c, r in rows}, EXPECTED_FKS)
        # Polymorphic reference and parent_id have no FK (docs/04 §9.1, §9.3).
        self.assertNotIn(("inventory_movements", "reference_id"), {(t, c) for t, c, _ in rows})
        self.assertNotIn(("categories", "parent_id"), {(t, c) for t, c, _ in rows})

    def test_business_keys_and_partial_indexes(self) -> None:
        indexes = dict(
            self.conn.execute("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public'").fetchall()
        )
        for unique in ("locations_code_key", "categories_code_key", "suppliers_code_key", "products_sku_key",
                       "purchase_orders_order_number_key", "product_suppliers_pair_uk",
                       "inventory_pair_uk", "demand_day_uk", "consumption_day_uk",
                       "inventory_movements_business_uk"):
            self.assertIn("UNIQUE", indexes[unique], unique)
        self.assertIn("NULLS NOT DISTINCT", indexes["inventory_movements_business_uk"])
        self.assertIn("WHERE (is_preferred AND is_active)", indexes["product_suppliers_one_active_preferred_ux"])
        self.assertIn("WHERE (status = 'COMPLETED'", indexes["data_loads_single_completed_ux"])

    def test_data_loads_columns(self) -> None:
        columns = {c[0]: (c[1], c[2]) for c in self._columns("data_loads")}
        self.assertEqual(
            list(columns),
            ["id", "dataset_version", "generator_version", "data_origin", "time_range", "manifest",
             "manifest_sha256", "files", "status", "outcome", "errors", "started_at", "finished_at"],
        )
        self.assertEqual(columns["manifest"], ("jsonb", "NO"))
        self.assertEqual(columns["time_range"][0], "daterange")
