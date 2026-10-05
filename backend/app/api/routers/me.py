"""``GET /api/v1/me``: the authenticated identity. Any authenticated subject (`docs/07` §7.2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import Identity, current_identity
from ..schemas import Me
from . import errors

router = APIRouter(prefix="/api/v1", tags=["identity"])


@router.get("/me", response_model=Me, responses=errors(401), summary="Identidad y roles (cualquier autenticado)")
def me(identity: Identity = Depends(current_identity)) -> dict:
    return {"subject_id": identity.subject_id, "roles": sorted(identity.roles)}
