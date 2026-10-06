"""Tests of the secret scan of U8 (`infra/ci/secret_scan.py`, `DT-096`); standard library only.

Every fake credential is assembled at run time from pieces, so this file never contains one that the
scan itself would report. Run from the repository root::

    python -m unittest discover -s infra/tests -t infra/tests
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "infra" / "ci"))

import secret_scan  # noqa: E402

B64 = "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789+/AbCdEfGhIjKlMnOpQrSt"
HEX32 = "0123456789abcdef" * 2


def fake(*parts: str) -> str:
    return "".join(parts)


FAKE_SECRETS = {
    "private-key": fake("-----BEGIN ", "RSA PRIVATE", " KEY-----"),
    "azure-storage-account-key": fake("DefaultEndpointsProtocol=https;AccountName=demo;Account", "Key=", B64, "=="),
    "azure-shared-access-key": fake("Endpoint=sb://demo/;SharedAccess", "Key=", B64[:44], "="),
    "azure-sas-signature": fake("https://demo.blob.core.windows.net/c?sv=2024&s", "ig=", "AbCdEf%2B", B64[:30]),
    "azure-ad-client-secret": fake("abc", "8Q~", "AbCdEfGhIjKlMnOpQrStUvWxYz012345"),
    "service-key-assignment": fake("AZURE_OPENAI_API_", "KEY=", HEX32),
    "github-token": fake("gh", "p_", "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9"),
    "aws-access-key-id": fake("AK", "IA", "ABCDEFGHIJKLMNOP"),
    "google-api-key": fake("AI", "za", "SyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q"),
    "slack-token": fake("xo", "xb-", "123456789012-abcdefghij"),
    "jwt": fake("ey", "JhbGciOiJIUzI1NiJ9.", "ey", "JzdWIiOiIxMjM0NTY3ODkwIn0.", "abcdefghijKLMNOPQRST"),
    "connection-string-password": fake("postgresql://app_user:", "S3cr3t-Value", "@db.example:5432/inventory"),
    "secret-assignment": fake('DB_PASS', 'WORD = "', "Zx9-Kq7-Wm3-Rt5", '"'),
}


class Patterns(unittest.TestCase):
    def test_each_rule_finds_its_fake_secret(self) -> None:
        for rule, line in FAKE_SECRETS.items():
            with self.subTest(rule=rule):
                rules = {finding.rule for finding in secret_scan.scan_text("f.txt", f"x\n{line}\n")}
                self.assertIn(rule, rules)

    def test_line_numbers(self) -> None:
        findings = secret_scan.scan_text("f.txt", "a\nb\n" + FAKE_SECRETS["aws-access-key-id"])
        self.assertEqual([(f.path, f.line) for f in findings], [("f.txt", 3)])

    def test_values_of_the_project_are_not_findings(self) -> None:
        clean = [
            "DATABASE_URL=postgresql://postgres@127.0.0.1:5432/inventory",  # trust, no password (DT-055)
            "U2_TEST_ADMIN_DSN=postgresql://postgres@localhost:5432/postgres",
            'DEV_AUTH_IDENTITIES={"dev-example-viewer-0000000000": {"subject_id": "example-viewer"}}',
            "postgresql://user:password@host:5432/db",  # documentation placeholder
            "postgresql://user:${DB_PASSWORD}@host/db",
            'password = "<placeholder>"',
            "image: python:3.11.17-slim-trixie@sha256:" + HEX32 * 2,
            "results_sha256 = " + HEX32 * 2,
        ]
        for line in clean:
            with self.subTest(line=line):
                self.assertEqual(secret_scan.scan_text("f.txt", line), [])


class Files(unittest.TestCase):
    def test_forbidden_files(self) -> None:
        for path in (".env", "backend/.env", ".env.local", ".env.production", "certs/server.key", "a/b.pem",
                     "x.pfx", "local.settings.json", "azure-credentials.json", "id_ed25519"):
            with self.subTest(path=path):
                self.assertTrue(secret_scan.forbidden(path))
        for path in (".env.example", "backend/.env.example", "docs/10-seguridad.md", "keys.py", "env.py"):
            with self.subTest(path=path):
                self.assertFalse(secret_scan.forbidden(path))

    def test_scan_file_skips_binaries_but_still_checks_the_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "blob.key").write_bytes(b"\0\1\2")
            findings, skipped = secret_scan.scan_file(root, "blob.key")
            self.assertTrue(skipped)
            self.assertEqual([f.rule for f in findings], ["forbidden-file"])


class CommandLine(unittest.TestCase):
    def run_scan(self, files: dict[str, str]) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / ".gitignore").write_text(".env\n", encoding="utf-8")
            for name, content in files.items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text(content, encoding="utf-8")
            out = io.StringIO()
            cwd = Path.cwd()
            try:
                import os
                os.chdir(root)
                with contextlib.redirect_stdout(out):
                    status = secret_scan.main()
            finally:
                os.chdir(cwd)
            return status, out.getvalue()

    def test_clean_repository(self) -> None:
        status, output = self.run_scan({".env.example": "APP_ENV=local\n", "app.py": "print('ok')\n"})
        self.assertEqual(status, 0)
        self.assertIn("0 finding(s)", output)

    def test_findings_fail_without_printing_the_value(self) -> None:
        value = FAKE_SECRETS["github-token"]
        status, output = self.run_scan({"config.txt": f"token: {value}\n", ".env.production": "X=1\n"})
        self.assertEqual(status, 1)
        self.assertIn("config.txt:1: github-token", output)
        self.assertIn(".env.production: forbidden-file", output)
        self.assertNotIn(value, output)

    def test_ignored_env_file_is_not_listed(self) -> None:
        # A real .env ignored by .gitignore cannot be committed by accident, so it is not reported.
        status, _ = self.run_scan({".env": "SECRET=" + FAKE_SECRETS["aws-access-key-id"] + "\n"})
        self.assertEqual(status, 0)


if __name__ == "__main__":
    unittest.main()
