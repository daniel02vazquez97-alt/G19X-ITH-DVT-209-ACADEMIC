"""Static checks of the Azure base of U10 (`DT-098`, infra/azure); standard library only.

They do not call Azure: the real verification is ``az deployment sub what-if`` and the checks of
``infra/azure/README.md``. Run from the repository root::

    python -m unittest discover -s infra/tests -t infra/tests
"""

from __future__ import annotations

import re
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
        # westus2 (no Azure OpenAI), westus/eastus/eastus2 (AI Search full) and mexicocentral are excluded.
        location = re.search(r"^param location = '([a-z0-9]+)'$", PARAMS, re.MULTILINE).group(1)
        self.assertIn(location, {"westus3", "southcentralus", "northcentralus"})
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
                         "enabledForTemplateDeployment: false"):
            self.assertIn(fragment, BASE)
        self.assertNotIn("enablePurgeProtection", BASE)

    def test_federation_is_oidc_and_limited_to_the_dev_environment(self) -> None:
        self.assertIn("issuer: 'https://token.actions.githubusercontent.com'", BASE)
        self.assertIn("'api://AzureADTokenExchange'", BASE)
        self.assertIn("subject: 'repo:${githubOwner}/${githubRepository}:environment:${githubEnvironment}'", BASE)
        self.assertEqual(BASE.count("federatedIdentityCredentials@"), 1)

    def test_the_only_role_is_reader_on_the_resource_group(self) -> None:
        self.assertEqual(re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", BASE), [READER])
        self.assertEqual(BASE.count("Microsoft.Authorization/roleAssignments@"), 1)
        self.assertNotIn("targetScope", BASE)  # resource-group scope: the assignment cannot reach the subscription


if __name__ == "__main__":
    unittest.main()
