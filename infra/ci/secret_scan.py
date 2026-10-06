"""Secret scan of the repository files (U8, `DT-096`); standard library only.

Run from the repository root (the same command locally and in CI)::

    python infra/ci/secret_scan.py

It checks the files Git would commit: the tracked ones plus the untracked ones not ignored by
``.gitignore`` (``git ls-files --cached --others --exclude-standard``). Two kinds of finding:

* **forbidden file**: a file that must never be versioned (a real ``.env``, keys, certificates,
  credential files), mirroring ``.gitignore`` (CLAUDE.md §9). ``.env.example`` is allowed: it only
  holds fictitious values (`DT-065`);
* **secret pattern**: content that looks like a private key, a cloud or service credential, a token
  or a connection string with a password.

Findings are printed as ``path:line: rule`` and the matched value is **never** printed. Exit status:
0 when nothing is found, 1 with findings, 2 when the file list cannot be obtained.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MAX_BYTES = 2_000_000  # larger files are reported as skipped, never silently ignored

# Basenames that must never be versioned (CLAUDE.md §9, `.gitignore`).
FORBIDDEN_NAMES = (".env", ".env.*", "*.pem", "*.key", "*.pfx", "*.p12", "*.jks", "local.settings.json",
                   "*credentials*.json", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".pgpass", ".netrc")
ALLOWED_NAMES = (".env.example",)

# Values that only stand for a password in documentation; a connection string with one of them is not a
# finding.
PLACEHOLDERS = frozenset({"password", "pass", "passwd", "secret", "changeme", "xxx", "xxxx", "***", "****",
                          "pwd", "usuario", "contrasena", "contraseña"})

RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN[ A-Z0-9]*PRIVATE KEY-----")),
    ("azure-storage-account-key", re.compile(r"AccountKey=[A-Za-z0-9+/]{40,}={0,2}")),
    ("azure-shared-access-key", re.compile(r"SharedAccessKey=[A-Za-z0-9+/]{30,}={0,2}")),
    ("azure-sas-signature", re.compile(r"[?&]sig=[A-Za-z0-9%+/]{30,}")),
    ("azure-ad-client-secret",
     re.compile(r"(?<![A-Za-z0-9_~.-])[A-Za-z0-9_~.]{3}[0-9]Q~[A-Za-z0-9_~.-]{31,34}(?![A-Za-z0-9_~.-])")),
    ("service-key-assignment",
     re.compile(r"(?i)(?<![a-z0-9])(?:api[_-]?key|subscription[_-]?key|ocp-apim-subscription-key|access[_-]?key)"
                r"[\"']?\s*[:=]\s*[\"']?[0-9a-f]{32}\b")),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})")),
    ("aws-access-key-id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack-token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
)
CONNECTION_STRING = re.compile(r"\b[a-z][a-z0-9+.-]*://(?P<user>[^\s:/@'\"`<>]+):(?P<password>[^\s@/'\"`<>]+)@")
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?<![a-z0-9])(?:password|passwd|client_secret|secret_key|api_key|apikey|access_token|auth_token)(?![a-z0-9])"
    r"[\"']?\s*[:=]\s*[\"'](?P<value>[^\"'\s]{8,})[\"']"
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int  # 0 for a forbidden file
    rule: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}" if self.line else f"{self.path}: {self.rule}"


def forbidden(path: str) -> bool:
    name = PurePosixPath(path).name
    if name in ALLOWED_NAMES:
        return False
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in FORBIDDEN_NAMES)


def _placeholder(value: str) -> bool:
    lowered = value.lower()
    return lowered in PLACEHOLDERS or lowered.startswith(("${", "$", "<", "{{", "%(")) or set(lowered) <= {"*", "x"}


def scan_text(path: str, text: str) -> list[Finding]:
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in RULES:
            if pattern.search(line):
                findings.append(Finding(path, number, rule))
        for match in CONNECTION_STRING.finditer(line):
            if not _placeholder(match.group("password")):
                findings.append(Finding(path, number, "connection-string-password"))
        for match in SECRET_ASSIGNMENT.finditer(line):
            if not _placeholder(match.group("value")):
                findings.append(Finding(path, number, "secret-assignment"))
    return findings


def scan_file(root: Path, path: str) -> tuple[list[Finding], bool]:
    """Findings of one file and whether it was skipped (binary or too large)."""
    findings = [Finding(path, 0, "forbidden-file")] if forbidden(path) else []
    file = root / path
    if not file.is_file():  # deleted in the working tree but still tracked
        return findings, False
    data = file.read_bytes()
    if len(data) > MAX_BYTES or b"\0" in data:
        return findings, True
    return findings + scan_text(path, data.decode("utf-8", errors="replace")), False


def repository_files(root: Path) -> list[str]:
    output = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root, check=True, capture_output=True,
    ).stdout
    return sorted({name for name in output.decode("utf-8").split("\0") if name})


def main() -> int:
    root = Path.cwd()
    try:
        paths = repository_files(root)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"secret scan: cannot list the repository files ({type(exc).__name__})", file=sys.stderr)
        return 2
    findings: list[Finding] = []
    skipped: list[str] = []
    for path in paths:
        file_findings, was_skipped = scan_file(root, path)
        findings.extend(file_findings)
        if was_skipped:
            skipped.append(path)
    for path in skipped:
        print(f"skipped (binary or larger than {MAX_BYTES} bytes): {path}")
    for finding in findings:
        print(f"FINDING {finding}")
    print(f"secret scan: {len(paths)} files, {len(findings)} finding(s), {len(skipped)} skipped")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
