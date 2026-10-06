"""F5b parity: engine inputs = pure U4 adapter; point forecasts = U3 ``forecast``; incremental weeks = U3."""

from __future__ import annotations

import datetime as _dt
import unittest
from decimal import Decimal
from fractions import Fraction

from app.forecasting import BASELINES, build_request, forecast
from app.forecasting.weekly import weekly_totals
from app.runs.recommendation_inputs import (
    ConsumptionRow,
    ForecastRow,
    InventoryRow,
    OrderLineRow,
    ProductRow,
    RelationRow,
    build_evaluation_input,
)
from app.supply_engine import V1_PROVISIONAL_PARAMETERS, LeadTimeObservation, MethodUsed, SupplierRelation
from ml.config import F5aConfig
from ml.data import ProductRecord
from ml.simulation.engine_inputs import LineState, evaluation_input
from ml.simulation.forecasters import WeeklyHistory, point_forecast

D = Decimal
UTC = _dt.timezone.utc
AS_OF = _dt.date(2024, 6, 5)


def _ts(d: _dt.date) -> _dt.datetime:
    return _dt.datetime(d.year, d.month, d.day, tzinfo=UTC)


class EngineInputParityTest(unittest.TestCase):
    def test_same_evaluation_input_as_the_u4_adapter(self) -> None:
        start = AS_OF - _dt.timedelta(days=99)
        quantities = [D(10 + (i % 4)) for i in range(100)]
        product = ProductRecord(5, True, start, None)
        relations = (SupplierRelation(3, True, True, D(10), D(5), 12), SupplierRelation(1, False, False, D(0), D(1), 4))
        observations = (
            LeadTimeObservation(3, _dt.date(2024, 1, 2), _dt.date(2024, 1, 15)),
            LeadTimeObservation(3, _dt.date(2024, 2, 2), _dt.date(2024, 2, 12)),
        )
        lines = [
            LineState(77, 2, 3, _dt.date(2024, 6, 9), D(30)),
            LineState(1_000_000_001, 1, 3, _dt.date(2024, 6, 15), D(45)),
        ]
        points = tuple(D("70.5") + i for i in range(14))
        mine = evaluation_input(
            AS_OF, product, 1, relations, D(42), lines, observations, start, quantities, points, 7, 2,
            MethodUsed.BASELINE, V1_PROVISIONAL_PARAMETERS,
        )
        order_rows = [
            OrderLineRow(l.purchase_order_id, l.item_id, 5, l.supplier_id, 1, "ISSUED", l.quantity_pending, D(0),
                         _ts(AS_OF - _dt.timedelta(days=3)), _ts(l.expected_on), None, None)
            for l in lines
        ] + [
            OrderLineRow(900 + i, 1, 5, o.supplier_id, 1, "RECEIVED", D(10), D(10), _ts(o.issued_on), _ts(o.issued_on), None, _ts(o.completed_on))
            for i, o in enumerate(observations)
        ]
        forecast_rows = [
            ForecastRow(7 if k == 0 else 1000 + k, AS_OF + _dt.timedelta(days=1 + 7 * k), AS_OF + _dt.timedelta(days=8 + 7 * k),
                        "WEEKLY", points[k], "BASELINE", 2, True)
            for k in range(14)
        ]
        u4 = build_evaluation_input(
            AS_OF,
            ProductRow(5, 1, True, start, None),
            [RelationRow(r.supplier_id, r.is_active, r.is_preferred, r.moq, r.order_multiple, r.agreed_lead_time_days) for r in relations],
            InventoryRow(D(42), D(0), D(75)),
            order_rows,
            [ConsumptionRow(start + _dt.timedelta(days=i), q) for i, q in enumerate(quantities)],
            forecast_rows,
        )
        self.assertEqual(mine, u4)

    def test_float_is_refused(self) -> None:
        product = ProductRecord(5, True, AS_OF, None)
        with self.assertRaises(TypeError):
            evaluation_input(AS_OF, product, 1, (), 4.0, [], (), AS_OF, [D(1)], None, 1, 1, MethodUsed.BASELINE,  # type: ignore[arg-type]
                             V1_PROVISIONAL_PARAMETERS)


class ForecasterParityTest(unittest.TestCase):
    def test_points_equal_u3_forecast_for_every_history_length(self) -> None:
        for weeks in (20, 24, 25, 36, 37, 62, 63, 70):
            days = 7 * weeks + 3
            as_of = _dt.date(2024, 6, 5)
            rows = [(as_of - _dt.timedelta(days=days - 1 - i), D((i * 7) % 13 + (i % 5)), False) for i in range(days)]
            result = forecast(build_request(1, 1, as_of, rows))
            history = WeeklyHistory([q for _, q, _ in rows])
            for definition in BASELINES:
                series = result.series_for(definition.name)
                mine = point_forecast(definition.name, history, F5aConfig())
                expected = None if series is None else tuple(p.predicted_quantity for p in series.periods)
                self.assertEqual(mine, expected, (weeks, definition.name))

    def test_incremental_weeks_equal_weekly_totals(self) -> None:
        daily = [D(i % 9) for i in range(7 * 30 + 4)]
        history = WeeklyHistory(daily)
        for k in range(5):
            week = [D((k * 3 + j) % 11) for j in range(7)]
            daily += week
            history.append_week(week)
            self.assertEqual(history.weeks, weekly_totals([Fraction(q) for q in daily]))


if __name__ == "__main__":
    unittest.main()
