"""Figure verification (`DT-069` points 3–5): maximal matches, exact string equality, no tolerance."""

from __future__ import annotations

import unittest

from app.genai import Fact, UnverifiedFigureError
from app.genai.verification import figures, verify

FACTS = (
    Fact("q_final", "2700", "2700", "QUANTITY"),
    Fact("safety_stock", "439.4786206640203006679518026", "439.478621", "QUANTITY"),
    Fact("on_hand", "-5", "-5", "QUANTITY"),
    Fact("review_period_days", "7", "7", "DAYS"),
)


class FiguresTest(unittest.TestCase):
    def test_maximal_matches(self) -> None:
        self.assertEqual(figures("pedir 2700 BOX, stock 439.478621 BOX."), ("2700", "439.478621"))
        self.assertEqual(figures("posición -5 EACH"), ("-5",))
        self.assertEqual(figures("SKU-00004"), ("-00004",))
        self.assertEqual(figures("corte 2025-12-31"), ("2025", "-12", "-31"))
        self.assertEqual(figures("versión 1.0.0"), ("1.0", "0"))
        self.assertEqual(figures("fin 7."), ("7",))
        self.assertEqual(figures("27007"), ("27007",))  # consecutive digits are one figure


class VerifyTest(unittest.TestCase):
    def assert_rejected(self, text: str, *expected: str) -> None:
        with self.assertRaises(UnverifiedFigureError) as raised:
            verify(text, FACTS)
        self.assertEqual(raised.exception.figures, expected)

    def test_valid_figures(self) -> None:
        verify("Se sugiere pedir 2700 BOX con 439.478621 de seguridad y -5 en existencia cada 7 días.", FACTS)
        verify("Sin cifras.", FACTS)

    def test_unknown_figure(self) -> None:
        self.assert_rejected("Se sugiere pedir 999 BOX.", "999")

    def test_no_numeric_tolerance(self) -> None:
        self.assert_rejected("stock 439.4786206640203006679518026", "439.4786206640203006679518026")
        self.assert_rejected("stock 439.47862", "439.47862")
        self.assert_rejected("pedir 2700.0", "2700.0")
        self.assert_rejected("pedir 02700", "02700")

    def test_sign_matters(self) -> None:
        self.assert_rejected("posición 5", "5")
        self.assert_rejected("posición -2700", "-2700")

    def test_decimal_glued_to_a_fact(self) -> None:
        self.assert_rejected("pedir 2700.7", "2700.7")

    def test_consecutive_figures(self) -> None:
        self.assert_rejected("pedir 27007", "27007")

    def test_dates_skus_versions_and_literals(self) -> None:
        self.assert_rejected("corte 2025-12-31", "2025", "-12", "-31")
        self.assert_rejected("producto SKU-00004", "-00004")
        self.assert_rejected("generador template/1.0.0", "1.0", "0")
        self.assert_rejected("dentro de 3 semanas", "3")


if __name__ == "__main__":
    unittest.main()
