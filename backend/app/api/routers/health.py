"""``GET /health``: public, process liveness only; never touches PostgreSQL (`DT-066`)."""

from __future__ import annotations

from fastapi import APIRouter

from .. import __version__
from ..schemas import Health

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Health, summary="Estado del proceso (público, sin base de datos)")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
