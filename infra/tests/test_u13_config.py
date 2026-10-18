"""U13 (`DT-101`): static checks of the Azure OpenAI deployment and of its wiring into the api of U12.

No Azure: the real verification is ``deploy-u13.ps1`` (what-if checked automatically, then -Stage Verify). The bicep
build runs when the Bicep CLI is available; ``-SelfTest`` when ``pwsh`` is. Standard library only.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
U13 = ROOT / "infra" / "azure" / "u13"
U12 = ROOT / "infra" / "azure" / "u12"
SCRIPT = ROOT / "infra" / "azure" / "deploy-u13.ps1"
PWSH = shutil.which("pwsh") or (str(Path.home() / "pwsh7" / "pwsh") if (Path.home() / "pwsh7" / "pwsh").is_file() else None)
BICEP = shutil.which("bicep") or (str(Path.home() / "bicep") if (Path.home() / "bicep").is_file() else None)
OPENAI_USER = "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class BicepTest(unittest.TestCase):
    def test_account_without_keys_and_minimum_role_on_the_account(self) -> None:
        main = read(U13 / "main.bicep")
        self.assertIn("kind: 'OpenAI'", main)
        self.assertIn("disableLocalAuth: true", main)
        self.assertIn("customSubDomainName: accountName", main)
        self.assertIn(f"var openAIUserRoleId = '{OPENAI_USER}'", main)
        self.assertRegex(main, r"resource runtimeOpenAIUser [^\n]+\n(?:.*\n){1,2}\s+scope: account\n")
        self.assertIn("versionUpgradeOption: 'NoAutoUpgrade'", main)
        self.assertNotRegex(main, r"(?i)listKeys|apiKey|key1|@secure|getSecret")
        self.assertEqual(main.count("Microsoft.Authorization/roleAssignments@"), 1)

    def test_parameters_match_the_script(self) -> None:
        params, script = read(U13 / "dev.bicepparam"), read(SCRIPT)
        for name, value in (("modelName", "gpt-4.1-mini"), ("modelVersion", "2025-04-14"),
                            ("deploymentName", "gpt-41-mini"), ("deploymentSku", "GlobalStandard")):
            self.assertIn(f"param {name} = '{value}'", params)
            self.assertIn(f"'{value}'", script)
        self.assertIn("param capacity = 10", params)
        self.assertIn("$Capacity = 10", script)

    @unittest.skipUnless(BICEP, "Bicep CLI not available")
    def test_build_and_lint(self) -> None:
        for args in (["build", str(U13 / "main.bicep"), "--stdout"], ["lint", str(U13 / "main.bicep")],
                     ["build-params", str(U13 / "dev.bicepparam"), "--stdout"]):
            result = subprocess.run([BICEP, *args], capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Warning", result.stderr)
        template = json.loads(subprocess.run([BICEP, "build", str(U13 / "main.bicep"), "--stdout"],
                                             capture_output=True, text=True, timeout=120).stdout)
        types = sorted(r["type"] for r in template["resources"].values()) if isinstance(template["resources"], dict) \
            else sorted(r["type"] for r in template["resources"])
        self.assertEqual(types, ["Microsoft.Authorization/roleAssignments", "Microsoft.CognitiveServices/accounts",
                                 "Microsoft.CognitiveServices/accounts/deployments"])


class U12WiringTest(unittest.TestCase):
    def test_api_gets_azure_openai_only_when_enabled_and_never_a_key(self) -> None:
        apps = read(U12 / "modules" / "apps.bicep")
        self.assertIn("var genaiEnv = genaiEnabled ? [", apps)
        for name in ("GENAI_PROVIDER", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT", "AZURE_CLIENT_ID"):
            self.assertIn(f"name: '{name}'", apps)
        self.assertIn("], genaiEnv, searchEnv)", apps)  # U15b (DT-103) appends the Search variables
        self.assertNotRegex(apps, r"(?i)OPENAI_API_KEY|AZURE_OPENAI_KEY")

    def test_disabled_by_default_and_enabled_in_dev_after_verification(self) -> None:
        self.assertIn("param genaiEnabled bool = false", read(U12 / "main.bicep"))
        # Activated in dev after deploy-u13.ps1 -Stage Verify (9/9) and the owner's authorization (DT-101, 2026-10-14).
        self.assertIn("param genaiEnabled = true", read(U12 / "dev.bicepparam"))
        # U12 itself never creates the account: its what-if guard still rejects openai/cognitive resources.
        self.assertNotIn("Microsoft.CognitiveServices", read(U12 / "main.bicep"))
        self.assertIn("openai|cognitive", read(ROOT / "infra" / "azure" / "deploy-u12.ps1"))


class ScriptTest(unittest.TestCase):
    def test_ascii_stages_and_confirmations(self) -> None:
        script = read(SCRIPT)
        self.assertTrue(script.isascii())
        self.assertIn("[ValidateSet('Preflight', 'Deploy', 'Verify', 'Remove')]", script)
        self.assertIn("Confirm-Or-Stop 'OPENAI'", script)
        self.assertIn("Confirm-Or-Stop 'BORRAR'", script)
        self.assertIn("if ($Arguments -contains 'keys') { Stop-U13", script)
        self.assertNotRegex(script, r"'keys',\s*'list'|api-key|ConvertTo-SecureString")

    def test_preflight_allow_list_is_read_only(self) -> None:
        allow = re.search(r"foreach \(\$ok in @\((.*?)\)\)", read(SCRIPT), re.S).group(1)
        for verb in re.findall(r"'([^']+)'", allow):
            self.assertRegex(verb, r"(show|list|version)$", verb)

    @unittest.skipUnless(PWSH, "pwsh not available")
    def test_selftest(self) -> None:
        result = subprocess.run([PWSH, "-NoProfile", "-File", str(SCRIPT), "-SelfTest"], capture_output=True,
                                text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SELFTEST OK (9 casos)", result.stdout)


if __name__ == "__main__":
    unittest.main()
