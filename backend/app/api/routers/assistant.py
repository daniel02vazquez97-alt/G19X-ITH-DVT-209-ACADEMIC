"""``GET /api/v1/assistant/answer`` (U15b, `DT-103`): documentary assistant over the synthetic corpus.

The 15th endpoint. It retrieves fragments of ``knowledge/search_corpus`` (Azure AI Search in ``dev``, the local
corpus otherwise), filtered by the groups of the caller's roles, and lets ``app.genai.assistant`` answer with the
U13 model citing them. Read-only like the rest of the API: no database, no engine, nothing is written; the four
roles. The question travels as a query parameter because the API has no request bodies (`docs/07` §7).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from app.genai.assistant import MAX_QUESTION, MIN_QUESTION

from ..assistant import AssistantUnavailable
from ..auth import ALL_ROLES, require_roles
from ..errors import ApiError
from ..schemas import AssistantAnswer
from . import errors

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

UNAVAILABLE = ("ASSISTANT_UNAVAILABLE", "El asistente documental no está disponible en este momento.")


@router.get("/answer", response_model=AssistantAnswer, responses=errors(401, 403, 422, 503),
            summary="Respuesta del asistente documental con citas del corpus sintético (los cuatro roles)")
def get_answer(
    request: Request,
    q: str = Query(..., min_length=MIN_QUESTION, max_length=MAX_QUESTION, description="Pregunta (3-300 caracteres)"),
    identity=Depends(require_roles(ALL_ROLES)),
) -> dict:
    assistant = getattr(request.app.state, "assistant", None)
    if assistant is None:
        raise ApiError(503, *UNAVAILABLE)
    try:
        result = assistant.ask(q, identity.roles, date.today())
    except AssistantUnavailable:
        raise ApiError(503, *UNAVAILABLE) from None
    except ValueError:
        raise ApiError(422, "INVALID_QUESTION", "La pregunta debe tener entre 3 y 300 caracteres.") from None
    return {
        "question": result.question,
        "answer": result.answer,
        "status": result.status,
        "warning": result.warning,
        "generator": result.generator,
        "retriever": result.retriever,
        "citations": [
            {"number": c.number, "document_id": c.document_id, "title": c.title, "section": c.section,
             "source_url": c.source_url, "excerpt": c.excerpt, "cited": c.cited}
            for c in result.citations
        ],
        "data_origin": "SYNTHETIC",
        "notices": ["SYNTHETIC_DATA"],
    }
