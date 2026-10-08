"""Static checks of the Azure base of U10 (`DT-098`, infra/azure); standard library only.

They do not call Azure: the real verification is ``az deployment sub what-if`` and the checks of
``infra/azure/README.md``. Run from the repository root::

    python -m unittest discover -s infra/tests -t infra/tests
"""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

AZURE = Path(__file__).resolve().parents[2] / "infra" / "azure"
READER = "acdd72a7-3385-48ef-bd42-f606fba81ae7"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


MAIN = text(AZURE / "main.bicep")
BASE = text(AZURE / "modules" / "base.bicep")
BUDGET = text(AZURE / "modules" / "budget.bicep")
PARAMS = text(AZURE / "parameters" / "dev.bicepparam")
ALL = {"main.bicep": MAIN, "base.bicep": BASE, "budget.bicep": BUDGET, "dev.bicepparam": PARAMS}
DEPLOY = AZURE / "deploy-dev.ps1"
PWSH = shutil.which("pwsh")
# Windows PowerShell 5.1 returns a JSON array from ConvertFrom-Json as ONE object; PowerShell 7 reproduces that
# with -NoEnumerate. This wrapper runs the script with that behaviour (the cause of the 2026-10-07 false positive).
EMULATE_PS51 = (
    "function global:ConvertFrom-Json { param([Parameter(ValueFromPipeline = $true)]$InputObject) "
    "process { Microsoft.PowerShell.Utility\\ConvertFrom-Json -InputObject $InputObject -NoEnumerate } }; "
)


def resource_types(source: str) -> set[str]:
    return set(re.findall(r"^resource \w+ '([^@']+)@", source, re.MULTILINE))


class Scope(unittest.TestCase):
    def test_only_the_resources_of_u10(self) -> None:
        self.assertEqual(resource_types(MAIN), {"Microsoft.Resources/resourceGroups"})
        self.assertEqual(resource_types(BASE), {
            "Microsoft.KeyVault/vaults",
            "Microsoft.ManagedIdentity/userAssignedIdentities",
            "Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials",
            "Microsoft.Authorization/roleAssignments",
        })
        self.assertEqual(resource_types(BUDGET), {"Microsoft.Consumption/budgets"})

    def test_only_dev_and_budget_off_by_default(self) -> None:
        self.assertRegex(MAIN, r"@allowed\(\[\n  'dev'\n\]\)\nparam environment string = 'dev'")
        self.assertIn("param deployBudget bool = false", MAIN)
        self.assertIn("module budget 'modules/budget.bicep' = if (deployBudget)", MAIN)
        self.assertIn("param deployBudget = false", PARAMS)

    def test_region_and_resource_group_follow_dt098(self) -> None:
        # Allowed by the subscription policy and complete for the stack: centralus, or northcentralus as backup.
        location = re.search(r"^param location = '([a-z0-9]+)'$", PARAMS, re.MULTILINE).group(1)
        self.assertIn(location, {"centralus", "northcentralus"})
        self.assertEqual(location, "centralus")
        # The guarded deployment script checks the what-if against the same region.
        script = text(AZURE / "deploy-dev.ps1")
        self.assertEqual(re.search(r"^\$Location = '([a-z0-9]+)'", script, re.MULTILINE).group(1), location)
        self.assertIn("param resourceGroupName = 'rg-motor-predictivo-dev'", PARAMS)
        self.assertIn("  name: resourceGroupName\n", MAIN)

    def test_every_resource_is_tagged(self) -> None:
        for key in ("project", "environment", "owner", "purpose", "managedBy", "costControl"):
            self.assertRegex(MAIN, rf"\n  {key}: ")
        self.assertEqual(BASE.count("tags: tags"), 2)  # vault and identity; child resources inherit nothing taggable
        self.assertIn("tags: tags", MAIN)


class Security(unittest.TestCase):
    def test_no_secret_parameter_or_value(self) -> None:
        for name, source in ALL.items():
            with self.subTest(file=name):
                self.assertNotRegex(source.lower(), r"password|clientsecret|client_secret|@secure\(\)|accountkey")
        self.assertNotRegex(PARAMS, r"[\w.+-]+@[\w-]+\.[\w.]+")  # no e-mail address is versioned

    def test_key_vault_rbac_private_and_purgeable(self) -> None:
        for fragment in ("enableRbacAuthorization: true", "accessPolicies: []", "publicNetworkAccess: 'Disabled'",
                         "defaultAction: 'Deny'", "softDeleteRetentionInDays: 7", "name: 'standard'",
                         "param armSecretAccess bool = false", "enabledForTemplateDeployment: armSecretAccess",
                         "bypass: armSecretAccess ? 'AzureServices' : 'None'"):
            self.assertIn(fragment, BASE)
        self.assertNotIn("enablePurgeProtection", BASE)
        # U12 (DT-100): only ARM template deployment (trusted service) may read secrets; no public network.
        self.assertIn("param keyVaultArmSecretAccess = true", PARAMS)
        self.assertEqual(BASE.count("publicNetworkAccess:"), 1)

    def test_federation_is_oidc_and_limited_to_the_dev_environment(self) -> None:
        self.assertIn("issuer: 'https://token.actions.githubusercontent.com'", BASE)
        self.assertIn("'api://AzureADTokenExchange'", BASE)
        self.assertIn("subject: 'repo:${githubOwner}/${githubRepository}:environment:${githubEnvironment}'", BASE)
        self.assertEqual(BASE.count("federatedIdentityCredentials@"), 1)

    def test_the_only_role_is_reader_on_the_resource_group(self) -> None:
        self.assertEqual(re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", BASE), [READER])
        self.assertEqual(BASE.count("Microsoft.Authorization/roleAssignments@"), 1)
        self.assertNotIn("targetScope", BASE)  # resource-group scope: the assignment cannot reach the subscription


class DeployScript(unittest.TestCase):
    """infra/azure/deploy-dev.ps1: JSON lists from az are counted by elements, never by lines or objects."""

    SOURCE = text(DEPLOY)

    def test_every_list_is_read_as_a_json_array(self) -> None:
        self.assertNotIn("@(Invoke-Az", self.SOURCE)  # wrapping a 5.1 ConvertFrom-Json array counted "[]" as 1
        for command in ("'resource', 'list'", "'lock', 'list'", "'federated-credential', 'list'",
                        "'role', 'assignment', 'list'"):
            with self.subTest(command=command):
                calls = [line for line in self.SOURCE.splitlines() if command in line]
                self.assertTrue(calls)
                for line in calls:
                    self.assertIn("-Array", line)
                    self.assertIn("'--output', 'json'", line)
        self.assertNotRegex(self.SOURCE, r"Select-String|--output', 'table'|Measure-Object -Line")

    def test_script_is_ascii(self) -> None:
        DEPLOY.read_bytes().decode("ascii")  # Windows PowerShell 5.1 reads files without BOM as ANSI

    def run_selftest(self, emulate_ps51: bool) -> str:
        command = f"{EMULATE_PS51 if emulate_ps51 else ''}& '{DEPLOY}' -SelfTest; exit $LASTEXITCODE"
        result = subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command", command],
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def assert_counts(self, output: str) -> None:
        self.assertIn("SELFTEST OK", output)
        for json_text, count in (("[]", 0), ("", 0), ("null", 0), ('[{"name":"a","type":"t"}]', 1),
                                 ('[{"name":"a","type":"t"},{"name":"b","type":"t"}]', 2)):
            with self.subTest(json=json_text):
                self.assertRegex(output, rf"OK +'{re.escape(json_text)}' +-> {count} \(esperado {count}\)")

    @unittest.skipUnless(PWSH, "pwsh not installed")
    def test_empty_list_is_zero_and_one_element_is_one(self) -> None:
        self.assert_counts(self.run_selftest(emulate_ps51=False))

    @unittest.skipUnless(PWSH, "pwsh not installed")
    def test_same_counts_with_windows_powershell_51_json_arrays(self) -> None:
        bug = subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command",
                              EMULATE_PS51 + "@('[]' | ConvertFrom-Json).Count"],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(bug.stdout.strip(), "1")  # the emulation reproduces the false positive...
        self.assert_counts(self.run_selftest(emulate_ps51=True))  # ...and the script is immune to it


if __name__ == "__main__":
    unittest.main()
