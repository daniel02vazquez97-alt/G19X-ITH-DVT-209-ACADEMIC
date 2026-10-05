"""Development `TokenValidator`, 401/403 and the explicit role matrix (`DT-065`, `docs/07` §7.2)."""

from __future__ import annotations

import logging
import unittest
from unittest import mock

from _api_support import ENDPOINTS, IDENTITIES, TOKENS, auth, client

from app.api import auth as auth_module
from app.api.auth import ADMIN, ANALYST, PLANNER, ROLES, VIEWER, DevTokenValidator, Identity, IdentityRegistryError, InvalidToken


class DevTokenValidatorTest(unittest.TestCase):
    def test_known_token_gives_its_identity(self) -> None:
        validator = DevTokenValidator(IDENTITIES)
        self.assertEqual(validator.validate(TOKENS[PLANNER]), Identity("dev-planner", frozenset({PLANNER})))

    def test_malformed_and_unknown_tokens(self) -> None:
        validator = DevTokenValidator(IDENTITIES)
        for token in ("", "dev-", "dev-short", "xyz-viewer-token-0000000", "dev-unknown-token-0000000",
                      TOKENS[VIEWER] + " ", "dev-" + "a" * 65):
            with self.subTest(token=token), self.assertRaises(InvalidToken):
                validator.validate(token)

    def test_every_entry_is_compared_in_constant_time(self) -> None:
        validator = DevTokenValidator(IDENTITIES)
        with mock.patch.object(auth_module.hmac, "compare_digest", wraps=auth_module.hmac.compare_digest) as compare:
            validator.validate(TOKENS[VIEWER])
        self.assertEqual(compare.call_count, len(IDENTITIES))

    def test_registry_is_validated(self) -> None:
        for registry in ({}, {"dev-bad": Identity("a", frozenset({VIEWER}))},
                         {TOKENS[VIEWER]: Identity("a", frozenset())},
                         {TOKENS[VIEWER]: Identity("a", frozenset({"ROOT"}))}):
            with self.subTest(registry=str(registry)[:40]), self.assertRaises(IdentityRegistryError):
                DevTokenValidator(registry)

    def test_the_four_roles_and_no_other(self) -> None:
        self.assertEqual(ROLES, {VIEWER, ANALYST, PLANNER, ADMIN})


class AuthenticationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = client()

    def test_missing_header_is_401_authentication_required(self) -> None:
        response = self.client.get("/api/v1/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "AUTHENTICATION_REQUIRED")
        self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_invalid_tokens_are_401_invalid_token(self) -> None:
        for header in ("Bearer", "Bearer ", f"Basic {TOKENS[VIEWER]}", TOKENS[VIEWER], "Bearer dev-unknown-token-0000000",
                       "Bearer not-a-dev-token"):
            with self.subTest(header=header):
                response = self.client.get("/api/v1/me", headers={"Authorization": header})
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["error"]["code"], "INVALID_TOKEN")
                self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_me_returns_the_identity(self) -> None:
        for role in (VIEWER, ANALYST, PLANNER, ADMIN):
            with self.subTest(role):
                response = self.client.get("/api/v1/me", headers=auth(role))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"subject_id": f"dev-{role.lower()}", "roles": [role]})

    def test_tokens_never_appear_in_logs(self) -> None:
        with self.assertLogs(level=logging.DEBUG) as captured:
            self.client.get("/api/v1/me", headers=auth(VIEWER))
            self.client.get("/api/v1/me", headers={"Authorization": "Bearer dev-unknown-token-0000000"})
            self.client.get("/api/v1/products/1/history", headers=auth(VIEWER))
        text = "\n".join(captured.output)
        self.assertIn("dev-viewer", text)  # the subject id is logged …
        for token in list(TOKENS.values()) + ["dev-unknown-token-0000000"]:
            self.assertNotIn(token, text)  # … never a token
        self.assertNotIn("Bearer", text)
        self.assertNotIn("uthorization", text)


class RoleMatrixTest(unittest.TestCase):
    """14 endpoints × 4 roles + no token. Allowed requests pass authentication and reach the (closed)
    database, so they answer 503; denied ones answer 403 before any query; without a token, 401."""

    def test_matrix(self) -> None:
        api = client()
        for path, allowed in ENDPOINTS:
            if allowed is None:
                self.assertEqual(api.get(path).status_code, 200)
                continue
            self.assertEqual(api.get(path).status_code, 401, path)
            for role in (VIEWER, ANALYST, PLANNER, ADMIN):
                with self.subTest(path=path, role=role):
                    status = api.get(path, headers=auth(role)).status_code
                    if role not in allowed:
                        self.assertEqual(status, 403)
                    elif path == "/api/v1/me":
                        self.assertEqual(status, 200)
                    else:
                        self.assertEqual(status, 503)  # authorized: it tried to read

    def test_no_role_hierarchy(self) -> None:
        # ADMIN does not imply VIEWER-only resources by hierarchy: each endpoint lists its roles.
        from app.api.auth import ALL_ROLES, HISTORY_ROLES, RUN_ROLES

        self.assertEqual(HISTORY_ROLES, {ANALYST, PLANNER, ADMIN})
        self.assertEqual(RUN_ROLES, {PLANNER, ADMIN})
        self.assertEqual(ALL_ROLES, {VIEWER, ANALYST, PLANNER, ADMIN})


if __name__ == "__main__":
    unittest.main()
