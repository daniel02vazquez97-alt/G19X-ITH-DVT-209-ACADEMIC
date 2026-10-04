"""Pure adapter of U4: rows → `EvaluationInput` (`docs/06` §16.13.2), without PostgreSQL."""

from __future__ import annotations

import ast
import dataclasses
import datetime as dt
import unittest
from decimal import Decimal
from pathlib import Path

import app.runs.recommendation_inputs as inputs_module
from app.runs.recommendation_inputs import (
    AdapterError,
    ConsumptionRow,
    build_evaluation_input,
    map_consumption,
    map_forecast,
    map_inventory,
    map_lead_time_observations,
    map_open_lines,
    map_product,
    map_supplier_relations,
    utc_date,
)
from app.supply_engine import V1_PROVISIONAL_PARAMETERS, EvaluationInput, MethodUsed

from ._u4_fixtures import A, DAY, UTC, WEEK, at, consumption, forecast, inventory, line, observations, product, relation


class PurityTest(unittest.TestCase):
    def test_no_sql_and_no_database_driver(self) -> None:
        source = Path(inputs_module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            (node.module or "").split(".")[0] if isinstance(node, ast.ImportFrom) else alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("psycopg", imported)
        for keyword in ("SELECT ", "INSERT ", "UPDATE ", "DELETE "):
            self.assertNotIn(keyword, source)


class UtcDateTest(unittest.TestCase):
    def test_naive_values_are_utc_wall_time(self) -> None:
        self.assertEqual(utc_date(dt.datetime(2025, 12, 31, 23, 59)), dt.date(2025, 12, 31))

    def test_aware_values_are_converted_to_utc(self) -> None:
        kiritimati = dt.timezone(dt.timedelta(hours=14))
        # 2026-01-01 10:00 at UTC+14 is still 2025-12-31 in UTC.
        self.assertEqual(utc_date(dt.datetime(2026, 1, 1, 10, tzinfo=kiritimati)), dt.date(2025, 12, 31))
        self.assertEqual(utc_date(dt.datetime(2025, 12, 31, 20, tzinfo=dt.timezone(dt.timedelta(hours=-6)))), dt.date(2026, 1, 1))

    def test_dates_pass_through(self) -> None:
        self.assertEqual(utc_date(A), A)


class ProductAndRelationsTest(unittest.TestCase):
    def test_inactive_and_out_of_validity_products_are_not_filtered(self) -> None:
        mapped = map_product(product(5, active=False, valid_to=dt.date(2025, 4, 2)))
        self.assertEqual((mapped.product_id, mapped.is_active, mapped.valid_to), (5, False, dt.date(2025, 4, 2)))

    def test_every_relation_ordered_by_supplier_without_choosing(self) -> None:
        mapped = map_supplier_relations([relation(9, preferred=False), relation(2, active=False), relation(7)])
        self.assertEqual([r.supplier_id for r in mapped], [2, 7, 9])
        self.assertEqual([(r.is_active, r.is_preferred) for r in mapped], [(False, True), (True, True), (True, False)])
        self.assertIsInstance(mapped[0].moq, Decimal)


class InventoryTest(unittest.TestCase):
    def test_maps_the_three_quantities(self) -> None:
        mapped = map_inventory(inventory("12", "5"))
        self.assertEqual((mapped.on_hand, mapped.reserved, mapped.total_in_transit), (12, 0, 5))

    def test_missing_row_fails_instead_of_zeros(self) -> None:
        with self.assertRaises(AdapterError) as caught:
            map_inventory(None)
        self.assertEqual(caught.exception.code, "MISSING_INVENTORY")


class OpenLinesTest(unittest.TestCase):
    def test_open_statuses_location_product_and_positive_pending(self) -> None:
        rows = [
            line(1, 1, status="ISSUED", received="0"),
            line(2, 2, status="PARTIALLY_RECEIVED", ordered="10", received="4"),
            line(3, 3, status="PARTIALLY_RECEIVED", ordered="10", received="10"),  # pending 0
            line(4, 4, status="RECEIVED"),
            line(5, 5, status="CANCELLED", received="0"),
            line(6, 6, status="DRAFT", received="0"),
            line(7, 7, status="ISSUED", received="0", location_id=2),
            line(8, 8, status="ISSUED", received="0", product_id=2),
        ]
        mapped = map_open_lines(rows, 1, 1)
        self.assertEqual([(l.purchase_order_id, l.quantity_pending) for l in mapped], [(1, 10), (2, 6)])

    def test_expected_on_is_the_line_date_or_else_the_header_date(self) -> None:
        rows = [
            line(1, 1, status="ISSUED", received="0", expected=dt.date(2026, 1, 20)),
            line(2, 2, status="ISSUED", received="0", expected=dt.date(2026, 1, 20), item_expected=dt.date(2026, 1, 9)),
        ]
        mapped = map_open_lines(rows, 1, 1)
        self.assertEqual([l.expected_on for l in mapped], [dt.date(2026, 1, 20), dt.date(2026, 1, 9)])

    def test_overdue_lines_are_kept_for_u1_to_classify(self) -> None:
        mapped = map_open_lines([line(1, 1, status="ISSUED", received="0", expected=A - DAY)], 1, 1)
        self.assertEqual(len(mapped), 1)

    def test_canonical_order_whatever_the_input_order(self) -> None:
        rows = [line(3, 9, status="ISSUED", received="0"), line(1, 4, status="ISSUED", received="0"), line(1, 2, status="ISSUED", received="0")]
        self.assertEqual([(l.purchase_order_id, l.item_id) for l in map_open_lines(rows, 1, 1)], [(1, 2), (1, 4), (3, 9)])


class LeadTimeObservationsTest(unittest.TestCase):
    def test_only_complete_lines_with_a_receipt_of_related_suppliers(self) -> None:
        rows = [
            line(1, 1),  # complete, supplier 7
            line(2, 2, status="PARTIALLY_RECEIVED"),  # complete line in a partially received order: counts
            line(3, 3, received="4"),  # incomplete
            line(4, 4, last_received=None),  # complete but without receipt
            line(5, 5, supplier_id=8),  # unrelated supplier
            line(6, 6, product_id=99),  # another product of the same supplier: counts (V1-09 is per supplier)
        ]
        mapped = map_lead_time_observations(rows, [7])
        self.assertEqual(len(mapped), 3)
        self.assertEqual({o.supplier_id for o in mapped}, {7})

    def test_dates_are_utc_and_completed_is_the_last_receipt(self) -> None:
        aware = dt.datetime(2025, 3, 2, 3, tzinfo=dt.timezone(dt.timedelta(hours=5)))  # 2025-03-01 22:00 UTC
        mapped = map_lead_time_observations([line(1, 1, issued=dt.date(2025, 2, 1), last_received=aware)], [7])
        self.assertEqual((mapped[0].issued_on, mapped[0].completed_on), (dt.date(2025, 2, 1), dt.date(2025, 3, 1)))

    def test_no_date_filter_in_the_adapter(self) -> None:
        future = line(1, 1, expected=A + DAY * 10)
        self.assertEqual(len(map_lead_time_observations([future], [7])), 1)

    def test_canonical_order(self) -> None:
        rows = observations(count=3)
        self.assertEqual(map_lead_time_observations(rows, [7]), map_lead_time_observations(list(reversed(rows)), [7]))


class ConsumptionTest(unittest.TestCase):
    def test_dense_series_up_to_the_cut(self) -> None:
        rows = consumption(10, end=A + DAY * 3)  # three days after the cut are dropped
        series = map_consumption(rows, A, dt.date(2023, 1, 1))
        self.assertEqual(series.start_date, A - DAY * 6)
        self.assertEqual(len(series.quantities), 7)

    def test_gap_fails_without_imputation(self) -> None:
        rows = consumption(10)
        del rows[4]
        with self.assertRaises(AdapterError) as caught:
            map_consumption(rows, A, dt.date(2023, 1, 1))
        self.assertEqual(caught.exception.code, "CONSUMPTION_GAP")

    def test_duplicate_fails(self) -> None:
        rows = consumption(5)
        rows.append(ConsumptionRow(rows[2].occurred_on, Decimal("1")))
        with self.assertRaises(AdapterError) as caught:
            map_consumption(rows, A, dt.date(2023, 1, 1))
        self.assertEqual(caught.exception.code, "CONSUMPTION_DUPLICATE")

    def test_order_independent_and_empty(self) -> None:
        rows = consumption(5)
        self.assertEqual(map_consumption(rows, A, dt.date(2023, 1, 1)), map_consumption(list(reversed(rows)), A, dt.date(2023, 1, 1)))
        empty = map_consumption([], A, dt.date(2024, 5, 1))
        self.assertEqual((empty.start_date, empty.quantities), (dt.date(2024, 5, 1), ()))


class ForecastTest(unittest.TestCase):
    def test_fourteen_contiguous_weeks_anchored_on_h1(self) -> None:
        mapped = map_forecast(forecast("7.5"), A)
        self.assertEqual(mapped.start_date, A + DAY)
        self.assertEqual(len(mapped.weekly_quantities), 14)
        self.assertEqual(mapped.forecast_id, 501)  # the id of h=1, the anchor of the series
        self.assertEqual(mapped.model_version, 3)
        self.assertIs(mapped.method_used, MethodUsed.BASELINE)
        self.assertEqual(mapped.weekly_quantities[0], Decimal("7.5"))

    def test_input_order_does_not_matter(self) -> None:
        rows = forecast()
        self.assertEqual(map_forecast(list(reversed(rows)), A), map_forecast(rows, A))

    def test_missing_series_is_none(self) -> None:
        self.assertIsNone(map_forecast([], A))

    def test_non_primary_rows_are_ignored(self) -> None:
        self.assertIsNone(map_forecast(forecast(primary=False), A))
        mixed = forecast("5") + forecast("99", start_id=900, model=4, primary=False)
        mapped = map_forecast(mixed, A)
        self.assertEqual(set(mapped.weekly_quantities), {Decimal("5")})
        self.assertEqual(mapped.model_version, 3)

    def test_wrong_length_gap_duplicate_or_mixed_versions_fail(self) -> None:
        bad = {
            "short": forecast(weeks=13),
            "long": forecast(weeks=15),
            "shifted": forecast(as_of=A + DAY),
            "duplicate": forecast()[:13] + [forecast()[12]],
            "mixed": forecast()[:7] + forecast(model=4)[7:],
            "daily": [dataclasses.replace(r, granularity="DAILY") for r in forecast()],
            "model": [dataclasses.replace(r, method_used="MODEL") for r in forecast()],
        }
        for name, rows in bad.items():
            with self.subTest(name), self.assertRaises(AdapterError) as caught:
                map_forecast(rows, A)
            self.assertEqual(caught.exception.code, "INVALID_FORECAST_SERIES")


class BuildEvaluationInputTest(unittest.TestCase):
    def build(self, **overrides: object) -> EvaluationInput:
        arguments = {
            "as_of_date": A,
            "product": product(),
            "relations": [relation()],
            "inventory": inventory(),
            "order_lines": observations(),
            "consumption": consumption(),
            "forecast_rows": forecast(),
        }
        arguments.update(overrides)
        return build_evaluation_input(**arguments)

    def test_blocks_in_contract_order_with_u1_policy(self) -> None:
        built = self.build()
        self.assertEqual(
            [f.name for f in dataclasses.fields(built)],
            ["as_of_date", "product", "supplier_relations", "inventory", "open_lines",
             "lead_time_observations", "consumption", "forecast", "policy"],
        )
        self.assertIs(built.policy, V1_PROVISIONAL_PARAMETERS)
        self.assertEqual(built.policy.policy_set, "V1_PROVISIONAL")

    def test_observations_only_of_related_suppliers(self) -> None:
        built = self.build(order_lines=observations(7) + observations(8))
        self.assertEqual({o.supplier_id for o in built.lead_time_observations}, {7})

    def test_without_forecast_rows_the_forecast_is_none(self) -> None:
        self.assertIsNone(self.build(forecast_rows=[]).forecast)


if __name__ == "__main__":
    unittest.main()
