"""End-to-end evaluations with hand-computed results (`docs/06` §14, §16.8, §16.10, §16.11).

Run from ``backend/``::

    python3 -m unittest discover -s tests -t .

Scope: the composed evaluation — cases 8 to 10 of `DT-031`; the cases of `docs/06` §14 in their V1
version (§16.8); the three limit cases of `DT-P20`; reasons, evaluability and canonical order
(`DT-051`); `PRODUCT_OUT_OF_VALIDITY` cases A and B (`DT-P22`); the partial-output frontier
(`DT-053`); an irrational ``σ_H`` reported with 28 digits (§16.6 point 7).

Base input (`builders.evaluation`): agreed lead time 14, no observations → ``L = 14`` (fallback),
``H = 21``; forecast ``(40, 40, 40, 40)`` → ``DDH = 120``, ``DDLT = 80``; constant consumption 5 for
60 days → 40 windows of 105 → ``A = 0`` and ``σ_H = 0``; open lines 10 (day +10, effective) and 20
(day +46, beyond ``H``) → ``IT_efectivo = 10``, ``IT_total = 30``; ``on_hand = 17`` →
``IP_decisión = 27``; ``x = 93`` → ``Q_final = 100`` with ``MOQ 25`` and ``M 10``.
"""

from __future__ import annotations

import datetime as dt
import unittest
from decimal import Decimal
from fractions import Fraction

from app.supply_engine import (
    ConsumptionSeries,
    Flag,
    Inventory,
    LeadTimeSource,
    Outcome,
    PolicyParameter,
    Reason,
    evaluate,
)

from . import builders as b

DESCRIPTIVE_FIELDS = (
    "supplier_id",
    "lead_time_days",
    "lead_time_source",
    "lead_time_observation_count",
    "uncapped_lead_time_days",
    "review_period_days",
    "coverage_horizon_days",
    "demand_conversion_rule",
    "demand_over_lead_time",
    "demand_over_horizon",
    "sigma_window_count",
    "sigma_h",
    "z",
    "safety_stock",
    "target_level",
    "on_hand",
    "reserved",
    "total_in_transit",
    "effective_in_transit",
    "effective_lines",
    "inventory_position_decision",
    "inventory_position_accounting",
    "moq",
    "order_multiple",
    "s1",
    "s2",
    "a",
    "b",
    "d",
    "p",
)
DECISION_FIELDS = ("raw_need", "q_moq", "q_final")


class BaseScenarioTest(unittest.TestCase):
    def test_full_breakdown_by_hand(self) -> None:
        result = evaluate(b.evaluation())
        self.assertEqual(result.outcome, Outcome.RECOMMEND)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.missing_policy_parameters, ())
        self.assertEqual(
            result.flags,
            (Flag.LEAD_TIME_AGREED_FALLBACK, Flag.ORDER_MULTIPLE_ROUNDING, Flag.UNCOUNTED_TRANSIT),
        )
        k = result.breakdown
        expected = {
            "as_of_date": b.AS_OF,
            "horizon_start": b.HORIZON_START,
            "supplier_id": 7,
            "lead_time_days": 14,
            "lead_time_source": LeadTimeSource.AGREED_FALLBACK,
            "lead_time_observation_count": 0,
            "uncapped_lead_time_days": 14,
            "review_period_days": 7,
            "coverage_horizon_days": 21,
            "demand_conversion_rule": "V1-04",
            "demand_over_lead_time": Fraction(80),
            "demand_over_horizon": Fraction(120),
            "sigma_window_count": 40,
            "sigma_h": Fraction(0),
            "z": Fraction(33, 20),
            "safety_stock": Fraction(0),
            "target_level": Fraction(120),
            "on_hand": Fraction(17),
            "reserved": Fraction(0),
            "total_in_transit": Fraction(30),
            "effective_in_transit": Fraction(10),
            "inventory_position_decision": Fraction(27),
            "inventory_position_accounting": Fraction(47),
            "moq": Fraction(25),
            "order_multiple": Fraction(10),
            "raw_need": Fraction(93),
            "q_moq": Fraction(93),
            "q_final": Fraction(100),
            "s1": 4200,
            "s2": 441000,
            "a": 0,
            "b": 0,
            "d": 800,
            "p": Fraction(93),
        }
        for name, value in expected.items():
            with self.subTest(term=name):
                self.assertEqual(getattr(k, name), value)
        self.assertEqual([line.purchase_order_id for line in k.effective_lines], [1])
        self.assertEqual(result.forecast_id, 9001)
        self.assertEqual(result.policy_set, "V1_PROVISIONAL")

    def test_irrational_sigma_is_reported_with_28_digits(self) -> None:
        # Consumption i % 5 over 60 days, H = 21: A = 3200 = 40²·2 → σ_H = √2.
        inputs = b.evaluation(consumption=b.consumption([i % 5 for i in range(60)]))
        result = evaluate(inputs)
        k = result.breakdown
        self.assertEqual((k.s1, k.s2, k.a, k.b, k.d), (1680, 70640, 3200, 1089 * 3200, 800))
        self.assertEqual(k.sigma_h, Decimal("1.414213562373095048801688724"))
        self.assertEqual(k.safety_stock, Decimal("2.333452377915606830522786395"))
        self.assertEqual(k.target_level, Decimal("122.3334523779156068305227864"))
        self.assertEqual(k.raw_need, Decimal("95.33345237791560683052278639"))
        self.assertEqual(k.q_moq, k.raw_need)
        self.assertEqual(k.q_final, Fraction(100))
        self.assertIsInstance(k.q_final, Fraction)
        self.assertEqual(result.outcome, Outcome.RECOMMEND)


class Dt031CasesTest(unittest.TestCase):
    def test_case_8_uses_the_preferred_relation(self) -> None:
        relations = (
            b.relation(supplier_id=8, is_preferred=False, moq=100, order_multiple=50, agreed_lead_time_days=30),
            b.relation(moq=25, order_multiple=10),
        )
        k = evaluate(b.evaluation(supplier_relations=relations)).breakdown
        self.assertEqual((k.supplier_id, k.moq, k.order_multiple, k.lead_time_days), (7, 25, 10, 14))
        self.assertEqual(k.q_final, Fraction(100))

    def test_case_9_no_preferred_relation(self) -> None:
        relations = (b.relation(is_preferred=False),)
        result = evaluate(b.evaluation(supplier_relations=relations))
        self.assertEqual(result.outcome, Outcome.NOT_CALCULABLE)
        self.assertEqual(result.reasons, (Reason.NO_ACTIVE_PREFERRED_SUPPLIER,))
        self.assertIsNone(result.breakdown.coverage_horizon_days)

    def test_case_10_no_active_relation(self) -> None:
        relations = (b.relation(is_active=False),)
        result = evaluate(b.evaluation(supplier_relations=relations))
        self.assertEqual(result.reasons, (Reason.NO_ACTIVE_PREFERRED_SUPPLIER,))
        self.assertEqual(evaluate(b.evaluation(supplier_relations=())).reasons, result.reasons)

    def test_observed_lead_time_end_to_end(self) -> None:
        observations = b.observations_with_lead_times([10, 14, 12, 18])  # median 13
        k = evaluate(b.evaluation(lead_time_observations=observations)).breakdown
        self.assertEqual((k.lead_time_days, k.lead_time_source, k.coverage_horizon_days), (13, LeadTimeSource.OBSERVED, 20))

    def test_capped_agreed_fallback_end_to_end(self) -> None:
        inputs = b.evaluation(
            supplier_relations=(b.relation(moq=25, order_multiple=10, agreed_lead_time_days=120),),
            forecast=b.forecast([40] * 14),
            consumption=b.constant_consumption(days=200),
        )
        result = evaluate(inputs)
        k = result.breakdown
        self.assertEqual((k.uncapped_lead_time_days, k.lead_time_days, k.coverage_horizon_days), (120, 90, 97))
        self.assertIn(Flag.LEAD_TIME_AGREED_FALLBACK, result.flags)
        self.assertIn(Flag.LEAD_TIME_CAPPED, result.flags)


class Section14InV1Test(unittest.TestCase):
    """`docs/06` §14 with the V1 result (§16.8)."""

    def test_effective_transit_above_the_level(self) -> None:
        inputs = b.evaluation(open_lines=(b.line(1, b.day(10), 200),), inventory=Inventory(17, 0, 200))
        result = evaluate(inputs)
        self.assertEqual(result.outcome, Outcome.NO_NEED)
        self.assertEqual(result.breakdown.raw_need, Fraction(0))
        self.assertIsNone(result.breakdown.q_moq)
        self.assertIsNone(result.breakdown.q_final)
        self.assertNotIn(Flag.UNCOUNTED_TRANSIT, result.flags)

    def test_total_transit_above_the_level_but_effective_insufficient(self) -> None:
        inputs = b.evaluation(open_lines=(b.line(1, b.day(30), 200),), inventory=Inventory(17, 0, 200))
        result = evaluate(inputs)
        self.assertEqual(result.outcome, Outcome.RECOMMEND)
        self.assertIn(Flag.UNCOUNTED_TRANSIT, result.flags)
        self.assertEqual(result.breakdown.inventory_position_accounting, Fraction(217))
        self.assertEqual(result.breakdown.inventory_position_decision, Fraction(17))
        self.assertEqual(result.breakdown.q_final, Fraction(110))  # x = 103

    def test_lead_time_not_a_multiple_of_seven(self) -> None:
        inputs = b.evaluation(supplier_relations=(b.relation(moq=25, order_multiple=10, agreed_lead_time_days=10),))
        k = evaluate(inputs).breakdown
        self.assertEqual(k.coverage_horizon_days, 17)
        self.assertEqual(k.demand_over_horizon, Fraction(680, 7))
        self.assertEqual(k.demand_over_lead_time, Fraction(400, 7))
        self.assertEqual(k.raw_need, Fraction(491, 7))
        self.assertEqual(k.q_final, Fraction(80))

    def test_moq_above_the_need(self) -> None:
        result = evaluate(b.evaluation(inventory=Inventory(92, 0, 30)))  # x = 120 − 102 = 18
        self.assertEqual(result.breakdown.raw_need, Fraction(18))
        self.assertEqual(result.breakdown.q_moq, Fraction(25))
        self.assertEqual(result.breakdown.q_final, Fraction(30))
        self.assertIn(Flag.MOQ_APPLIED, result.flags)
        self.assertIn(Flag.ORDER_MULTIPLE_ROUNDING, result.flags)

    def test_large_order_multiple(self) -> None:
        inputs = b.evaluation(
            supplier_relations=(b.relation(moq=25, order_multiple=100),), inventory=Inventory(9, 0, 30)
        )
        self.assertEqual(evaluate(inputs).breakdown.q_final, Fraction(200))  # x = 101

    def test_without_forecast(self) -> None:
        result = evaluate(b.evaluation(forecast=None))
        self.assertEqual(result.reasons, (Reason.FORECAST_MISSING,))
        self.assertIsNone(result.forecast_id)
        self.assertIsNone(result.breakdown.demand_over_horizon)
        self.assertEqual(result.breakdown.coverage_horizon_days, 21)

    def test_inactive_product(self) -> None:
        result = evaluate(b.evaluation(product=b.product(is_active=False)))
        self.assertEqual(result.reasons, (Reason.PRODUCT_INACTIVE,))

    def test_zero_inventory_recommends_without_urgency(self) -> None:
        result = evaluate(b.evaluation(inventory=Inventory(0, 0, 30)))
        self.assertEqual(result.outcome, Outcome.RECOMMEND)
        self.assertEqual(result.breakdown.q_final, Fraction(110))
        self.assertFalse(hasattr(result, "urgency"))

    def test_negative_on_hand(self) -> None:
        result = evaluate(b.evaluation(inventory=Inventory(-1, 0, 30)))
        self.assertEqual(result.reasons, (Reason.NEGATIVE_ON_HAND,))

    def test_service_level_not_defined(self) -> None:
        result = evaluate(b.evaluation(policy=b.v1_policy(z=None)))
        self.assertEqual(result.reasons, (Reason.MISSING_POLICY_PARAMETER,))
        self.assertEqual(result.missing_policy_parameters, (PolicyParameter.Z,))
        self.assertIsNone(result.breakdown.safety_stock)
        self.assertEqual(result.breakdown.sigma_h, Fraction(0))

    def test_overdue_lines_are_excluded_and_flagged(self) -> None:
        lines = (b.line(1, b.day(0), 10), b.line(2, b.day(46), 20))
        result = evaluate(b.evaluation(open_lines=lines))
        self.assertIn(Flag.OVERDUE_ORDERS_EXCLUDED, result.flags)
        self.assertEqual(result.breakdown.effective_in_transit, Fraction(0))


class DtP20Test(unittest.TestCase):
    """`docs/06` §16.10."""

    def test_zero_forecast_without_variability_is_no_need(self) -> None:
        result = evaluate(b.evaluation(forecast=b.forecast([0, 0, 0, 0])))
        self.assertEqual(result.outcome, Outcome.NO_NEED)
        self.assertIn(Flag.ZERO_FORECAST_DEMAND, result.flags)

    def test_zero_forecast_with_variability_recommends(self) -> None:
        # Alternating 0, 2 over 60 days, H = 21: A = 1600, σ_H = 1, SS = 33/20; IP = 0.
        inputs = b.evaluation(
            forecast=b.forecast([0, 0, 0, 0]),
            consumption=b.consumption([0, 2] * 30),
            open_lines=(),
            inventory=Inventory(0, 0, 0),
        )
        result = evaluate(inputs)
        k = result.breakdown
        self.assertEqual((k.sigma_h, k.safety_stock, k.raw_need), (Fraction(1), Fraction(33, 20), Fraction(33, 20)))
        self.assertEqual(result.outcome, Outcome.RECOMMEND)
        self.assertEqual(k.q_final, Fraction(30))
        self.assertEqual(
            result.flags,
            (Flag.LEAD_TIME_AGREED_FALLBACK, Flag.MOQ_APPLIED, Flag.ORDER_MULTIPLE_ROUNDING, Flag.ZERO_FORECAST_DEMAND),
        )

    def test_zero_lead_time(self) -> None:
        inputs = b.evaluation(supplier_relations=(b.relation(moq=25, order_multiple=10, agreed_lead_time_days=0),))
        k = evaluate(inputs).breakdown
        self.assertEqual((k.lead_time_days, k.coverage_horizon_days), (0, 7))
        self.assertEqual((k.demand_over_lead_time, k.demand_over_horizon), (Fraction(0), Fraction(40)))
        self.assertEqual(k.inventory_position_decision, Fraction(17))
        self.assertEqual(k.q_final, Fraction(30))  # x = 23 → MOQ 25 → 30

    def test_zero_sigma_gives_s_equal_to_ddh(self) -> None:
        k = evaluate(b.evaluation()).breakdown
        self.assertEqual((k.sigma_h, k.safety_stock, k.target_level), (Fraction(0), Fraction(0), Fraction(120)))


class ReasonsTest(unittest.TestCase):
    def test_reasons_accumulate_in_canonical_order(self) -> None:
        inputs = b.evaluation(
            product=b.product(is_active=False),
            supplier_relations=(),
            inventory=Inventory(-1, 0, 30),
            forecast=None,
            policy=b.v1_policy(z=None),
        )
        self.assertEqual(
            evaluate(inputs).reasons,
            (
                Reason.PRODUCT_INACTIVE,
                Reason.NO_ACTIVE_PREFERRED_SUPPLIER,
                Reason.NEGATIVE_ON_HAND,
                Reason.FORECAST_MISSING,
                Reason.MISSING_POLICY_PARAMETER,
            ),
        )

    def test_several_missing_parameters_one_reason(self) -> None:
        result = evaluate(b.evaluation(policy=b.v1_policy(r=None, z=None, lt_max=None)))
        self.assertEqual(result.reasons, (Reason.MISSING_POLICY_PARAMETER,))
        self.assertEqual(
            result.missing_policy_parameters,
            (PolicyParameter.R, PolicyParameter.Z, PolicyParameter.LT_MAX),
        )
        self.assertIsNone(result.breakdown.coverage_horizon_days)

    def test_forecast_too_short_keeps_what_was_computable(self) -> None:
        result = evaluate(b.evaluation(forecast=b.forecast([40, 40])))
        self.assertEqual(result.reasons, (Reason.FORECAST_TOO_SHORT,))
        self.assertEqual(result.breakdown.demand_over_lead_time, Fraction(80))  # K(14) = 2
        self.assertIsNone(result.breakdown.demand_over_horizon)

    def test_empty_forecast_is_too_short(self) -> None:
        self.assertEqual(evaluate(b.evaluation(forecast=b.forecast([]))).reasons, (Reason.FORECAST_TOO_SHORT,))

    def test_insufficient_history(self) -> None:
        result = evaluate(b.evaluation(consumption=b.constant_consumption(days=20)))
        self.assertEqual(result.reasons, (Reason.INSUFFICIENT_HISTORY,))
        self.assertEqual(result.breakdown.sigma_window_count, 0)
        self.assertIsNone(result.breakdown.sigma_h)

    def test_exactly_one_window_gives_zero_sigma(self) -> None:
        k = evaluate(b.evaluation(consumption=b.consumption(list(range(21))))).breakdown
        self.assertEqual((k.sigma_window_count, k.sigma_h), (1, Fraction(0)))


class OutOfValidityTest(unittest.TestCase):
    """`DT-P22`: cases A and B, one single reason, the horizon never adapted."""

    def test_case_a_before_valid_from_without_h(self) -> None:
        start = dt.date(2026, 2, 1)
        inputs = b.evaluation(
            product=b.product(valid_from=start),
            supplier_relations=(),  # H is not calculable
            consumption=ConsumptionSeries(start_date=start, quantities=()),
        )
        result = evaluate(inputs)
        self.assertEqual(result.outcome, Outcome.NOT_CALCULABLE)
        self.assertEqual(
            result.reasons, (Reason.PRODUCT_OUT_OF_VALIDITY, Reason.NO_ACTIVE_PREFERRED_SUPPLIER)
        )

    def test_case_a_after_valid_to(self) -> None:
        valid_to = dt.date(2025, 4, 2)
        inputs = b.evaluation(
            product=b.product(valid_to=valid_to), consumption=b.consumption([5] * 60, end=valid_to)
        )
        result = evaluate(inputs)
        self.assertEqual(result.reasons, (Reason.PRODUCT_OUT_OF_VALIDITY,))

    def _case_b_inputs(self, valid_to: dt.date) -> object:
        as_of = dt.date(2025, 3, 20)
        return b.evaluation(
            as_of_date=as_of,
            product=b.product(valid_to=valid_to),
            supplier_relations=(b.relation(moq=25, order_multiple=10, agreed_lead_time_days=30),),
            open_lines=(),
            inventory=Inventory(17, 0, 0),
            consumption=b.consumption([5] * 60, end=as_of),
            forecast=b.forecast([10, 10, 10, 10, 10, 14], start=dt.date(2025, 3, 21)),
        )

    def test_case_b_normative_example(self) -> None:
        result = evaluate(self._case_b_inputs(dt.date(2025, 3, 31)))
        self.assertEqual(result.outcome, Outcome.NOT_CALCULABLE)
        self.assertEqual(result.reasons, (Reason.PRODUCT_OUT_OF_VALIDITY,))
        k = result.breakdown
        self.assertEqual((k.lead_time_days, k.review_period_days, k.coverage_horizon_days), (30, 7, 37))
        self.assertEqual(k.demand_over_horizon, Fraction(54))  # whole horizon, never 11 days
        self.assertEqual((k.sigma_h, k.safety_stock, k.target_level), (Fraction(0), Fraction(0), Fraction(54)))
        for name in DECISION_FIELDS:
            self.assertIsNone(getattr(k, name))

    def test_case_b_border_is_calculable(self) -> None:
        as_of_plus_h = dt.date(2025, 3, 20) + dt.timedelta(days=37)
        result = evaluate(self._case_b_inputs(as_of_plus_h))
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.outcome, Outcome.RECOMMEND)
        self.assertEqual(result.breakdown.raw_need, Fraction(37))
        one_day_earlier = evaluate(self._case_b_inputs(as_of_plus_h - dt.timedelta(days=1)))
        self.assertEqual(one_day_earlier.reasons, (Reason.PRODUCT_OUT_OF_VALIDITY,))

    def test_valid_to_equal_to_as_of_is_case_b(self) -> None:
        result = evaluate(self._case_b_inputs(dt.date(2025, 3, 20)))
        self.assertEqual(result.reasons, (Reason.PRODUCT_OUT_OF_VALIDITY,))
        self.assertEqual(result.breakdown.coverage_horizon_days, 37)

    def test_both_cases_give_one_reason(self) -> None:
        # as_of < valid_from ≤ valid_to < as_of + H.
        valid_from, valid_to = dt.date(2026, 1, 5), dt.date(2026, 1, 10)
        inputs = b.evaluation(
            product=b.product(valid_from=valid_from, valid_to=valid_to),
            consumption=ConsumptionSeries(start_date=valid_from, quantities=()),
        )
        reasons = evaluate(inputs).reasons
        self.assertEqual(reasons.count(Reason.PRODUCT_OUT_OF_VALIDITY), 1)
        self.assertEqual(reasons, (Reason.PRODUCT_OUT_OF_VALIDITY,))

    def test_case_b_is_not_evaluated_without_h(self) -> None:
        no_supplier = evaluate(b.replace(self._case_b_inputs(dt.date(2025, 3, 31)), supplier_relations=()))
        self.assertEqual(no_supplier.reasons, (Reason.NO_ACTIVE_PREFERRED_SUPPLIER,))
        no_review = evaluate(b.replace(self._case_b_inputs(dt.date(2025, 3, 31)), policy=b.v1_policy(r=None)))
        self.assertEqual(no_review.reasons, (Reason.MISSING_POLICY_PARAMETER,))
        self.assertEqual(no_review.missing_policy_parameters, (PolicyParameter.R,))

    def test_inactive_and_out_of_validity_coexist(self) -> None:
        valid_to = dt.date(2025, 4, 2)
        inputs = b.evaluation(
            product=b.product(is_active=False, valid_to=valid_to),
            consumption=b.consumption([5] * 60, end=valid_to),
        )
        self.assertEqual(
            evaluate(inputs).reasons, (Reason.PRODUCT_INACTIVE, Reason.PRODUCT_OUT_OF_VALIDITY)
        )


class PartialOutputTest(unittest.TestCase):
    """`DT-053`: descriptive magnitudes may survive; decision magnitudes never do."""

    def test_inactive_product_has_no_operational_magnitude(self) -> None:
        result = evaluate(b.evaluation(product=b.product(is_active=False)))
        for name in DESCRIPTIVE_FIELDS + DECISION_FIELDS:
            with self.subTest(term=name):
                self.assertIsNone(getattr(result.breakdown, name))
        self.assertEqual(result.flags, ())
        self.assertEqual(result.breakdown.as_of_date, b.AS_OF)

    def test_case_a_has_no_operational_magnitude(self) -> None:
        valid_to = dt.date(2025, 4, 2)
        inputs = b.evaluation(product=b.product(valid_to=valid_to), consumption=b.consumption([5] * 60, end=valid_to))
        result = evaluate(inputs)
        for name in DESCRIPTIVE_FIELDS + DECISION_FIELDS:
            with self.subTest(term=name):
                self.assertIsNone(getattr(result.breakdown, name))

    def test_negative_on_hand_keeps_descriptive_magnitudes(self) -> None:
        k = evaluate(b.evaluation(inventory=Inventory(-1, 0, 30))).breakdown
        self.assertEqual(k.coverage_horizon_days, 21)
        self.assertEqual(k.demand_over_horizon, Fraction(120))
        self.assertEqual((k.sigma_h, k.safety_stock, k.target_level), (Fraction(0), Fraction(0), Fraction(120)))
        # Positions and P depend on the invalid on_hand: never produced.
        self.assertIsNone(k.inventory_position_decision)
        self.assertIsNone(k.inventory_position_accounting)
        self.assertIsNone(k.p)
        for name in DECISION_FIELDS:
            self.assertIsNone(getattr(k, name))

    def test_not_calculable_never_has_decision_terms_nor_decision_flags(self) -> None:
        variants = [
            b.evaluation(product=b.product(is_active=False)),
            b.evaluation(inventory=Inventory(-1, 0, 30)),
            b.evaluation(forecast=None),
            b.evaluation(forecast=b.forecast([40])),
            b.evaluation(policy=b.v1_policy(z=None)),
            b.evaluation(consumption=b.constant_consumption(days=10)),
            b.evaluation(supplier_relations=()),
            b.evaluation(inventory=Inventory(0, 0, 30), forecast=b.forecast([0, 0, 0, 0]), policy=b.v1_policy(n=None)),
        ]
        for inputs in variants:
            result = evaluate(inputs)
            with self.subTest(reasons=result.reasons):
                self.assertEqual(result.outcome, Outcome.NOT_CALCULABLE)
                for name in DECISION_FIELDS:
                    self.assertIsNone(getattr(result.breakdown, name))
                self.assertNotIn(Flag.MOQ_APPLIED, result.flags)
                self.assertNotIn(Flag.ORDER_MULTIPLE_ROUNDING, result.flags)


if __name__ == "__main__":
    unittest.main()
