"""Bootstrap of an empty `dev` database in Azure (U12, `DT-100`): one job execution, one container, in order.

    generate the synthetic dataset 0.4.0 → migrate → ingest → forecast → recommend → application role → summary

It only orchestrates the existing entry points (the generator of `data/synthetic`, ``app.db``, ``app.ingestion``
and ``app.runs``) as subprocesses, exactly as ``init`` does in infra/docker-compose.yml; it adds no logic of its own
to U1–U6. The dataset is written to a temporary directory of this same container and disappears with it: nothing is
shared between executions and no storage account is involved.

Idempotent: the generator is deterministic except for the manifest's ``generated_at``, which defaults to «now»;
a new timestamp changes ``manifest_sha256`` and ingestion would answer ``INTEGRITY_CONFLICT`` on the second
execution (seen on 2026-10-07). So the dataset is generated through the generator's own public entry point
``pipeline.run(config, output, generated_at=…)`` with the timestamp of the published ``ds-6c8ad65b4999``
(``DATASET_GENERATED_AT``): every execution produces byte-identical files and manifest, ingestion answers
``ALREADY_LOADED`` and the runs ``ALREADY_COMPUTED``. The generator is not modified. The role step only (re)sets
grants and the password. A second execution changes no business row.

Environment (Container Apps job, infra/azure/u12/modules/apps.bicep):
    DATABASE_URL     owner connection WITHOUT password (``postgresql://mpa_owner@host:5432/inventory?sslmode=require``)
    PGPASSWORD       owner password (secret; read by libpq, never by this script)
    APP_DB_USER      login of the API (``mpa_app``)
    APP_DB_PASSWORD  its password (secret): stored in PostgreSQL only as a SCRAM-SHA-256 verifier
    RUN_AS_OF        cut of the runs (``2025-12-31``, `DT-058`)
No value of any variable is ever printed.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

SRV = Path(os.environ.get("BOOTSTRAP_ROOT", "/srv"))
BACKEND = SRV / "backend"
#: Tables whose row counts are printed at the end, to compare a first and a second execution.
SUMMARY_TABLES = ("data_loads", "products", "inventory", "consumption", "calculation_runs", "forecasts",
                  "recommendations")
ROLE_NAME = re.compile(r"[a-z_][a-z0-9_]{0,62}")
#: ``generated_at`` of the published ``ds-6c8ad65b4999`` (data/synthetic/output/manifest.json, 2026-09-29).
DATASET_GENERATED_AT = "2026-09-29T22:54:38Z"
#: The generator's public API with its existing ``generated_at`` keyword; same output as ``python -m
#: data.synthetic.generator --output <dir>`` except that the manifest timestamp is fixed.
GENERATE = (
    "import datetime, sys\n"
    "from data.synthetic.config.config import load_config\n"
    "from data.synthetic.generator import pipeline\n"
    "moment = datetime.datetime.strptime(sys.argv[2], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)\n"
    "manifest = pipeline.run(load_config(None), sys.argv[1], generated_at=moment)\n"
    "print(f\"dataset {manifest['dataset_version']} (generator {manifest['generator_version']}) -> {sys.argv[1]}\")\n"
)
SCRAM_ITERATIONS = 4096

Runner = Callable[[Sequence[str], Path], int]


def run(command: Sequence[str], cwd: Path) -> int:
    """Runs one existing entry point; its own output goes straight to the job log."""
    return subprocess.run(list(command), cwd=cwd, check=False).returncode


def steps(dataset_dir: Path, as_of: str, generated_at: str = DATASET_GENERATED_AT) -> list[tuple[str, list[str], Path]]:
    py = sys.executable
    return [
        ("generar el dataset sintético 0.4.0", [py, "-c", GENERATE, str(dataset_dir), generated_at], SRV),
        ("migraciones", [py, "-m", "app.db", "migrate"], BACKEND),
        ("ingesta", [py, "-m", "app.ingestion", str(dataset_dir)], BACKEND),
        ("forecast", [py, "-m", "app.runs", "forecast", "--as-of", as_of], BACKEND),
        ("recomendaciones", [py, "-m", "app.runs", "recommend", "--as-of", as_of], BACKEND),
    ]


def scram_sha256_verifier(password: str, salt: bytes | None = None, iterations: int = SCRAM_ITERATIONS) -> str:
    """PostgreSQL's SCRAM-SHA-256 verifier (RFC 5802/7677), so the clear password never reaches the server."""
    salt = os.urandom(16) if salt is None else salt
    salted = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    client_key = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
    stored_key = hashlib.sha256(client_key).digest()
    server_key = hmac.new(salted, b"Server Key", hashlib.sha256).digest()

    def b64(data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

    return f"SCRAM-SHA-256${iterations}:{b64(salt)}${b64(stored_key)}:{b64(server_key)}"


def role_statements(role: str, owner: str, database: str, verifier: str):
    """Least privilege for the API (docs/12 §6): read-only V1 (`docs/07` §7.1), no DDL, no write."""
    from psycopg import sql  # only in the image; the tests of this module do not need it

    if not ROLE_NAME.fullmatch(role) or not ROLE_NAME.fullmatch(owner) or role == owner:
        raise ValueError("invalid role names")
    r, o = sql.Identifier(role), sql.Identifier(owner)
    return [
        sql.SQL("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = {}) THEN CREATE ROLE {} LOGIN; "
                "END IF; END $$").format(sql.Literal(role), r),
        # CREATE ROLE already defaults to NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION and NOBYPASSRLS; the
        # Azure administrator is not a superuser and PostgreSQL 16 only lets it set what it holds itself.
        sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(r, sql.Literal(verifier)),
        sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), r),
        sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(r),
        sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(r),
        sql.SQL("ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public GRANT SELECT ON TABLES TO {}").format(o, r),
    ]


def ensure_app_role(role: str, password: str) -> None:
    import psycopg

    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        owner, database = conn.execute("SELECT current_user, current_database()").fetchone()
        for statement in role_statements(role, owner, database, scram_sha256_verifier(password)):
            conn.execute(statement)


def summary() -> dict[str, int]:
    import psycopg
    from psycopg import sql

    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        return {table: conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]
                for table in SUMMARY_TABLES}


def main(runner: Runner = run, role_step: Callable[[str, str], None] = ensure_app_role,
         summary_step: Callable[[], dict[str, int]] = summary, environ: dict[str, str] | None = None) -> int:
    env = os.environ if environ is None else environ
    missing = [name for name in ("DATABASE_URL", "PGPASSWORD", "APP_DB_USER", "APP_DB_PASSWORD", "RUN_AS_OF")
               if not env.get(name)]
    if missing:
        print(f"BOOTSTRAP REFUSED: missing {', '.join(missing)}", file=sys.stderr)
        return 2
    authority = env["DATABASE_URL"].split("//", 1)[-1].split("/", 1)[0]
    if "@" in authority and ":" in authority.split("@", 1)[0]:
        print("BOOTSTRAP REFUSED: DATABASE_URL must not carry a password (use PGPASSWORD)", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="dataset-") as tmp:
        dataset_dir = Path(tmp) / "output"
        plan = steps(dataset_dir, env["RUN_AS_OF"], env.get("DATASET_GENERATED_AT") or DATASET_GENERATED_AT)
        for index, (name, command, cwd) in enumerate(plan, start=1):
            print(f"== {index}. {name}", flush=True)
            code = runner(command, cwd)
            if code != 0:
                print(f"BOOTSTRAP FAILED at step {index} ({name}): exit {code}", file=sys.stderr)
                return 1
    print("== 6. rol de la API (solo lectura)", flush=True)
    role_step(env["APP_DB_USER"], env["APP_DB_PASSWORD"])
    print("== 7. resumen (filas por tabla; una segunda ejecución debe dar las mismas)", flush=True)
    for table, count in summary_step().items():
        print(f"  {table}: {count}")
    print("BOOTSTRAP OK", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
