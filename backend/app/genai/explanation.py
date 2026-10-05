"""``TextGenerator`` port, the template generator and ``explain`` (`docs/09` §14.3 and §14.5).

``explain`` renders, verifies and, if a figure is not authorized, degrades (RS-010): HTTP 200 with
``status = DEGRADED``, no narrative and ``warning = NARRATIVE_UNVERIFIED``; the data stays. The rejected
text is never returned; the event is logged with the request's ``correlation_id``.
"""

from __future__ import annotations

import logging
from typing import Protocol

from .errors import ExplanationError, UnverifiedFigureError
from .templates import (
    FLAG_SENTENCES,
    LEAD_TIME_SOURCE_TEXTS,
    MAIN,
    NOTICES,
    PROVISIONAL_SENTENCES,
    REASON_TEXTS,
    SOURCE_PLACEHOLDER,
    UNIT_PLACEHOLDER,
)
from .types import (
    DEGRADED,
    GENERATOR,
    NARRATIVE_UNVERIFIED,
    NOT_APPLICABLE,
    NOT_CALCULABLE,
    VERIFIED,
    Explanation,
    ExplanationContext,
    ReasonDetail,
)
from .verification import verify

logger = logging.getLogger("app.genai")


class TextGenerator(Protocol):
    """Port of `docs/03` §16.5: the template now, Azure OpenAI in Fase 10 behind the same interface."""

    name: str

    def generate(self, context: ExplanationContext) -> str: ...


class TemplateGenerator:
    """``template/1.0.0``: main sentence of the outcome, flag sentences in canonical order, provisional
    sentence last, joined by one space."""

    name = GENERATOR

    def generate(self, context: ExplanationContext) -> str:
        main = MAIN.get(context.outcome)
        if main is None:
            raise ExplanationError(f"no narrative for {context.outcome}")
        if not context.unit_of_measure:
            raise ExplanationError("unit_of_measure is required for a narrative")
        source = LEAD_TIME_SOURCE_TEXTS.get(context.lead_time_source or "")
        if source is None:
            raise ExplanationError(f"unknown lead_time_source {context.lead_time_source!r}")
        values = {fact.key: fact.display for fact in context.facts}
        values[UNIT_PLACEHOLDER] = context.unit_of_measure
        values[SOURCE_PLACEHOLDER] = source
        try:
            sentences = [main.substitute(values)]
            sentences += [sentence.substitute(values) for flag, sentence in FLAG_SENTENCES if flag in context.flags]
        except KeyError as exc:
            raise ExplanationError(f"missing fact {exc.args[0]} for the template") from exc
        notices = frozenset(context.provenance.notices) & NOTICES
        if notices:
            sentences.append(PROVISIONAL_SENTENCES[notices])
        return " ".join(sentences)


def reason_details(context: ExplanationContext) -> tuple[ReasonDetail, ...]:
    """Fixed text per reason, in the canonical order of U1, without figures."""
    return tuple(ReasonDetail(code, text) for code, text in REASON_TEXTS if code in context.reasons)


def explain(
    context: ExplanationContext, generator: TextGenerator | None = None, correlation_id: str | None = None
) -> Explanation:
    generator = TemplateGenerator() if generator is None else generator
    if context.outcome == NOT_CALCULABLE:
        return Explanation(generator.name, NOT_APPLICABLE, None, None, reason_details(context))
    text = generator.generate(context)
    try:
        verify(text, context.facts)
    except UnverifiedFigureError as exc:
        logger.warning(
            "explanation degraded: unverified figures (correlation_id=%s, recommendation_id=%s, generator=%s, "
            "figures=%d)", correlation_id, context.recommendation_id, generator.name, len(exc.figures),
        )
        return Explanation(generator.name, DEGRADED, None, NARRATIVE_UNVERIFIED, ())
    return Explanation(generator.name, VERIFIED, text, None, ())
