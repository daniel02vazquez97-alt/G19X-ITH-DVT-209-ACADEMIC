"""U15b (`DT-103`): assembly of the documentary assistant of ``GET /api/v1/assistant/answer``.

* Retriever: Azure AI Search with the managed identity (``SEARCH_PROVIDER=azure``, U15) and, as fallback, the
  in-memory retriever over the synthetic corpus shipped with the API; only the local one with
  ``SEARCH_PROVIDER=local`` (default). If neither is available, the endpoint answers 503.
* Chat call: the U13 Azure OpenAI deployment (``GENAI_PROVIDER=azure-openai``) or none, in which case the answer is
  the list of fragments.
* Groups: every role of the API reads the demo group of the synthetic corpus (``U15-DEMO-READERS``). Real Entra ID
  groups wait for a real corpus (``ASSUMPTION-008``); the filter is still applied by the retriever before any text
  reaches the model.

No key: Search and Azure OpenAI use the token of ``id-mpa-dev-runtime``. Errors never contain tokens or content.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from app.genai import DocumentRetriever, InMemoryDocumentRetriever, RetrievalFilters
from app.genai.assistant import AssistantAnswer, Complete, answer_question, clean_question
from app.genai.corpus import load_markdown_corpus

from .auth import ROLES

#: Synthetic corpus of U15: ``knowledge/search_corpus`` in the repository and ``/srv/knowledge/search_corpus`` in the
#: API image (``infra/docker/backend.Dockerfile``).
CORPUS_MANIFEST = Path(__file__).resolve().parents[3] / "knowledge" / "search_corpus" / "manifest.json"
DEMO_GROUP = "U15-DEMO-READERS"
ROLE_GROUPS: Mapping[str, tuple[str, ...]] = {role: (DEMO_GROUP,) for role in ROLES}
TOP_K = 4
AZURE_RETRIEVER = "azure-ai-search"
LOCAL_RETRIEVER = "local"
LOCAL_FALLBACK = "local (respaldo)"


class AssistantUnavailable(RuntimeError):
    """No retriever could answer; the endpoint maps it to 503."""


@dataclass(frozen=True)
class AzureSearchSettings:
    search_endpoint: str  # https://<service>.search.windows.net
    index: str
    openai_endpoint: str  # embeddings: the U13 account
    embedding_deployment: str
    client_id: str  # user-assigned identity of the API
    timeout_seconds: float = 10.0


class Assistant:
    def __init__(self, primary: DocumentRetriever | None, primary_name: str, fallback: DocumentRetriever | None,
                 complete: Complete | None, generator: str | None) -> None:
        if primary is None and fallback is None:
            raise ValueError("the assistant needs a retriever")
        self._primary = primary
        self._primary_name = primary_name
        self._fallback = fallback
        self._complete = complete
        self.generator = generator

    def ask(self, question: str, roles: frozenset[str], as_of: date) -> AssistantAnswer:
        question = clean_question(question)  # ValueError -> 422, before any retrieval
        groups = tuple(sorted({group for role in roles for group in ROLE_GROUPS.get(role, ())}))
        filters = RetrievalFilters(groups, as_of)
        results, retriever = None, self._primary_name
        if self._primary is not None:
            try:
                results = self._primary.search(question, filters, TOP_K)
            except Exception:  # any failure of the remote retriever falls back to the local one
                if self._fallback is None:
                    raise AssistantUnavailable("retriever unavailable") from None
        if results is None:
            results = self._fallback.search(question, filters, TOP_K)
            retriever = LOCAL_FALLBACK if self._primary is not None else LOCAL_RETRIEVER
        return answer_question(question, results, self._complete, self.generator, retriever)


def local_retriever(manifest: Path = CORPUS_MANIFEST) -> InMemoryDocumentRetriever | None:
    """Lexical in-memory retriever over the synthetic corpus, or ``None`` when the corpus is not shipped."""
    if not manifest.is_file():
        return None
    return InMemoryDocumentRetriever(load_markdown_corpus(manifest), lambda _text: ())


def azure_retriever(config: AzureSearchSettings, environ: Mapping[str, str]) -> DocumentRetriever:
    from .azure_search import OPENAI_TOKEN_RESOURCE, AzureOpenAIEmbedder, AzureSearchRetriever, ManagedIdentityToken

    search_token = ManagedIdentityToken(config.client_id, environ)
    openai_token = ManagedIdentityToken(config.client_id, environ)
    embed = AzureOpenAIEmbedder(config.openai_endpoint, config.embedding_deployment,
                                lambda: openai_token.get(OPENAI_TOKEN_RESOURCE), timeout_seconds=config.timeout_seconds)
    return AzureSearchRetriever(config.search_endpoint, config.index, search_token.get, embed,
                                timeout_seconds=config.timeout_seconds)


def build_assistant(settings: Any, complete: Complete | None, generator: str | None,
                    environ: Mapping[str, str] | None = None,
                    local: Callable[[], DocumentRetriever | None] = local_retriever) -> Assistant | None:
    """The assistant for these settings, or ``None`` when there is no retriever at all (503)."""
    fallback = local()
    if settings.search is not None:
        primary = azure_retriever(settings.search, os.environ if environ is None else environ)
        return Assistant(primary, AZURE_RETRIEVER, fallback, complete, generator)
    if fallback is None:
        return None
    return Assistant(None, LOCAL_RETRIEVER, fallback, complete, generator)
