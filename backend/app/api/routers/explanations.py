"""``GET /api/v1/recommendations/{recommendation_id}/explanation`` (U6, `DT-068`, `DT-069`).

The 14th endpoint: a deterministic explanation by template of a persisted evaluation. It reads the row,
builds an immutable ``ExplanationContext`` and lets ``app.genai`` render and verify; nothing is
recalculated and nothing is written. Same roles as the recommendation detail.
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, Path, Request

from app.db.read import recommendations as recommendations_read
from app.db.read import runs as runs_read
from app.genai import build_context, explain

from ..auth import ALL_ROLES, require_roles
from ..errors import ApiError
from ..provenance import recommendation_provenance
from ..schemas import RecommendationExplanation
from . import connection, errors

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


@router.get("/{recommendation_id}/explanation", response_model=RecommendationExplanation,
            responses=errors(401, 403, 404, 422),
            summary="Explicación por plantilla de una evaluación (los cuatro roles)")
def get_explanation(
    request: Request,
    recommendation_id: int = Path(..., ge=1),
    _identity=Depends(require_roles(ALL_ROLES)),
    conn: psycopg.Connection = Depends(connection),
) -> dict:
    row = recommendations_read.explanation_source(conn, recommendation_id)
    if row is None:
        raise ApiError(404, "RECOMMENDATION_NOT_FOUND", "No existe la evaluación indicada.",
                       {"recommendation_id": recommendation_id})
    provenance = recommendation_provenance(runs_read.run_context(conn, row["calculation_run_id"]))
    context = build_context(
        recommendation_id=row["id"],
        run_id=row["calculation_run_id"],
        outcome=row["outcome"],
        flags=row["flags"],
        reasons=row["reasons"],
        missing_policy_parameters=row["missing_policy_parameters"],
        breakdown=row["calculation_inputs"]["breakdown"],
        unit_of_measure=row["unit_of_measure"],
        provenance=provenance,
    )
    result = explain(context, request.app.state.text_generator, getattr(request.state, "correlation_id", None))
    return {
        "recommendation_id": context.recommendation_id,
        "run_id": context.run_id,
        "outcome": context.outcome,
        "explanation": {"generator": result.generator, "status": result.status, "narrative": result.narrative,
                        "warning": result.warning},
        "facts": [{"key": f.key, "value": f.value, "display": f.display, "unit": f.unit} for f in context.facts],
        "flags": list(context.flags),
        "reasons": list(context.reasons),
        "reason_details": [{"code": d.code, "text": d.text} for d in result.reason_details],
        "missing_policy_parameters": list(context.missing_policy_parameters),
        "provenance": provenance,
    }
