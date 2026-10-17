"""U15 (`DT-094`): index, synthetic corpus and verification of Azure AI Search with the owner's Entra ID session.

Run by ``infra/azure/deploy-u15.ps1`` (stages Preflight, Index, Load and Verify) from the repository root::

    python infra/azure/u15/search_setup.py status --search-endpoint https://<service>.search.windows.net
    python infra/azure/u15/search_setup.py index  --search-endpoint ...
    python infra/azure/u15/search_setup.py load   --search-endpoint ... --openai-endpoint ... --embedding-deployment ...
    python infra/azure/u15/search_setup.py verify --search-endpoint ... --openai-endpoint ... --embedding-deployment ...
                                                  [--evidence tmp/u15-evidence/u15-verify.json]

It reuses the adapters of ``backend/app/api/azure_search.py`` and only loads ``knowledge/search_corpus/`` (synthetic).
Tokens come from the signed-in Azure CLI (``az account get-access-token``): they stay in memory and are never printed,
logged or written. ``verify`` uses the owner's identity, not ``id-mpa-dev-runtime``: it proves the index, the corpus,
the embeddings and the group filter, not the API (which is not wired to Search yet). Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.api.azure_search import (  # noqa: E402
    SEARCH_API_VERSION,
    SEARCH_TOKEN_RESOURCE,
    AzureOpenAIEmbedder,
    AzureSearchIndexer,
    AzureSearchIndexProvisioner,
    AzureSearchRetriever,
    SearchUnavailable,
)
from app.genai import RetrievalFilters  # noqa: E402
from app.genai.corpus import load_markdown_corpus  # noqa: E402
from app.genai.evaluation import evaluate_retriever  # noqa: E402

INDEX_FILE = ROOT / "infra" / "azure" / "u15" / "index.json"
MANIFEST = ROOT / "knowledge" / "search_corpus" / "manifest.json"
EVALUATION = ROOT / "knowledge" / "search_corpus" / "evaluation.json"
OPENAI_TOKEN_RESOURCE = "https://cognitiveservices.azure.com"
#: A group that no document carries: a search with it must return nothing (the filter is applied by Search).
NO_ACCESS_GROUP = "U15-SIN-ACCESO"
SEARCH_ENDPOINT = re.compile(r"^https://[a-z0-9][a-z0-9-]{0,58}[a-z0-9]\.search\.windows\.net/?$")
Runner = Callable[..., Any]
Opener = Callable[..., Any]


class AzCliToken:
    """Token of the signed-in Azure CLI for one resource, cached for 30 minutes; never printed."""

    def __init__(self, resource: str, *, run: Runner = subprocess.run, az: str | None = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._resource = resource
        self._run = run
        self._az = az
        self._clock = clock
        self._token: str | None = None
        self._at = 0.0

    def __call__(self) -> str:
        if self._token is not None and self._clock() - self._at < 1800:
            return self._token
        az = self._az or shutil.which("az")
        if not az:
            raise SearchUnavailable("Azure CLI (az) not found")
        result = self._run([az, "account", "get-access-token", "--resource", self._resource, "--query", "accessToken",
                            "--output", "tsv"], capture_output=True, text=True, timeout=120, check=False)
        token = (result.stdout or "").strip()
        if result.returncode != 0 or not token or any(c.isspace() for c in token):
            raise SearchUnavailable(f"az account get-access-token failed for {self._resource}")
        self._token, self._at = token, self._clock()
        return token


class DiagnosticOpener:
    """``urlopen`` that keeps the service's error message (never headers or tokens) so the owner sees why a call
    failed; the adapters only report the HTTP status."""

    def __init__(self, opener: Opener = urllib.request.urlopen) -> None:
        self._opener = opener
        self.last_error: str | None = None

    def __call__(self, request: Any, *, timeout: float) -> Any:
        try:
            return self._opener(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            self.last_error = error_detail(exc)
            raise


def error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", "replace")
    except (OSError, ValueError):  # a missing body only loses the detail
        body = ""
    message: Any = body
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict) and isinstance(parsed.get("error"), dict):
            message = parsed["error"].get("message") or body
    except ValueError:
        pass
    host = urllib.parse.urlsplit(exc.geturl() or "").hostname or "?"
    return f"{host} HTTP {exc.code}: {' '.join(str(message).split())[:400]}"


class PacedEmbedder:
    """Spaces embedding calls (the deployment allows 10 requests every 10 s) and retries HTTP 429 a few times."""

    def __init__(self, embed: Callable[[str], Sequence[float]], *, min_interval: float = 1.2, retries: int = 3,
                 backoff: float = 10.0, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._embed = embed
        self._min_interval = min_interval
        self._retries = retries
        self._backoff = backoff
        self._sleep = sleep
        self._clock = clock
        self._last: float | None = None
        self.calls = 0

    def __call__(self, text: str) -> Sequence[float]:
        for attempt in range(self._retries + 1):
            if self._last is not None:
                wait = self._last + self._min_interval - self._clock()
                if wait > 0:
                    self._sleep(wait)
            self._last = self._clock()
            self.calls += 1
            try:
                return self._embed(text)
            except SearchUnavailable as exc:
                if "HTTP 429" not in str(exc) or attempt == self._retries:
                    raise
                self._sleep(self._backoff * (attempt + 1))
        raise AssertionError("unreachable")


def index_definition() -> dict[str, Any]:
    definition = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    if not isinstance(definition, dict) or not isinstance(definition.get("name"), str):
        raise ValueError("index.json must define a named index")
    return definition


def corpus_groups(chunks: Sequence[Any]) -> tuple[str, ...]:
    return tuple(sorted({group for chunk in chunks for group in chunk.security_groups}))


def index_status(endpoint: str, index_name: str, token: Callable[[], str], *,
                 opener: Opener = urllib.request.urlopen) -> int | None:
    """Documents in the index, or ``None`` when it does not exist. Read only."""
    url = (endpoint.rstrip("/") + "/indexes/" + urllib.parse.quote(index_name, safe="")
           + "/docs/$count?api-version=" + SEARCH_API_VERSION)
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token()}", "Accept": "text/plain"})
    try:
        with opener(request, timeout=30.0) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise SearchUnavailable(f"Azure AI Search HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SearchUnavailable(f"Azure AI Search {type(exc).__name__}") from None
    try:
        return int(raw.decode("utf-8-sig").strip())
    except ValueError:
        raise SearchUnavailable("Azure AI Search returned an invalid document count") from None


def verify(endpoint: str, index_name: str, search_token: Callable[[], str], embed: Callable[[str], Sequence[float]],
           *, today: date, opener: Opener = urllib.request.urlopen) -> dict[str, Any]:
    """Document count, fixed evaluation set and the group filter; returns identifiers and counts only."""
    chunks = load_markdown_corpus(MANIFEST)
    cases = json.loads(EVALUATION.read_text(encoding="utf-8"))["cases"]
    groups = corpus_groups(chunks)
    count = index_status(endpoint, index_name, search_token, opener=opener)
    retriever = AzureSearchRetriever(endpoint, index_name, search_token, embed, opener=opener, timeout_seconds=30.0)
    report = evaluate_retriever(retriever, cases, RetrievalFilters(groups, today))
    blocked = retriever.search(cases[0]["query"], RetrievalFilters((NO_ACCESS_GROUP,), today))
    hits = sum(1 for item in report if item.hit)
    checks = {
        "index exists with one document per corpus chunk": count == len(chunks),
        "every evaluation query returns documents": all(item.retrieved_document_ids for item in report),
        "a group without documents gets nothing (filter applied by Search)": not blocked,
    }
    return {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "identity": "owner (Azure CLI session), not id-mpa-dev-runtime",
        "index": index_name,
        "documents": count,
        "expectedChunks": len(chunks),
        "groups": list(groups),
        "cases": [{"query": item.query, "expected": list(item.expected_document_ids),
                   "retrieved": list(item.retrieved_document_ids), "hit": item.hit} for item in report],
        "hits": hits,
        "hitRate": round(hits / len(report), 3) if report else 0.0,
        "hitRateNote": "informative only; no business threshold (DT-094, evaluation.json)",
        "checks": checks,
        "checksFailed": sum(1 for ok in checks.values() if not ok),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("status", "index", "load", "verify"))
    parser.add_argument("--search-endpoint", required=True)
    parser.add_argument("--openai-endpoint")
    parser.add_argument("--embedding-deployment")
    parser.add_argument("--evidence")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not SEARCH_ENDPOINT.match(args.search_endpoint):
        print("ERROR: --search-endpoint must be https://<service>.search.windows.net")
        return 2
    needs_embeddings = args.command in ("load", "verify")
    if needs_embeddings and (not args.openai_endpoint or not args.openai_endpoint.startswith("https://")
                             or not args.embedding_deployment):
        print("ERROR: load and verify need --openai-endpoint (https) and --embedding-deployment")
        return 2
    endpoint = args.search_endpoint.rstrip("/")
    search_token = AzCliToken(SEARCH_TOKEN_RESOURCE)
    opener = DiagnosticOpener()
    try:
        definition = index_definition()
        name = definition["name"]
        embed = None
        if needs_embeddings:
            embed = PacedEmbedder(AzureOpenAIEmbedder(args.openai_endpoint, args.embedding_deployment,
                                                      AzCliToken(OPENAI_TOKEN_RESOURCE), opener=opener,
                                                      timeout_seconds=30.0))
        if args.command == "status":
            count = index_status(endpoint, name, search_token, opener=opener)
            print(f"STATUS indice {name}: " + ("no existe" if count is None else f"{count} documentos"))
        elif args.command == "index":
            AzureSearchIndexProvisioner(endpoint, search_token, opener=opener,
                                        timeout_seconds=30.0).create_or_update(definition)
            print(f"INDEX OK {name}")
        elif args.command == "load":
            chunks = load_markdown_corpus(MANIFEST)
            loaded = AzureSearchIndexer(endpoint, name, search_token, embed, opener=opener,
                                        timeout_seconds=30.0).upload(chunks)
            print(f"LOAD OK {loaded} fragmentos sinteticos en {name} ({embed.calls} llamadas de embeddings)")
        else:
            result = verify(endpoint, name, search_token, embed, today=date.today(), opener=opener)
            for case in result["cases"]:
                mark = "OK  " if case["hit"] else "NO  "
                print(f"  {mark} {case['query']} -> {', '.join(case['retrieved']) or '(nada)'}")
            for text, ok in result["checks"].items():
                print(f"  {'OK    ' if ok else 'FALLO '} {text}")
            print(f"  INFO   aciertos {result['hits']}/{len(result['cases'])} (informativo, sin umbral de negocio)")
            if args.evidence:
                path = Path(args.evidence)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            if result["checksFailed"]:
                print(f"VERIFY FALLO ({result['checksFailed']})")
                return 1
            print("VERIFY OK")
    except (SearchUnavailable, ValueError, OSError) as exc:
        print(f"ERROR: {exc}")
        if opener.last_error:
            print(f"  detalle del servicio: {opener.last_error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
