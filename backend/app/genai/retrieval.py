"""U15 document retrieval contracts and an in-memory hybrid implementation."""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol

TOKEN_PATTERN = re.compile(r"[\w.-]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    id: str
    content: str
    title: str
    document_id: str
    section: str
    document_type: str
    effective_date: date | None
    expiry_date: date | None
    security_groups: tuple[str, ...]
    source_url: str
    source_type: str = "SYNTHETIC"
    content_vector: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class RetrievalFilters:
    security_groups: tuple[str, ...]
    as_of: date


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


class DocumentRetriever(Protocol):
    def search(self, query: str, filters: RetrievalFilters, top_k: int = 5) -> tuple[RetrievedChunk, ...]: ...


Vectorizer = Callable[[str], Sequence[float]]


class InMemoryDocumentRetriever:
    """No-network retriever for local use and tests; combines lexical and vector rankings."""

    def __init__(self, documents: Sequence[DocumentChunk], vectorize: Vectorizer) -> None:
        self._documents = tuple(documents)
        self._vectorize = vectorize

    def search(self, query: str, filters: RetrievalFilters, top_k: int = 5) -> tuple[RetrievedChunk, ...]:
        _validate_search(query, filters, top_k)
        if not filters.security_groups:
            return ()
        allowed = set(filters.security_groups)
        eligible = [
            doc for doc in self._documents
            if allowed.intersection(doc.security_groups)
            and (doc.effective_date is None or doc.effective_date <= filters.as_of)
            and (doc.expiry_date is None or doc.expiry_date >= filters.as_of)
        ]
        query_tokens = set(_tokens(query))
        lexical = sorted(
            eligible,
            key=lambda doc: (len(query_tokens.intersection(_tokens(doc.content))), doc.id),
            reverse=True,
        )
        query_vector = tuple(self._vectorize(query))
        vector = sorted(eligible, key=lambda doc: (_cosine(query_vector, doc.content_vector), doc.id), reverse=True)
        lexical_ranks = {
            doc.id: rank for rank, doc in enumerate(lexical, 1) if query_tokens.intersection(_tokens(doc.content))
        }
        vector_ranks = {doc.id: rank for rank, doc in enumerate(vector, 1) if doc.content_vector and query_vector}
        scores: list[RetrievedChunk] = []
        for doc in eligible:
            score = (1 / (60 + lexical_ranks[doc.id]) if doc.id in lexical_ranks else 0) + (
                1 / (60 + vector_ranks[doc.id]) if doc.id in vector_ranks else 0
            )
            if score:
                scores.append(RetrievedChunk(doc, score))
        return tuple(sorted(scores, key=lambda item: (-item.score, item.chunk.id))[:top_k])


def _validate_search(query: str, filters: RetrievalFilters, top_k: int) -> None:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must not be empty")
    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20")
    if any(not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", group) for group in filters.security_groups):
        raise ValueError("security group identifiers contain unsupported characters")


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(token.casefold() for token in TOKEN_PATTERN.findall(text))


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0
