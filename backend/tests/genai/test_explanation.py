"""``explain`` with the template generator (`docs/09` §14.5, `DT-068`, `DT-069`, RS-010)."""

from __future__ import annotations

import unittest

from app.genai import (
    DEGRADED,
    GENERATOR,
    NARRATIVE_UNVERIFIED,
    NOT_APPLICABLE,
    VERIFIED,
    ExplanationError,
    TemplateGenerator,
    explain,
)
from app.genai.templates import FLAG_SENTENCES

from ._genai_fixtures import (
    NO_NEED_ROW,
    NO_NEED_TEXT,
    NOT_CALCULABLE_ROW,
    PROVENANCE,
    PROVISIONAL,
    RECOMMEND_ROW,
    RECOMMEND_TEXT,
    context_of,
    row,
)


class RecommendTest(unittest.TestCase):
    def test_exact_text_of_the_real_row(self) -> None:
        result = explain(context_of(RECOMMEND_ROW))
        self.assertEqual((result.generator, result.status, result.warning), (GENERATOR, VERIFIED, None))
        self.assertEqual(result.narrative, RECOMMEND_TEXT)
        self.assertEqual(result.reason_details, ())

    def test_order_of_the_main_sentence(self) -> None:
        text = explain(context_of(RECOMMEND_ROW)).narrative
        anchors = ["Se sugiere pedir", "La posición de inventario", "El nivel objetivo", "Ese horizonte suma",
                   "La necesidad bruta", "La cantidad se redondea", "Aviso:"]
        positions = [text.index(a) for a in anchors]
        self.assertEqual(positions, sorted(positions))

    def test_every_flag_sentence_in_canonical_order(self) -> None:
        flags = ["ZERO_FORECAST_DEMAND", "OVERDUE_ORDERS_EXCLUDED", "UNCOUNTED_TRANSIT", "ORDER_MULTIPLE_ROUNDING",
                 "MOQ_APPLIED", "LEAD_TIME_CAPPED", "LEAD_TIME_AGREED_FALLBACK"]  # given in reverse
        source = row(RECOMMEND_ROW, flags=flags, breakdown__uncapped_lead_time_days="120",
                     breakdown__lead_time_days="90", breakdown__total_in_transit="10",
                     breakdown__inventory_position_accounting="252", breakdown__lead_time_source="AGREED_FALLBACK")
        result = explain(context_of(source))
        self.assertEqual(result.status, VERIFIED)
        text = result.narrative
        starts = [text.index(s.template.split("$")[0]) for _, s in FLAG_SENTENCES]
        self.assertEqual(starts, sorted(starts))
        self.assertIn("de 120 días, supera el máximo de la política y se limita a 90 días", text)
        self.assertIn("pedido mínimo del proveedor, de 1 BOX", text)
        self.assertIn("En total hay 10 BOX en tránsito (posición contable de 252 BOX)", text)
        self.assertIn("(acordado con el proveedor)", text)

    def test_no_priority_risk_or_urgency(self) -> None:
        text = explain(context_of(RECOMMEND_ROW)).narrative.lower()
        for word in ("priorit", "urgen", "riesgo", "si no se actúa"):
            self.assertNotIn(word, text)

    def test_the_unit_of_the_product_never_units(self) -> None:
        text = explain(context_of(row(RECOMMEND_ROW, unit_of_measure="KG"))).narrative
        self.assertIn("pedir 2700 KG", text)
        self.assertNotIn("unidades", text)


class NoNeedTest(unittest.TestCase):
    def test_exact_text_of_the_real_row(self) -> None:
        result = explain(context_of(NO_NEED_ROW))
        self.assertEqual((result.status, result.narrative), (VERIFIED, NO_NEED_TEXT))

    def test_own_template_without_quantities(self) -> None:
        text = explain(context_of(row(NO_NEED_ROW, flags=[]))).narrative
        self.assertTrue(text.startswith("No se sugiere pedido:"))
        self.assertNotIn("Se sugiere pedir", text)
        self.assertNotIn("pedido mínimo", text)
        self.assertNotIn("En total hay", text)

    def test_zero_forecast_demand(self) -> None:
        text = explain(context_of(row(NO_NEED_ROW, flags=["ZERO_FORECAST_DEMAND"]))).narrative
        self.assertIn("No se prevé demanda en el horizonte: puede tratarse de un producto sin rotación.", text)


class NotCalculableTest(unittest.TestCase):
    def test_structured_explanation(self) -> None:
        result = explain(context_of(NOT_CALCULABLE_ROW))
        self.assertEqual((result.status, result.narrative, result.warning), (NOT_APPLICABLE, None, None))
        self.assertEqual([(d.code, d.text) for d in result.reason_details],
                         [("NO_ACTIVE_PREFERRED_SUPPLIER", "El producto no tiene un proveedor preferente activo.")])

    def test_reason_details_in_canonical_order(self) -> None:
        source = row(NOT_CALCULABLE_ROW, reasons=["MISSING_POLICY_PARAMETER", "FORECAST_MISSING", "PRODUCT_INACTIVE"],
                     missing_policy_parameters=["R", "z"])
        result = explain(context_of(source))
        self.assertEqual([d.code for d in result.reason_details],
                         ["PRODUCT_INACTIVE", "FORECAST_MISSING", "MISSING_POLICY_PARAMETER"])
        self.assertEqual(context_of(source).missing_policy_parameters, ("R", "z"))


class ProvisionalityTest(unittest.TestCase):
    def sentence(self, notices: list[str]) -> str:
        return explain(context_of(RECOMMEND_ROW, dict(PROVENANCE, notices=notices))).narrative

    def test_four_combinations(self) -> None:
        self.assertTrue(self.sentence(["SYNTHETIC_DATA", "V1_PROVISIONAL_POLICY"]).endswith(PROVISIONAL))
        self.assertTrue(self.sentence(["SYNTHETIC_DATA"]).endswith(
            "calculadas con datos sintéticos; no constituyen una recomendación de negocio definitiva."))
        self.assertTrue(self.sentence(["V1_PROVISIONAL_POLICY"]).endswith(
            "calculadas con la política provisional de la primera versión; no constituyen una recomendación de "
            "negocio definitiva."))
        self.assertNotIn("Aviso", self.sentence([]))

    def test_notices_are_not_touched(self) -> None:
        context = context_of(RECOMMEND_ROW)
        explain(context)
        self.assertEqual(context.provenance.notices, ("SYNTHETIC_DATA", "V1_PROVISIONAL_POLICY"))


class _Injecting(TemplateGenerator):
    """RS-010 test generator: the template text plus a figure that is not in the context."""

    def __init__(self, extra: str) -> None:
        self.extra = extra

    def generate(self, context):  # type: ignore[override]
        return super().generate(context) + self.extra


class DegradationTest(unittest.TestCase):
    def test_foreign_figures_degrade(self) -> None:
        for extra in (" Faltan 999 BOX.", " Corte 2025-12-31.", " Producto SKU-00004.", " Posición -5 BOX."):
            with self.subTest(extra):
                with self.assertLogs("app.genai", "WARNING") as logs:
                    result = explain(context_of(RECOMMEND_ROW), _Injecting(extra), correlation_id="corr-test-0001")
                self.assertEqual((result.status, result.narrative, result.warning),
                                 (DEGRADED, None, NARRATIVE_UNVERIFIED))
                self.assertEqual(result.generator, GENERATOR)
                self.assertIn("corr-test-0001", logs.output[0])
                self.assertNotIn(extra.strip(), logs.output[0])  # the rejected text is never logged

    def test_data_is_kept(self) -> None:
        context = context_of(NO_NEED_ROW)
        with self.assertLogs("app.genai", "WARNING"):
            result = explain(context, _Injecting(" 999"))
        self.assertEqual(result.status, DEGRADED)
        self.assertEqual(len(context.facts), 12)
        self.assertEqual(context.flags, ("UNCOUNTED_TRANSIT",))
        self.assertEqual(context.provenance.notices, ("SYNTHETIC_DATA", "V1_PROVISIONAL_POLICY"))

    def test_not_calculable_never_reaches_the_generator(self) -> None:
        self.assertEqual(explain(context_of(NOT_CALCULABLE_ROW), _Injecting(" 999")).status, NOT_APPLICABLE)

    def test_contract_errors_are_not_degradation(self) -> None:
        with self.assertRaises(ExplanationError):
            explain(context_of(row(RECOMMEND_ROW, unit_of_measure=None)))
        with self.assertRaises(ExplanationError):
            explain(context_of(row(RECOMMEND_ROW, flags=["MOQ_APPLIED"], breakdown__moq=None)))


class DeterminismTest(unittest.TestCase):
    def test_same_input_same_output(self) -> None:
        first, second = context_of(RECOMMEND_ROW), context_of(row(RECOMMEND_ROW))
        self.assertEqual(first, second)
        self.assertEqual(first.facts, second.facts)
        self.assertEqual(explain(first), explain(second))


if __name__ == "__main__":
    unittest.main()
