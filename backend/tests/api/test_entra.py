"""Microsoft Entra ID `TokenValidator` (U11, `DT-099`): cryptographic validation, claims and the role matrix.

No Entra ID, no network: an RSA key pair generated per run plays the tenant's signing key and a fake key
source plays its JWKS. Requires the optional groups ``api``, ``test`` and ``entra``.
"""

from __future__ import annotations

import logging
import sys
import time
import unittest
import uuid

import jwt
from _api_support import ENDPOINTS, UNREACHABLE_DB
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from starlette.testclient import TestClient

from app.api.app import create_app
from app.api.auth import ADMIN, ANALYST, PLANNER, VIEWER, Identity, InvalidToken
from app.api.entra import (
    EntraConfig,
    EntraConfigError,
    EntraTokenValidator,
    SigningKeysUnavailable,
    TenantSigningKeys,
)
from app.api.settings import Settings

TENANT = "11111111-2222-4333-8444-555555555555"
OTHER_TENANT = "99999999-2222-4333-8444-555555555555"
API = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
SPA = "12345678-bbbb-4ccc-8ddd-eeeeeeeeeeee"
USER = "0f0f0f0f-1111-4222-8333-444444444444"
KID = "test-kid-1"
CONFIG = EntraConfig(TENANT, API, SPA)
ISSUER = f"https://login.microsoftonline.com/{TENANT}/v2.0"

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeKeys:
    """The tenant's JWKS: one known ``kid``; an unknown one is refused like `TenantSigningKeys` does."""

    def __init__(self, unavailable: bool = False) -> None:
        self.unavailable = unavailable
        self.calls = 0

    def key_for(self, token: str):
        self.calls += 1
        if self.unavailable:
            raise SigningKeysUnavailable("JWKS unavailable")
        if jwt.get_unverified_header(token).get("kid") != KID:
            raise InvalidToken()
        return PRIVATE_KEY.public_key()


def claims(**overrides):
    now = int(time.time())
    base = {
        "aud": API, "iss": ISSUER, "iat": now - 10, "nbf": now - 10, "exp": now + 3600,
        "tid": TENANT, "oid": USER, "sub": "pairwise-sub", "ver": "2.0", "azp": SPA, "azpacr": "0",
        "scp": "access_as_user", "roles": [VIEWER],
    }
    base.update(overrides)
    return {key: value for key, value in base.items() if value is not None}


def token(key=PRIVATE_KEY, algorithm="RS256", kid=KID, **overrides) -> str:
    headers = {"kid": kid} if kid is not None else {}
    return jwt.encode(claims(**overrides), key, algorithm=algorithm, headers=headers)


def validator(keys=None) -> EntraTokenValidator:
    return EntraTokenValidator(CONFIG, keys if keys is not None else FakeKeys())


class EntraConfigTest(unittest.TestCase):
    def test_issuer_and_metadata_derive_from_the_tenant_on_the_fixed_host(self) -> None:
        self.assertEqual(CONFIG.issuer, ISSUER)
        self.assertEqual(CONFIG.metadata_url,
                         f"https://login.microsoftonline.com/{TENANT}/v2.0/.well-known/openid-configuration")

    def test_identifiers_must_be_guids_and_distinct(self) -> None:
        for args in (("common", API, SPA), (TENANT, "api://x", SPA), (TENANT, API, ""), (TENANT, API, API),
                     (TENANT, API.upper(), SPA)):
            with self.subTest(args=args), self.assertRaises(EntraConfigError):
                EntraConfig(*args)


class ValidTokenTest(unittest.TestCase):
    def test_valid_token_gives_oid_and_roles(self) -> None:
        identity = validator().validate(token(roles=[PLANNER, VIEWER]))
        self.assertEqual(identity, Identity(USER, frozenset({PLANNER, VIEWER})))

    def test_scope_among_others(self) -> None:
        self.assertEqual(validator().validate(token(scp="openid access_as_user")).subject_id, USER)

    def test_without_roles_claim_authenticates_with_no_roles(self) -> None:
        self.assertEqual(validator().validate(token(roles=None)).roles, frozenset())

    def test_unknown_role_values_are_ignored(self) -> None:
        identity = validator().validate(token(roles=["Admin", "viewer", "ROOT", ANALYST]))
        self.assertEqual(identity.roles, frozenset({ANALYST}))

    def test_clock_skew_is_bounded(self) -> None:
        now = int(time.time())
        self.assertEqual(validator().validate(token(exp=now - 30)).subject_id, USER)  # within 60 s
        with self.assertRaises(InvalidToken):
            validator().validate(token(exp=now - 120))


class RejectedTokenTest(unittest.TestCase):
    def assertRejected(self, value: str) -> None:
        with self.assertRaises(InvalidToken):
            validator().validate(value)

    def test_invalid_signature(self) -> None:
        self.assertRejected(token(key=OTHER_KEY))
        good = token()
        head, payload, signature = good.split(".")
        self.assertRejected(f"{head}.{payload}.{signature[:-4]}AAAA")

    def test_tampered_payload(self) -> None:
        forged = token(roles=[ADMIN]).split(".")[1]
        head, _, signature = token(roles=[VIEWER]).split(".")
        self.assertRejected(f"{head}.{forged}.{signature}")

    def test_invalid_issuer(self) -> None:
        for issuer in (f"https://login.microsoftonline.com/{OTHER_TENANT}/v2.0",
                       f"https://sts.windows.net/{TENANT}/", "https://evil.example/v2.0", None):
            with self.subTest(issuer=issuer):
                self.assertRejected(token(iss=issuer))

    def test_invalid_audience(self) -> None:
        for audience in (SPA, f"api://{API}", "00000003-0000-0000-c000-000000000000", [SPA], None):
            with self.subTest(audience=audience):
                self.assertRejected(token(aud=audience))

    def test_expired(self) -> None:
        self.assertRejected(token(exp=int(time.time()) - 3600))

    def test_not_yet_valid(self) -> None:
        self.assertRejected(token(nbf=int(time.time()) + 3600))

    def test_issued_in_the_future(self) -> None:
        self.assertRejected(token(iat=int(time.time()) + 3600))

    def test_invalid_tenant(self) -> None:
        self.assertRejected(token(tid=OTHER_TENANT))
        self.assertRejected(token(tid=None))

    def test_other_client_application(self) -> None:
        self.assertRejected(token(azp="deadbeef-bbbb-4ccc-8ddd-eeeeeeeeeeee"))
        self.assertRejected(token(azp=None))

    def test_app_only_or_wrong_scope(self) -> None:
        for scope in (None, "", "User.Read", "access_as_user_x", "Access_As_User"):
            with self.subTest(scope=scope):
                self.assertRejected(token(scp=scope))

    def test_v1_tokens(self) -> None:
        self.assertRejected(token(ver="1.0"))

    def test_required_claims(self) -> None:
        for claim in ("exp", "nbf", "iat", "oid", "ver"):
            with self.subTest(claim=claim):
                self.assertRejected(token(**{claim: None}))

    def test_bad_oid_and_roles_shapes(self) -> None:
        self.assertRejected(token(oid="not-a-guid"))
        self.assertRejected(token(roles="ADMIN"))
        self.assertRejected(token(roles=[ADMIN, 1]))

    def test_other_algorithms(self) -> None:
        public_pem = PRIVATE_KEY.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        self.assertRejected(token_hs256(public_pem))  # HS256 keyed with the public key (key confusion)
        unsigned = jwt.encode(claims(), None, algorithm="none", headers={"kid": KID})
        self.assertRejected(unsigned)
        self.assertRejected(unsigned + "AAAA")
        self.assertRejected(token(key=PRIVATE_KEY, algorithm="RS512"))

    def test_unknown_or_missing_kid(self) -> None:
        self.assertRejected(token(kid="other-kid"))
        self.assertRejected(token(kid=None))

    def test_malformed(self) -> None:
        for value in ("", "abc", "a.b", "a.b.c.d", "dev-viewer-token-0000000", "x" * 20000, token() + " "):
            with self.subTest(value=value[:20]):
                self.assertRejected(value)

    def test_no_key_lookup_for_other_algorithms(self) -> None:
        keys = FakeKeys()
        with self.assertRaises(InvalidToken):
            EntraTokenValidator(CONFIG, keys).validate(token(key=PRIVATE_KEY, algorithm="RS512"))
        self.assertEqual(keys.calls, 0)


def token_hs256(secret: bytes) -> str:
    """HS256 token whose HMAC key is the public key: PyJWT refuses PEM keys for HMAC, so sign by hand."""
    import base64
    import hashlib
    import hmac
    import json

    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    head = b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": KID}).encode())
    body = b64(json.dumps(claims()).encode())
    signature = b64(hmac.new(secret, f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{signature}"


class TenantSigningKeysTest(unittest.TestCase):
    METADATA = {"issuer": ISSUER, "jwks_uri": f"https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys"}

    def test_discovery_runs_once_from_the_tenant_metadata(self) -> None:
        fetched, created = [], []

        class Client:
            def get_signing_key_from_jwt(self, value):
                return type("K", (), {"key": PRIVATE_KEY.public_key()})()

        keys = TenantSigningKeys(CONFIG, fetch_json=lambda url: fetched.append(url) or self.METADATA,
                                 client_factory=lambda uri: created.append(uri) or Client())
        validator_ = EntraTokenValidator(CONFIG, keys)
        for _ in range(3):
            self.assertEqual(validator_.validate(token()).subject_id, USER)
        self.assertEqual(fetched, [CONFIG.metadata_url])
        self.assertEqual(created, [self.METADATA["jwks_uri"]])

    def test_inconsistent_metadata_is_a_server_failure(self) -> None:
        for metadata in ({"issuer": f"https://login.microsoftonline.com/{OTHER_TENANT}/v2.0",
                          "jwks_uri": self.METADATA["jwks_uri"]},
                         {"issuer": ISSUER, "jwks_uri": "https://evil.example/keys"},
                         {"issuer": ISSUER, "jwks_uri": "http://login.microsoftonline.com/x"},
                         {"issuer": ISSUER}):
            with self.subTest(metadata=metadata):
                keys = TenantSigningKeys(CONFIG, fetch_json=lambda url, m=metadata: m,
                                         client_factory=lambda uri: self.fail("no JWKS client"))
                with self.assertRaises(SigningKeysUnavailable):
                    keys.key_for(token())

    def test_network_failure_is_a_server_failure(self) -> None:
        def offline(url):
            raise OSError("offline")

        with self.assertRaises(SigningKeysUnavailable):
            TenantSigningKeys(CONFIG, fetch_json=offline).key_for(token())

    def test_fetch_is_limited_to_the_authority_host(self) -> None:
        from app.api.entra import _fetch_json

        with self.assertRaises(SigningKeysUnavailable):
            _fetch_json("https://evil.example/.well-known/openid-configuration")

    def test_unknown_kid_from_the_real_client_is_an_invalid_token(self) -> None:
        class Client:
            def get_signing_key_from_jwt(self, value):
                raise jwt.PyJWKClientError("Unable to find a signing key that matches")

        keys = TenantSigningKeys(CONFIG, fetch_json=lambda url: self.METADATA, client_factory=lambda uri: Client())
        with self.assertRaises(InvalidToken):
            keys.key_for(token())


def entra_client(keys=None, **kwargs) -> TestClient:
    settings = Settings("dev", UNREACHABLE_DB, {}, CONFIG)
    return TestClient(create_app(settings, EntraTokenValidator(CONFIG, keys or FakeKeys())), **kwargs)


def bearer(value: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {value}"}


class EntraApiTest(unittest.TestCase):
    """The same 401/403 contract and role matrix as `DT-065`, with Entra ID tokens (`DT-099`)."""

    def test_app_env_dev_builds_the_entra_validator(self) -> None:
        app = create_app(Settings("dev", UNREACHABLE_DB, {}, CONFIG))
        self.assertIsInstance(app.state.token_validator, EntraTokenValidator)

    def test_401_without_token_and_with_invalid_tokens(self) -> None:
        api = entra_client()
        response = api.get("/api/v1/me")
        self.assertEqual((response.status_code, response.json()["error"]["code"]), (401, "AUTHENTICATION_REQUIRED"))
        for value in (token(key=OTHER_KEY), token(aud=SPA), token(exp=int(time.time()) - 3600),
                      "dev-viewer-token-0000000", token(scp=None)):
            response = api.get("/api/v1/me", headers=bearer(value))
            self.assertEqual((response.status_code, response.json()["error"]["code"]), (401, "INVALID_TOKEN"))
            self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_me_with_and_without_roles(self) -> None:
        api = entra_client()
        response = api.get("/api/v1/me", headers=bearer(token(roles=[ANALYST, VIEWER])))
        self.assertEqual(response.json(), {"subject_id": USER, "roles": [ANALYST, VIEWER]})
        response = api.get("/api/v1/me", headers=bearer(token(roles=None)))
        self.assertEqual((response.status_code, response.json()), (200, {"subject_id": USER, "roles": []}))

    def test_role_matrix(self) -> None:
        api = entra_client()
        for path, allowed in ENDPOINTS:
            if allowed is None:
                self.assertEqual(api.get(path).status_code, 200)
                continue
            self.assertEqual(api.get(path).status_code, 401, path)
            for roles in ([VIEWER], [ANALYST], [PLANNER], [ADMIN], None):
                with self.subTest(path=path, roles=roles):
                    status = api.get(path, headers=bearer(token(roles=roles))).status_code
                    if path == "/api/v1/me":
                        self.assertEqual(status, 200)
                    elif roles is None or roles[0] not in allowed:
                        self.assertEqual(status, 403)
                    else:
                        self.assertEqual(status, 503)  # authorized: it tried to read the (closed) database

    def test_jwks_unavailable_is_not_reported_as_the_clients_fault(self) -> None:
        api = entra_client(FakeKeys(unavailable=True), raise_server_exceptions=False)
        response = api.get("/api/v1/me", headers=bearer(token()))
        self.assertEqual(response.status_code, 500)

    def test_tokens_and_claims_never_appear_in_logs(self) -> None:
        api = entra_client()
        good, bad = token(roles=[VIEWER]), token(key=OTHER_KEY)
        with self.assertLogs(level=logging.DEBUG) as captured:
            api.get("/api/v1/me", headers=bearer(good))
            api.get("/api/v1/me", headers=bearer(bad))
            api.get("/api/v1/runs/1", headers=bearer(good))
        text = "\n".join(captured.output)
        self.assertIn(USER, text)  # the subject id (oid) is logged …
        for value in (good, bad, good.split(".")[1], bad.split(".")[2]):
            self.assertNotIn(value, text)  # … never a token or a part of one
        self.assertNotIn("Bearer", text)
        self.assertNotIn(SPA, text)
        self.assertIn("entra token rejected: InvalidSignatureError", text)


class LocalModeIsUntouchedTest(unittest.TestCase):
    def test_local_runs_without_the_entra_group(self) -> None:
        import subprocess
        from pathlib import Path

        backend = Path(__file__).resolve().parents[2]
        code = (
            "import sys; sys.modules['jwt'] = None\n"
            "from app.api.app import create_app\n"
            "from app.api.auth import DevTokenValidator, Identity\n"
            "from app.api.settings import load_settings\n"
            "s = load_settings({'APP_ENV': 'local', 'DATABASE_URL': 'postgresql://x@127.0.0.1:1/x',"
            " 'DEV_AUTH_IDENTITIES': '{\"dev-viewer-token-0000000\": {\"subject_id\": \"v\", \"roles\": [\"VIEWER\"]}}'})\n"
            "app = create_app(s)\n"
            "assert isinstance(app.state.token_validator, DevTokenValidator)\n"
            "assert 'app.api.entra' not in sys.modules\n"
            "print('LOCAL_OK')\n"
        )
        result = subprocess.run([sys.executable, "-c", code], cwd=backend, capture_output=True, text=True, check=False)
        self.assertIn("LOCAL_OK", result.stdout, result.stderr)


if __name__ == "__main__":
    unittest.main()
