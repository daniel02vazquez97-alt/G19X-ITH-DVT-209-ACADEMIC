"""``L + R`` comes from the U1 rules and the demand over it from ``demand_over_horizon``."""

from __future__ import annotations

import datetime as _dt
import unittest
from decimal import Decimal
from fractions import Fraction
from unittest import mock

from app.supply_engine import (
    V1_PROVISIONAL_PARAMETERS,
    ConsumptionSeries,
    EvaluationInput,
    Forecast,
    Inventory,
    MethodUsed,
    Product,
    evaluate,
)
from app.supply_engine import rules
from ml.backtest import LR, observations_of, run_series_cut
from ml.config import F5aConfig
from ml.data import load_dataset
from ml.models import SES_NAME
from ml.protection import demand_over, protection_horizon
from ml.tests.fixtures import TempDataset

CUT = _dt.date(2024, 3, 27)


class ProtectionTest(unittest.TestCase):
    def setUp(self) -> None:
        with TempDataset() as path:
            self.ds = load_dataset(path)

    def test_lead_time_from_the_u1_window(self) -> None:
        horizon = protection_horizon(self.ds.relations[1], self.ds.lead_time_observations, CUT, V1_PROVISIONAL_PARAMETERS)
        assert horizon is not None
        # Observations ≤ cut: 12, 17, 11, 20 days → median 14.5 → ceil 15; R = 7.
        self.assertEqual((horizon.lead_time_days, horizon.observation_count, horizon.coverage_days), (15, 4, 22))
        self.assertNotEqual(horizon.coverage_days % 7, 0)
        early = protection_horizon(self.ds.relations[1], self.ds.lead_time_observations, _dt.date(2023, 6, 1), V1_PROVISIONAL_PARAMETERS)
        assert early is not None
        self.assertEqual((early.lead_time_days, early.lead_time_source.value), (10, "AGREED_FALLBACK"))  # n = 2 < 3
        self.assertIsNone(protection_horizon(self.ds.relations[4], self.ds.lead_time_observations, CUT, V1_PROVISIONAL_PARAMETERS))

    def test_demand_over_l_plus_r_calls_the_engine_function(self) -> None:
        sc = run_series_cut(self.ds, (1, 1), CUT, F5aConfig())
        with mock.patch.object(rules, "demand_over_horizon", wraps=rules.demand_over_horizon) as spy:
            obs = [o for o in observations_of(sc, F5aConfig()) if o.horizon == LR]
        self.assertEqual(len(obs), 4)
        self.assertEqual(spy.call_count, 4)
        for call in spy.call_args_list:
            weekly, days = call.args
            self.assertEqual(days, 22)
            self.assertTrue(all(isinstance(w, Fraction) for w in weekly))
        points = sc.forecasts[SES_NAME].points
        expected = sum(Fraction(p) for p in points[:3]) + Fraction(1, 7) * Fraction(points[3])
        ses_obs = next(o for o in obs if o.model == SES_NAME)
        self.assertEqual(ses_obs.forecast, float(expected))

    def test_same_l_h_and_ddh_as_evaluate(self) -> None:
        """Cross-check with the engine itself: `evaluate()` reaches the same L, H and DDH."""
        sc = run_series_cut(self.ds, (1, 1), CUT, F5aConfig())
        history = self.ds.history((1, 1), CUT)
        for name, fc in sc.forecasts.items():
            result = evaluate(
                EvaluationInput(
                    as_of_date=CUT,
                    product=Product(1, 1, True, _dt.date(2023, 1, 1), None),
                    supplier_relations=self.ds.relations[1],
                    inventory=Inventory(on_hand=Decimal(0), reserved=Decimal(0), total_in_transit=Decimal(0)),
                    open_lines=(),
                    lead_time_observations=self.ds.lead_time_observations,
                    consumption=ConsumptionSeries(history[0].day, tuple(r.quantity for r in history)),
                    forecast=Forecast(CUT + _dt.timedelta(days=1), fc.points, 1, 1, MethodUsed.BASELINE),
                    policy=V1_PROVISIONAL_PARAMETERS,
                )
            )
            b = result.breakdown
            assert sc.protection is not None
            self.assertEqual(b.lead_time_days, sc.protection.lead_time_days, name)
            self.assertEqual(b.coverage_horizon_days, sc.protection.coverage_days, name)
            self.assertEqual(b.demand_over_horizon, demand_over(fc.points, sc.protection.coverage_days), name)

    def test_float_is_refused_at_the_boundary(self) -> None:
        with self.assertRaises(TypeError):
            demand_over([1.5] * 14, 22)  # type: ignore[list-item]


if __name__ == "__main__":
    unittest.main()
