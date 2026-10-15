"""Static checks for the prepared U15 Azure AI Search service; no Azure calls."""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
U15 = ROOT / "infra" / "azure" / "u15"
BICEP = shutil.which("bicep") or (str(Path.home() / "bicep") if (Path.home() / "bicep").is_file() else None)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class U15ConfigTest(unittest.TestCase):
    def test_search_service_uses_basic_entra_only_and_reader_role(self) -> None:
        main = read(U15 / "main.bicep")
        for needle in (
            "Microsoft.Search/searchServices@2025-05-01",
            "name: 'basic'",
            "disableLocalAuth: true",
            "aadAuthFailureMode: 'http401WithBearerChallenge'",
            "searchIndexDataReaderRoleId",
            "principalId: runtimeIdentity.properties.principalId",
        ):
            self.assertIn(needle, main)
        self.assertNotIn("Search Index Data Contributor", main)
        self.assertNotIn("apiKeyOnly", main)
        self.assertNotIn("Microsoft.Search/searchServices/indexes", main)

    def test_documentation_marks_deployment_pending_due_to_cost(self) -> None:
        readme = read(U15 / "README.md")
        self.assertIn("no se ha desplegado ningún recurso", readme)
        self.assertIn("USD 50", readme)
        self.assertIn("autorización explícita", readme)
        self.assertIn("az deployment group what-if", readme)

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


if __name__ == "__main__":
    unittest.main()
