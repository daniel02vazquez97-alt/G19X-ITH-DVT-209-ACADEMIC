"""Smoke check of the local Docker system (U7, `DT-095`); standard library only.

Run from the repository root once ``docker compose -f infra/docker-compose.yml --profile app up`` is
healthy::

    python infra/docker/smoke.py

It goes through the same origin the browser uses (``frontend`` on 127.0.0.1:8080, ``/api`` proxied to
``api``), so a pass shows the chain frontend → API → PostgreSQL with the dataset, the forecast and the
recommendations loaded. The token is one of the fictitious development identities of ``.env.example``
(override with ``SMOKE_TOKEN``); it is never printed. Exit status 0 when every check passes, 1 otherwise.

U11 (`DT-099`): with ``--entra`` it checks the isolated ``u11-entra-dev`` project instead
(infra/docker-compose.entra-dev.yml, infra/azure/entra/README.md)::

    python infra/docker/smoke.py --entra

There the API runs with ``APP_ENV=dev`` and only accepts Microsoft Entra ID access tokens, which this script
never has: it checks the same chain up to authentication (health, SPA, proxy), that development tokens and
forged tokens are now rejected (401), and that the SPA bundle was built for Entra ID with the identifiers of
``tmp/u11-evidence/entra-dev.env`` (override with ``SMOKE_ENTRA_ENV``). Data behind authentication is checked by
the real test (``/acceso``), not here.

U12 (`DT-100`): against Azure, ``SMOKE_FRONTEND_URL=https://<frontend>`` and ``SMOKE_API_URL=none`` (the API has no
public ingress)::

    SMOKE_FRONTEND_URL=https://ca-mpa-dev-frontend.<domain> SMOKE_API_URL=none SMOKE_TIMEOUT=120 python infra/docker/smoke.py --entra
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

FRONTEND = os.environ.get("SMOKE_FRONTEND_URL", "http://127.0.0.1:8080")
API = os.environ.get("SMOKE_API_URL", "http://127.0.0.1:8000")
ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"
# Seconds per request; in Azure the first request may wake apps scaled to zero (U12): SMOKE_TIMEOUT=120.
TIMEOUT = float(os.environ.get("SMOKE_TIMEOUT", "10"))
ENTRA_ENV = Path(os.environ.get("SMOKE_ENTRA_ENV", Path(__file__).resolve().parents[2] / "tmp" / "u11-evidence" / "entra-dev.env"))
# An RS256-shaped token with a kid and no valid signature: APP_ENV=dev must answer 401 without crashing.
FORGED_JWT = "eyJhbGciOiJSUzI1NiIsImtpZCI6InNtb2tlIiwidHlwIjoiSldUIn0.eyJzdWIiOiJzbW9rZSJ9.c21va2U"


def example_token() -> str:
    """The first development token of `.env.example`; every checked endpoint accepts any role."""
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        if line.startswith("DEV_AUTH_IDENTITIES="):
            identities = json.loads(line.split("=", 1)[1])
            return next(iter(identities))
    raise SystemExit("DEV_AUTH_IDENTITIES not found in .env.example")


def get(url: str, token: str | None = None) -> tuple[int, bytes]:
    request = urllib.request.Request(url)
    if token is not None:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def entra_identifiers() -> dict[str, str]:
    """ENTRA_TENANT_ID, ENTRA_API_CLIENT_ID and ENTRA_SPA_CLIENT_ID (identifiers, not secrets)."""
    values = {}
    for line in ENTRA_ENV.read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def entra_checks(check) -> None:
    """U11: the chain up to authentication, with the API in APP_ENV=dev (see the module docstring)."""
    ids = entra_identifiers()
    status, _ = get(f"{FRONTEND}/api/v1/me", example_token())
    check("proxy /api: a development token is rejected (APP_ENV=dev)", status == 401, f"HTTP {status}")
    status, _ = get(f"{FRONTEND}/api/v1/products", FORGED_JWT)
    check("proxy /api: a forged RS256 token is rejected", status == 401, f"HTTP {status}")
    status, _ = get(f"{FRONTEND}/api/v1/runs/1")
    check("proxy /api/v1/runs/1 without token is rejected (401)", status == 401, f"HTTP {status}")
    status, html = get(f"{FRONTEND}/")
    scripts = re.findall(rb'src="(/assets/[^"]+\.js)"', html)
    bundle = b"".join(get(f"{FRONTEND}{src.decode()}")[1] for src in scripts)
    expected = [ids.get("ENTRA_SPA_CLIENT_ID", "?"), f"api://{ids.get('ENTRA_API_CLIENT_ID', '?')}/access_as_user"]
    check("SPA built for Entra ID with the identifiers of entra-dev.env",
          bool(scripts) and all(value.encode() in bundle for value in expected), f"{len(scripts)} script(s)")


def main() -> int:
    entra = "--entra" in sys.argv[1:] or os.environ.get("SMOKE_MODE") == "entra"
    token = os.environ.get("SMOKE_TOKEN") or example_token()
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"{'OK  ' if ok else 'FAIL'} {name}{f' — {detail}' if detail else ''}")
        if not ok:
            failures.append(name)

    if API.lower() == "none":
        # U12 (DT-100): in Azure the API has internal ingress only; it is reached through the frontend's /api proxy.
        print("SKIP api /health — API interna (sin ingress público): se comprueba a través del proxy /api")
    else:
        status, body = get(f"{API}/health")
        check("api /health", status == 200 and json.loads(body).get("status") == "ok", f"HTTP {status}")

    status, body = get(f"{FRONTEND}/")
    check("frontend /", status == 200 and b'id="root"' in body, f"HTTP {status}")
    status, body = get(f"{FRONTEND}/productos")
    check("frontend deep route served by the SPA", status == 200 and b'id="root"' in body, f"HTTP {status}")

    status, _ = get(f"{FRONTEND}/api/v1/me")
    check("proxy /api without token is rejected (401)", status == 401, f"HTTP {status}")
    if entra:
        entra_checks(check)
        print("SMOKE OK (entra-dev)" if not failures else f"SMOKE FAILED: {len(failures)} check(s)")
        return 0 if not failures else 1
    status, body = get(f"{FRONTEND}/api/v1/me", token)
    check("proxy /api/v1/me with a development token", status == 200, f"HTTP {status}")

    status, body = get(f"{FRONTEND}/api/v1/recommendations?page_size=5", token)
    recommendations = json.loads(body) if status == 200 else {}
    total = recommendations.get("total", 0)
    check("recommendations persisted in PostgreSQL", status == 200 and total > 0, f"HTTP {status}, total {total}")

    status, body = get(f"{FRONTEND}/api/v1/forecasts?page_size=5", token)
    forecasts = json.loads(body) if status == 200 else {}
    check("forecasts persisted in PostgreSQL", status == 200 and forecasts.get("total", 0) > 0,
          f"HTTP {status}, total {forecasts.get('total', 0)}")

    items = recommendations.get("items") or []
    if items:
        status, _ = get(f"{FRONTEND}/api/v1/recommendations/{items[0]['id']}/explanation", token)
        check("explanation of a recommendation (U6)", status == 200, f"HTTP {status}")
    else:
        check("explanation of a recommendation (U6)", False, "no recommendation to explain")

    print("SMOKE OK" if not failures else f"SMOKE FAILED: {len(failures)} check(s)")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
