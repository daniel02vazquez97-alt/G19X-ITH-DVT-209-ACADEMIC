"""Read-only loader: allowed files only and the U4 lead-time rule rebuilt as of the limit."""

from __future__ import annotations

import datetime as _dt
import unittest
from decimal import Decimal
from pathlib import Path

from app.runs.recommendation_inputs import OrderLineRow, map_lead_time_observations
from ml.data import DatasetError, _open_csv, load_dataset
from ml.tests.fixtures import DEFAULT_ORDERS, TempDataset


def _ts(text: str) -> _dt.datetime:
    return _dt.datetime.fromisoformat(f"{text}T00:00:00+00:00")


class LoaderTest(unittest.TestCase):
    def test_forbidden_and_unknown_files_are_refused(self) -> None:
        with TempDataset() as path:
            for name in ("demand.csv", "inventory.csv"):
                with self.assertRaises(DatasetError):
                    list(_open_csv(Path(path) / name))

    def test_lead_time_observations_match_the_u4_adapter(self) -> None:
        """Same observations as `map_lead_time_observations` for lines whose receipts are all ≤ the limit."""
        with TempDataset() as path:
            ds = load_dataset(path)
        visible = [o for o in DEFAULT_ORDERS if all(day <= "2025-09-24" for day, _ in o[3])]
        rows = [
            OrderLineRow(
                purchase_order_id=order,
                item_id=order,
                product_id=product,
                supplier_id=supplier,
                location_id=1,
                status="RECEIVED",
                quantity_ordered=Decimal(ordered),
                quantity_received=Decimal(sum(q for _, q in receipts)),
                issued_at=_ts(issued),
                header_expected_at=_ts(issued),
                item_expected_at=None,
                last_received_at=_ts(max(day for day, _ in receipts)),
            )
            for order, supplier, issued, receipts, ordered, product in visible
        ]
        expected = map_lead_time_observations(rows, {1, 2})
        self.assertEqual(ds.lead_time_observations, expected)
        self.assertEqual(len(expected), 5)  # order 5 is incomplete, order 6 completes after the limit

    def test_snapshot_column_quantity_received_is_ignored(self) -> None:
        # The fixture writes 999999 in purchase_order_items.quantity_received; observations still exist.
        with TempDataset() as path:
            ds = load_dataset(path)
        self.assertTrue(ds.lead_time_observations)

    def test_metadata(self) -> None:
        with TempDataset() as path:
            ds = load_dataset(path)
        self.assertEqual(ds.dataset_version, "ds-fixture")
        self.assertEqual(ds.data_origin, "SYNTHETIC")
        self.assertEqual(ds.series_keys(), [(1, 1), (2, 1), (3, 1), (4, 1)])


if __name__ == "__main__":
    unittest.main()
