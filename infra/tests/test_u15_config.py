"""U15 (`DT-094`): static checks of the Search template, the setup tool and deploy-u15.ps1, without Azure.

The setup tool runs against fake openers and a fake Azure CLI runner; deploy-u15.ps1 runs ``-SelfTest`` and its stages
against ``fake_az_u15.py`` when ``pwsh`` is available on a POSIX host. The Bicep build runs when the Bicep CLI is
available. Standard library only.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
import urllib.error
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
U15 = ROOT / "infra" / "azure" / "u15"
SCRIPT = ROOT / "infra" / "azure" / "deploy-u15.ps1"
FAKE_AZ = Path(__file__).parent / "fake_az_u15.py"
BICEP = shutil.which("bicep") or (str(Path.home() / "bicep") if (Path.home() / "bicep").is_file() else None)
PWSH = shutil.which("pwsh") or (str(Path.home() / "pwsh7" / "pwsh") if (Path.home() / "pwsh7" / "pwsh").is_file() else None)
FAKE_AZ_USABLE = bool(PWSH) and os.name == "posix"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def setup_tool():
    spec = importlib.util.spec_from_file_location("u15_search_setup", U15 / "search_setup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Response:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class BicepTest(unittest.TestCase):
    def test_describes_the_real_free_service_and_the_reader_role(self) -> None:
        main = read(U15 / "main.bicep")
        for needle in (
            "Microsoft.Search/searchServices@2025-05-01",
            "param serviceName string = 'motor-predictivo-search-dev'",
            "param searchSku string = 'free'",
            "name: searchSku",
            "disableLocalAuth: disableLocalAuth",
            "authOptions: disableLocalAuth ? null : {",
            "aadAuthFailureMode: 'http401WithBearerChallenge'",
            "searchIndexDataReaderRoleId",
            "principalId: runtimeIdentity.properties.principalId",
        ):
            self.assertIn(needle, main)
        self.assertNotIn("Search Index Data Contributor", main)
        self.assertNotIn("apiKeyOnly", main)
        self.assertNotIn("Microsoft.Search/searchServices/indexes", main)
        self.assertNotIn("uniqueString", main)  # the real name, not a generated one

    def test_dev_parameters_match_the_service_seen_on_2026_10_16(self) -> None:
        params = read(U15 / "dev.bicepparam")
        for needle in ("param serviceName = 'motor-predictivo-search-dev'", "param searchSku = 'free'",
                       "param disableLocalAuth = false", "param semanticSearch = 'free'"):
            self.assertIn(needle, params)

    @unittest.skipUnless(BICEP, "Bicep CLI not available")
    def test_bicep_build_and_params(self) -> None:
        for args in (
            ["build", str(U15 / "main.bicep"), "--stdout"],
            ["lint", str(U15 / "main.bicep")],
            ["build-params", str(U15 / "dev.bicepparam"), "--stdout"],
        ):
            result = subprocess.run([BICEP, *args], capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Warning", result.stderr)

    @unittest.skipUnless(BICEP, "Bicep CLI not available")
    def test_auth_options_are_omitted_when_keys_are_disabled(self) -> None:
        result = subprocess.run([BICEP, "build", str(U15 / "main.bicep"), "--stdout"], capture_output=True, text=True,
                                timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("if(parameters('disableLocalAuth'), null()", result.stdout.replace('"', "'"))


class U12WiringTest(unittest.TestCase):
    """U15b (`DT-103`): the api of U12 gets the Search identifiers only with U13 active and never a key."""

    def test_api_gets_search_variables_only_with_genai_and_without_keys(self) -> None:
        u12 = ROOT / "infra" / "azure" / "u12"
        apps, main, params = read(u12 / "modules" / "apps.bicep"), read(u12 / "main.bicep"), read(u12 / "dev.bicepparam")
        self.assertIn("var searchEnv = searchEnabled ? [", apps)
        for name in ("SEARCH_PROVIDER", "AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_INDEX", "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"):
            self.assertIn(f"name: '{name}'", apps)
        self.assertIn("], genaiEnv, searchEnv)", apps)
        self.assertNotRegex(apps, r"(?i)SEARCH_(API_)?KEY|adminKey|queryKey")
        self.assertIn("param searchEnabled bool = false", main)
        self.assertIn("searchEnabled: searchEnabled && genaiEnabled", main)
        self.assertIn("searchEndpoint: 'https://${searchServiceName}.search.windows.net'", main)
        self.assertNotIn("Microsoft.Search", main)  # U12 never declares the service
        for needle in ("param searchEnabled = true", "param searchServiceName = 'motor-predictivo-search-dev'",
                       "param searchIndex = 'u15-demo-documents'", "param embeddingDeployment = 'text-embedding-3-small'"):
            self.assertIn(needle, params)
        self.assertEqual(json.loads(read(U15 / "index.json"))["name"], "u15-demo-documents")


class DocumentationTest(unittest.TestCase):
    def test_readme_states_what_is_verified_and_what_is_pending(self) -> None:
        readme = read(U15 / "README.md")
        for needle in ("motor-predictivo-search-dev", "Free", "text-embedding-3-small", "[AZ-U]", "deploy-u15.ps1",
                       "-Stage Roles", "deploy-u12.ps1 -Stage Verify", "## Pendiente", "No está autorizado",
                       "USD 50", "Verificada en `dev`", "DT-103"):
            self.assertIn(needle, readme)
        self.assertNotRegex(readme, r"(?i)integraci[oó]n (probada|funcional|verificada)")


class SetupToolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.m = setup_tool()

    def test_cli_token_is_requested_once_and_never_shown(self) -> None:
        calls = []

        def run(args, **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, stdout="tok-123\n", stderr="")

        token = self.m.AzCliToken("https://search.azure.com", run=run, az="az")
        self.assertEqual((token(), token()), ("tok-123", "tok-123"))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:5], ["az", "account", "get-access-token", "--resource", "https://search.azure.com"])

        def failing(args, **kwargs):
            return subprocess.CompletedProcess(args, 1, stdout="secret-ish output", stderr="error")

        with self.assertRaises(self.m.SearchUnavailable) as caught:
            self.m.AzCliToken("https://search.azure.com", run=failing, az="az")()
        self.assertNotIn("secret-ish", str(caught.exception))

    def test_embeddings_are_paced_and_429_is_retried(self) -> None:
        now = [0.0]
        sleeps = []

        def sleep(seconds: float) -> None:
            sleeps.append(round(seconds, 2))
            now[0] += seconds

        answers = [self.m.SearchUnavailable("Azure AI Search HTTP 429"), [0.5], [0.25]]

        def embed(text: str):
            answer = answers.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return answer

        paced = self.m.PacedEmbedder(embed, sleep=sleep, clock=lambda: now[0])
        self.assertEqual(paced("a"), [0.5])  # 429, backoff 10 s, retry
        self.assertEqual(paced("b"), [0.25])
        self.assertEqual(sleeps, [10.0, 1.2])  # backoff after the 429, then the minimum interval
        self.assertEqual(paced.calls, 3)

        def denied(text: str):
            raise self.m.SearchUnavailable("Azure AI Search HTTP 403")

        with self.assertRaises(self.m.SearchUnavailable):
            self.m.PacedEmbedder(denied, sleep=sleep, clock=lambda: now[0])("x")

    def test_consecutive_embeddings_wait_the_minimum_interval(self) -> None:
        now = [100.0]
        sleeps = []
        paced = self.m.PacedEmbedder(lambda text: [1.0], sleep=lambda s: sleeps.append(round(s, 2)), clock=lambda: now[0])
        paced("a")
        paced("b")
        self.assertEqual(sleeps, [1.2])

    def test_index_status_reads_the_count_and_reports_a_missing_index(self) -> None:
        seen = []

        def opener(request, *, timeout):
            seen.append(request)
            return Response(b"\xef\xbb\xbf17")

        count = self.m.index_status("https://s.search.windows.net", "u15-demo-documents", lambda: "t", opener=opener)
        self.assertEqual(count, 17)
        self.assertIn("/indexes/u15-demo-documents/docs/$count?api-version=2026-04-01", seen[0].full_url)
        self.assertEqual(seen[0].get_header("Authorization"), "Bearer t")
        self.assertEqual(seen[0].get_method(), "GET")

        def missing(request, *, timeout):
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, io.BytesIO(b""))

        self.assertIsNone(self.m.index_status("https://s.search.windows.net", "x", lambda: "t", opener=missing))

    @staticmethod
    def key(chunk_id: str) -> str:
        from app.api.azure_search import search_document_key

        return search_document_key(chunk_id)

    def test_load_sends_valid_document_keys_for_every_real_chunk(self) -> None:
        # 2026-10-17: the first -Stage Load got HTTP 400 because the chunk ids (with ':') were sent as keys.
        from app.api.azure_search import AzureSearchIndexer, chunk_id_from_key

        chunks = self.m.load_markdown_corpus(self.m.MANIFEST)
        sent = []

        def opener(request, *, timeout):
            actions = json.loads(request.data)["value"]
            sent.extend(actions)
            return Response(json.dumps({"value": [{"key": a["id"], "status": True} for a in actions]}).encode())

        uploaded = AzureSearchIndexer("https://s.search.windows.net", "i", lambda: "t", lambda text: [0.1],
                                      opener=opener).upload(chunks)
        self.assertEqual(uploaded, len(chunks))
        self.assertTrue(any(":" in chunk.id for chunk in chunks))
        for action, chunk in zip(sent, chunks):
            self.assertRegex(action["id"], r"^[A-Za-z0-9][A-Za-z0-9_=-]{0,1023}$")
            self.assertEqual(chunk_id_from_key(action["id"]), chunk.id)

    def test_selected_fields_are_retrievable_in_the_versioned_index(self) -> None:
        # 2026-10-17: the first -Stage Verify got HTTP 400 because security_groups (retrievable: false) was selected.
        from app.api.azure_search import SEARCH_SELECT

        fields = {f["name"]: f for f in json.loads(read(U15 / "index.json"))["fields"]}
        for name in SEARCH_SELECT:
            self.assertIn(name, fields)
            self.assertTrue(fields[name].get("retrievable", True), name)
        self.assertFalse(fields["security_groups"]["retrievable"])
        self.assertNotIn("security_groups", SEARCH_SELECT)

    def test_service_error_message_is_kept_without_headers(self) -> None:
        body = json.dumps({"error": {"code": "", "message": "Invalid document key: 'U15:1'."}}).encode()

        def failing(request, *, timeout):
            raise urllib.error.HTTPError("https://s.search.windows.net/indexes/i/docs/index", 400, "Bad Request",
                                         {"WWW-Authenticate": "Bearer x"}, io.BytesIO(body))

        opener = self.m.DiagnosticOpener(failing)
        with self.assertRaises(urllib.error.HTTPError):
            opener(object(), timeout=1.0)
        self.assertEqual(opener.last_error, "s.search.windows.net HTTP 400: Invalid document key: 'U15:1'.")

    def fake_search(self, *, leak: bool, count_delta: int = 0):
        chunks = self.m.load_markdown_corpus(self.m.MANIFEST)
        document = {
            "id": self.key("U15-SYN-001:x:1"), "content": "c", "title": "t", "document_id": "U15-SYN-001", "section": "s",
            "document_type": "demo-policy", "effective_date": "2026-10-14T00:00:00Z", "expiry_date": None,
            "security_groups": ["U15-DEMO-READERS"], "source_url": "knowledge/search_corpus/politica-v1.md#x",
            "source_type": "SYNTHETIC", "@search.score": 1.0,
        }
        bodies = []

        def opener(request, *, timeout):
            if "/docs/$count" in request.full_url:
                return Response(str(len(chunks) + count_delta).encode())
            body = json.loads(request.data)
            bodies.append(body)
            blocked = self.m.NO_ACCESS_GROUP in body["filter"]
            return Response(json.dumps({"value": [document] if (leak or not blocked) else []}).encode())

        return opener, bodies

    def test_verify_counts_documents_runs_the_fixed_set_and_checks_the_group_filter(self) -> None:
        opener, bodies = self.fake_search(leak=False)
        result = self.m.verify("https://s.search.windows.net", "u15-demo-documents", lambda: "t", lambda text: [0.1] * 4,
                               today=date(2026, 10, 17), opener=opener)
        self.assertEqual(result["checksFailed"], 0)
        self.assertEqual(result["documents"], result["expectedChunks"])
        self.assertEqual(result["groups"], ["U15-DEMO-READERS"])
        self.assertEqual(len(result["cases"]), 6)
        self.assertEqual(result["hits"], 4)  # every case that expects U15-SYN-001
        self.assertIn("not id-mpa-dev-runtime", result["identity"])
        self.assertTrue(all(body["vectorFilterMode"] == "preFilter" for body in bodies))
        self.assertNotIn("Bearer", json.dumps(result))  # identifiers and counts only, never the token

    def test_verify_fails_when_the_filter_leaks_or_the_index_is_incomplete(self) -> None:
        opener, _ = self.fake_search(leak=True)
        leaked = self.m.verify("https://s.search.windows.net", "i", lambda: "t", lambda text: [0.1],
                               today=date(2026, 10, 17), opener=opener)
        self.assertFalse(leaked["checks"]["a group without documents gets nothing (filter applied by Search)"])
        opener, _ = self.fake_search(leak=False, count_delta=-1)
        partial = self.m.verify("https://s.search.windows.net", "i", lambda: "t", lambda text: [0.1],
                                today=date(2026, 10, 17), opener=opener)
        self.assertEqual(partial["checksFailed"], 1)

    def test_arguments_are_validated_before_any_call(self) -> None:
        with unittest.mock.patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(self.m.main(["status", "--search-endpoint", "http://s.search.windows.net"]), 2)
            self.assertEqual(self.m.main(["status", "--search-endpoint", "https://evil.example.com"]), 2)
            self.assertEqual(self.m.main(["load", "--search-endpoint", "https://s.search.windows.net"]), 2)

    def test_tool_only_loads_the_synthetic_corpus_and_the_versioned_index(self) -> None:
        source = read(U15 / "search_setup.py")
        self.assertIn('ROOT / "knowledge" / "search_corpus" / "manifest.json"', source)
        self.assertEqual(json.loads(read(U15 / "index.json"))["name"], "u15-demo-documents")
        for absent in ("api-key", "admin-key", "print(token", "listAdminKeys"):
            self.assertNotIn(absent, source)


class ScriptSourceTest(unittest.TestCase):
    SOURCE = read(SCRIPT)

    def test_ascii_stages_and_no_key_commands(self) -> None:
        self.assertTrue(self.SOURCE.isascii())
        self.assertIn("[ValidateSet('Preflight', 'WhatIf', 'Index', 'Load', 'Roles', 'Verify')]", self.SOURCE)
        for word in ("'keys'", "'admin-key'", "'query-key'", "'get-access-token'"):
            self.assertIn(word, self.SOURCE)  # refused by Invoke-Az
        self.assertNotRegex(self.SOURCE, r"Invoke-Az @\('search', 'service', '(update|create|delete)'")
        self.assertNotIn("Invoke-Az @('deployment', 'group', 'create'", self.SOURCE)

    def test_the_only_role_it_grants_is_the_reader_on_the_service(self) -> None:
        creates = re.findall(r"Invoke-Az @\('role', 'assignment', 'create'[^)]*\)", self.SOURCE)
        self.assertEqual(len(creates), 1)
        self.assertIn("'--role', $SearchReaderRoleId, '--scope', \"$($svc.id", creates[0])
        self.assertIn("$SearchReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'", self.SOURCE)

    def test_u12_accepts_the_reader_only_on_a_search_service(self) -> None:
        u12 = read(ROOT / "infra" / "azure" / "deploy-u12.ps1")
        self.assertIn("elseif ($name -eq 'Search Index Data Reader' -and $scope -match $searchPattern) { $search++ }", u12)
        self.assertIn("/providers/Microsoft.Search/searchServices/\") + '[a-z0-9-]+$'", u12)


def run_pwsh(workdir: Path, *args: str, env: dict | None = None):
    command = f"& '{SCRIPT}' {' '.join(args)}; exit $LASTEXITCODE"
    environment = {"PATH": str(workdir / "bin"), "HOME": os.environ.get("HOME", str(workdir)),
                   "FAKE_AZ_STATE": str(workdir / "state.json"), **(env or {})}
    result = subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command", command], cwd=ROOT,
                            capture_output=True, text=True, timeout=300, env=environment)
    state = json.loads((workdir / "state.json").read_text()) if (workdir / "state.json").exists() else {"argv": []}
    return result, state


@unittest.skipUnless(FAKE_AZ_USABLE, "pwsh and a POSIX host are needed for the fake Azure CLI")
class ScriptFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="u15-"))
        (self.dir / "bin").mkdir()
        wrapper = self.dir / "bin" / "az"
        wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_AZ}" "$@"\n')
        wrapper.chmod(0o755)

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_selftest(self) -> None:
        result, _ = run_pwsh(self.dir, "-SelfTest")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SELFTEST OK", result.stdout)

    def test_preflight_only_reads(self) -> None:
        result, state = run_pwsh(self.dir, "-PreflightOnly")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for line in ("motor-predictivo-search-dev: SKU free, running", "autenticacion: Entra ID y claves de API",
                     "las claves de API siguen activas", "text-embedding-3-small en oai-mpa-dev-x",
                     "tus roles de datos", "id-mpa-dev-runtime sin rol sobre Search todavia",
                     "Python 3.10+ no encontrado", "PREFLIGHT OK"):
            self.assertIn(line, result.stdout)
        self.assertTrue(state["argv"])
        for argv in state["argv"]:
            self.assertNotIn("create", argv)
            self.assertNotIn("update", argv)

    def test_preflight_blocks_without_data_roles_basic_or_embeddings(self) -> None:
        for env, text in (({"FAKE_U15_OWNER_ROLES": "none"}, "FALTA  Search Service Contributor"),
                          ({"FAKE_U15_SKU": "basic"}, "SKU basic"),
                          ({"FAKE_U15_EMBEDDINGS": "0"}, "falta el despliegue text-embedding-3-small")):
            with self.subTest(env=env):
                (self.dir / "state.json").unlink(missing_ok=True)
                result, _ = run_pwsh(self.dir, "-PreflightOnly", env=env)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(text, result.stdout)
                self.assertIn("PREFLIGHT BLOQUEADO", result.stdout)

    def test_roles_grants_one_reader_on_the_service_and_is_idempotent(self) -> None:
        result, state = run_pwsh(self.dir, "-Stage", "Roles", "-Yes")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(state["assignments"]), 1)
        assignment = state["assignments"][0]
        self.assertEqual(assignment["role"], "1407120a-92aa-4202-b7e9-c0e197c71c8f")
        self.assertTrue(assignment["scope"].endswith("/Microsoft.Search/searchServices/motor-predictivo-search-dev"))
        self.assertEqual((assignment["principal"], assignment["type"]),
                         ("2b5317cf-0000-4000-8000-000000000002", "ServicePrincipal"))
        again, state = run_pwsh(self.dir, "-Stage", "Roles", "-Yes")
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertIn("ya tiene Search Index Data Reader", again.stdout)
        self.assertEqual(len(state["assignments"]), 1)

    def test_writing_stages_stop_without_python_before_changing_anything(self) -> None:
        for stage in ("Index", "Load"):
            with self.subTest(stage=stage):
                result, state = run_pwsh(self.dir, "-Stage", stage, "-Yes")
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("Python 3.10+ no encontrado", result.stdout)
                self.assertEqual(state.get("assignments"), [])


if __name__ == "__main__":
    unittest.main()
