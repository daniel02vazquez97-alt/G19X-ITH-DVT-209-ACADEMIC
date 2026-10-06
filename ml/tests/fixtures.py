"""Small synthetic datasets written to a temporary directory, with known behaviour.

Products (one location):

* 1 — active, smooth weekly pattern from 2023-01-01;
* 2 — active, intermittent: demand only one week out of three;
* 3 — active, history from 2023-06-01 (seasonal naïve needs 63 weeks: not eligible at early cuts);
* 4 — inactive, valid until 2024-06-30 (discontinued; the snapshot rule excludes it everywhere).

Rows after the holdout limit (2025-09-24) exist on purpose: the loader must discard them.
``demand.csv`` exists with content that cannot be parsed: reading it would fail loudly.
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
import tempfile
from collections.abc import Callable
from pathlib import Path

START = _dt.date(2023, 1, 1)
END = _dt.date(2025, 12, 31)
ONE_DAY = _dt.timedelta(days=1)

PRODUCTS = {
    1: (True, START, None),
    2: (True, START, None),
    3: (True, _dt.date(2023, 6, 1), None),
    4: (False, START, _dt.date(2024, 6, 30)),
}


def default_quantity(product: int, day: _dt.date) -> int:
    index = (day - START).days
    if product == 1:
        return 10 + (index % 7) + (index // 7) % 3
    if product == 2:
        return 6 if (index // 7) % 3 == 0 else 0
    if product == 3:
        return 4 + (index % 5)
    return 3


def default_stockout(product: int, day: _dt.date) -> bool:
    return product == 1 and (day - START).days % 29 == 0


def _write(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


# (order id, supplier, issued, receipts [(date, quantity)], ordered quantity, product)
DEFAULT_ORDERS: list[tuple[int, int, str, list[tuple[str, int]], int, int]] = [
    (1, 1, "2023-02-01", [("2023-02-13", 50)], 50, 1),  # 12 days
    (2, 1, "2023-05-01", [("2023-05-11", 30), ("2023-05-18", 20)], 50, 1),  # 17 days, split
    (3, 1, "2023-09-01", [("2023-09-12", 40)], 40, 2),  # 11 days
    (4, 1, "2024-01-10", [("2024-01-30", 40)], 40, 3),  # 20 days
    (5, 1, "2024-02-01", [("2024-02-10", 10)], 40, 1),  # never completed
    (6, 1, "2025-09-10", [("2025-09-20", 10), ("2025-10-02", 30)], 40, 1),  # completes after the limit
    (7, 2, "2023-03-01", [("2023-03-08", 5)], 5, 4),
]


def write_dataset(
    directory: Path,
    quantity: Callable[[int, _dt.date], int] = default_quantity,
    stockout: Callable[[int, _dt.date], bool] = default_stockout,
    orders: list | None = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(
        json.dumps({"dataset_version": "ds-fixture", "data_origin": "SYNTHETIC"}), encoding="utf-8"
    )
    (directory / "demand.csv").write_text("NOT A CSV THAT F5a MAY READ\x00", encoding="utf-8")
    _write(directory / "locations.csv", ["id", "code", "name", "type", "is_active", "data_origin"],
           [[1, "LOC-001", "L1", "MAIN_WAREHOUSE", "true", "SYNTHETIC"]])
    _write(
        directory / "products.csv",
        ["id", "sku", "is_active", "valid_from", "valid_to", "data_origin"],
        [[p, f"SKU-{p}", str(a).lower(), f.isoformat(), t.isoformat() if t else "", "SYNTHETIC"]
         for p, (a, f, t) in PRODUCTS.items()],
    )
    rows = []
    row_id = 1
    for p, (_active, first, last) in PRODUCTS.items():
        day = first
        while day <= (last or END):
            rows.append([row_id, p, 1, day.isoformat(), quantity(p, day), "", str(stockout(p, day)).lower(), "SYNTHETIC"])
            row_id += 1
            day += ONE_DAY
    _write(directory / "consumption.csv",
           ["id", "product_id", "location_id", "occurred_on", "quantity", "channel", "is_stockout_affected", "data_origin"], rows)
    _write(
        directory / "product_suppliers.csv",
        ["id", "product_id", "supplier_id", "agreed_lead_time_days", "moq", "order_multiple", "unit_cost",
         "is_preferred", "is_active", "data_origin"],
        [[1, 1, 1, 10, 0, 1, 1, "true", "true", "SYNTHETIC"],
         [2, 2, 1, 10, 0, 1, 1, "true", "true", "SYNTHETIC"],
         [3, 3, 1, 10, 0, 1, 1, "true", "true", "SYNTHETIC"],
         [4, 4, 2, 7, 0, 1, 1, "false", "false", "SYNTHETIC"]],
    )
    orders = DEFAULT_ORDERS if orders is None else orders
    _write(directory / "purchase_orders.csv", ["id", "supplier_id", "location_id", "status", "issued_at", "data_origin"],
           [[o, s, 1, "RECEIVED", f"{issued}T00:00:00Z", "SYNTHETIC"] for o, s, issued, _r, _q, _p in orders])
    # The snapshot column quantity_received is deliberately wrong: F5a must not read it.
    _write(directory / "purchase_order_items.csv",
           ["id", "purchase_order_id", "product_id", "quantity_ordered", "quantity_received", "data_origin"],
           [[o, o, p, q, 999999, "SYNTHETIC"] for o, _s, _i, _r, q, p in orders])
    receipts = []
    rid = 1
    for o, _s, _i, recs, _q, _p in orders:
        for day, qty in recs:
            receipts.append([rid, o, f"{day}T00:00:00Z", qty, "", "SYNTHETIC"])
            rid += 1
    _write(directory / "purchase_order_receipts.csv",
           ["id", "purchase_order_item_id", "received_at", "quantity_received", "quality_rejected", "data_origin"], receipts)
    return directory


class TempDataset:
    """Context manager: a fixture dataset in a fresh temporary directory."""

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        return write_dataset(Path(self._tmp.name) / "ds", **self.kwargs)

    def __exit__(self, *exc) -> None:
        self._tmp.cleanup()
