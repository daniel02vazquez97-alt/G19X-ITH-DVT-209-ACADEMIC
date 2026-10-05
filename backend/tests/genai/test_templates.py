"""Fixed texts of ``template/1.0.0`` (`docs/09` §14.5, `DT-069` point 5): literals and neighbourhood."""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from string import Template

from app.genai import GENERATOR
from app.genai.facts import UNIT_OF
from app.genai.templates import (
    FLAG_ORDER,
    FLAG_SENTENCES,
    LEAD_TIME_SOURCE_TEXTS,
    MAIN,
    PROVISIONAL_SENTENCES,
    REASON_ORDER,
    REASON_TEXTS,
    TEXT_PLACEHOLDERS,
    all_templates,
    all_texts,
    literal_violations,
    placeholder_violations,
    placeholders,
)

DOCS_09 = Path(__file__).resolve().parents[3] / "docs" / "09-ia-generativa.md"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("`", "")).strip()


class LiteralsTest(unittest.TestCase):
    def test_no_digit_percent_or_number_word_in_any_text(self) -> None:
        for name, text in all_texts():
            with self.subTest(name):
                self.assertEqual(literal_violations(text), [])

    def test_the_checker_catches_violations(self) -> None:
        self.assertIn("digit in literal text", literal_violations("pedir 5 cajas"))
        self.assertIn("digit in literal text", literal_violations("SKU-00004"))
        self.assertIn("digit in literal text", literal_violations("corte 2025-12-31"))
        self.assertIn("digit in literal text", literal_violations("versión 1.0.0"))
        self.assertIn("percent sign", literal_violations("un $x % más"))
        self.assertIn("number word 'cero'", literal_violations("la demanda es cero"))
        self.assertEqual(literal_violations("pedidos todos $q_final"), [])

    def test_placeholders_are_fact_keys_or_the_two_text_ones(self) -> None:
        for name, template in all_templates():
            with self.subTest(name):
                self.assertLessEqual(placeholders(template), set(UNIT_OF) | TEXT_PLACEHOLDERS)

    def test_text_values_have_no_digits(self) -> None:
        for text in LEAD_TIME_SOURCE_TEXTS.values():
            self.assertIsNone(re.search(r"\d", text))


class NeighbourhoodTest(unittest.TestCase):
    def test_every_template_respects_the_rules(self) -> None:
        for name, template in all_templates():
            with self.subTest(name):
                self.assertEqual(placeholder_violations(template), [])

    def test_violations_are_detected(self) -> None:
        cases = {
            "$q_final$raw_need": "placeholder before",          # two adjacent placeholders
            "$q_final.$raw_need": "'.' followed by",            # would read as one decimal
            "-$on_hand": "'-' before",                          # would read as a negative figure
            ".$on_hand": "'.' before",
            "x$on_hand": None,                                  # a letter before is harmless
            "$on_hand$u": "'$' after",                     # any placeholder right after is refused
            "$on_hand. Fin": None,                              # sentence end
            "$on_hand.": None,
        }
        for text, expected in cases.items():
            with self.subTest(text):
                problems = placeholder_violations(Template(text))
                if expected is None:
                    self.assertEqual(problems, [])
                else:
                    self.assertTrue(any(expected in p for p in problems), problems)


class OrderTest(unittest.TestCase):
    def test_flags_in_the_canonical_order_of_u1(self) -> None:
        self.assertEqual(FLAG_ORDER, ("LEAD_TIME_AGREED_FALLBACK", "LEAD_TIME_CAPPED", "MOQ_APPLIED",
                                      "ORDER_MULTIPLE_ROUNDING", "UNCOUNTED_TRANSIT", "OVERDUE_ORDERS_EXCLUDED",
                                      "ZERO_FORECAST_DEMAND"))

    def test_reasons_in_the_canonical_order_of_u1(self) -> None:
        self.assertEqual(REASON_ORDER, ("PRODUCT_INACTIVE", "PRODUCT_OUT_OF_VALIDITY", "NO_ACTIVE_PREFERRED_SUPPLIER",
                                        "NEGATIVE_ON_HAND", "FORECAST_MISSING", "FORECAST_TOO_SHORT",
                                        "INSUFFICIENT_HISTORY", "MISSING_POLICY_PARAMETER"))

    def test_generator_identity(self) -> None:
        self.assertEqual(GENERATOR, "template/1.0.0")

    def test_lead_time_sources(self) -> None:
        self.assertEqual(LEAD_TIME_SOURCE_TEXTS, {"OBSERVED": "observado en las recepciones del proveedor",
                                                  "AGREED_FALLBACK": "acordado con el proveedor"})


@unittest.skipUnless(DOCS_09.exists(), "docs/09 not available")
class NormativeTextTest(unittest.TestCase):
    """The code texts are exactly the normative texts of `docs/09` §14.5 (``template/1.0.0``)."""

    @classmethod
    def setUpClass(cls) -> None:
        source = DOCS_09.read_text(encoding="utf-8")
        section = source[source.index("### 14.5"):source.index("### 14.6")]
        cls.quoted = {_normalize(q) for q in re.findall(r"«(.*?)»", section, re.DOTALL)}

    def test_every_text_is_in_the_document(self) -> None:
        texts = [t.template for t in MAIN.values()] + [t.template for _, t in FLAG_SENTENCES]
        texts += list(PROVISIONAL_SENTENCES.values()) + [text for _, text in REASON_TEXTS]
        texts += list(LEAD_TIME_SOURCE_TEXTS.values())
        for text in texts:
            with self.subTest(text[:40]):
                self.assertIn(_normalize(text), self.quoted)


if __name__ == "__main__":
    unittest.main()
