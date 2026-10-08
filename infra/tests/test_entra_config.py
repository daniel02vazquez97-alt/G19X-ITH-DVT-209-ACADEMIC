"""U11 (`DT-099`): the Entra ID desired state and infra/azure/deploy-u11.ps1, without Entra ID.

Static checks tie the desired state to the backend and the frontend (roles, scope, redirect URIs). The flow
tests run the real script with PowerShell 7 against ``fake_az.py`` (a fake Azure CLI with Graph-like state);
they are skipped where ``pwsh`` is not installed. Run from the repository root::

    python -m unittest discover -s infra/tests -t infra/tests
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "infra" / "azure" / "entra" / "u11-entra.dev.json"
SCRIPT = ROOT / "infra" / "azure" / "deploy-u11.ps1"
FAKE_AZ = Path(__file__).resolve().parent / "fake_az.py"
SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
PWSH = shutil.which("pwsh")
USER = "0f0f0f0f-1111-4222-8333-444444444444"
GUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
EMULATE_PS51 = (
    "function global:ConvertFrom-Json { param([Parameter(ValueFromPipeline = $true)]$InputObject) "
    "process { Microsoft.PowerShell.Utility\\ConvertFrom-Json -InputObject $InputObject -NoEnumerate } }; "
)


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


class DesiredState(unittest.TestCase):
    def test_the_four_roles_of_assumption_010_and_of_the_backend(self) -> None:
        values = [role["value"] for role in SPEC["api"]["appRoles"]]
        self.assertEqual(sorted(values), ["ADMIN", "ANALYST", "PLANNER", "VIEWER"])
        backend = text(ROOT / "backend" / "app" / "api" / "auth.py")
        self.assertIn('VIEWER, ANALYST, PLANNER, ADMIN = "VIEWER", "ANALYST", "PLANNER", "ADMIN"', backend)
        frontend = text(ROOT / "frontend" / "src" / "roles" / "access.ts")
        self.assertIn("export const ROLES = ['VIEWER', 'ANALYST', 'PLANNER', 'ADMIN'] as const;", frontend)
        for role in SPEC["api"]["appRoles"]:
            with self.subTest(role=role["value"]):
                self.assertEqual(role["allowedMemberTypes"], ["User"])  # users (and groups); no app-only callers
                self.assertTrue(role["isEnabled"])
                self.assertEqual(role["displayName"], role["value"])
                self.assertIn("ASSUMPTION-010", role["description"])

    def test_fixed_unique_guids(self) -> None:
        ids = [role["id"] for role in SPEC["api"]["appRoles"]] + [SPEC["api"]["scope"]["id"]]
        self.assertEqual(len(set(ids)), 5)
        for value in ids + [SPEC["tenantId"]]:
            self.assertRegex(value, GUID)
        self.assertEqual(SPEC["tenantId"], "6ce4b1ba-ae4f-4887-bd6b-acb3c72039ad")  # DT-098

    def test_scope_token_version_and_assignment(self) -> None:
        self.assertEqual(SPEC["api"]["scope"]["value"], "access_as_user")
        self.assertIn('REQUIRED_SCOPE = "access_as_user"', text(ROOT / "backend" / "app" / "api" / "entra.py"))
        self.assertIn("export const API_SCOPE_NAME = 'access_as_user';", text(ROOT / "frontend" / "src" / "auth" / "authMode.ts"))
        self.assertEqual(SPEC["api"]["requestedAccessTokenVersion"], 2)  # aud = API client ID, iss .../v2.0
        self.assertTrue(SPEC["api"]["appRoleAssignmentRequired"])
        self.assertEqual(SPEC["signInAudience"], "AzureADMyOrg")

    def test_redirect_uris_are_the_dev_origins_actually_used(self) -> None:
        uris = SPEC["spa"]["redirectUris"]
        self.assertEqual(uris[:2], ["http://localhost:5173", "http://localhost:8080"])
        # U12 (DT-100): deploy-u12.ps1 -Stage Core may add the HTTPS frontend of Azure Container Apps, and nothing else.
        for extra in uris[2:]:
            self.assertRegex(extra, r"^https://ca-mpa-dev-frontend\.[a-z0-9-]+\.centralus\.azurecontainerapps\.io$")
        self.assertLessEqual(len(uris), 3)
        self.assertIn("port: 5173", text(ROOT / "frontend" / "vite.config.ts"))
        self.assertIn('"127.0.0.1:8080:8080"', text(ROOT / "infra" / "docker-compose.yml"))
        self.assertIn("VITE_ENTRA_REDIRECT_URI: http://localhost:8080", text(ROOT / "infra" / "docker-compose.entra-dev.yml"))

    def test_nothing_secret(self) -> None:
        text(SPEC_PATH).encode("ascii")
        values = json.dumps({k: v for k, v in SPEC.items() if k != "_comment"}).lower()
        self.assertNotRegex(values, r"secret|password|certificate|private|bearer")


class ScriptSource(unittest.TestCase):
    SOURCE = text(SCRIPT)

    def test_ascii(self) -> None:
        SCRIPT.read_bytes().decode("ascii")

    def test_never_creates_credentials_or_enables_the_implicit_flow(self) -> None:
        for forbidden in ("credential reset", "credential create", "--password", "--cert", "addPassword", "addKey",
                          "enableIdTokenIssuance = $true", "enableAccessTokenIssuance = $true", "--enable-id-token-issuance true",
                          "Directory.Read.All", "User.Read.All", "Application.ReadWrite.All", "graph.microsoft.com/.default",
                          "get-access-token"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.SOURCE)

    def test_lists_from_az_are_json_arrays(self) -> None:
        self.assertNotIn("@(Invoke-Az", self.SOURCE)
        for line in self.SOURCE.splitlines():
            if "'list'" in line and "Invoke-Az" in line:
                self.assertIn("-Array", line)
                self.assertIn("'--output', 'json'", line)


def run_script(workdir: Path, *args: str, env: dict | None = None, emulate_ps51: bool = False):
    command = f"{EMULATE_PS51 if emulate_ps51 else ''}& '{workdir / 'infra' / 'azure' / 'deploy-u11.ps1'}' {' '.join(args)}; exit $LASTEXITCODE"
    environment = {**os.environ, "PATH": f"{workdir / 'bin'}{os.pathsep}{os.environ['PATH']}",
                   "FAKE_AZ_STATE": str(workdir / "state.json"), **(env or {})}
    return subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command", command], cwd=workdir,
                          capture_output=True, text=True, timeout=300, env=environment)


# The fake Azure CLI is a POSIX shell wrapper; on Windows `az` would resolve to the REAL Azure CLI.
@unittest.skipUnless(PWSH and os.name == "posix", "pwsh and a POSIX host are needed for the fake Azure CLI")
class ScriptFlow(unittest.TestCase):
    """deploy-u11.ps1 end to end against the fake Azure CLI."""

    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="u11-"))
        (self.dir / "infra" / "azure" / "entra").mkdir(parents=True)
        shutil.copy(SCRIPT, self.dir / "infra" / "azure" / "deploy-u11.ps1")
        shutil.copy(SPEC_PATH, self.dir / "infra" / "azure" / "entra" / "u11-entra.dev.json")
        (self.dir / "bin").mkdir()
        wrapper = self.dir / "bin" / "az"
        wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_AZ}" "$@"\n', encoding="utf-8")
        wrapper.chmod(0o755)

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def state(self) -> dict:
        return json.loads((self.dir / "state.json").read_text(encoding="utf-8"))

    def seed(self, state: dict) -> None:
        (self.dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    def configure(self, *args: str, **kwargs):
        result = run_script(self.dir, "-Yes", *args, **kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def apps(self) -> dict:
        return {app["displayName"]: app for app in self.state()["applications"].values()}

    def test_fresh_tenant_is_configured_and_verified(self) -> None:
        output = self.configure().stdout
        self.assertIn("U11: Entra ID configurado y verificado.", output)
        self.assertNotIn("FAIL", output)
        apps = self.apps()
        api, spa = apps["app-mpa-dev-api"], apps["app-mpa-dev-spa"]
        self.assertEqual(api["identifierUris"], [f"api://{api['appId']}"])
        self.assertEqual(api["api"]["requestedAccessTokenVersion"], 2)
        self.assertEqual([s["value"] for s in api["api"]["oauth2PermissionScopes"]], ["access_as_user"])
        self.assertEqual({r["value"]: r["id"] for r in api["appRoles"]},
                         {r["value"]: r["id"] for r in SPEC["api"]["appRoles"]})
        self.assertEqual(api["api"]["preAuthorizedApplications"],
                         [{"appId": spa["appId"], "delegatedPermissionIds": [SPEC["api"]["scope"]["id"]]}])
        self.assertEqual(spa["spa"]["redirectUris"], SPEC["spa"]["redirectUris"])
        self.assertEqual(spa["requiredResourceAccess"],
                         [{"resourceAppId": api["appId"], "resourceAccess": [{"id": SPEC["api"]["scope"]["id"], "type": "Scope"}]}])
        for app in (api, spa):
            self.assertEqual((app["passwordCredentials"], app["keyCredentials"]), ([], []))
            self.assertEqual(app["web"]["implicitGrantSettings"],
                             {"enableIdTokenIssuance": False, "enableAccessTokenIssuance": False})
        sps = {sp["appId"]: sp for sp in self.state()["servicePrincipals"].values()}
        self.assertTrue(sps[api["appId"]]["appRoleAssignmentRequired"])
        self.assertIn(USER, sps[api["appId"]]["owners"])
        self.assertEqual(self.state()["assignments"], [])  # no role is granted by default
        evidence = (self.dir / "tmp" / "u11-evidence" / "u11-evidence.json").read_text(encoding="ascii")
        self.assertEqual(json.loads(evidence)["checksFailed"], 0)
        self.assertNotRegex(evidence.lower(), r'"(access_?token|id_?token|refresh_?token|secrettext|password|client_?secret)"\s*:')
        env = (self.dir / "tmp" / "u11-evidence" / "entra-dev.env").read_text(encoding="ascii")
        self.assertIn(f"ENTRA_API_CLIENT_ID={api['appId']}", env)
        self.assertIn(f"ENTRA_SPA_CLIENT_ID={spa['appId']}", env)
        created = list((self.dir / "tmp" / "u11-evidence").glob("created-*.json"))
        self.assertEqual(len(json.loads(created[0].read_text(encoding="ascii"))["created"]), 4)

    def test_second_run_is_already_configured_and_changes_nothing(self) -> None:
        self.configure()
        calls = len(self.state()["calls"])
        output = self.configure().stdout
        self.assertIn("ALREADY_CONFIGURED", output)
        new_calls = self.state()["calls"][calls:]
        self.assertFalse([c for c in new_calls if c.startswith(("PATCH", "DELETE", "ad app create", "ad sp create"))], new_calls)
        self.assertEqual(len(self.apps()), 2)

    def test_same_result_with_windows_powershell_51_json(self) -> None:
        self.configure(emulate_ps51=True)
        self.assertIn("ALREADY_CONFIGURED", self.configure(emulate_ps51=True).stdout)

    def test_role_assignment_is_explicit_and_only_for_the_signed_in_user(self) -> None:
        self.configure()
        self.configure("-AssignRole", "VIEWER")
        viewer = next(r["id"] for r in SPEC["api"]["appRoles"] if r["value"] == "VIEWER")
        self.assertEqual([(a["principalId"], a["appRoleId"]) for a in self.state()["assignments"]], [(USER, viewer)])
        self.assertIn("VIEWER ya estaba asignado", self.configure("-AssignRole", "VIEWER").stdout)
        self.configure("-RemoveRole", "VIEWER")
        self.assertEqual(self.state()["assignments"], [])
        result = run_script(self.dir, "-Yes", "-AssignRole", "Administrator")
        self.assertEqual(result.returncode, 1)
        self.assertIn("rol desconocido", result.stdout)

    def test_duplicates_stop_without_creating(self) -> None:
        self.configure()
        state = self.state()
        api = next(a for a in state["applications"].values() if a["displayName"] == "app-mpa-dev-api")
        clone = {**api, "id": "11111111-0000-4000-8000-000000000001", "appId": "11111111-0000-4000-8000-000000000002"}
        state["applications"][clone["id"]] = clone
        self.seed(state)
        result = run_script(self.dir, "-Yes")
        self.assertEqual(result.returncode, 1)
        self.assertIn("hay 2 aplicaciones llamadas app-mpa-dev-api", result.stdout)
        self.assertEqual(len(self.state()["applications"]), 3)

    def test_without_permission_to_register_apps_it_stops_before_creating(self) -> None:
        result = run_script(self.dir, "-Yes", env={"FAKE_AZ_ALLOW_CREATE": "false"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("Application Developer", result.stdout)
        self.assertEqual(self.state()["applications"], {})

    def test_authorization_request_denied_stops_and_never_elevates(self) -> None:
        result = run_script(self.dir, "-Yes", env={"FAKE_AZ_DENY": "create"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("Authorization_RequestDenied", result.stdout)
        self.assertIn("No se intenta elevar privilegios", result.stdout)
        self.assertEqual(self.state()["applications"], {})

    def test_an_existing_secret_is_a_stop(self) -> None:
        self.configure()
        state = self.state()
        for app in state["applications"].values():
            if app["displayName"] == "app-mpa-dev-spa":
                app["passwordCredentials"] = [{"keyId": "k"}]
        self.seed(state)
        result = run_script(self.dir, "-Yes")
        self.assertEqual(result.returncode, 1)
        self.assertIn("secretos de cliente", result.stdout)

    def test_preflight_changes_nothing(self) -> None:
        result = run_script(self.dir, "-PreflightOnly")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CREAR aplicacion app-mpa-dev-api", result.stdout)
        self.assertEqual(self.state()["applications"], {})

    def test_rollback_deletes_only_what_that_run_created(self) -> None:
        self.seed({"applications": {"22222222-0000-4000-8000-000000000001": {
            "id": "22222222-0000-4000-8000-000000000001", "appId": "22222222-0000-4000-8000-000000000002",
            "displayName": "otra-aplicacion", "owners": [], "federatedIdentityCredentials": []}},
            "servicePrincipals": {}, "assignments": [], "calls": []})
        self.configure()
        run_id = next((self.dir / "tmp" / "u11-evidence").glob("created-*.json")).stem.removeprefix("created-")
        result = run_script(self.dir, "-Rollback", run_id, "-Yes")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([a["displayName"] for a in self.state()["applications"].values()], ["otra-aplicacion"])
        self.assertEqual(self.state()["servicePrincipals"], {})
        bad = run_script(self.dir, "-Rollback", "cualquiera", "-Yes")
        self.assertEqual(bad.returncode, 1)



class ComposeIsolation(unittest.TestCase):
    """U11 runs in its own Compose project: never the PostgreSQL volume of the local environment (2026-10-07)."""

    BASE = text(ROOT / "infra" / "docker-compose.yml")
    ENTRA = text(ROOT / "infra" / "docker-compose.entra-dev.yml")
    DOCS = {path: text(ROOT / path) for path in ("infra/azure/entra/README.md", "infra/docker-compose.entra-dev.yml",
                                                  "docs/12-devops.md")}

    def test_entra_dev_has_its_own_project_name_and_local_keeps_the_default(self) -> None:
        self.assertRegex(self.ENTRA, r"(?m)^name: u11-entra-dev$")
        self.assertNotRegex(self.BASE, r"(?m)^name:")  # local stays project `infra` (infra_pgdata)

    def test_no_volume_or_network_is_shared_with_the_local_project(self) -> None:
        for source in (self.BASE, self.ENTRA):
            active = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
            self.assertNotRegex(active, r"(?m)^\s+external:")
            self.assertNotIn("infra_", active)  # no volume or network of the local project by name
        self.assertNotRegex(self.ENTRA, r"(?m)^volumes:")
        self.assertNotRegex(self.ENTRA, r"(?m)^\s+volumes:")

    def test_every_documented_u11_command_uses_the_isolated_project(self) -> None:
        for path, source in self.DOCS.items():
            commands = [line for line in source.replace("\\\n", " ").splitlines()
                        if "docker compose" in line and "docker-compose.entra-dev.yml" in line]
            self.assertTrue(commands, path)
            for line in commands:
                with self.subTest(path=path, line=line.strip()[:80]):
                    self.assertIn("-p u11-entra-dev", line)
            for line in source.splitlines():
                if "down -v" in line and "docker compose" in line:
                    self.assertIn("-p u11-entra-dev", line, path)

    @unittest.skipUnless(shutil.which("docker"), "docker not installed")
    def test_compose_resolves_separate_volumes(self) -> None:
        env = Path(tempfile.mkdtemp()) / "entra-dev.env"
        env.write_text("ENTRA_TENANT_ID=t\nENTRA_API_CLIENT_ID=a\nENTRA_SPA_CLIENT_ID=s\n", encoding="utf-8")
        base = ["docker", "compose", "-f", "infra/docker-compose.yml"]
        names = {}
        for label, args in (("local", base), ("u11", base + ["-f", "infra/docker-compose.entra-dev.yml", "--env-file", str(env)])):
            result = subprocess.run(args + ["--profile", "app", "config", "--format", "json"], cwd=ROOT,
                                    capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                self.skipTest(f"docker compose config unavailable: {result.stderr[:200]}")
            config = json.loads(result.stdout)
            names[label] = (config["name"], sorted(v["name"] for v in config["volumes"].values()))
        self.assertEqual(names["local"], ("infra", ["infra_dataset", "infra_pgdata"]))
        self.assertEqual(names["u11"], ("u11-entra-dev", ["u11-entra-dev_dataset", "u11-entra-dev_pgdata"]))


class SmokeEntraMode(unittest.TestCase):
    """infra/docker/smoke.py --entra against a stub of the frontend origin (no Docker, no Entra ID)."""

    SPA = "12345678-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    API = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"

    def serve(self, accept_dev_token: bool):
        import http.server
        import threading

        spa, api = self.SPA, self.API

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def do_GET(self) -> None:
                if self.path == "/health":
                    status, body = 200, b'{"status": "ok", "version": "0"}'
                elif self.path.startswith("/api/"):
                    dev = (self.headers.get("Authorization") or "").startswith("Bearer dev-")
                    status, body = (200, b"{}") if (dev and accept_dev_token) else (401, b"{}")
                elif self.path.startswith("/assets/"):
                    status, body = 200, f'const a="{spa}",b="api://{api}/access_as_user";'.encode()
                else:
                    status, body = 200, b'<div id="root"></div><script type="module" crossorigin src="/assets/index-x.js"></script>'
                self.send_response(status)
                self.end_headers()
                self.wfile.write(body)

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def run_smoke(self, url: str):
        env_file = Path(tempfile.mkdtemp()) / "entra-dev.env"
        env_file.write_text(f"# ids\nENTRA_TENANT_ID=t\nENTRA_API_CLIENT_ID={self.API}\nENTRA_SPA_CLIENT_ID={self.SPA}\n",
                            encoding="utf-8")
        environment = {**os.environ, "SMOKE_FRONTEND_URL": url, "SMOKE_API_URL": url, "SMOKE_ENTRA_ENV": str(env_file)}
        return subprocess.run([sys.executable, str(ROOT / "infra" / "docker" / "smoke.py"), "--entra"],
                              capture_output=True, text=True, timeout=60, env=environment)

    def test_passes_when_the_api_is_in_dev(self) -> None:
        result = self.run_smoke(self.serve(accept_dev_token=False))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SMOKE OK (entra-dev)", result.stdout)

    def test_fails_if_a_development_token_is_accepted(self) -> None:
        result = self.run_smoke(self.serve(accept_dev_token=True))
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL proxy /api: a development token is rejected", result.stdout)


if __name__ == "__main__":
    unittest.main()
