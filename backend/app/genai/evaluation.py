"""Small, reproducible relevance evaluation for a ``DocumentRetriever`` implementation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .retrieval import DocumentRetriever, RetrievalFilters


@dataclass(frozen=True, slots=True)
class RetrievalEvaluation:
    query: str
    expected_document_ids: tuple[str, ...]
    retrieved_document_ids: tuple[str, ...]
    hit: bool


def evaluate_retriever(
    retriever: DocumentRetriever,
    cases: Iterable[Mapping[str, object]],
    filters: RetrievalFilters,
    *,
    top_k: int = 5,
) -> tuple[RetrievalEvaluation, ...]:
    """Run a fixed query set and report document-level hits; this does not set a business threshold."""
    results: list[RetrievalEvaluation] = []
    for case in cases:
        query = case.get("query")
        expected = case.get("expected_document_ids")
        if not isinstance(query, str) or not isinstance(expected, list) or not all(
            isinstance(item, str) for item in expected
        ):
            raise ValueError("invalid retrieval evaluation case")
        found = tuple(result.chunk.document_id for result in retriever.search(query, filters, top_k))
        results.append(RetrievalEvaluation(query, tuple(expected), found, bool(set(expected).intersection(found))))
    return tuple(results)
