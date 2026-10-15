"""U6 — deterministic explanation of a persisted recommendation (`docs/09` §14.5, `DT-068`, `DT-069`).

Persisted recommendation → ``ExplanationContext`` → ``facts[]`` → fixed template → verification →
``VERIFIED`` / ``DEGRADED`` / ``NOT_APPLICABLE``. Standard library only: no RAG, no database connection, no call
to the engine and no recalculation (`docs/03` §16.4). U13 (`DT-101`) adds ``ChatGenerator``: a chat model behind
the same port, with the call injected by ``app.api`` and the template as fallback.
"""

from .chat import ChatGenerator, build_messages, message_list
from .context import build_context
from .errors import ExplanationError, GeneratorUnavailable, UnverifiedFigureError
from .explanation import TemplateGenerator, TextGenerator, explain, provisional_sentence
from .retrieval import DocumentChunk, DocumentRetriever, InMemoryDocumentRetriever, RetrievedChunk, RetrievalFilters
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
    "ChatGenerator",
    "DEGRADED",
    "GENERATOR",
    "NARRATIVE_UNVERIFIED",
    "NOT_APPLICABLE",
    "VERIFIED",
    "Explanation",
    "ExplanationContext",
    "DocumentChunk",
    "DocumentRetriever",
    "ExplanationError",
    "Fact",
    "GeneratorUnavailable",
    "InMemoryDocumentRetriever",
    "Provenance",
    "ReasonDetail",
    "RetrievedChunk",
    "RetrievalFilters",
    "TemplateGenerator",
    "TextGenerator",
    "UnverifiedFigureError",
    "build_context",
    "build_messages",
    "explain",
    "message_list",
    "provisional_sentence",
]
