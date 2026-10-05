"""Invariants of the supply engine over seeded pseudo-random valid inputs.

Run from ``backend/``::

    python3 -m unittest discover -s tests -t .

No property-based framework is used (no dependency is authorised, `DT-043`); the equivalent of the
repository is a seeded generator of valid inputs (`docs/13` §11: no unseeded randomness) checked
against invariants that follow directly from the contract:

* ``PRODUCT_OUT_OF_VALIDITY`` at most once; reasons and flags unique and in canonical order;
* ``reasons ≠ ()`` ⇔ ``NOT_CALCULABLE``; ``missing_policy_parameters ≠ ()`` ⇔ the reason;
* ``H = L + R`` and ``H ≥ 7`` whenever ``H`` exists (`DT-054`);
* case A does not depend on ``H``; the input is never modified;
* decision terms only without reasons; decision flags only with ``RECOMMEND`` (`DT-053`);
* with ``RECOMMEND``: ``Q_final > 0``, ``Q_final ≥ MOQ``, ``Q_final`` multiple of ``M``,
  ``Q_final ≥ raw_need``;
* ``Decimal`` only in the five reported fields (§16.6 point 7);
* determinism, also with permuted input collections.

There is deliberately **no** test of a global monotonicity of ``S`` in ``L``: it is not an invariant
of V1 (`DT-054`). The audited counter-example is kept as a regression that documents why.
"""

from __future__ import annotations

import copy
import dataclasses
import datetime as dt
import random
import unittest
from decimal import Decimal
from fractions import Fraction

from app.supply_engine import (
    ConsumptionSeries,
    EvaluationInput,
    Flag,
    Inventory,
    Outcome,
    PolicyParameter,
    Reason,
    evaluate,
)

from . import builders as b

SEED = 20261001
CASES = 400
DECIMAL_FIELDS = {"sigma_h", "safety_stock", "target_level", "raw_need", "q_moq"}


def _random_input(rng: random.Random) -> EvaluationInput:
    as_of = b.AS_OF
    valid_from = as_of - dt.timedelta(days=rng.choice([1200, 400, 60, 10, 0, -5]))
    valid_to = rng.choice([None, None, None, as_of + dt.timedelta(days=rng.randint(-30, 120))])
    if valid_to is not None and valid_to < valid_from:
        valid_to = valid_from + dt.timedelta(days=rng.randint(0, 40))
    product = b.product(is_active=rng.random() > 0.1, valid_from=valid_from, valid_to=valid_to)

    relations = []
    for supplier_id in range(1, rng.randint(0, 3) + 1):
        relations.append(
            b.relation(
                supplier_id=supplier_id,
                is_active=rng.random() > 0.2,
                is_preferred=False,
                moq=rng.choice([0, 1, 25, Fraction(5, 2), 100]),
                order_multiple=rng.choice([1, 5, 10, Fraction(3, 2), 100]),
                agreed_lead_time_days=rng.choice([0, 3, 14, 30, 89, 120]),
            )
        )
    if relations and rng.random() > 0.15:
        index = rng.randrange(len(relations))
        relations[index] = dataclasses.replace(relations[index], is_active=True, is_preferred=True)

    lines = tuple(
        b.line(po, as_of + dt.timedelta(days=rng.randint(-10, 120)), rng.randint(0, 80), supplier=1)
        for po in range(1, rng.randint(0, 4) + 1)
    )
    total = sum(line.quantity_pending for line in lines)
    inventory = Inventory(rng.choice([-3, 0, 5, 40, 300]), rng.choice([0, 0, 4]), total)

    observations = []
    for _ in range(rng.randint(0, 16)):
        completed = as_of - dt.timedelta(days=rng.randint(-5, 300))
        issued = completed - dt.timedelta(days=rng.randint(0, 130))
        observations.append(b.observation(issued, completed, supplier=rng.randint(1, 3)))

    end = as_of if valid_to is None else min(as_of, valid_to)
    longest = (end - valid_from).days + 1
    length = 0 if longest <= 0 else rng.randint(0, min(longest, 400))
    pattern = rng.choice(["constant", "alternating", "random"])
    if pattern == "constant":
        quantities = [rng.choice([0, 3, Fraction(7, 2)])] * length
    elif pattern == "alternating":
        quantities = [0, 2] * (length // 2) + [0] * (length % 2)
    else:
        quantities = [rng.randint(0, 9) for _ in range(length)]
    if length:
        consumption = ConsumptionSeries(end - dt.timedelta(days=length - 1), tuple(quantities))
    else:
        consumption = ConsumptionSeries(max(valid_from, as_of), ())

    forecast = None
    if rng.random() > 0.1:
        weeks = [rng.choice([0, 10, 40, Fraction(35, 2)]) for _ in range(rng.randint(0, 16))]
        forecast = b.forecast(weeks, start=as_of + dt.timedelta(days=1))

    policy = b.v1_policy()
    if rng.random() < 0.15:
        name = rng.choice(["r", "z", "n", "n_min", "lt_max"])
        policy = b.v1_policy(**{name: None})

    return EvaluationInput(
        as_of_date=as_of,
        product=product,
        supplier_relations=tuple(relations),
        inventory=inventory,
        open_lines=lines,
        lead_time_observations=tuple(observations),
        consumption=consumption,
        forecast=forecast,
        policy=policy,
    )


def _inputs() -> list[EvaluationInput]:
    rng = random.Random(SEED)
    return [_random_input(rng) for _ in range(CASES)]


class InvariantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = _inputs()
        cls.results = [evaluate(i) for i in cls.inputs]

    def test_the_generator_covers_every_outcome_and_reason(self) -> None:
        outcomes = {r.outcome for r in self.results}
        reasons = {reason for r in self.results for reason in r.reasons}
        self.assertEqual(outcomes, set(Outcome))
        self.assertEqual(reasons, set(Reason))

    def test_reasons_and_flags_are_unique_and_canonical(self) -> None:
        order = list(Reason)
        flag_order = list(Flag)
        for result in self.results:
            self.assertLessEqual(result.reasons.count(Reason.PRODUCT_OUT_OF_VALIDITY), 1)
            self.assertEqual(list(result.reasons), sorted(set(result.reasons), key=order.index))
            self.assertEqual(list(result.flags), sorted(set(result.flags), key=flag_order.index))

    def test_reasons_if_and_only_if_not_calculable(self) -> None:
        for result in self.results:
            self.assertEqual(bool(result.reasons), result.outcome is Outcome.NOT_CALCULABLE)

    def test_missing_parameters_if_and_only_if_the_reason(self) -> None:
        for result in self.results:
            self.assertEqual(
                bool(result.missing_policy_parameters),
                Reason.MISSING_POLICY_PARAMETER in result.reasons,
            )
            order = list(PolicyParameter)
            self.assertEqual(
                list(result.missing_policy_parameters),
                sorted(result.missing_policy_parameters, key=order.index),
            )

    def test_h_is_l_plus_r_and_at_least_seven(self) -> None:
        seen = 0
        for result in self.results:
            k = result.breakdown
            if k.coverage_horizon_days is not None:
                seen += 1
                self.assertEqual(k.coverage_horizon_days, k.lead_time_days + k.review_period_days)
                self.assertEqual(k.review_period_days, 7)
                self.assertGreaterEqual(k.coverage_horizon_days, 7)
                self.assertLessEqual(k.lead_time_days, 90)
        self.assertGreater(seen, CASES // 4)

    def test_decision_terms_only_without_reasons(self) -> None:
        for result in self.results:
            k = result.breakdown
            if result.outcome is Outcome.NOT_CALCULABLE:
                self.assertIsNone(k.raw_need)
                self.assertIsNone(k.q_moq)
                self.assertIsNone(k.q_final)
            if result.outcome is not Outcome.RECOMMEND:
                self.assertNotIn(Flag.MOQ_APPLIED, result.flags)
                self.assertNotIn(Flag.ORDER_MULTIPLE_ROUNDING, result.flags)
                self.assertIsNone(k.q_final)

    def test_recommendation_respects_moq_and_multiple(self) -> None:
        recommended = 0
        for result in self.results:
            if result.outcome is not Outcome.RECOMMEND:
                continue
            recommended += 1
            k = result.breakdown
            self.assertGreater(k.q_final, 0)
            self.assertGreaterEqual(k.q_final, k.moq)
            self.assertEqual((k.q_final / k.order_multiple).denominator, 1)
            raw = k.raw_need if isinstance(k.raw_need, Fraction) else Fraction(k.raw_need)
            # A 28-digit Decimal may round up by at most half a unit in the last place.
            self.assertGreaterEqual(k.q_final + Fraction(1, 10**20), raw)
        self.assertGreater(recommended, 10)

    def test_decimal_only_in_the_five_reported_fields(self) -> None:
        for result in self.results:
            for field in dataclasses.fields(result.breakdown):
                value = getattr(result.breakdown, field.name)
                if isinstance(value, Decimal):
                    self.assertIn(field.name, DECIMAL_FIELDS)
                    self.assertEqual(len(value.as_tuple().digits), 28)

    def test_exclusion_produces_no_magnitude(self) -> None:
        for inputs, result in zip(self.inputs, self.results):
            excluded = Reason.PRODUCT_INACTIVE in result.reasons or not (
                inputs.product.valid_from <= inputs.as_of_date
                and (inputs.product.valid_to is None or inputs.as_of_date <= inputs.product.valid_to)
            )
            if excluded:
                self.assertIsNone(result.breakdown.coverage_horizon_days)
                self.assertIsNone(result.breakdown.on_hand)
                self.assertEqual(result.flags, ())


class IndependenceAndDeterminismTest(unittest.TestCase):
    def test_case_a_does_not_depend_on_h(self) -> None:
        for inputs in _inputs():
            product = inputs.product
            case_a = inputs.as_of_date < product.valid_from or (
                product.valid_to is not None and inputs.as_of_date > product.valid_to
            )
            without_h = evaluate(dataclasses.replace(inputs, supplier_relations=()))
            with_h = evaluate(inputs)
            if case_a:
                self.assertIn(Reason.PRODUCT_OUT_OF_VALIDITY, without_h.reasons)
                self.assertIn(Reason.PRODUCT_OUT_OF_VALIDITY, with_h.reasons)

    def test_the_input_is_never_modified(self) -> None:
        for inputs in _inputs()[:100]:
            before = copy.deepcopy(inputs)
            evaluate(inputs)
            self.assertEqual(inputs, before)

    def test_same_input_same_result(self) -> None:
        for inputs in _inputs()[:100]:
            self.assertEqual(evaluate(inputs), evaluate(copy.deepcopy(inputs)))

    def test_permuted_collections_give_the_same_result(self) -> None:
        rng = random.Random(SEED + 7)
        for inputs in _inputs()[:150]:
            relations = list(inputs.supplier_relations)
            lines = list(inputs.open_lines)
            observations = list(inputs.lead_time_observations)
            for items in (relations, lines, observations):
                rng.shuffle(items)
            permuted = dataclasses.replace(
                inputs,
                supplier_relations=tuple(relations),
                open_lines=tuple(lines),
                lead_time_observations=tuple(observations),
            )
            self.assertEqual(evaluate(permuted), evaluate(inputs))


class MonotonicityIsNotAnInvariantTest(unittest.TestCase):
    """`DT-054`: the audited counter-example, kept so nobody reinstates the global property."""

    def _evaluate(self, lead_time: int) -> object:
        inputs = b.evaluation(
            supplier_relations=(b.relation(agreed_lead_time_days=lead_time),),
            consumption=b.consumption([0, 2] * 20),
            forecast=b.forecast([10, 0, 0]),
            open_lines=(),
            inventory=Inventory(0, 0, 0),
        )
        return evaluate(inputs).breakdown

    def test_raising_l_can_lower_s_in_v1(self) -> None:
        short, longer = self._evaluate(0), self._evaluate(1)
        self.assertEqual((short.lead_time_days, short.coverage_horizon_days), (0, 7))
        self.assertEqual((longer.lead_time_days, longer.coverage_horizon_days), (1, 8))
        self.assertEqual((short.sigma_h, longer.sigma_h), (Fraction(1), Fraction(0)))
        self.assertEqual(short.target_level, Fraction(1165, 100))
        self.assertEqual(longer.target_level, Fraction(10))
        self.assertLess(longer.target_level, short.target_level)


if __name__ == "__main__":
    unittest.main()
