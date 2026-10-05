"""Shared helpers of the API suite without PostgreSQL (U5, `docs/13` §14).

This suite needs the optional groups ``db``, ``api`` and ``test`` (`DT-064`) and runs apart from the
default suite, from ``backend/``::

    python -m unittest discover -s tests/api -t tests/api

PostgreSQL is never reached: the database URL points to a closed port, so an endpoint that passes
authentication and validation answers 503 when it would query.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:  # discovered with -t tests/api
    sys.path.insert(0, str(BACKEND_DIR))

from starlette.testclient import TestClient  # noqa: E402

from app.api.app import create_app  # noqa: E402
from app.api.auth import ADMIN, ANALYST, PLANNER, VIEWER, Identity  # noqa: E402
from app.api.settings import Settings  # noqa: E402

UNREACHABLE_DB = "postgresql://nobody@127.0.0.1:1/none"
TOKENS = {
    VIEWER: "dev-viewer-token-0000000",
    ANALYST: "dev-analyst-token-000000",
    PLANNER: "dev-planner-token-000000",
    ADMIN: "dev-admin-token-00000000",
}
IDENTITIES = {token: Identity(f"dev-{role.lower()}", frozenset({role})) for role, token in TOKENS.items()}

#: The fourteen endpoints of `docs/07` §7.2 (13 of U5 + the explanation of U6, `DT-068`) with sample paths and
#: their explicit roles (None: public).
ALL4 = frozenset({VIEWER, ANALYST, PLANNER, ADMIN})
ENDPOINTS = [
    ("/health", None),
    ("/api/v1/me", ALL4),
    ("/api/v1/products", ALL4),
    ("/api/v1/products/1", ALL4),
    ("/api/v1/products/1/history", frozenset({ANALYST, PLANNER, ADMIN})),
    ("/api/v1/inventory", ALL4),
    ("/api/v1/inventory/1", ALL4),
    ("/api/v1/forecasts", ALL4),
    ("/api/v1/products/1/forecast", ALL4),
    ("/api/v1/recommendations", ALL4),
    ("/api/v1/recommendations/1", ALL4),
    ("/api/v1/products/1/recommendation", ALL4),
    ("/api/v1/runs/1", frozenset({PLANNER, ADMIN})),
    ("/api/v1/recommendations/1/explanation", ALL4),
]


def settings(database_url: str = UNREACHABLE_DB) -> Settings:
    return Settings("local", database_url, IDENTITIES)


def client(database_url: str = UNREACHABLE_DB, **kwargs) -> TestClient:
    return TestClient(create_app(settings(database_url)), **kwargs)


def auth(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKENS[role]}"}
