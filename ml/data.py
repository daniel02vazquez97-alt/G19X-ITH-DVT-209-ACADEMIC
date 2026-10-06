"""Read-only, as-of access to a published dataset directory (CSV + ``manifest.json``).

* Only the files in ``READ_FILES`` are ever opened. ``demand.csv`` (latent demand) is evaluation-only
  for the `DT-011` study and is never an input of F5a (`DT-034`, `DT-076` point 2).
* Holdout guard (`DT-075` point 4): every dated row after ``LAST_READABLE_DATE`` is discarded while
  parsing and never kept; any request for a later date raises `HoldoutAccessError`.
* Nothing is written anywhere and no database is used (`DT-072`).

Lead-time observations follow the U4 rule (a line fully received, completion = its last receipt;
`app.runs.recommendation_inputs.map_lead_time_observations`) but are rebuilt from the receipts dated
up to the readable limit, so the snapshot column ``purchase_order_items.quantity_received`` (which
includes later receipts) is never read. For consistent data both rules give the same observations.
"""

from __future__ import annotations

import bisect
import csv
import datetime as _dt
import json
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from app.supply_engine import LeadTimeObservation, SupplierRelation

from .cuts import LAST_READABLE_DATE, check_readable

#: The only files F5a reads. ``demand.csv`` is deliberately absent.
READ_FILES = (
    "manifest.json",
    "products.csv",
    "locations.csv",
    "consumption.csv",
    "product_suppliers.csv",
    "purchase_orders.csv",
    "purchase_order_items.csv",
    "purchase_order_receipts.csv",
    "inventory_movements.csv",  # F5b: on_hand at the first cut (DT-080 point 5)
)
FORBIDDEN_FILES = frozenset({"demand.csv"})

SeriesKey = tuple[int, int]  # (product_id, location_id)
_ONE_DAY = _dt.timedelta(days=1)


class DatasetError(ValueError):
    """The dataset cannot be read without inventing data."""


@dataclass(frozen=True, slots=True)
class ProductRecord:
    product_id: int
    is_active: bool
    valid_from: _dt.date
    valid_to: _dt.date | None

    def valid_on(self, day: _dt.date) -> bool:
        return self.valid_from <= day and (self.valid_to is None or day <= self.valid_to)


@dataclass(frozen=True, slots=True)
class DailyRow:
    """One day of observed consumption (satisfied demand) with its stockout flag."""

    day: _dt.date
    quantity: Decimal
    stockout: bool


class Dataset:
    """In-memory, read-only view of the dataset up to ``LAST_READABLE_DATE``."""

    def __init__(
        self,
        dataset_version: str,
        data_origin: str,
        products: dict[int, ProductRecord],
        location_ids: tuple[int, ...],
        consumption: dict[SeriesKey, tuple[DailyRow, ...]],
        relations: dict[int, tuple[SupplierRelation, ...]],
        lead_time_observations: tuple[LeadTimeObservation, ...],
    ) -> None:
        self.dataset_version = dataset_version
        self.data_origin = data_origin
        self.products = products
        self.location_ids = location_ids
        self._consumption = consumption
        self._days = {key: [row.day for row in rows] for key, rows in consumption.items()}
        self.relations = relations
        self.lead_time_observations = lead_time_observations

    @property
    def readable_until(self) -> _dt.date:
        return LAST_READABLE_DATE

    def series_keys(self) -> list[SeriesKey]:
        """Every product × location pair, ordered (the U3 candidate set)."""
        return [(p, loc) for p in sorted(self.products) for loc in self.location_ids]

    def last_day(self, key: SeriesKey) -> _dt.date | None:
        days = self._days.get(key)
        return days[-1] if days else None

    def history(self, key: SeriesKey, as_of: _dt.date) -> tuple[DailyRow, ...]:
        """Rows with ``day ≤ as_of`` (training data of a cut)."""
        check_readable(as_of)
        rows = self._consumption.get(key, ())
        end = bisect.bisect_right(self._days.get(key, []), as_of)
        return rows[:end]

    def window(self, key: SeriesKey, first: _dt.date, last: _dt.date) -> tuple[DailyRow, ...] | None:
        """Rows of ``[first, last]`` if every day is observed; ``None`` otherwise (no truth)."""
        check_readable(last)
        days = self._days.get(key, [])
        start = bisect.bisect_left(days, first)
        end = bisect.bisect_right(days, last)
        rows = self._consumption.get(key, ())[start:end]
        if len(rows) != (last - first).days + 1:
            return None
        return rows


def _open_csv(path: Path) -> Iterator[dict[str, str]]:
    if path.name in FORBIDDEN_FILES or path.name not in READ_FILES:
        raise DatasetError(f"{path.name} is not an input of F5a")
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def _bool(text: str, field: str) -> bool:
    if text == "true":
        return True
    if text == "false":
        return False
    raise DatasetError(f"{field}: {text!r} is not a boolean")


def _date(text: str) -> _dt.date:
    return _dt.date.fromisoformat(text)


def _utc_date(text: str) -> _dt.date:
    """Calendar date in UTC of an ISO timestamp (naive timestamps are UTC, `docs/04` §9.7)."""
    value = _dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.tzinfo is not None:
        value = value.astimezone(_dt.timezone.utc)
    return value.date()


def load_dataset(directory: Path | str) -> Dataset:
    """Load ``directory`` read-only, discarding every dated row after ``LAST_READABLE_DATE``."""
    base = Path(directory)
    manifest_path = base / "manifest.json"
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    limit = LAST_READABLE_DATE

    products = {}
    for row in _open_csv(base / "products.csv"):
        pid = int(row["id"])
        products[pid] = ProductRecord(
            product_id=pid,
            is_active=_bool(row["is_active"], "products.is_active"),
            valid_from=_date(row["valid_from"]),
            valid_to=_date(row["valid_to"]) if row["valid_to"] else None,
        )
    location_ids = tuple(sorted(int(row["id"]) for row in _open_csv(base / "locations.csv")))

    consumption: dict[SeriesKey, list[DailyRow]] = defaultdict(list)
    for row in _open_csv(base / "consumption.csv"):
        day = _date(row["occurred_on"])
        if day > limit:
            continue  # holdout: discarded on parse, never kept
        key = (int(row["product_id"]), int(row["location_id"]))
        consumption[key].append(
            DailyRow(day, Decimal(row["quantity"]), _bool(row["is_stockout_affected"], "is_stockout_affected"))
        )
    ordered = {}
    for key, rows in consumption.items():
        rows.sort(key=lambda r: r.day)
        for previous, current in zip(rows, rows[1:]):
            if current.day == previous.day:
                raise DatasetError(f"consumption {key}: duplicate day {current.day}")
        ordered[key] = tuple(rows)

    relations: dict[int, list[SupplierRelation]] = defaultdict(list)
    for row in _open_csv(base / "product_suppliers.csv"):
        relations[int(row["product_id"])].append(
            SupplierRelation(
                supplier_id=int(row["supplier_id"]),
                is_active=_bool(row["is_active"], "product_suppliers.is_active"),
                is_preferred=_bool(row["is_preferred"], "product_suppliers.is_preferred"),
                moq=Decimal(row["moq"]),
                order_multiple=Decimal(row["order_multiple"]),
                agreed_lead_time_days=int(row["agreed_lead_time_days"]),
            )
        )
    relation_map = {p: tuple(sorted(rs, key=lambda r: r.supplier_id)) for p, rs in relations.items()}

    observations = _lead_time_observations(base, limit)
    return Dataset(
        dataset_version=str(manifest.get("dataset_version")),
        data_origin=str(manifest.get("data_origin")),
        products=dict(sorted(products.items())),
        location_ids=location_ids,
        consumption=ordered,
        relations=relation_map,
        lead_time_observations=observations,
    )


def _lead_time_observations(base: Path, limit: _dt.date) -> tuple[LeadTimeObservation, ...]:
    """Lines whose receipts dated ``≤ limit`` add up to the ordered quantity (U4 rule, as of ``limit``)."""
    headers = {}
    for row in _open_csv(base / "purchase_orders.csv"):
        issued = _utc_date(row["issued_at"])
        if issued > limit:
            continue
        headers[int(row["id"])] = (int(row["supplier_id"]), issued)
    items = {}
    for row in _open_csv(base / "purchase_order_items.csv"):
        order = int(row["purchase_order_id"])
        if order in headers:
            items[int(row["id"])] = (order, Decimal(row["quantity_ordered"]))
    received: dict[int, Decimal] = defaultdict(Decimal)
    last: dict[int, _dt.date] = {}
    for row in _open_csv(base / "purchase_order_receipts.csv"):
        day = _utc_date(row["received_at"])
        if day > limit:
            continue  # holdout: discarded on parse, never kept
        item = int(row["purchase_order_item_id"])
        if item not in items:
            continue
        received[item] += Decimal(row["quantity_received"])
        if item not in last or day > last[item]:
            last[item] = day
    observations = []
    for item, (order, ordered_quantity) in items.items():
        if item in last and received[item] == ordered_quantity:
            supplier, issued = headers[order]
            observations.append(LeadTimeObservation(supplier_id=supplier, issued_on=issued, completed_on=last[item]))
    observations.sort(key=lambda o: (o.supplier_id, o.issued_on, o.completed_on))
    return tuple(observations)


def daily_window(first: _dt.date, days: int) -> tuple[_dt.date, _dt.date]:
    """``[first, first + days − 1]`` as an inclusive pair."""
    return first, first + _ONE_DAY * (days - 1)


# --- F5b: initial state of the Level 2 simulation (DT-080 point 5, OD-S1) ---------------------------


@dataclass(frozen=True, slots=True)
class ExogenousLine:
    """A real purchase-order line open at the first cut: an exogenous event, identical in every branch.

    ``received_at_cut`` counts the receipts dated ``≤ cut``; ``receipts_after`` lists the later real receipts
    up to the readable limit (holdout excluded).
    """

    purchase_order_id: int
    item_id: int
    product_id: int
    location_id: int
    supplier_id: int
    issued_on: _dt.date
    expected_on: _dt.date
    quantity_ordered: Decimal
    received_at_cut: Decimal
    receipts_after: tuple[tuple[_dt.date, Decimal], ...]

    @property
    def pending_at_cut(self) -> Decimal:
        return self.quantity_ordered - self.received_at_cut


def on_hand_at(directory: Path | str, cut: _dt.date) -> dict[SeriesKey, Decimal]:
    """``on_hand`` at the close of ``cut``: the sum of the movements dated ``≤ cut`` (`DT-038`, `DT-080` point 5)."""
    check_readable(cut)
    totals: dict[SeriesKey, Decimal] = defaultdict(Decimal)
    for row in _open_csv(Path(directory) / "inventory_movements.csv"):
        day = _utc_date(row["occurred_at"])
        if day > LAST_READABLE_DATE:
            continue  # holdout: discarded on parse, never kept
        if day <= cut:
            totals[(int(row["product_id"]), int(row["location_id"]))] += Decimal(row["quantity"])
    return dict(sorted(totals.items()))


def open_lines_at(directory: Path | str, cut: _dt.date) -> tuple[ExogenousLine, ...]:
    """Lines issued ``≤ cut``, not closed by ``cut`` and with receipts ``≤ cut`` below the ordered quantity.

    The header ``status`` is a snapshot of the dataset end and is not read; ``closed_at`` (receipt completion
    or cancellation) is compared with ``cut``. Rows after the readable limit are discarded on parse.
    """
    check_readable(cut)
    base = Path(directory)
    headers = {}
    for row in _open_csv(base / "purchase_orders.csv"):
        issued = _utc_date(row["issued_at"])
        if issued > cut:
            continue  # real orders issued after the first cut are discarded (OD-S1)
        closed = _utc_date(row["closed_at"]) if row["closed_at"] else None
        if closed is not None and closed <= cut:
            continue
        headers[int(row["id"])] = (int(row["supplier_id"]), int(row["location_id"]), issued, _utc_date(row["expected_at"]))
    receipts: dict[int, list[tuple[_dt.date, Decimal]]] = defaultdict(list)
    for row in _open_csv(base / "purchase_order_receipts.csv"):
        day = _utc_date(row["received_at"])
        if day > LAST_READABLE_DATE:
            continue  # holdout: discarded on parse, never kept
        receipts[int(row["purchase_order_item_id"])].append((day, Decimal(row["quantity_received"])))
    lines = []
    for row in _open_csv(base / "purchase_order_items.csv"):
        order = int(row["purchase_order_id"])
        if order not in headers:
            continue
        supplier, location, issued, header_expected = headers[order]
        item = int(row["id"])
        ordered = Decimal(row["quantity_ordered"])
        got = sum((q for d, q in receipts.get(item, []) if d <= cut), Decimal(0))
        if got >= ordered:
            continue
        after = tuple(sorted((d, q) for d, q in receipts.get(item, []) if d > cut))
        lines.append(
            ExogenousLine(
                purchase_order_id=order,
                item_id=item,
                product_id=int(row["product_id"]),
                location_id=location,
                supplier_id=supplier,
                issued_on=issued,
                expected_on=_utc_date(row["expected_at"]) if row["expected_at"] else header_expected,
                quantity_ordered=ordered,
                received_at_cut=got,
                receipts_after=after,
            )
        )
    lines.sort(key=lambda line: (line.purchase_order_id, line.item_id))
    return tuple(lines)


def preferred_unit_costs(directory: Path | str) -> dict[int, Decimal]:
    """``unit_cost`` of the active and preferred relation of each product (inventory value, `DT-080` point 9)."""
    costs = {}
    for row in _open_csv(Path(directory) / "product_suppliers.csv"):
        if row["is_active"] == "true" and row["is_preferred"] == "true" and row.get("unit_cost"):
            costs[int(row["product_id"])] = Decimal(row["unit_cost"])
    return dict(sorted(costs.items()))
