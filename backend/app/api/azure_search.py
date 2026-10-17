"""U15 Azure AI Search and Azure OpenAI embeddings adapters; Entra ID only."""

from __future__ import annotations

import base64
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from typing import Any

from app.genai import DocumentChunk, RetrievedChunk, RetrievalFilters
from app.genai.retrieval import _validate_search

SEARCH_API_VERSION = "2026-04-01"
SEARCH_TOKEN_RESOURCE = "https://search.azure.com"
IDENTITY_API_VERSION = "2019-08-01"
Opener = Callable[..., Any]
Vectorizer = Callable[[str], Sequence[float]]
#: Fields read back from the index; all are retrievable in infra/azure/u15/index.json. ``security_groups`` and
#: ``content_vector`` are not retrievable: the group filter is applied by Search before retrieval and the ACL is never
#: returned to the caller (2026-10-17, Search answered HTTP 400 when it was selected).
SEARCH_SELECT = ("id", "content", "title", "document_id", "section", "document_type", "effective_date", "expiry_date",
                 "source_url", "source_type")


def search_document_key(chunk_id: str) -> str:
    """Search document key of a chunk. Keys only admit letters, digits, '-', '_' and '=' (Microsoft Learn, naming
    rules) and chunk ids use ':' separators, so the key is the URL-safe Base64 of the id, prefixed with 'k' so that it
    never starts with '_'. Deterministic: uploading the corpus again replaces the same documents."""
    return "k" + base64.urlsafe_b64encode(chunk_id.encode("utf-8")).decode("ascii")


def chunk_id_from_key(key: str) -> str:
    """Inverse of ``search_document_key``; ``ValueError`` for any other key."""
    if not isinstance(key, str) or not key.startswith("k"):
        raise ValueError("unexpected document key")
    return base64.b64decode(key[1:].encode("ascii"), altchars=b"-_", validate=True).decode("utf-8")


class SearchUnavailable(RuntimeError):
    """Safe, content-free failure for the optional Azure Search integration."""


class ManagedIdentityToken:
    """Cached token for a user-assigned Container Apps managed identity."""

    def __init__(self, client_id: str, environ: Mapping[str, str], opener: Opener = urllib.request.urlopen) -> None:
        self._client_id = client_id
        self._environ = environ
        self._opener = opener
        self._token: str | None = None
        self._expires_on = 0.0
        self._resource: str | None = None
        self._lock = threading.Lock()

    def get(self, resource: str = SEARCH_TOKEN_RESOURCE) -> str:
        with self._lock:
            if self._token is not None and self._resource == resource and time.time() < self._expires_on - 300:
                return self._token
            endpoint = self._environ.get("IDENTITY_ENDPOINT")
            header = self._environ.get("IDENTITY_HEADER")
            if not endpoint or not header:
                raise SearchUnavailable("managed identity is unavailable")
            query = urllib.parse.urlencode({"resource": resource, "api-version": IDENTITY_API_VERSION,
                                            "client_id": self._client_id})
            request = urllib.request.Request(f"{endpoint}?{query}", headers={"X-IDENTITY-HEADER": header})
            body = _read_json(self._opener, request, 10.0)
            try:
                token = body["access_token"]
                expires_on = float(body["expires_on"])
            except (KeyError, TypeError, ValueError):
                raise SearchUnavailable("managed identity returned an invalid response") from None
            if not isinstance(token, str) or not token:
                raise SearchUnavailable("managed identity returned an invalid response")
            self._token, self._expires_on, self._resource = token, expires_on, resource
            return token


class AzureOpenAIEmbedder:
    """Callable Azure OpenAI v1 embeddings adapter, typically text-embedding-3-small."""

    def __init__(self, endpoint: str, deployment: str, token: Callable[[], str], *, dimensions: int = 1536,
                 opener: Opener = urllib.request.urlopen, timeout_seconds: float = 10.0) -> None:
        if not endpoint.startswith("https://") or not deployment or dimensions <= 0:
            raise ValueError("a valid HTTPS endpoint and embedding deployment are required")
        self._url = endpoint.rstrip("/") + "/openai/v1/embeddings"
        self._deployment = deployment
        self._dimensions = dimensions
        self._token = token
        self._opener = opener
        self._timeout = timeout_seconds

    def __call__(self, text: str) -> tuple[float, ...]:
        if not text.strip() or len(text) > 8000:
            raise ValueError("embedding text must contain 1 to 8000 characters")
        request = urllib.request.Request(
            self._url,
            data=json.dumps({"model": self._deployment, "input": text, "dimensions": self._dimensions},
                            ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"},
            method="POST",
        )
        body = _read_json(self._opener, request, self._timeout)
        try:
            vector = body["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError):
            raise SearchUnavailable("embedding service returned an invalid response") from None
        if not isinstance(vector, list) or not vector or not all(isinstance(item, (int, float)) for item in vector):
            raise SearchUnavailable("embedding service returned an invalid vector")
        if len(vector) != self._dimensions:
            raise SearchUnavailable("embedding service returned an unexpected vector size")
        return tuple(float(item) for item in vector)


class AzureSearchRetriever:
    """Azure hybrid search with mandatory pre-query group and validity filters."""

    def __init__(self, endpoint: str, index_name: str, token: Callable[[], str], vectorize: Vectorizer,
                 *, opener: Opener = urllib.request.urlopen, timeout_seconds: float = 10.0) -> None:
        if not endpoint.startswith("https://") or not index_name:
            raise ValueError("a valid HTTPS endpoint and index name are required")
        self._url = (endpoint.rstrip("/") + "/indexes/" + urllib.parse.quote(index_name, safe="")
                     + "/docs/search?api-version=" + SEARCH_API_VERSION)
        self._token = token
        self._vectorize = vectorize
        self._opener = opener
        self._timeout = timeout_seconds

    def search(self, query: str, filters: RetrievalFilters, top_k: int = 5) -> tuple[RetrievedChunk, ...]:
        _validate_search(query, filters, top_k)
        if not filters.security_groups:
            return ()
        vector = tuple(self._vectorize(query))
        if not vector:
            raise SearchUnavailable("embedding provider returned an empty vector")
        payload = {
            "search": query,
            "vectorFilterMode": "preFilter",
            "filter": build_filter(filters),
            "top": top_k,
            "select": ",".join(SEARCH_SELECT),
            "vectorQueries": [{"kind": "vector", "vector": list(vector), "fields": "content_vector", "k": max(50, top_k)}],
        }
        request = urllib.request.Request(
            self._url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"},
            method="POST",
        )
        body = _read_json(self._opener, request, self._timeout)
        values = body.get("value") if isinstance(body, dict) else None
        if not isinstance(values, list):
            raise SearchUnavailable("search returned an invalid response")
        results: list[RetrievedChunk] = []
        for item in values:
            try:
                chunk = DocumentChunk(
                    id=chunk_id_from_key(item["id"]), content=item["content"], title=item["title"], document_id=item["document_id"],
                    section=item["section"], document_type=item["document_type"],
                    effective_date=_date(item.get("effective_date")), expiry_date=_date(item.get("expiry_date")),
                    security_groups=(), source_url=item["source_url"],
                    source_type=item["source_type"],
                )
                results.append(RetrievedChunk(chunk, float(item["@search.score"])))
            except (KeyError, TypeError, ValueError):
                raise SearchUnavailable("search returned an invalid document") from None
        return tuple(results)


class AzureSearchIndexProvisioner:
    """Create/update an index definition using a separately authorized Entra identity."""

    def __init__(self, endpoint: str, token: Callable[[], str], *, opener: Opener = urllib.request.urlopen,
                 timeout_seconds: float = 10.0) -> None:
        if not endpoint.startswith("https://"):
            raise ValueError("a valid HTTPS endpoint is required")
        self._endpoint = endpoint.rstrip("/")
        self._token = token
        self._opener = opener
        self._timeout = timeout_seconds

    def create_or_update(self, definition: Mapping[str, Any]) -> Any:
        index_name = definition.get("name")
        if not isinstance(index_name, str) or not index_name:
            raise ValueError("index definition must include a name")
        url = (self._endpoint + "/indexes/" + urllib.parse.quote(index_name, safe="")
               + "?api-version=" + SEARCH_API_VERSION)
        request = urllib.request.Request(
            url,
            data=json.dumps(definition, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"},
            method="PUT",
        )
        return _read_json(self._opener, request, self._timeout)


class AzureSearchIndexer:
    """Upload vectorized chunks; requires Search Index Data Contributor, never used by query flow."""

    def __init__(self, endpoint: str, index_name: str, token: Callable[[], str], vectorize: Vectorizer,
                 *, opener: Opener = urllib.request.urlopen, timeout_seconds: float = 10.0) -> None:
        if not endpoint.startswith("https://") or not index_name:
            raise ValueError("a valid HTTPS endpoint and index name are required")
        self._url = (endpoint.rstrip("/") + "/indexes/" + urllib.parse.quote(index_name, safe="")
                     + "/docs/index?api-version=" + SEARCH_API_VERSION)
        self._token = token
        self._vectorize = vectorize
        self._opener = opener
        self._timeout = timeout_seconds

    def upload(self, chunks: Sequence[DocumentChunk]) -> int:
        if not chunks:
            return 0
        if len(chunks) > 1000:
            raise ValueError("Search upload batches cannot exceed 1000 documents")
        actions = []
        for chunk in chunks:
            if chunk.source_type != "SYNTHETIC":
                raise ValueError("U15 only indexes synthetic documents")
            if not chunk.security_groups or any(
                not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", group) for group in chunk.security_groups
            ):
                raise ValueError("every indexed document must have valid security groups")
            vector = tuple(self._vectorize(chunk.content))
            if not vector:
                raise SearchUnavailable("embedding provider returned an empty vector")
            actions.append({
                "@search.action": "upload", "id": search_document_key(chunk.id), "content": chunk.content,
                "content_vector": list(vector), "title": chunk.title, "document_id": chunk.document_id,
                "section": chunk.section, "document_type": chunk.document_type,
                "effective_date": _iso_date(chunk.effective_date), "expiry_date": _iso_date(chunk.expiry_date),
                "security_groups": list(chunk.security_groups), "source_url": chunk.source_url,
                "source_type": chunk.source_type,
            })
        request = urllib.request.Request(
            self._url,
            data=json.dumps({"value": actions}, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"},
            method="POST",
        )
        body = _read_json(self._opener, request, self._timeout)
        results = body.get("value") if isinstance(body, dict) else None
        if not isinstance(results, list) or len(results) != len(actions) or any(
            not isinstance(item, dict) or item.get("status") is not True for item in results
        ):
            raise SearchUnavailable("one or more documents could not be indexed")
        return len(results)


def build_filter(filters: RetrievalFilters) -> str:
    """Build an OData filter that Search applies before lexical and vector retrieval."""
    if not filters.security_groups:
        return "false"
    groups = ",".join(filters.security_groups)
    instant = filters.as_of.isoformat() + "T00:00:00Z"
    return (
        f"security_groups/any(g: search.in(g, '{groups}', ',')) and "
        f"(effective_date eq null or effective_date le {instant}) and "
        f"(expiry_date eq null or expiry_date ge {instant})"
    )


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value[:10]) if value else None


def _iso_date(value: date | None) -> str | None:
    return value.isoformat() + "T00:00:00Z" if value else None


def _read_json(opener: Opener, request: urllib.request.Request, timeout: float) -> Any:
    try:
        with opener(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise SearchUnavailable(f"Azure AI Search HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SearchUnavailable(f"Azure AI Search {type(exc).__name__}") from None
    try:
        return json.loads(raw)
    except ValueError:
        raise SearchUnavailable("Azure AI Search returned invalid JSON") from None
