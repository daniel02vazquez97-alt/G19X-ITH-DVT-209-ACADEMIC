"""Smoke check of the local Docker system (U7, `DT-095`); standard library only.

Run from the repository root once ``docker compose -f infra/docker-compose.yml --profile app up`` is
healthy::

    python infra/docker/smoke.py

It goes through the same origin the browser uses (``frontend`` on 127.0.0.1:8080, ``/api`` proxied to
``api``), so a pass shows the chain frontend → API → PostgreSQL with the dataset, the forecast and the
recommendations loaded. The token is one of the fictitious development identities of ``.env.example``
(override with ``SMOKE_TOKEN``); it is never printed. Exit status 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

FRONTEND = os.environ.get("SMOKE_FRONTEND_URL", "http://127.0.0.1:8080")
API = os.environ.get("SMOKE_API_URL", "http://127.0.0.1:8000")
ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"


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
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def main() -> int:
    token = os.environ.get("SMOKE_TOKEN") or example_token()
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"{'OK  ' if ok else 'FAIL'} {name}{f' — {detail}' if detail else ''}")
        if not ok:
            failures.append(name)

    status, body = get(f"{API}/health")
    check("api /health", status == 200 and json.loads(body).get("status") == "ok", f"HTTP {status}")

    status, body = get(f"{FRONTEND}/")
    check("frontend /", status == 200 and b'id="root"' in body, f"HTTP {status}")
    status, body = get(f"{FRONTEND}/productos")
    check("frontend deep route served by the SPA", status == 200 and b'id="root"' in body, f"HTTP {status}")

    status, _ = get(f"{FRONTEND}/api/v1/me")
    check("proxy /api without token is rejected (401)", status == 401, f"HTTP {status}")
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
