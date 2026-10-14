"""Un solo comando para las pruebas del proyecto, en Windows (PowerShell) y en Linux/macOS (bash).

Desde la raíz del repositorio::

    python scripts/test.py                 # todas las suites cuyos requisitos están instalados
    python scripts/test.py --list          # qué suites hay y qué necesita cada una
    python scripts/test.py backend api     # solo esas suites
    python scripts/test.py --coverage      # además, cobertura de backend/app en backend y api
    python scripts/test.py --frontend      # añade el frontend (npm ci, lint, typecheck, test y build)

Usa los mismos comandos que CI (.github/workflows/ci.yml); no define otros. Una suite cuyo requisito falta se marca
OMITIDA con la instrucción para instalarlo, nunca como aprobada. La salida es 0 solo si ninguna suite ejecutada
falla. Biblioteca estándar; el intérprete es el que ejecuta este archivo.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MANIFEST = ROOT / "data" / "synthetic" / "output" / "manifest.json"
PY = sys.executable
QUALITY = "pip install -r infra/ci/requirements-quality.txt"


def has(*modules: str) -> bool:
    return all(importlib.util.find_spec(m) is not None for m in modules)


@dataclass
class Suite:
    name: str
    what: str
    command: list[str]
    cwd: Path = ROOT
    needs: tuple[str, ...] = ()  # importable modules
    hint: str = ""
    env: dict[str, str] = field(default_factory=dict)
    dataset: bool = False  # needs the published synthetic dataset
    coverable: bool = False
    enabled: bool = True  # False: only when asked explicitly
    condition: str | None = None  # environment variable that must be set

    def missing(self) -> str | None:
        if self.condition and not os.environ.get(self.condition):
            return f"define {self.condition}"
        if self.needs and not has(*self.needs):
            return self.hint
        if self.name == "frontend" and not shutil.which("npm"):
            return "instala Node 24 y npm 11"
        return None


def suites() -> list[Suite]:
    backend_api = "pip install -r requirements generado con: python infra/ci/backend_requirements.py db api test entra"
    return [
        Suite("secrets", "Detección de secretos y archivos prohibidos", [PY, "infra/ci/secret_scan.py"]),
        Suite("lint", "Ruff, solo errores reales (ruff.toml)", [PY, "-m", "ruff", "check", "."],
              needs=("ruff",), hint=QUALITY),
        Suite("backend", "Motor, pronóstico, ingesta y explicación (suite por defecto)",
              [PY, "-m", "unittest", "discover", "-s", "tests", "-t", "."], cwd=BACKEND, dataset=True,
              coverable=True),
        Suite("api", "API sin base: contrato, autenticación, roles, Entra ID y Azure OpenAI simulado",
              [PY, "-m", "unittest", "discover", "-s", "tests/api", "-t", "tests/api"], cwd=BACKEND,
              needs=("fastapi", "psycopg", "jwt", "httpx2"), coverable=True,
              hint=backend_api),
        Suite("integration", "Migraciones y API contra PostgreSQL 16",
              [PY, "-m", "unittest", "discover", "-s", "tests/db", "-t", "tests/db"], cwd=BACKEND,
              needs=("psycopg", "fastapi"), condition="U2_TEST_ADMIN_DSN", dataset=True, coverable=True,
              hint=backend_api),
        Suite("ml", "Backtesting, métricas y candidatos (ml/)",
              [PY, "-m", "unittest", "discover", "-s", "ml/tests", "-t", "."], env={"PYTHONPATH": str(BACKEND)},
              dataset=True),
        Suite("generator", "Generador sintético 0.4.0 y su validador",
              [PY, "-m", "unittest", "discover", "-s", "data/synthetic/tests", "-t", "."], needs=("yaml",),
              hint="pip install -r data/synthetic/requirements.txt"),
        Suite("infra", "Bicep, workflows y scripts de despliegue (Azure CLI simulado)",
              [PY, "-m", "unittest", "discover", "-s", "infra/tests", "-t", "infra/tests"]),
        Suite("frontend", "ESLint, tsc, Prettier, Vitest y build", ["npm"], cwd=ROOT / "frontend", enabled=False),
    ]


def publish_dataset() -> str | None:
    """The suites that read data/synthetic/output need the dataset published once (as CI does)."""
    if MANIFEST.is_file():
        return None
    if not has("yaml"):
        return "pip install -r data/synthetic/requirements.txt (para publicar el dataset)"
    print("== publicando el dataset sintético 0.4.0 (python -m data.synthetic.generator)", flush=True)
    result = subprocess.run([PY, "-m", "data.synthetic.generator"], cwd=ROOT)
    return None if result.returncode == 0 and MANIFEST.is_file() else "no se pudo publicar el dataset"


def run(suite: Suite, coverage: bool) -> int:
    env = {**os.environ, **suite.env, "PYTHONDONTWRITEBYTECODE": "1"}
    if suite.name == "frontend":
        npm = shutil.which("npm") or "npm"
        for args in (["ci", "--no-audit", "--no-fund"], ["run", "lint"], ["run", "typecheck"],
                     ["run", "format:check"], ["test"], ["run", "build"]):
            code = subprocess.run([npm, *args], cwd=suite.cwd, env=env).returncode
            if code:
                return code
        return 0
    command = list(suite.command)
    if coverage and suite.coverable:
        command = [PY, "-m", "coverage", "run", "--source=app", *command[1:]]
    code = subprocess.run(command, cwd=suite.cwd, env=env).returncode
    if coverage and suite.coverable and code == 0:
        subprocess.run([PY, "-m", "coverage", "report"], cwd=suite.cwd, env=env)
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("names", nargs="*", help="suites a ejecutar (por defecto, todas las disponibles)")
    parser.add_argument("--list", action="store_true", help="lista las suites y sus requisitos")
    parser.add_argument("--coverage", action="store_true", help="cobertura de backend/app (requiere coverage)")
    parser.add_argument("--frontend", action="store_true", help="incluye el frontend (npm)")
    args = parser.parse_args(argv)
    all_suites = suites()
    by_name = {s.name: s for s in all_suites}
    if args.list:
        for s in all_suites:
            state = s.missing() or "disponible"
            print(f"{s.name:<12} {s.what}\n{'':<12} -> {state}")
        return 0
    unknown = [n for n in args.names if n not in by_name]
    if unknown:
        parser.error(f"suite desconocida: {', '.join(unknown)} (ver --list)")
    if args.coverage and not has("coverage"):
        parser.error(f"--coverage necesita coverage: {QUALITY}")
    chosen = [by_name[n] for n in args.names] if args.names else [
        s for s in all_suites if s.enabled or (s.name == "frontend" and args.frontend)]
    results: list[tuple[str, str, float]] = []
    dataset_problem: str | None = None
    if any(s.dataset for s in chosen if not s.missing()):
        dataset_problem = publish_dataset()
    for s in chosen:
        reason = s.missing() or (dataset_problem if s.dataset else None)
        if reason:
            results.append((s.name, f"OMITIDA: {reason}", 0.0))
            continue
        print(f"\n== {s.name}: {s.what}", flush=True)
        start = time.monotonic()
        code = run(s, args.coverage)
        results.append((s.name, "OK" if code == 0 else f"FALLO (código {code})", time.monotonic() - start))
    print("\nResumen")
    for name, state, seconds in results:
        print(f"  {name:<12} {state}" + (f"  ({seconds:.0f} s)" if seconds else ""))
    failed = [r for r in results if r[1].startswith("FALLO")]
    if not any(r[1] == "OK" for r in results):
        print("Ninguna suite se ejecutó.")
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
