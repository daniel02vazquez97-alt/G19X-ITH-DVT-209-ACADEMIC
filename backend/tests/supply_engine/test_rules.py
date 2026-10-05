"""One test group per V1 rule (`docs/06` §16.4, `DT-031`).

Run from ``backend/``::

    python3 -m unittest discover -s tests -t .

Scope: cases 1 to 7 of `DT-031` (lead time), `DT-050` (order and ties) and aclaración A-1 (cap on any
source); `V1-03`; `V1-04` with `DT-048` (``K(H)``); `V1-02` transit borders (`DT-P15`); `V1-05`
windows; validity cases A and B (`DT-P22`); `V1-06` examples. Expected values computed by hand.
"""

from __future__ import annotations

import datetime as dt
import unittest
from fractions import Fraction

from app.supply_engine import LeadTimeSource
from app.supply_engine import rules
from app.supply_engine.exact import Surd

from . import builders as b


def _lead_time(lead_times: list[int], agreed: int = 14) -> tuple[int, LeadTimeSource, int]:
    observations = b.observations_with_lead_times(lead_times)
    return rules.observed_lead_time(observations, 7, b.AS_OF, 12, 3, agreed)


class LeadTimeTest(unittest.TestCase):
    """`V1-09`, cases 1 to 7 of `DT-031`."""

    def test_cases_1_2_3_fewer_than_three_observations_fall_back(self) -> None:
        for lead_times in ([], [10], [10, 12]):
            with self.subTest(n=len(lead_times)):
                self.assertEqual(
                    _lead_time(lead_times), (14, LeadTimeSource.AGREED_FALLBACK, len(lead_times))
                )

    def test_case_4_three_observations_median_rounded_up(self) -> None:
        self.assertEqual(_lead_time([10, 13, 12]), (12, LeadTimeSource.OBSERVED, 3))
        self.assertEqual(_lead_time([10, 14, 12, 18]), (13, LeadTimeSource.OBSERVED, 4))  # DT-031 example
        self.assertEqual(_lead_time([10, 13, 12, 18]), (13, LeadTimeSource.OBSERVED, 4))  # 12.5 → 13

    def test_case_5_only_the_twelve_most_recent_by_completion(self) -> None:
        # 12 recent observations of 5 days, then 6 older ones of 60 days: the old ones never count.
        lead_times = [5] * 12 + [60] * 6
        self.assertEqual(_lead_time(lead_times), (5, LeadTimeSource.OBSERVED, 12))

    def test_ordering_is_by_completion_not_by_issue(self) -> None:
        """An order issued long ago and completed recently is recent information (`V1-09`)."""
        recent_completion = b.observation(b.day(-200), b.day(-1))  # 199 days, completed yesterday
        others = b.observations_with_lead_times([5] * 12)  # completed days -10 … -21
        result = rules.observed_lead_time(
            (recent_completion,) + others, 7, b.AS_OF, 12, 3, 14
        )
        self.assertEqual(result, (5, LeadTimeSource.OBSERVED, 12))  # 11×5 + 199 → median 5

    def test_future_and_foreign_observations_are_ignored(self) -> None:
        future = b.observation(b.day(-3), b.day(1))
        foreign = b.observation(b.day(-50), b.day(-2), supplier=99)
        base = b.observations_with_lead_times([10, 12])
        result = rules.observed_lead_time(base + (future, foreign), 7, b.AS_OF, 12, 3, 14)
        self.assertEqual(result, (14, LeadTimeSource.AGREED_FALLBACK, 2))

    def test_cases_6_and_7_cap_with_trace(self) -> None:
        uncapped, source, _ = _lead_time([100, 120, 95])
        self.assertEqual((uncapped, source), (100, LeadTimeSource.OBSERVED))
        self.assertEqual(rules.cap_lead_time(uncapped, 90), (90, True))
        self.assertEqual(rules.cap_lead_time(90, 90), (90, False))

    def test_a1_cap_applies_to_the_agreed_fallback(self) -> None:
        uncapped, source, _ = _lead_time([], agreed=120)
        self.assertEqual((uncapped, source), (120, LeadTimeSource.AGREED_FALLBACK))
        self.assertEqual(rules.cap_lead_time(uncapped, 90), (90, True))
        self.assertEqual(rules.cap_lead_time(91, 90), (90, True))


class LeadTimeTieTest(unittest.TestCase):
    """`DT-050`: ``completed_on`` descending, ``issued_on`` ascending."""

    def _tie_inputs(self) -> tuple[object, ...]:
        recent = []
        for index, days in enumerate([10] * 5 + [20] * 6):
            completed = b.day(-1 - index)
            recent.append(b.observation(completed - dt.timedelta(days=days), completed))
        boundary = b.day(-40)
        a = b.observation(boundary - dt.timedelta(days=21), boundary)  # issued earlier: 21 days
        bb = b.observation(boundary - dt.timedelta(days=10), boundary)  # issued later: 10 days
        return tuple(recent), a, bb

    def test_the_tie_keeps_the_earlier_issue(self) -> None:
        recent, a, bb = self._tie_inputs()
        for order in ((a, bb), (bb, a)):
            with self.subTest(first=order[0].issued_on):
                result = rules.observed_lead_time(recent + order, 7, b.AS_OF, 12, 3, 14)
                self.assertEqual(result, (20, LeadTimeSource.OBSERVED, 12))

    def test_input_order_never_matters(self) -> None:
        recent, a, bb = self._tie_inputs()
        forward = rules.observed_lead_time(recent + (a, bb), 7, b.AS_OF, 12, 3, 14)
        backward = rules.observed_lead_time(tuple(reversed(recent + (a, bb))), 7, b.AS_OF, 12, 3, 14)
        self.assertEqual(forward, backward)

    def test_a_total_tie_gives_the_same_lead_time(self) -> None:
        same = b.observation(b.day(-30), b.day(-5))
        result = rules.observed_lead_time((same, same, same, same), 7, b.AS_OF, 3, 3, 14)
        self.assertEqual(result, (25, LeadTimeSource.OBSERVED, 3))


class HorizonAndForecastTest(unittest.TestCase):
    def test_coverage_horizon_is_l_plus_r(self) -> None:
        self.assertEqual(rules.coverage_horizon(14, 7), 21)
        self.assertEqual(rules.coverage_horizon(0, 7), 7)
        self.assertEqual(rules.coverage_horizon(90, 7), 97)

    def test_weeks_required(self) -> None:
        cases = {7: 1, 17: 3, 21: 3, 35: 5, 37: 6, 97: 14, 0: 0}
        for days, weeks in cases.items():
            with self.subTest(days=days):
                self.assertEqual(rules.weeks_required(days), weeks)

    def test_demand_over_horizon_examples(self) -> None:
        f = [Fraction(40)] * 4
        self.assertEqual(rules.demand_over_horizon(f, 17), Fraction(680, 7))  # V1-04 example
        six = [Fraction(10)] * 5 + [Fraction(14)]
        self.assertEqual(rules.demand_over_horizon(six, 37), Fraction(54))  # DT-048 example
        self.assertEqual(rules.demand_over_horizon(six[:5], 35), Fraction(50))  # r = 0: F6 unused

    def test_demand_needs_k_weeks(self) -> None:
        with self.assertRaises(ValueError):
            rules.demand_over_horizon([Fraction(10)] * 5, 37)


class TransitTest(unittest.TestCase):
    """`V1-02` with the borders of `DT-P15`."""

    def test_window_is_after_as_of_and_up_to_as_of_plus_h(self) -> None:
        lines = (
            b.line(1, b.day(0), 1),  # overdue: excluded
            b.line(2, b.day(1), 10),
            b.line(3, b.day(21), 100),  # as_of + H: included
            b.line(4, b.day(22), 1000),  # beyond: excluded
        )
        total, included = rules.effective_in_transit(lines, b.AS_OF, 21)
        self.assertEqual(total, Fraction(110))
        self.assertEqual([line.purchase_order_id for line in included], [2, 3])
        self.assertTrue(rules.has_overdue_lines(lines, b.AS_OF))

    def test_included_lines_are_ordered(self) -> None:
        lines = (b.line(9, b.day(2), 1, item=2), b.line(9, b.day(3), 1, item=1), b.line(3, b.day(4), 1))
        _, included = rules.effective_in_transit(lines, b.AS_OF, 21)
        self.assertEqual(
            [(l.purchase_order_id, l.item_id) for l in included], [(3, 1), (9, 1), (9, 2)]
        )


class ValidityTest(unittest.TestCase):
    """Cases A and B of ``PRODUCT_OUT_OF_VALIDITY`` (`DT-P22`)."""

    def test_case_a(self) -> None:
        product = b.product(valid_from=dt.date(2023, 1, 1), valid_to=dt.date(2025, 4, 2))
        self.assertFalse(rules.is_valid_on(product, dt.date(2022, 12, 31)))
        self.assertTrue(rules.is_valid_on(product, dt.date(2023, 1, 1)))
        self.assertTrue(rules.is_valid_on(product, dt.date(2025, 4, 2)))
        self.assertFalse(rules.is_valid_on(product, dt.date(2025, 4, 3)))
        self.assertTrue(rules.is_valid_on(b.product(valid_to=None), dt.date(2099, 1, 1)))

    def test_case_b_borders(self) -> None:
        product = b.product(valid_to=dt.date(2025, 4, 2))
        ends = rules.validity_ends_within_horizon
        self.assertFalse(ends(product, dt.date(2025, 3, 13), 20))  # valid_to == as_of + H
        self.assertTrue(ends(product, dt.date(2025, 3, 14), 20))
        self.assertTrue(ends(product, dt.date(2025, 4, 2), 20))  # valid_to == as_of
        self.assertFalse(ends(product, dt.date(2025, 4, 3), 20))  # case A, not B
        self.assertFalse(ends(b.product(valid_to=None), dt.date(2025, 4, 2), 20))

    def test_normative_example(self) -> None:
        product = b.product(valid_to=dt.date(2025, 3, 31))
        self.assertTrue(rules.validity_ends_within_horizon(product, dt.date(2025, 3, 20), 37))


class SigmaTest(unittest.TestCase):
    """`V1-05` with the population estimator of `docs/06` §16.6 point 2."""

    def test_window_count(self) -> None:
        self.assertEqual(rules.sigma_components([Fraction(1)] * 6, 7), (0, None, None, None))
        count, s1, s2, a = rules.sigma_components([Fraction(1)] * 7, 7)
        self.assertEqual((count, s1, s2, a), (1, 7, 49, 0))  # n = 1 → σ_H = 0

    def test_alternating_series(self) -> None:
        series = [Fraction(v) for v in [0, 2] * 4]  # 8 days, H = 7 → windows 6 and 8
        count, s1, s2, a = rules.sigma_components(series, 7)
        self.assertEqual((count, s1, s2, a), (2, 14, 100, 4))  # σ_H = √4 / 2 = 1

    def test_safety_stock_components(self) -> None:
        self.assertEqual(rules.safety_stock_components(Fraction(4), 2, Fraction(33, 20)), (4356, 40))


class SupplierConstraintsTest(unittest.TestCase):
    """`V1-06` examples of `DT-031`."""

    def _rational(self, value: Fraction) -> Surd:
        return Surd(value, Fraction(0), 20)

    def test_examples(self) -> None:
        cases = [
            (Fraction(18), 25, 10, (Fraction(25), Fraction(30), True, True)),
            (Fraction(8694, 100), 25, 10, (Fraction(8694, 100), Fraction(90), False, True)),
            (Fraction(10), 0, 1, (Fraction(10), Fraction(10), False, False)),
            (Fraction(25), 25, 5, (Fraction(25), Fraction(25), False, False)),  # x == MOQ
        ]
        for raw, moq, multiple, expected in cases:
            with self.subTest(raw=raw):
                result = rules.apply_supplier_constraints(
                    self._rational(raw), Fraction(moq), Fraction(multiple)
                )
                self.assertEqual(result, expected)

    def test_irrational_need(self) -> None:
        x = Surd(Fraction(30), Fraction(2), 1)  # 31.41…
        q_moq, q_final, moq_applied, rounding = rules.apply_supplier_constraints(
            x, Fraction(25), Fraction(10)
        )
        self.assertEqual((q_moq, q_final, moq_applied, rounding), (None, Fraction(40), False, True))

    def test_need(self) -> None:
        self.assertFalse(rules.has_need(Surd(Fraction(0), Fraction(0), 20)))
        self.assertFalse(rules.has_need(Surd(Fraction(-5), Fraction(4), 1)))  # −5 + 2 < 0
        self.assertTrue(rules.has_need(Surd(Fraction(-1), Fraction(2), 1)))  # −1 + 1.41 > 0


if __name__ == "__main__":
    unittest.main()
