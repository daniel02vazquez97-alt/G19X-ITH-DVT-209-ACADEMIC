"""U6 — deterministic explanation of a persisted recommendation (`docs/09` §14.5, `DT-068`, `DT-069`).

Persisted recommendation → ``ExplanationContext`` → ``facts[]`` → fixed template → verification →
``VERIFIED`` / ``DEGRADED`` / ``NOT_APPLICABLE``. Standard library only: no LLM, no RAG, no Azure, no
database connection, no call to the engine and no recalculation (`docs/03` §16.4).
"""

from .context import build_context
from .errors import ExplanationError, UnverifiedFigureError
from .explanation import TemplateGenerator, TextGenerator, explain
from .types import (
    DEGRADED,
    GENERATOR,
    NARRATIVE_UNVERIFIED,
    NOT_APPLICABLE,
    VERIFIED,
    Explanation,
    ExplanationContext,
    Fact,
    Provenance,
    ReasonDetail,
)

__all__ = [
    "DEGRADED",
    "GENERATOR",
    "NARRATIVE_UNVERIFIED",
    "NOT_APPLICABLE",
    "VERIFIED",
    "Explanation",
    "ExplanationContext",
    "ExplanationError",
    "Fact",
    "Provenance",
    "ReasonDetail",
    "TemplateGenerator",
    "TextGenerator",
    "UnverifiedFigureError",
    "build_context",
    "explain",
]
