"""Authentication and role authorization (`DT-065`, `docs/10` §15).

* `TokenValidator` — the port: ``validate(token) -> Identity``; Fase 8 swaps the implementation
  (Entra ID), not the port.
* `DevTokenValidator` — opaque development tokens ``dev-…`` registered in tests or in
  ``DEV_AUTH_IDENTITIES``. No JWT, no signature, no expiry. Tokens are never logged.
* `require_roles` — one dependency per endpoint with the explicit roles of `docs/07` §7.2; there is no
  role hierarchy.
"""

from __future__ import annotations

import hmac
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .errors import ApiError

VIEWER, ANALYST, PLANNER, ADMIN = "VIEWER", "ANALYST", "PLANNER", "ADMIN"
ROLES = frozenset({VIEWER, ANALYST, PLANNER, ADMIN})

#: Explicit role sets of `docs/07` §7.2 (no hierarchy, §7.1).
ALL_ROLES = ROLES
HISTORY_ROLES = frozenset({ANALYST, PLANNER, ADMIN})
RUN_ROLES = frozenset({PLANNER, ADMIN})

TOKEN_PATTERN = re.compile(r"dev-[A-Za-z0-9_-]{16,64}")
SUBJECT_PATTERN = re.compile(r"[a-z0-9-]{1,64}")


class InvalidToken(Exception):
    """The token is malformed or unknown. Never carries the token."""


class IdentityRegistryError(ValueError):
    """The registry of development identities is invalid: the API refuses to start."""


@dataclass(frozen=True)
class Identity:
    subject_id: str
    roles: frozenset[str]


class TokenValidator(Protocol):
    def validate(self, token: str) -> Identity: ...


def parse_identities(text: str | None) -> dict[str, Identity]:
    """``DEV_AUTH_IDENTITIES``: JSON object ``{token: {"subject_id": …, "roles": [...]}}``."""
    if not text:
        raise IdentityRegistryError("DEV_AUTH_IDENTITIES is required with APP_ENV=local")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise IdentityRegistryError("DEV_AUTH_IDENTITIES is not valid JSON") from exc
    if not isinstance(raw, dict):
        raise IdentityRegistryError("DEV_AUTH_IDENTITIES must be a JSON object")
    identities = {}
    for index, (token, entry) in enumerate(raw.items()):
        if not isinstance(entry, dict) or set(entry) != {"subject_id", "roles"}:
            raise IdentityRegistryError(f"identity #{index} must have exactly subject_id and roles")
        if not isinstance(entry["roles"], list):
            raise IdentityRegistryError(f"identity #{index}: roles must be a list")
        identities[token] = Identity(entry["subject_id"], frozenset(entry["roles"]))
    return identities


class DevTokenValidator:
    """Development validator: an immutable registry of opaque tokens (`DT-065`)."""

    def __init__(self, identities: Mapping[str, Identity]) -> None:
        if not identities:
            raise IdentityRegistryError("the development identity registry is empty")
        for index, (token, identity) in enumerate(identities.items()):
            # Messages never contain the token itself.
            if not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
                raise IdentityRegistryError(f"identity #{index}: token does not match dev-[A-Za-z0-9_-]{{16,64}}")
            if not isinstance(identity.subject_id, str) or not SUBJECT_PATTERN.fullmatch(identity.subject_id):
                raise IdentityRegistryError(f"identity #{index}: subject_id does not match [a-z0-9-]{{1,64}}")
            if not identity.roles or not identity.roles <= ROLES:
                raise IdentityRegistryError(f"identity #{index}: roles must be a non-empty subset of {sorted(ROLES)}")
        self._identities = tuple((token.encode(), identity) for token, identity in identities.items())

    def validate(self, token: str) -> Identity:
        if not TOKEN_PATTERN.fullmatch(token):
            raise InvalidToken()
        candidate = token.encode()
        found = None
        for known, identity in self._identities:  # every entry is compared: constant time per entry
            if hmac.compare_digest(known, candidate):
                found = identity
        if found is None:
            raise InvalidToken()
        return found


#: Documents the Bearer scheme in OpenAPI; the checks below read the raw header themselves.
_bearer = HTTPBearer(auto_error=False, description="Token opaco de desarrollo `dev-…` (DT-065)")

_UNAUTHENTICATED = {"WWW-Authenticate": "Bearer"}


def current_identity(
    request: Request, _credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)
) -> Identity:
    """401 without credentials or with an invalid token; records ``subject_id`` for the access log."""
    header = request.headers.get("authorization")
    if header is None:
        raise ApiError(401, "AUTHENTICATION_REQUIRED", "Se requiere autenticación.", headers=_UNAUTHENTICATED)
    scheme, _, token = header.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        raise ApiError(401, "INVALID_TOKEN", "El token no es válido.", headers=_UNAUTHENTICATED)
    try:
        identity = request.app.state.token_validator.validate(token)
    except InvalidToken:
        raise ApiError(401, "INVALID_TOKEN", "El token no es válido.", headers=_UNAUTHENTICATED) from None
    request.state.subject_id = identity.subject_id
    return identity


def require_roles(allowed: frozenset[str]) -> Callable[..., Identity]:
    """Dependency: the identity must hold at least one of ``allowed``; otherwise 403."""

    def dependency(identity: Identity = Depends(current_identity)) -> Identity:
        if not identity.roles & allowed:
            raise ApiError(403, "FORBIDDEN", "No tiene permiso para este recurso.")
        return identity

    dependency.allowed_roles = allowed  # type: ignore[attr-defined]  # read by the role-matrix tests
    return dependency
