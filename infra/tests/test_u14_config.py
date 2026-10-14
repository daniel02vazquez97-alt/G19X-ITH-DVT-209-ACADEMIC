"""U14 (`DT-102`): static checks of the Azure ML deployment, the job and its wrapper, without Azure.

The real verification is ``deploy-u14.ps1`` (what-if checked automatically, Submit and Verify). The Bicep build runs
when the Bicep CLI is available; ``-SelfTest`` when ``pwsh`` is. Standard library only.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
U14 = ROOT / "infra" / "azure" / "u14"
JOB = U14 / "job"
SCRIPT = ROOT / "infra" / "azure" / "deploy-u14.ps1"
VERSIONED = ROOT / "docs" / "reports" / "fase5-f5a-backtest-sintetico.json"
PWSH = shutil.which("pwsh") or (str(Path.home() / "pwsh7" / "pwsh") if (Path.home() / "pwsh7" / "pwsh").is_file() else None)
BICEP = shutil.which("bicep") or (str(Path.home() / "bicep") if (Path.home() / "bicep").is_file() else None)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def wrapper():
    spec = importlib.util.spec_from_file_location("u14_run_backtest", JOB / "run_backtest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BicepTest(unittest.TestCase):
    def test_minimal_workspace(self) -> None:
        main = read(U14 / "main.bicep")
        for needle in ("Microsoft.MachineLearningServices/workspaces@2026-07-01", "kind: 'Default'",
                       "type: 'SystemAssigned'", "name: 'Standard_LRS'", "allowBlobPublicAccess: false",
                       "minimumTlsVersion: 'TLS1_2'", "supportsHttpsTrafficOnly: true", "softDeleteRetentionInDays: 7"):
            self.assertIn(needle, main)
        for absent in ("containerRegistry", "applicationInsights", "Microsoft.Insights", "Microsoft.ContainerRegistry",
                       "computes", "onlineEndpoints", "enablePurgeProtection: true", "listKeys", "@secure"):
            self.assertNotIn(absent, main)
        self.assertEqual(len(re.findall(r"^resource ", main, re.M)), 3)

    @unittest.skipUnless(BICEP, "Bicep CLI not available")
    def test_build_and_lint(self) -> None:
        for args in (["build", str(U14 / "main.bicep"), "--stdout"], ["lint", str(U14 / "main.bicep")],
                     ["build-params", str(U14 / "dev.bicepparam"), "--stdout"]):
            result = subprocess.run([BICEP, *args], capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Warning", result.stderr)


class JobTest(unittest.TestCase):
    def test_serverless_job_with_the_pinned_api_base_image(self) -> None:
        job = read(JOB / "job.yml")
        image = re.search(r"^\s*image: (\S+)", job, re.M).group(1)
        self.assertIn(f"FROM {image}", read(ROOT / "infra" / "docker" / "backend.Dockerfile"))
        self.assertRegex(image, r"@sha256:[0-9a-f]{64}$")
        self.assertIn("instance_type: Standard_DS2_v2", job)
        self.assertNotRegex(job, r"(?m)^compute:")  # serverless: no compute target
        self.assertIn("${{outputs.model}}", job)
        self.assertIn("timeout: 1800", job)

    def test_pinned_requirements(self) -> None:
        lines = [l for l in read(JOB / "requirements.txt").splitlines() if l and not l.startswith("#")]
        self.assertEqual(lines, ["PyYAML==6.0.3", "mlflow-skinny==3.15.0", "azureml-mlflow==1.62.0.post6"])
        self.assertIn("PyYAML==6.0.3", read(ROOT / "data" / "synthetic" / "requirements.txt"))

    def test_ml_stays_standard_library(self) -> None:
        for path in (ROOT / "ml").rglob("*.py"):
            self.assertNotRegex(read(path), r"(?m)^\s*(import|from) (mlflow|azureml|azure)\b", str(path))


class WrapperTest(unittest.TestCase):
    def test_metrics_and_comparison_of_the_versioned_report(self) -> None:
        module = wrapper()
        summary = json.loads(read(VERSIONED))
        metrics = module.aggregated_metrics(summary)
        self.assertAlmostEqual(metrics["baseline.moving_average.mase"], 0.983463)
        self.assertEqual({k.split(".")[-1] for k in metrics}, set(module.METRICS))
        same = module.comparison(summary, summary)
        self.assertTrue(same["reproduces_versioned_report"])
        other = {**summary, "results_sha256": "0" * 64}
        self.assertFalse(module.comparison(other, summary)["reproduces_versioned_report"])

    def test_model_folder(self) -> None:
        module = wrapper()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "r.json").write_text("{}", encoding="utf-8")
            (tmp / "r.md").write_text("#", encoding="utf-8")
            module.write_model(tmp / "model", tmp / "r.json", tmp / "r.md", {"reproduces_versioned_report": True})
            config = json.loads(read(tmp / "model" / "baseline-ma13.json"))
            self.assertEqual((config["baseline"], config["window_weeks"]), ("baseline.moving_average", 13))
            self.assertEqual(sorted(p.name for p in (tmp / "model").iterdir()),
                             ["baseline-ma13.json", "comparison.json", "f5a-report.json", "f5a-report.md"])

    def test_no_mlflow_without_tracking_uri(self) -> None:
        module = wrapper()
        self.assertFalse(module.log_mlflow({}, {}, ROOT))


class ScriptTest(unittest.TestCase):
    def test_ascii_stages_and_confirmations(self) -> None:
        script = read(SCRIPT)
        self.assertTrue(script.isascii())
        self.assertIn("[ValidateSet('Preflight', 'Deploy', 'Submit', 'Verify', 'Remove')]", script)
        self.assertIn("Confirm-Or-Stop 'AZUREML'", script)
        self.assertIn("Confirm-Or-Stop 'BORRAR'", script)
        self.assertIn("'--all-resources', '--permanently-delete'", script)
        self.assertIn("results_sha256", script)
        self.assertNotRegex(script, r"'keys',\s*'list'|show-connection-string'\s*,|ConvertTo-SecureString")

    def test_model_registered_only_when_reproduced(self) -> None:
        script = read(SCRIPT)
        self.assertLess(script.index("if (-not $evidence.reproduces)"), script.index("'ml', 'model', 'create'"))

    def test_preflight_allow_list_is_read_only(self) -> None:
        allow = re.search(r"foreach \(\$ok in @\((.*?)\)\)", read(SCRIPT), re.S).group(1)
        for verb in re.findall(r"'([^']+)'", allow):
            self.assertRegex(verb, r"(show|list|version)$", verb)

    @unittest.skipUnless(PWSH, "pwsh not available")
    def test_selftest(self) -> None:
        result = subprocess.run([PWSH, "-NoProfile", "-File", str(SCRIPT), "-SelfTest"], capture_output=True,
                                text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SELFTEST OK (7 casos)", result.stdout)


if __name__ == "__main__":
    unittest.main()
