"""Microsoft Entra ID access-token validator for ``APP_ENV=dev`` (U11, `DT-099`, `docs/10` §2.3).

Implements the `TokenValidator` port of `DT-065`: the port, the role matrix and the 401/403 contract do
not change; only where the identity comes from does.

Only **v2.0 delegated access tokens issued for this API** are accepted (Microsoft Learn, «Access tokens» and
«Access token claims reference», verified 2026-10-07):

* signature: RS256 only, with a public key of the tenant's JWKS (discovered from the tenant's OpenID
  metadata on the fixed host ``login.microsoftonline.com``, cached 24 h, one forced refresh on an unknown
  ``kid``); never decoded without verifying the signature;
* ``iss`` exactly ``https://login.microsoftonline.com/{tenant}/v2.0`` and ``tid`` exactly the tenant;
* ``aud`` exactly the API client ID (in v2.0 tokens ``aud`` is always the API's client ID);
* ``exp``, ``nbf`` and ``iat`` with a bounded clock skew of 60 s;
* ``ver`` ``2.0``; ``azp`` the SPA client ID (the only client of this API);
* ``scp`` contains ``access_as_user``: app-only tokens (no ``scp``) are rejected;
* ``oid`` (immutable object ID) becomes ``subject_id``; ``roles`` keeps only the four values of
  ASSUMPTION-010. A valid token without any of them authenticates (``/me`` answers) and every other
  endpoint answers 403 (RS-002).

Tokens and claims are never logged; a rejection logs only the category of the failure.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import jwt

from .auth import ROLES, Identity, InvalidToken

logger = logging.getLogger("app.api.entra")

LOGIN_HOST = "https://login.microsoftonline.com"
ALGORITHMS = ("RS256",)
REQUIRED_SCOPE = "access_as_user"
CLOCK_SKEW_SECONDS = 60
JWKS_LIFESPAN_SECONDS = 24 * 3600  # «A reasonable frequency to check for updates … is every 24 hours»
HTTP_TIMEOUT_SECONDS = 10
MAX_TOKEN_LENGTH = 16 * 1024
REQUIRED_CLAIMS = ("exp", "nbf", "iat", "iss", "aud", "tid", "oid", "ver", "azp", "scp")

GUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
JWT_SHAPE = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


class EntraConfigError(ValueError):
    """The Entra ID configuration is incomplete or malformed: the API refuses to start."""


class SigningKeysUnavailable(RuntimeError):
    """The tenant metadata or its JWKS could not be obtained or are inconsistent (server-side failure)."""


@dataclass(frozen=True)
class EntraConfig:
    """Non-secret identifiers of the tenant and of the two app registrations (`DT-099`)."""

    tenant_id: str
    api_client_id: str
    spa_client_id: str

    def __post_init__(self) -> None:
        for name in ("tenant_id", "api_client_id", "spa_client_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not GUID.fullmatch(value):
                raise EntraConfigError(f"{name} must be a lowercase GUID")
        if self.api_client_id == self.spa_client_id:
            raise EntraConfigError("the API and the SPA must be different app registrations")

    @property
    def issuer(self) -> str:
        return f"{LOGIN_HOST}/{self.tenant_id}/v2.0"

    @property
    def metadata_url(self) -> str:
        return f"{LOGIN_HOST}/{self.tenant_id}/v2.0/.well-known/openid-configuration"


class SigningKeySource(Protocol):
    def key_for(self, token: str) -> Any: ...


def _fetch_json(url: str) -> Mapping[str, Any]:
    if not url.startswith(LOGIN_HOST + "/"):
        raise SigningKeysUnavailable("refusing to fetch outside the Entra ID authority host")
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:  # noqa: S310 (fixed https host)
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise SigningKeysUnavailable("the OpenID metadata is not a JSON object")
    return payload


class TenantSigningKeys:
    """JWKS of the tenant: ``jwks_uri`` comes from the tenant's own OpenID metadata, never from the token
    or from user input, and must stay on the authority host. Discovery is lazy (first request) and runs once."""

    def __init__(self, config: EntraConfig, fetch_json: Callable[[str], Mapping[str, Any]] = _fetch_json,
                 client_factory: Callable[[str], Any] | None = None) -> None:
        self._config = config
        self._fetch_json = fetch_json
        self._client_factory = client_factory or (lambda uri: jwt.PyJWKClient(
            uri, cache_jwk_set=True, lifespan=JWKS_LIFESPAN_SECONDS, timeout=HTTP_TIMEOUT_SECONDS))
        self._client: Any = None
        self._lock = threading.Lock()

    def _jwks_client(self) -> Any:
        with self._lock:
            if self._client is None:
                try:
                    metadata = self._fetch_json(self._config.metadata_url)
                except SigningKeysUnavailable:
                    raise
                except Exception as exc:  # network, TLS, JSON: a server-side failure, not a bad token
                    raise SigningKeysUnavailable(f"OpenID metadata unavailable ({type(exc).__name__})") from None
                if metadata.get("issuer") != self._config.issuer:
                    raise SigningKeysUnavailable("the OpenID metadata issuer is not the expected tenant issuer")
                jwks_uri = metadata.get("jwks_uri")
                if not isinstance(jwks_uri, str) or not jwks_uri.startswith(LOGIN_HOST + "/"):
                    raise SigningKeysUnavailable("the jwks_uri is not on the Entra ID authority host")
                self._client = self._client_factory(jwks_uri)
            return self._client

    def key_for(self, token: str) -> Any:
        client = self._jwks_client()
        try:
            return client.get_signing_key_from_jwt(token).key
        except jwt.PyJWKClientConnectionError:
            raise SigningKeysUnavailable("JWKS unavailable") from None
        except jwt.PyJWKClientError:
            raise InvalidToken() from None  # unknown kid after the forced refresh


class EntraTokenValidator:
    """`TokenValidator` for Microsoft Entra ID access tokens (see the module docstring)."""

    def __init__(self, config: EntraConfig, keys: SigningKeySource | None = None,
                 clock_skew: int = CLOCK_SKEW_SECONDS) -> None:
        self._config = config
        self._keys = keys if keys is not None else TenantSigningKeys(config)
        self._clock_skew = clock_skew

    @staticmethod
    def _reject(reason: str) -> InvalidToken:
        logger.info("entra token rejected: %s", reason)  # category only: never the token or its claims
        return InvalidToken()

    def validate(self, token: str) -> Identity:
        if len(token) > MAX_TOKEN_LENGTH or not JWT_SHAPE.fullmatch(token):
            raise self._reject("malformed")
        try:
            header = jwt.get_unverified_header(token)  # only to refuse other algorithms before any key lookup
        except jwt.PyJWTError:
            raise self._reject("malformed header") from None
        if header.get("alg") not in ALGORITHMS or not header.get("kid"):
            raise self._reject("unexpected algorithm or missing kid")
        try:
            key = self._keys.key_for(token)
        except InvalidToken:
            raise self._reject("unknown signing key") from None
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=list(ALGORITHMS),
                audience=self._config.api_client_id,
                issuer=self._config.issuer,
                leeway=self._clock_skew,
                options={"require": list(REQUIRED_CLAIMS), "verify_signature": True},
            )
        except jwt.PyJWTError as exc:
            raise self._reject(type(exc).__name__) from None
        return self._identity(claims)

    def _identity(self, claims: Mapping[str, Any]) -> Identity:
        if claims.get("ver") != "2.0":
            raise self._reject("not a v2.0 token")
        if claims.get("tid") != self._config.tenant_id:
            raise self._reject("unexpected tenant")
        if claims.get("azp") != self._config.spa_client_id:
            raise self._reject("unexpected client application")
        scopes = claims.get("scp")
        if not isinstance(scopes, str) or REQUIRED_SCOPE not in scopes.split(" "):
            raise self._reject("missing delegated scope")
        oid = claims.get("oid")
        if not isinstance(oid, str) or not GUID.fullmatch(oid):
            raise self._reject("invalid oid")
        raw_roles = claims.get("roles", [])
        if not isinstance(raw_roles, list) or not all(isinstance(role, str) for role in raw_roles):
            raise self._reject("invalid roles claim")
        return Identity(oid, frozenset(raw_roles) & ROLES)
