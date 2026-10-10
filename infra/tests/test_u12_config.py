"""U12 (`DT-100`): static checks of the dev deployment, the bootstrap, the CD workflow and deploy-u12.ps1.

No Azure: the real verification is ``deploy-u12.ps1`` (what-if checked automatically, then -Stage Verify). The bicep
build runs when the Bicep CLI is available; the PowerShell checks when ``pwsh`` is. Standard library only, from the
repository root::

    python -m unittest discover -s infra/tests -t infra/tests
"""

from __future__ import annotations

import base64
import hashlib
import hmac
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
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
U12 = ROOT / "infra" / "azure" / "u12"
SCRIPT = ROOT / "infra" / "azure" / "deploy-u12.ps1"
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-dev.yml"
PWSH = shutil.which("pwsh")
BICEP = shutil.which("bicep") or (str(Path.home() / "bicep") if (Path.home() / "bicep").is_file() else None)
# Windows PowerShell 5.1 enumerates a JSON array piped through ConvertFrom-Json; PowerShell 7 does not. The same
# emulation as test_entra_config.py (U11) runs the script as 5.1 would.
EMULATE_PS51 = (
    "function global:ConvertFrom-Json { param([Parameter(ValueFromPipeline = $true)]$InputObject) "
    "process { Microsoft.PowerShell.Utility\\ConvertFrom-Json -InputObject $InputObject -NoEnumerate } }; "
)
# The fake Azure CLI is a POSIX shell wrapper: on Windows `az` would resolve to the REAL Azure CLI, so the flow tests
# only run on POSIX hosts (CI and the Linux VM).
FAKE_AZ_USABLE = bool(PWSH) and os.name == "posix"
READ_ONLY = ("account show", "group exists", "group show", "provider show", "resource list", "resource show",
             "role assignment list", "role definition list", "ad signed-in-user show", "identity show",
             "identity federated-credential list", "bicep lint")
GUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def code(source: str) -> str:
    """Source without comment or @description lines, so documentation may name what the code forbids."""
    return "\n".join(line for line in source.splitlines()
                     if not line.lstrip().startswith(("//", "#", "@description")))


MAIN = text(U12 / "main.bicep")
MODULES = {path.name: text(path) for path in sorted((U12 / "modules").glob("*.bicep"))}
ALL = {"main.bicep": MAIN, **MODULES}
PARAMS = text(U12 / "dev.bicepparam")

spec = importlib.util.spec_from_file_location("bootstrap", ROOT / "infra" / "docker" / "bootstrap.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class Infrastructure(unittest.TestCase):
    def test_only_the_resource_types_of_u12(self) -> None:
        types = set()
        for source in ALL.values():
            types |= set(re.findall(r"^resource \w+ '([^@']+)@", source, re.MULTILINE))
        self.assertEqual(types, {
            "Microsoft.KeyVault/vaults", "Microsoft.ManagedIdentity/userAssignedIdentities",
            "Microsoft.Authorization/roleAssignments", "Microsoft.ContainerRegistry/registries",
            "Microsoft.DBforPostgreSQL/flexibleServers", "Microsoft.DBforPostgreSQL/flexibleServers/databases",
            "Microsoft.DBforPostgreSQL/flexibleServers/configurations",
            "Microsoft.DBforPostgreSQL/flexibleServers/firewallRules", "Microsoft.App/managedEnvironments",
            "Microsoft.App/containerApps", "Microsoft.App/jobs"})
        self.assertIn("resource keyVault 'Microsoft.KeyVault/vaults@2024-11-01' existing", MAIN)  # U10's, read only
        joined = "\n".join(ALL.values()).lower()
        for forbidden in ("staging", "prod'", "openai", "cognitive", "search", "machinelearning", "insights",
                          "operationalinsights", "natgateway", "virtualnetworks", "privateendpoints"):
            self.assertNotIn(forbidden, joined)

    def test_cheapest_skus_and_no_redundancy(self) -> None:
        registry, postgres = MODULES["registry.bicep"], MODULES["postgres.bicep"]
        self.assertIn("name: 'Basic'", registry)
        self.assertIn("adminUserEnabled: false", registry)
        self.assertIn("name: 'Standard_B1ms'", postgres)
        self.assertIn("tier: 'Burstable'", postgres)
        self.assertIn("version: '16'", postgres)
        self.assertIn("mode: 'Disabled'", postgres)  # high availability
        self.assertIn("geoRedundantBackup: 'Disabled'", postgres)
        self.assertIn("charset: 'UTF8'", postgres)
        environment = MODULES["environment.bicep"]
        self.assertIn("workloadProfileType: 'Consumption'", environment)
        # Express does not run jobs nor allowInsecure (ARM failure of 2026-10-09): the mode is always explicit.
        self.assertIn("environmentMode: 'WorkloadProfiles'", environment)
        self.assertIn("'Microsoft.App/managedEnvironments@2026-07-01'", environment)
        self.assertNotIn("Express", code(environment))
        self.assertNotIn("Dedicated", code(environment))
        self.assertNotIn("appLogsConfiguration", environment)  # no Log Analytics

    def test_postgres_network_and_tls(self) -> None:
        postgres = MODULES["postgres.bicep"]
        self.assertIn("name: 'require_secure_transport'", postgres)
        self.assertIn("value: 'ON'", postgres)
        self.assertIn("startIpAddress: ip", postgres)
        self.assertIn("endIpAddress: ip", postgres)  # one rule per outbound IP, never a range
        self.assertIn("name: 'aca-out-${replace(ip, '.', '-')}'", postgres)
        self.assertNotIn("0.0.0.0", code(postgres))
        self.assertNotIn("0.0.0.0", MAIN.split("param postgresAllowedIps")[1].split("\n")[0])

    def test_apps_ingress_scale_and_identity(self) -> None:
        apps = MODULES["apps.bicep"]
        api, frontend = apps.split("resource frontend")[0], apps.split("resource frontend")[1].split("resource bootstrap")[0]
        self.assertIn("external: false", api)
        self.assertIn("allowInsecure: false", api)  # internal AND HTTPS only
        self.assertNotIn("allowInsecure: true", apps)
        self.assertIn("targetPort: 8000", api)
        self.assertIn("external: true", frontend)
        self.assertIn("allowInsecure: false", frontend)
        self.assertIn("targetPort: 8080", frontend)
        # nginx reaches the api over TLS at its internal FQDN (<app>.internal.<domain>), never over plain HTTP.
        self.assertIn("{ name: 'API_UPSTREAM', value: 'https://${api.properties.configuration.ingress.fqdn}' }", frontend)
        self.assertNotIn("'http://${apiName}'", apps)
        self.assertEqual(apps.count("minReplicas: 0"), 2)
        self.assertEqual(apps.count("maxReplicas: 1"), 2)
        self.assertIn("triggerType: 'Manual'", apps)
        self.assertIn("replicaRetryLimit: 0", apps)
        self.assertNotIn("passwordSecretRef", apps)  # registry pull by managed identity
        self.assertIn("identity: runtimeIdentityId", apps)
        self.assertIn("path: '/health'", api)
        self.assertIn("{ name: 'APP_ENV', value: 'dev' }", api)
        self.assertNotIn("DEV_AUTH_IDENTITIES", apps)

    def test_passwords_only_from_key_vault_never_in_a_string(self) -> None:
        self.assertEqual(MAIN.count("keyVault.getSecret('pg-owner-password')"), 2)
        self.assertEqual(MAIN.count("keyVault.getSecret('pg-app-password')"), 1)
        apps, postgres = MODULES["apps.bicep"], MODULES["postgres.bicep"]
        self.assertEqual(apps.count("@secure()"), 2)
        self.assertIn("@secure()", postgres)
        for source in ALL.values():
            self.assertNotRegex(source, r"\$\{(ownerPassword|appPassword)\}")  # never interpolated into a URL
            self.assertNotIn("keyVaultUrl", source)  # Container Apps never reads the vault
        self.assertIn("value: 'postgresql://${appLogin}@${postgresHost}:5432/inventory?sslmode=require'", apps)
        self.assertIn("{ name: 'PGPASSWORD', secretRef: 'app-db-password' }", apps)
        self.assertNotRegex(code(PARAMS).lower(), r"password|secret")

    def test_role_assignment_names_are_known_before_deployment(self) -> None:
        # A principalId inside guid() is only known at run time: what-if then reports the assignment as
        # "Unsupported" and the deployment guard (rightly) refuses it. Names are built from resource ids.
        for name, source in ALL.items():
            for guid_call in re.findall(r"name: guid\(([^\n]*)\)", source):
                self.assertNotIn("rincipalId", guid_call, f"{name}: guid({guid_call})")
        self.assertIn("name: guid(registry.id, runtimeIdentityId, acrPullRoleId)", MODULES["registry.bicep"])
        self.assertIn("name: guid(registry.id, githubIdentityId, acrPushRoleId)", MODULES["registry.bicep"])

    def test_roles_are_the_four_minimum_ones(self) -> None:
        guids = set(re.findall(GUID, "\n".join(ALL.values())))
        self.assertEqual(guids, {"7f951dda-4ed3-4680-a7ca-43fe172d538d", "8311e382-0749-4cb8-b61a-304f252e45ec"})
        self.assertEqual("\n".join(ALL.values()).count("Microsoft.Authorization/roleAssignments@"), 4)
        self.assertNotRegex("\n".join(ALL.values()), r"8e3af657-a8ff-443c-a75c-2fe8c4bcb635|b24988ac-6180-42a0-ab88-20f7382dd24c")
        self.assertIn("scope: runtimeIdentity", MAIN)  # Managed Identity Operator only on the runtime identity
        self.assertNotIn("targetScope = 'subscription'", MAIN)

    def test_parameters_are_identifiers_of_u10_and_u11(self) -> None:
        self.assertIn("param keyVaultName = 'kv-mpa-dev-dymtafh7zjbba'", PARAMS)
        self.assertIn("param entraApiClientId = 'a9c9ec35-cd73-4ce6-8efd-46755ac86cbe'", PARAMS)
        self.assertIn("param entraSpaClientId = '1ce46703-15f3-4f3d-8668-431e43b813ac'", PARAMS)
        self.assertIn("param deployApps = false", PARAMS)

    @unittest.skipUnless(BICEP, "Bicep CLI not available")
    def test_bicep_builds_and_lints_clean(self) -> None:
        for args in (["build", str(U12 / "main.bicep"), "--stdout"], ["lint", str(U12 / "main.bicep")],
                     ["build-params", str(U12 / "dev.bicepparam"), "--stdout"]):
            result = subprocess.run([BICEP, *args], capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            # Strict on purpose: no warning is tolerated (a BCP081 means Bicep cannot validate that resource).
            self.assertNotIn("Warning", result.stderr, f"{bicep_version()}: {result.stderr}")


class Images(unittest.TestCase):
    def test_bootstrap_image(self) -> None:
        dockerfile = text(ROOT / "infra" / "docker" / "bootstrap.Dockerfile")
        backend = text(ROOT / "infra" / "docker" / "backend.Dockerfile")
        base = re.search(r"FROM (python:\S+@sha256:[0-9a-f]{64})", backend).group(1)
        self.assertIn(f"FROM {base}", dockerfile)  # same pinned base
        self.assertIn("USER bootstrap", dockerfile)
        self.assertNotRegex(dockerfile, r"output|\.csv|ENV\s+\w*(PASSWORD|SECRET|TOKEN)")
        self.assertNotIn("data/synthetic/output", dockerfile)
        self.assertIn('CMD ["python", "bootstrap.py"]', dockerfile)

    def test_runtime_image_keeps_no_generator(self) -> None:
        backend = text(ROOT / "infra" / "docker" / "backend.Dockerfile")
        self.assertNotIn("data/synthetic", backend)


class Bootstrap(unittest.TestCase):
    ENV = {"DATABASE_URL": "postgresql://mpa_owner@db.example:5432/inventory?sslmode=require",
           "PGPASSWORD": "own-pw1", "APP_DB_USER": "mpa_app", "APP_DB_PASSWORD": "app-pw1",
           "RUN_AS_OF": "2025-12-31"}

    def run_main(self, runner, env=None):
        calls, roles = [], []

        def record(command, cwd):
            calls.append((list(command), cwd))
            return runner(command)

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = bootstrap.main(record, lambda user, pw: roles.append((user, pw)), lambda: {"products": 100},
                                  env or self.ENV)
        return code, calls, roles, out.getvalue() + err.getvalue()

    def test_one_execution_in_order(self) -> None:
        code, calls, roles, output = self.run_main(lambda command: 0)
        self.assertEqual(code, 0)
        modules = [c[0][2] if c[0][1] == "-m" else "generator-api" for c in calls]
        self.assertEqual(modules, ["generator-api", "app.db", "app.ingestion", "app.runs", "app.runs"])
        self.assertEqual([c[0][3] for c in calls[3:]], ["forecast", "recommend"])
        self.assertEqual(calls[0][0][-1], bootstrap.DATASET_GENERATED_AT)  # fixed manifest timestamp
        self.assertEqual(calls[2][0][-1], calls[0][0][-2])  # ingestion reads what the generator wrote
        self.assertEqual(roles, [("mpa_app", "app-pw1")])
        self.assertIn("BOOTSTRAP OK", output)
        self.assertNotIn("own-pw1", output)
        self.assertNotIn("app-pw1", output)

    def test_stops_at_the_first_failure(self) -> None:
        code, calls, roles, output = self.run_main(lambda command: 1 if "app.ingestion" in command else 0)
        self.assertEqual(code, 1)
        self.assertEqual(len(calls), 3)
        self.assertEqual(roles, [])
        self.assertIn("step 3 (ingesta)", output)

    def test_refuses_missing_configuration_or_a_password_in_the_url(self) -> None:
        for env in ({**self.ENV, "PGPASSWORD": ""},
                    {**self.ENV, "DATABASE_URL": "postgresql://mpa_owner:password@db.example:5432/inventory"}):
            code, calls, _, output = self.run_main(lambda command: 0, env)
            self.assertEqual((code, calls), (2, []))
            self.assertNotIn("password@", output)

    def test_generator_is_called_through_its_public_api(self) -> None:
        self.assertIn("pipeline.run(load_config(None), sys.argv[1], generated_at=moment)", bootstrap.GENERATE)
        self.assertEqual(bootstrap.DATASET_GENERATED_AT, "2026-09-29T22:54:38Z")

    def test_scram_verifier_matches_rfc_7677(self) -> None:
        verifier = bootstrap.scram_sha256_verifier("pencil", base64.b64decode("W22ZaJ0SNY7soEsUEjb6gQ=="))
        self.assertEqual(verifier, "SCRAM-SHA-256$4096:W22ZaJ0SNY7soEsUEjb6gQ==$WG5d8oPm3OtcPnkdi4Uo7BkeZkBFzpcXkuLmtbsT4qY="
                                   ":wfPLwcE6nTWhTAmQ7tl2KeoiWGPlZqQxSrmfPwDl2dU=")
        server_key = base64.b64decode(verifier.split("$")[2].split(":")[1])
        auth = ("n=user,r=rOprNGfwEbeRWgbNEkqO,r=rOprNGfwEbeRWgbNEkqO%hvYDpWUa2RaTCAfuxFIlj)hNlF$k0,"
                "s=W22ZaJ0SNY7soEsUEjb6gQ==,i=4096,c=biws,r=rOprNGfwEbeRWgbNEkqO%hvYDpWUa2RaTCAfuxFIlj)hNlF$k0")
        self.assertEqual(base64.b64encode(hmac.new(server_key, auth.encode(), hashlib.sha256).digest()).decode(),
                         "6rriTRBi23WpRR/wtup+mMhUZUn/dB5nLTJRsjl95G4=")  # RFC 7677 server signature
        self.assertNotEqual(bootstrap.scram_sha256_verifier("pencil"), bootstrap.scram_sha256_verifier("pencil"))


def bicep_version() -> str:
    return subprocess.run([BICEP, "--version"], capture_output=True, text=True, timeout=60).stdout.strip()


class Workflow(unittest.TestCase):
    def test_ci_pins_the_bicep_cli_that_has_the_types(self) -> None:
        # The runner image's Bicep (0.46.1) lacks Microsoft.App/managedEnvironments@2026-07-01 (BCP081): CI installs
        # 0.48.1 by exact version and SHA-256 before infra/tests, and puts it first on PATH.
        ci = text(ROOT / ".github" / "workflows" / "ci.yml")
        docker_job = ci.split("\n  docker:\n")[1]
        self.assertIn('BICEP_VERSION: "0.48.1"', docker_job)
        self.assertIn('BICEP_SHA256: "b09ec25a9d376c1f8e33ede6ed22b587f915ad68488d5db77a6f9541748c7f6e"', docker_job)
        self.assertIn("releases/download/v${BICEP_VERSION}/bicep-linux-x64", docker_job)
        self.assertIn('sha256sum --check --strict', docker_job)
        self.assertIn('>> "$GITHUB_PATH"', docker_job)
        self.assertLess(docker_job.index("Bicep CLI 0.48.1"), docker_job.index("discover -s infra/tests"))
        install = docker_job.split("Bicep CLI 0.48.1")[1].split("- name:")[0]
        self.assertNotIn("latest", install)  # never floating
        # Version and hash belong to the job (every step sees the same values) and the hash is checked before the
        # binary is ever made executable or run.
        job_env = docker_job.split("\n    steps:\n")[0]
        self.assertIn('BICEP_VERSION: "0.48.1"', job_env)
        self.assertIn('BICEP_SHA256: "%s"' % "b09ec25a9d376c1f8e33ede6ed22b587f915ad68488d5db77a6f9541748c7f6e", job_env)
        self.assertLess(install.index("sha256sum --check --strict"), install.index("chmod +x"))
        self.assertLess(install.index("sha256sum --check --strict"), install.index("--version"))
        self.assertIn('grep -F "Bicep CLI version ${BICEP_VERSION} "', install)
        tests_step = docker_job.split("Pruebas estáticas de infra/")[1].split("- name:")[0]
        self.assertLess(tests_step.index("bicep --version"), tests_step.index("python -m unittest discover -s infra/tests"))

    SOURCE = text(WORKFLOW)

    def test_oidc_without_secrets(self) -> None:
        self.assertIn("permissions:\n  contents: read\n  id-token: write", self.SOURCE)
        self.assertIn("environment: dev", self.SOURCE)  # the federated credential's subject
        self.assertIn("uses: azure/login@a641126d1b8aa4d1fa005f4f92df94a3a4c4c906 # v3.1.0", self.SOURCE)
        self.assertNotRegex(self.SOURCE, r"secrets\.|client-secret|AZURE_CLIENT_SECRET|password|creds:")
        self.assertIn("az acr login", self.SOURCE)
        self.assertNotIn("docker login", self.SOURCE)
        for uses in re.findall(r"uses: (\S+)", self.SOURCE):
            self.assertRegex(uses, r"@[0-9a-f]{40}$")

    def test_manual_dev_only(self) -> None:
        self.assertIn("workflow_dispatch:", self.SOURCE)
        self.assertNotRegex(self.SOURCE, r"(?m)^\s+(push|pull_request|schedule):")
        self.assertNotRegex(self.SOURCE.lower(), r"environment: (staging|prod)")

    def test_builds_the_three_existing_dockerfiles(self) -> None:
        for dockerfile in ("backend", "frontend", "bootstrap"):
            self.assertIn(f"--file infra/docker/{dockerfile}.Dockerfile", self.SOURCE)
        self.assertIn('VITE_ENTRA_API_SCOPE="api://${{ vars.ENTRA_API_CLIENT_ID }}/access_as_user"', self.SOURCE)
        self.assertNotIn("VITE_ENTRA_REDIRECT_URI", self.SOURCE)  # the SPA uses its own HTTPS origin


class ScriptSource(unittest.TestCase):
    SOURCE = text(SCRIPT)

    def test_ascii_and_no_secret_output(self) -> None:
        SCRIPT.read_bytes().decode("ascii")
        self.assertNotIn("@(Invoke-Az", self.SOURCE)
        # As-Array returns `,array`: piping or @()-wrapping the bare call hands the WHOLE array over as one item (the
        # bug that made -Stage KeyVault report ALREADY_CONFIGURED while the vault still had to change). Always (As-Array x).
        self.assertNotRegex(self.SOURCE, r"@\(As-Array|\{ As-Array|As-Array [^()\n|]*\| ")
        self.assertNotRegex(self.SOURCE, r"keyvault secret (show|download)|--query value|Write-Host[^\n]*New-DbPassword")
        allowed = ("-eq '0.0.0.0'", "'regla 0.0.0.0'", "Stop-U12 (", "sin 0.0.0.0")  # refusals, self-test, messages
        for line in code(self.SOURCE).splitlines():
            if "0.0.0.0" in line:
                self.assertTrue(any(mark in line for mark in allowed), line)


    def test_verify_covers_the_acceptance_checks(self) -> None:
        verify = self.SOURCE.split("    'Verify' {")[1]
        for check in ("ACR Basic sin usuario administrador", "PostgreSQL con TLS obligatorio", "sin 0.0.0.0",
                      "api sin ingress publico", "imagenes con identidad administrada, sin credenciales",
                      "Key Vault opcion C: privado, plantillas=true, bypass=AzureServices", "GitHub sin deploy/action",
                      "contrasenas solo como secretRef", "PostgreSQL arrancado (Ready)",
                      "bootstrap: ultima ejecucion Succeeded", "frontend responde 200 por HTTPS",
                      "API viva tras el proxy", "GitHub: 4 roles minimos"):
            self.assertIn(check, verify)
        self.assertIn("    Protect-Evidence $Object\n", self.SOURCE)  # every evidence file is redacted
        self.assertNotRegex(self.SOURCE, r"--assignee-object-id', \$gh")  # the deploy role is never given to GitHub


def run_pwsh(workdir: Path, *args: str, env: dict | None = None):
    command = f"& '{workdir / 'infra' / 'azure' / 'deploy-u12.ps1'}' {' '.join(args)}; exit $LASTEXITCODE"
    environment = {**os.environ, "PATH": f"{workdir / 'bin'}{os.pathsep}{os.environ['PATH']}",
                   "FAKE_AZ_STATE": str(workdir / "state.json"), **(env or {})}
    return subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command", command], cwd=workdir,
                          capture_output=True, text=True, timeout=300, env=environment)


@unittest.skipUnless(FAKE_AZ_USABLE, "pwsh and a POSIX host are needed for the fake Azure CLI")
class ScriptFlow(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="u12-"))
        for relative in ("infra/azure/deploy-u12.ps1", "infra/azure/main.bicep", "infra/azure/u12/main.bicep",
                         "infra/azure/u12/dev.bicepparam"):
            (self.dir / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / relative, self.dir / relative)
        (self.dir / "bin").mkdir()
        wrapper = self.dir / "bin" / "az"
        wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{Path(__file__).parent / "fake_az_u12.py"}" "$@"\n')
        wrapper.chmod(0o755)

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_selftest(self) -> None:
        result = run_pwsh(ROOT, "-SelfTest")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SELFTEST OK", result.stdout)

    def test_key_vault_role_is_minimal_scoped_and_not_duplicated(self) -> None:
        reader = {"FAKE_AZ_DEPLOYER_ROLE": "Reader"}
        first = run_pwsh(self.dir, "-Stage", "KeyVaultRole", "-Yes", env=reader)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        state = json.loads((self.dir / "state.json").read_text())
        rg = "/subscriptions/0239bbd1-fc72-4dd7-a816-fcbf29f5a631/resourceGroups/rg-motor-predictivo-dev"
        [role] = state["roles"]
        self.assertEqual(role["roleName"], "Key Vault Resource Manager Template Deployment Operator")
        self.assertEqual(role["permissions"][0]["actions"], ["Microsoft.KeyVault/vaults/deploy/action"])
        self.assertEqual(role["assignableScopes"], [rg])  # never the subscription
        [assignment] = state["assignments"]
        self.assertEqual(assignment["principal"], "11111111-1111-4111-8111-111111111111")  # you, never GitHub
        self.assertEqual(assignment["scope"], rg + "/providers/Microsoft.KeyVault/vaults/kv-mpa-dev-dymtafh7zjbba")
        again = run_pwsh(self.dir, "-Stage", "KeyVaultRole", "-Yes", env=reader)
        self.assertIn("ALREADY_ALLOWED", again.stdout)  # the custom role now grants the action: nothing duplicated
        state = json.loads((self.dir / "state.json").read_text())
        self.assertEqual((len(state["roles"]), len(state["assignments"])), (1, 1))

    def test_key_vault_role_is_not_created_when_not_needed(self) -> None:
        result = run_pwsh(self.dir, "-Stage", "KeyVaultRole", "-Yes")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ALREADY_ALLOWED", result.stdout)
        self.assertEqual(json.loads((self.dir / "state.json").read_text())["roles"], [])

    def test_secrets_are_generated_once_and_never_shown(self) -> None:
        first = run_pwsh(self.dir, "-Stage", "Secrets")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        state = json.loads((self.dir / "state.json").read_text())
        self.assertEqual(sorted(state["secrets"]), ["pg-app-password", "pg-owner-password"])
        for value in state["secrets"].values():
            self.assertRegex(value, r"^[A-Za-z0-9]{32}$")
            self.assertNotIn(value, first.stdout + first.stderr)
        self.assertEqual(len(set(state["secrets"].values())), 2)
        leftovers = [p for p in (self.dir / "tmp" / "u12-evidence").glob("*") if "request-" in p.name]
        self.assertEqual(leftovers, [])  # the temporary request bodies are deleted
        for path in (self.dir / "tmp").rglob("*"):
            if path.is_file():
                for value in state["secrets"].values():
                    self.assertNotIn(value, path.read_text(errors="ignore"))
        second = run_pwsh(self.dir, "-Stage", "Secrets")
        self.assertEqual(second.returncode, 0)
        self.assertEqual(json.loads((self.dir / "state.json").read_text())["puts"], 2)  # nothing regenerated
        self.assertIn("ya existe (no se toca)", second.stdout)


def is_read_only(argv: list[str]) -> bool:
    words = [a.lower() for a in argv]
    if "--body" in words or "--yes" in words or "--set" in words:
        return False
    if words[:2] in (["bicep", "build"], ["bicep", "build-params"]):
        return "--stdout" in words
    if words[0] == "rest":
        return "--method" in words and words[words.index("--method") + 1] == "get"
    return any(" ".join(words).startswith(prefix) for prefix in READ_ONLY)


@unittest.skipUnless(FAKE_AZ_USABLE, "pwsh and a POSIX host are needed for the fake Azure CLI")
class PreflightOnly(unittest.TestCase):
    """`-PreflightOnly` against the fake Azure CLI, from the real repository root: it must only read."""

    SECTIONS = ("== 1. Sesión Azure", "== 2. Suscripción", "== 3. Resource Group", "== 4. Providers", "== 5. Key Vault",
                "== 6. RBAC", "== 7. ACR", "== 8. PostgreSQL", "== 9. Container Apps", "== 10. Bicep",
                "== 11. Seguridad", "== 12. Resultado")

    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="u12-pre-"))
        (self.dir / "bin").mkdir()
        wrapper = self.dir / "bin" / "az"
        wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{Path(__file__).parent / "fake_az_u12.py"}" "$@"\n')
        wrapper.chmod(0o755)

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_preflight(self, *args: str, env: dict | None = None, python: bool = False, ps51: bool = False):
        if python:  # section 11 runs the secret scan and the configuration tests with this interpreter
            (self.dir / "bin" / "python").symlink_to(sys.executable)
            (self.dir / "bin" / "git").symlink_to(shutil.which("git"))  # the secret scan lists the tracked files
        command = f"{EMULATE_PS51 if ps51 else ''}& '{SCRIPT}' {' '.join(args or ('-PreflightOnly',))}; exit $LASTEXITCODE"
        environment = {"PATH": str(self.dir / "bin"), "HOME": os.environ.get("HOME", str(self.dir)),
                       "FAKE_AZ_STATE": str(self.dir / "state.json"), **(env or {})}
        result = subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command", command], cwd=ROOT,
                                capture_output=True, text=True, timeout=300, env=environment)
        state = json.loads((self.dir / "state.json").read_text()) if (self.dir / "state.json").exists() else {}
        return result, state

    def assert_only_reads(self, state: dict) -> None:
        self.assertTrue(state.get("argv"))
        for argv in state["argv"]:
            self.assertTrue(is_read_only(argv), " ".join(argv))
        self.assertEqual((state["puts"], state["roles"], state["assignments"], state["secrets"]), (0, [], [], {}))

    def test_parameter_exists_and_everything_is_read_only(self) -> None:
        self.assertIn("[switch]$PreflightOnly", ScriptSource.SOURCE)
        result, state = self.run_preflight(python=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        positions = [result.stdout.index(section) for section in self.SECTIONS]
        self.assertEqual(positions, sorted(positions))  # the twelve sections, in order
        self.assertIn("KeyVault deploy/action:\n  ALLOWED", result.stdout)
        self.assertIn("\nPREFLIGHT OK\n", result.stdout)
        self.assertIn("U12 PREFLIGHT OK — KeyVaultRole no requerido", result.stdout)
        self.assertRegex(result.stdout, r"detector de secretos: secret scan: \d+ files, 0 finding")
        self.assertRegex(result.stdout, r"pruebas de configuracion de U12: Ran \d+ tests .*OK")
        self.assertNotIn("BLOQUEO", result.stdout)
        self.assert_only_reads(state)
        self.assertFalse((self.dir / "tmp").exists())

    def test_stage_preflight_is_the_same_read_only_mode(self) -> None:
        result, state = self.run_preflight("-Stage", "Preflight")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PREFLIGHT OK", result.stdout)
        self.assertIn("AVISO  Python 3.9+ no encontrado", result.stdout)  # no interpreter on this PATH
        self.assert_only_reads(state)

    def test_existing_u12_resources_are_checked(self) -> None:
        result, state = self.run_preflight(env={"FAKE_AZ_EXISTING": "1"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for line in ("acrmpadevx: usuario administrador deshabilitado", "psql-mpa-dev-x: SKU Standard_B1ms",
                     "ca-mpa-dev-api: ingress interno, solo HTTPS", "caj-mpa-dev-bootstrap: job manual",
                     "cae-mpa-dev: modo WorkloadProfiles (admite el job de bootstrap)",
                     "id-mpa-dev-runtime: roles AcrPull (solo AcrPull)"):
            self.assertIn(line, result.stdout)
        self.assert_only_reads(state)

    def test_an_express_environment_is_reported_without_touching_it(self) -> None:
        result, state = self.run_preflight(env={"FAKE_AZ_EXISTING": "1", "FAKE_AZ_EXPRESS": "1"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)  # a warning: Core tries the conversion
        self.assertIn("AVISO  cae-mpa-dev: modo 'Express', sin jobs", result.stdout)
        self.assertIn("README de U12, 5.2", result.stdout)
        self.assert_only_reads(state)

    def test_missing_deploy_action_asks_for_the_key_vault_role_stage(self) -> None:
        result, state = self.run_preflight(env={"FAKE_AZ_DEPLOYER_ROLE": "Reader"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("KeyVault deploy/action:\n  MISSING", result.stdout)
        self.assertIn("U12 PREFLIGHT OK — requiere etapa KeyVaultRole", result.stdout)
        self.assert_only_reads(state)  # the role is NOT created here

    def test_blockers_end_with_a_non_zero_exit(self) -> None:
        cases = {
            "Key Vault publico": ({"FAKE_AZ_KV_PUBLIC": "1"}, "publicNetworkAccess = Enabled"),
            "ACR con administrador": ({"FAKE_AZ_EXISTING": "1", "FAKE_AZ_ACR_ADMIN": "1"}, "usuario administrador"),
            "API publica": ({"FAKE_AZ_EXISTING": "1", "FAKE_AZ_API_PUBLIC": "1"}, "ca-mpa-dev-api: ingress interno"),
            "regla 0.0.0.0": ({"FAKE_AZ_EXISTING": "1", "FAKE_AZ_OPEN_RULE": "1"}, "regla de firewall no permitida"),
            "GitHub lee secretos": ({"FAKE_AZ_GITHUB_ROLE": "Key Vault Contributor"}, "id-mpa-dev-github: roles"),
            "sujeto OIDC antiguo": ({"FAKE_AZ_OIDC_SUBJECT": "repo:daniel02vazquez97-alt/Motor-Predictivo-de-Abastecimiento-de-Inventarios:environment:dev"},
                                    "una sola federacion OIDC, sujeto esperado"),
            "sujeto OIDC de rama": ({"FAKE_AZ_OIDC_SUBJECT": "repo:daniel02vazquez97-alt@290574726/G19X-ITH-DVT-209-ACADEMIC@1408075880:ref:refs/heads/main"},
                                    "una sola federacion OIDC, sujeto esperado"),
        }
        for name, (env, reason) in cases.items():
            with self.subTest(name):

                (self.dir / "state.json").unlink(missing_ok=True)
                result, state = self.run_preflight(env=env)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("BLOQUEO", result.stdout)
                self.assertIn(reason, result.stdout)
                self.assertTrue(result.stdout.rstrip().endswith("PREFLIGHT BLOQUEADO"))
                self.assertNotIn("\nPREFLIGHT OK", result.stdout)
                self.assert_only_reads(state)

    def test_windows_powershell_51_behaviour(self) -> None:
        result, state = self.run_preflight(env={"FAKE_AZ_EXISTING": "1"}, ps51=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("U12 PREFLIGHT OK", result.stdout)
        self.assert_only_reads(state)

    def test_cannot_be_combined_with_a_writing_stage(self) -> None:
        result, state = self.run_preflight("-PreflightOnly", "-Stage", "Core")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(state, {})  # not a single az call

    def test_preflight_source_has_no_writing_command(self) -> None:
        body = ScriptSource.SOURCE.split("function Invoke-Preflight {")[1].split("\nif ($Stage -eq 'Preflight'")[0]
        for verb in ("'create'", "'delete'", "'update'", "'set'", "'start'", "'stop'", "'register'", "'put'", "'login'",
                     "'keyvault'", "'postgres'", "'acr'", "'containerapp'", "'deployment'", "Set-Content", "New-Item",
                     "Save-Evidence"):
            self.assertNotIn(verb, body)
        self.assertIn("if ($script:ReadOnly -and -not (Test-ReadOnlyAz $Arguments))", ScriptSource.SOURCE)


if __name__ == "__main__":
    unittest.main()
