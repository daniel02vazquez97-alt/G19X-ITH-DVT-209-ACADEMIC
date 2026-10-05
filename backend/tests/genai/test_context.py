"""``ExplanationContext`` and ``facts[]`` (`DT-068` points 4, 5 and 11)."""

from __future__ import annotations

import dataclasses
import unittest

from ._genai_fixtures import NO_NEED_ROW, NOT_CALCULABLE_ROW, PROVENANCE, RECOMMEND_ROW, context_of, row

from app.genai import ExplanationError
from app.genai.facts import VOCABULARY, fact_keys


def keys(context) -> list[str]:
    return [fact.key for fact in context.facts]


class FactsTest(unittest.TestCase):
    def test_recommend(self) -> None:
        context = context_of(RECOMMEND_ROW)
        self.assertEqual(keys(context), [
            "q_final", "raw_need", "safety_stock", "target_level", "lead_time_days", "review_period_days",
            "coverage_horizon_days", "demand_over_horizon", "inventory_position_decision", "effective_in_transit",
            "order_multiple", "q_moq", "on_hand", "reserved"])
        by_key = {f.key: f for f in context.facts}
        self.assertEqual(by_key["demand_over_horizon"].value, "265346154/109375")  # persisted text, untouched
        self.assertEqual(by_key["demand_over_horizon"].display, "2426.021979")
        self.assertEqual({f.unit for f in context.facts if f.key.endswith("_days")}, {"DAYS"})
        self.assertEqual(by_key["q_final"].unit, "QUANTITY")

    def test_no_need(self) -> None:
        context = context_of(NO_NEED_ROW)
        self.assertEqual(keys(context), [
            "safety_stock", "target_level", "lead_time_days", "review_period_days", "coverage_horizon_days",
            "demand_over_horizon", "inventory_position_decision", "inventory_position_accounting",
            "total_in_transit", "effective_in_transit", "on_hand", "reserved"])
        self.assertNotIn("moq", keys(context))  # persisted "25", but NO_NEED has no MOQ sentence

    def test_not_calculable_has_no_facts(self) -> None:
        context = context_of(NOT_CALCULABLE_ROW)
        self.assertEqual(context.facts, ())
        self.assertEqual(context.reasons, ("NO_ACTIVE_PREFERRED_SUPPLIER",))

    def test_conditional_facts_follow_the_flags(self) -> None:
        self.assertNotIn("uncapped_lead_time_days", keys(context_of(RECOMMEND_ROW)))
        capped = context_of(row(RECOMMEND_ROW, flags=["LEAD_TIME_CAPPED", "MOQ_APPLIED"]))
        self.assertIn("uncapped_lead_time_days", keys(capped))
        self.assertIn("moq", keys(capped))
        self.assertNotIn("order_multiple", keys(capped))
        self.assertNotIn("total_in_transit", keys(capped))
        self.assertEqual(fact_keys("NO_NEED", ("MOQ_APPLIED", "ORDER_MULTIPLE_ROUNDING")) & {"moq", "q_moq"}, set())

    def test_null_values_give_no_fact(self) -> None:
        context = context_of(row(RECOMMEND_ROW, breakdown__reserved=None))
        self.assertNotIn("reserved", keys(context))

    def test_excluded_terms_never_become_facts(self) -> None:
        excluded = {"z", "sigma_h", "demand_over_lead_time", "a", "b", "d", "p", "s1", "s2", "sigma_window_count",
                    "lead_time_observation_count", "forecast_id", "effective_lines", "weekly_quantities",
                    "as_of_date", "horizon_start", "engine_version", "supplier_id"}
        self.assertEqual(excluded & {key for key, _ in VOCABULARY}, set())
        for source in (RECOMMEND_ROW, NO_NEED_ROW):
            self.assertEqual(excluded & set(keys(context_of(source))), set())


class ContextTest(unittest.TestCase):
    def test_immutable(self) -> None:
        context = context_of(RECOMMEND_ROW)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            context.outcome = "NO_NEED"  # type: ignore[misc]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            context.facts[0].display = "999"  # type: ignore[misc]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            context.provenance.notices = ()  # type: ignore[misc]
        with self.assertRaises((AttributeError, TypeError)):  # slots: no new attribute either
            context.extra = 1  # type: ignore[attr-defined]

    def test_collections_are_tuples(self) -> None:
        context = context_of(RECOMMEND_ROW)
        for name in ("facts", "flags", "reasons", "missing_policy_parameters"):
            self.assertIsInstance(getattr(context, name), tuple, name)
        self.assertIsInstance(context.provenance.notices, tuple)
        for field in dataclasses.fields(context):
            self.assertNotIsInstance(getattr(context, field.name), (dict, list))

    def test_defensive_copy(self) -> None:
        source = row(RECOMMEND_ROW)
        provenance = dict(PROVENANCE, notices=list(PROVENANCE["notices"]))
        context = context_of(source, provenance)
        before = (context.facts, context.flags, context.provenance)
        source["flags"].append("MOQ_APPLIED")
        source["breakdown"]["q_final"] = "1"
        provenance["notices"].clear()
        self.assertEqual((context.facts, context.flags, context.provenance), before)

    def test_kind_and_metadata(self) -> None:
        context = context_of(RECOMMEND_ROW)
        self.assertEqual(context.kind, "RECOMMENDATION_EXPLANATION")
        self.assertEqual((context.recommendation_id, context.run_id), (4, 2))
        self.assertEqual((context.lead_time_source, context.unit_of_measure), ("OBSERVED", "BOX"))
        self.assertNotIn("BOX", [f.value for f in context.facts])  # the unit is metadata, never a fact

    def test_invalid_input(self) -> None:
        with self.assertRaises(ExplanationError):
            context_of(row(RECOMMEND_ROW, outcome="MAYBE"))
        with self.assertRaises(ExplanationError):
            context_of(row(RECOMMEND_ROW, breakdown__q_final=2700))  # not the persisted text
        with self.assertRaises(ExplanationError):
            context_of(RECOMMEND_ROW, {k: v for k, v in PROVENANCE.items() if k != "notices"})

    def test_deterministic(self) -> None:
        self.assertEqual(context_of(RECOMMEND_ROW), context_of(row(RECOMMEND_ROW)))


if __name__ == "__main__":
    unittest.main()
