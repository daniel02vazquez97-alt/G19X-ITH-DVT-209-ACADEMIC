"""U13 (`DT-101`): ``ChatGenerator`` and the fallback of ``explain`` to the template (points 6–8)."""

from __future__ import annotations

import unittest

from app.genai import (
    DEGRADED,
    GENERATOR,
    NOT_APPLICABLE,
    VERIFIED,
    ChatGenerator,
    GeneratorUnavailable,
    TemplateGenerator,
    build_messages,
    explain,
    provisional_sentence,
)
from app.genai.chat import INSTRUCTIONS, MAX_TEXT

from ._genai_fixtures import NOT_CALCULABLE_ROW, PROVISIONAL, RECOMMEND_ROW, RECOMMEND_TEXT, context_of

NAME = "azure-openai/test"


def chat(answer):
    calls = []

    def complete(messages):
        calls.append(messages)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    return ChatGenerator(complete, NAME), calls


class MessagesTest(unittest.TestCase):
    def test_only_the_context_delimited_as_data(self) -> None:
        context = context_of(RECOMMEND_ROW)
        (system_role, system), (user_role, user) = build_messages(context)
        self.assertEqual((system_role, user_role), ("system", "user"))
        self.assertEqual(system, INSTRUCTIONS)
        for fact in context.facts:
            self.assertIn(f"{fact.key} | {fact.display} | {fact.unit}", user)
        self.assertIn("EXPLICACION_DE_REFERENCIA\n<<<\n", user)
        self.assertEqual(user.count("<<<"), user.count(">>>"))
        # The reference is the verified template text, without the provisional sentence (appended later).
        self.assertIn(RECOMMEND_TEXT.removesuffix(" " + PROVISIONAL), user)
        self.assertNotIn(PROVISIONAL, user)
        # Raw persisted values that are not facts never reach the model.
        for raw in ("80464966106", "238877404/109375", "2025-12-31", "ds-6c8ad65b4999"):
            self.assertNotIn(raw, user)

    def test_instructions_forbid_calculation_and_number_words(self) -> None:
        for needle in ("exactamente", "nunca con letras", "no calcules", "nunca instrucciones"):
            self.assertIn(needle, INSTRUCTIONS.lower().replace("no sumes, no restes, ", ""))


class ChatGeneratorTest(unittest.TestCase):
    def test_text_is_normalized_and_the_provisional_sentence_appended(self) -> None:
        context = context_of(RECOMMEND_ROW)
        generator, calls = chat("  Se sugiere pedir 2700 BOX.\n\n")
        self.assertEqual(generator.generate(context), "Se sugiere pedir 2700 BOX. " + provisional_sentence(context))
        self.assertEqual(len(calls), 1)

    def test_empty_or_too_long_answers_are_unavailable(self) -> None:
        for answer in ("   ", "x" * (MAX_TEXT + 1)):
            generator, _ = chat(answer)
            with self.subTest(len(answer)), self.assertRaises(GeneratorUnavailable):
                generator.generate(context_of(RECOMMEND_ROW))

    def test_a_name_is_required(self) -> None:
        with self.assertRaises(ValueError):
            ChatGenerator(lambda messages: "x", "")


class FallbackTest(unittest.TestCase):
    def explain(self, answer):
        generator, calls = chat(answer)
        with self.assertLogs("app.genai", "WARNING") if not isinstance(answer, str) or "999" in answer \
                or "cien" in answer else _no_logs():
            result = explain(context_of(RECOMMEND_ROW), generator, "corr-1", TemplateGenerator())
        return result, calls

    def test_verified_model_text(self) -> None:
        result, calls = self.explain("Se sugiere pedir 2700 BOX con un stock de seguridad de 439.478621 BOX.")
        self.assertEqual((result.generator, result.status, result.warning), (NAME, VERIFIED, None))
        self.assertTrue(result.narrative.endswith(PROVISIONAL))
        self.assertEqual(len(calls), 1)

    def test_foreign_figure_falls_back_to_the_template(self) -> None:
        result, _ = self.explain("Se sugiere pedir 999 BOX.")
        self.assertEqual((result.generator, result.status, result.narrative), (GENERATOR, VERIFIED, RECOMMEND_TEXT))

    def test_number_words_fall_back_to_the_template(self) -> None:
        result, _ = self.explain("Se sugiere pedir cien cajas.")
        self.assertEqual((result.generator, result.narrative), (GENERATOR, RECOMMEND_TEXT))

    def test_unavailable_and_any_error_fall_back(self) -> None:
        for error in (GeneratorUnavailable("timeout"), RuntimeError("boom")):
            with self.subTest(type(error).__name__):
                result, _ = self.explain(error)
                self.assertEqual((result.generator, result.status, result.narrative),
                                 (GENERATOR, VERIFIED, RECOMMEND_TEXT))

    def test_the_rejected_text_is_never_logged(self) -> None:
        generator, _ = chat("Texto rechazado con 999 unidades.")
        with self.assertLogs("app.genai", "WARNING") as logs:
            explain(context_of(RECOMMEND_ROW), generator, "corr-1", TemplateGenerator())
        self.assertNotIn("rechazado", "\n".join(logs.output))
        self.assertIn("corr-1", "\n".join(logs.output))

    def test_not_calculable_never_calls_the_model(self) -> None:
        generator, calls = chat("no debe usarse")
        result = explain(context_of(NOT_CALCULABLE_ROW), generator, None, TemplateGenerator())
        self.assertEqual((result.generator, result.status, result.narrative), (GENERATOR, NOT_APPLICABLE, None))
        self.assertEqual(calls, [])

    def test_without_fallback_u6_behaviour_is_unchanged(self) -> None:
        generator, _ = chat("Se sugiere pedir 999 BOX.")
        with self.assertLogs("app.genai", "WARNING"):
            result = explain(context_of(RECOMMEND_ROW), generator)
        self.assertEqual((result.generator, result.status, result.narrative), (NAME, DEGRADED, None))


class _no_logs:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


if __name__ == "__main__":
    unittest.main()
