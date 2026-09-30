"""Contract tests for the eligibility of synthetic CANCELLED orders - DT-039 section 5.2.

Run from the repository root::

    python3 -m unittest discover -s data/synthetic/tests -t .

**Component 5 is not implemented.** These tests pin down, before any code exists, the rule
closed on 2026-09-27 (D-01, option A) in `DT-039` section 5.2, point 1::

    planned_close = issued_on + ORDERS_CANCELLED_CLOSE_LAG_DAYS        (today: + 1 day)

    eligible =  causal order
                AND planned_close <  end_date
                AND (valid_to IS NULL OR planned_close <= valid_to)

:func:`expected_eligibility` is that rule written as an **executable specification**, with
the approved values of `DT-039` section 5.2 as literals. It is not an implementation of
Component 5: when Component 5 exists, its own tests must show that its candidate set agrees
with this function on every case below. The rule is a synthetic eligibility restriction,
not a business rule, and it leaves `DT-027` untouched.

What is checked here without Component 5:

* the seven boundary cases of the decision;
* that `DT-039` states the rule, the approved values and the absence of clipping;
* that the case the rule exists for - an order issued on the product's own ``valid_to`` -
  is actually produced by Component 4, and that the rule removes it from the universe;
* that an empty universe leaves B2 applicable (``K >= 1`` with zero candidates).
"""

from __future__ import annotations

import datetime as _dt
import math
import re
import tempfile
import unittest
from pathlib import Path

from data.synthetic.tests.test_inventory import START, make_profile, run_handmade

#: `DT-039` section 5.2, approved on 2026-09-26. Literals on purpose: the policy constants
#: do not exist in code until Component 5 is authorised.
CANCELLED_PERMILLE = 20
CLOSE_LAG_DAYS = 1

DT039 = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "decisions"
    / "DT-039-contrato-salida-c5.md"
)

END = _dt.date(2026, 1, 1)
DAY = _dt.timedelta(days=1)


def expected_eligibility(
    issued_on: _dt.date, valid_to: _dt.date | None, end_date: _dt.date
) -> bool:
    """`DT-039` section 5.2, point 1, for one causal order."""
    planned_close = issued_on + _dt.timedelta(days=CLOSE_LAG_DAYS)
    return planned_close < end_date and (valid_to is None or planned_close <= valid_to)


def expected_k(causal_orders: int) -> int:
    """`DT-039` section 5.2, point 2, before capping by the number of candidates."""
    return max(1, math.ceil(causal_orders * CANCELLED_PERMILLE / 1000))


class BoundaryCaseTests(unittest.TestCase):
    """The seven cases of the D-01 closure, one test each."""

    def test_case_1_null_valid_to_is_eligible(self) -> None:
        self.assertTrue(expected_eligibility(_dt.date(2025, 6, 1), None, END))

    def test_case_2_close_exactly_on_valid_to_is_eligible(self) -> None:
        # issued 2025-04-01, valid_to 2025-04-02: closed_at = 2025-04-02 <= valid_to.
        self.assertTrue(
            expected_eligibility(_dt.date(2025, 4, 1), _dt.date(2025, 4, 2), END)
        )

    def test_case_3_close_after_valid_to_is_not_eligible(self) -> None:
        self.assertFalse(
            expected_eligibility(_dt.date(2025, 4, 1), _dt.date(2025, 3, 31), END)
        )

    def test_case_4_issued_on_valid_to_is_not_eligible(self) -> None:
        # issued 2025-04-02, valid_to 2025-04-02: closed_at would be 2025-04-03.
        valid_to = _dt.date(2025, 4, 2)
        self.assertFalse(expected_eligibility(valid_to, valid_to, END))

    def test_case_5_close_exactly_on_end_date_is_not_eligible(self) -> None:
        # The existing inequality stays strict: the period is [start_date, end_date).
        self.assertFalse(expected_eligibility(END - DAY, None, END))

    def test_case_6_close_before_end_date_is_eligible(self) -> None:
        self.assertTrue(expected_eligibility(END - 2 * DAY, None, END))

    def test_case_7_both_conditions_failing_is_not_eligible(self) -> None:
        # Close after valid_to AND not before end_date.
        self.assertFalse(expected_eligibility(END - DAY, END - 2 * DAY, END))


class DocumentTests(unittest.TestCase):
    """`DT-039` is the authority; it must state what the cases above assume."""

    @classmethod
    def setUpClass(cls) -> None:
        text = DT039.read_text(encoding="utf-8")
        start = text.index("### 5.2 La política")
        cls.section = text[start : text.index("### 5.3", start)]

    def test_rule_is_stated_in_section_5_2(self) -> None:
        compact = re.sub(r"\s+", " ", self.section)
        self.assertIn(
            "cierre_previsto = issued_on + ORDERS_CANCELLED_CLOSE_LAG_DAYS", compact
        )
        self.assertIn("AND cierre_previsto < end_date", compact)
        self.assertIn(
            "( valid_to del producto de su línea IS NULL OR cierre_previsto <= valid_to )",
            compact,
        )

    def test_approved_values_are_unchanged(self) -> None:
        self.assertRegex(self.section, r"ORDERS_CANCELLED_PERMILLE\s+=\s+20\b")
        self.assertRegex(self.section, r"ORDERS_CANCELLED_CLOSE_LAG_DAYS\s+=\s+1\b")

    def test_closed_at_is_never_clipped(self) -> None:
        # Every ``min(`` in the section belongs to the paragraph that forbids clipping.
        paragraph_start = self.section.index("**`closed_at` no se recorta nunca.**")
        paragraph = self.section[
            paragraph_start : self.section.index("\n\n", paragraph_start)
        ]
        self.assertEqual(
            self.section.count("min(issued_at"), paragraph.count("min(issued_at")
        )
        self.assertIn("min(issued_at + lag, valid_to)", paragraph)
        self.assertIn(
            "`closed_at = issued_at + ORDERS_CANCELLED_CLOSE_LAG_DAYS`", self.section
        )


class ReachabilityTests(unittest.TestCase):
    """The case the rule exists for is produced by the real Component 4."""

    def test_an_order_issued_on_valid_to_exists_and_is_excluded(self) -> None:
        valid_to = START + _dt.timedelta(days=42)
        with tempfile.TemporaryDirectory() as tmp:
            config, _, simulation = run_handmade(
                tmp,
                "valid_to",
                products=[(1, START, valid_to), (2, START, None), (3, START, None)],
                relations=[
                    (1, 2, 5, 0, 1, True, True),
                    (2, 1, 3, 0, 1, True, True),
                    (3, 2, 7, 0, 1, True, True),
                ],
                demand={1: lambda k: 10, 2: lambda k: 6, 3: lambda k: 8},
                profiles=[
                    make_profile(1),
                    make_profile(2, on_time=0, delay=(10, 10)),
                ],
            )
        valid_to_of = {1: valid_to, 2: None, 3: None}
        end = config.period.end_date
        on_valid_to = [
            o
            for o in simulation.orders
            if o.line.product_id == 1 and o.issued_on == valid_to
        ]
        self.assertEqual(len(on_valid_to), 1, "C4 must emit an order on valid_to")

        universe = [
            o
            for o in simulation.orders
            if expected_eligibility(o.issued_on, valid_to_of[o.line.product_id], end)
        ]
        self.assertNotIn(on_valid_to[0], universe)
        # Every other order of the discontinued product closes within its validity.
        for order in simulation.orders:
            if order.line.product_id == 1 and order is not on_valid_to[0]:
                self.assertIn(order, universe)

    def test_an_empty_universe_leaves_b2_applicable(self) -> None:
        # Two causal orders, both issued on their product's valid_to: zero candidates,
        # while K = max(1, ceil(2 x 20 / 1000)) = 1 > 0. B2: the run must fail.
        valid_to = _dt.date(2025, 5, 10)
        orders = [valid_to, valid_to]
        candidates = [d for d in orders if expected_eligibility(d, valid_to, END)]
        self.assertEqual(candidates, [])
        self.assertEqual(expected_k(len(orders)), 1)
        self.assertEqual(expected_k(0), 1)  # N = 0 is covered by the same floor


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
