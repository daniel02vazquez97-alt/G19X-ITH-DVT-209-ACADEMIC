from __future__ import annotations

import json
import unittest
from datetime import date
from typing import Any

from app.api.azure_search import (
    AzureOpenAIEmbedder,
    AzureSearchIndexer,
    AzureSearchIndexProvisioner,
    AzureSearchRetriever,
    SearchUnavailable,
    build_filter,
)
from app.genai import DocumentChunk, RetrievalFilters


class Response:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = json.dumps(body).encode()

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class AzureSearchTest(unittest.TestCase):
    def test_embedding_adapter_uses_v1_and_does_not_log_or_require_keys(self) -> None:
        captured: list[Any] = []

        def opener(request: Any, *, timeout: float) -> Response:
            captured.append(request)
            return Response({"data": [{"embedding": [0.25, -0.5]}]})

        embedder = AzureOpenAIEmbedder("https://aoai.example.net", "embed-small", lambda: "test-token",
                                       dimensions=2, opener=opener)
        self.assertEqual(embedder("consulta sintética"), (0.25, -0.5))
        self.assertTrue(captured[0].full_url.endswith("/openai/v1/embeddings"))
        self.assertEqual(captured[0].get_header("Authorization"), "Bearer test-token")
        self.assertEqual(json.loads(captured[0].data), {
            "model": "embed-small", "input": "consulta sintética", "dimensions": 2,
        })

    def test_index_definition_uses_a_separate_privileged_identity(self) -> None:
        captured: list[Any] = []

        def opener(request: Any, *, timeout: float) -> Response:
            captured.append(request)
            return Response({"name": "u15-demo-documents"})

        provisioner = AzureSearchIndexProvisioner("https://search.example.net", lambda: "admin-token",
                                                  opener=opener)
        result = provisioner.create_or_update({"name": "u15-demo-documents", "fields": []})
        self.assertEqual(result["name"], "u15-demo-documents")
        self.assertEqual(captured[0].get_method(), "PUT")
        self.assertEqual(captured[0].get_header("Authorization"), "Bearer admin-token")

    def test_indexer_upload_requires_acl_and_persists_vector_and_citation(self) -> None:
        captured: list[Any] = []

        def opener(request: Any, *, timeout: float) -> Response:
            captured.append(request)
            return Response({"value": [{"key": "c1", "status": True, "statusCode": 201}]})

        indexer = AzureSearchIndexer("https://search.example.net", "u15-demo", lambda: "write-token",
                                     lambda _: (0.5, 0.25), opener=opener)
        chunk = DocumentChunk("c1", "content", "title", "doc", "section", "guide", None, None,
                              ("PLANNER",), "demo.md#section")
        self.assertEqual(indexer.upload((chunk,)), 1)
        action = json.loads(captured[0].data)["value"][0]
        self.assertEqual(action["@search.action"], "upload")
        self.assertEqual(action["content_vector"], [0.5, 0.25])
        self.assertEqual(action["security_groups"], ["PLANNER"])
        self.assertEqual(action["source_url"], "demo.md#section")

    def test_indexer_rejects_documents_without_group_metadata(self) -> None:
        indexer = AzureSearchIndexer("https://search.example.net", "u15-demo", lambda: "token", lambda _: (1.0,))
        chunk = DocumentChunk("c1", "content", "title", "doc", "section", "guide", None, None, (), "demo.md")
        with self.assertRaisesRegex(ValueError, "security group"):
            indexer.upload((chunk,))

    def test_indexer_rejects_unapproved_source_types_and_invalid_groups(self) -> None:
        indexer = AzureSearchIndexer("https://search.example.net", "u15-demo", lambda: "token", lambda _: (1.0,))
        real_chunk = DocumentChunk("c1", "content", "title", "doc", "section", "guide", None, None,
                                   ("PLANNER",), "demo.md", source_type="REAL")
        with self.assertRaisesRegex(ValueError, "synthetic"):
            indexer.upload((real_chunk,))
        unsafe_group = DocumentChunk("c2", "content", "title", "doc", "section", "guide", None, None,
                                     ("PLANNER') or true or ('",), "demo.md")
        with self.assertRaisesRegex(ValueError, "valid security groups"):
            indexer.upload((unsafe_group,))

    def test_filter_applies_groups_and_document_validity_at_query_time(self) -> None:
        expression = build_filter(RetrievalFilters(("PLANNER", "ANALYST"), date(2026, 10, 14)))
        self.assertIn("search.in(g, 'PLANNER,ANALYST', ',')", expression)
        self.assertIn("effective_date le 2026-10-14T00:00:00Z", expression)
        self.assertIn("expiry_date ge 2026-10-14T00:00:00Z", expression)
        self.assertEqual(build_filter(RetrievalFilters((), date(2026, 10, 14))), "false")

    def test_search_sends_hybrid_vector_query_and_acl_before_retrieval(self) -> None:
        captured: list[tuple[Any, float]] = []

        def opener(request: Any, *, timeout: float) -> Response:
            captured.append((request, timeout))
            return Response({"value": [{
                "id": "c1", "content": "demostración", "title": "Manual", "document_id": "d1",
                "section": "Uso", "document_type": "demo-guide", "effective_date": "2026-10-14T00:00:00Z",
                "expiry_date": None, "security_groups": ["PLANNER"], "source_url": "demo.md#uso",
                "source_type": "SYNTHETIC", "@search.score": 0.8,
            }]})

        retriever = AzureSearchRetriever("https://search.example.net", "u15-demo", lambda: "test-token",
                                         lambda _: (0.1, 0.2), opener=opener)
        results = retriever.search("consulta", RetrievalFilters(("PLANNER",), date(2026, 10, 14)), 3)
        request, _ = captured[0]
        payload = json.loads(request.data)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
        self.assertEqual(payload["vectorFilterMode"], "preFilter")
        self.assertIn("security_groups/any", payload["filter"])
        self.assertEqual(payload["top"], 3)
        self.assertEqual(payload["vectorQueries"][0]["fields"], "content_vector")
        self.assertEqual(results[0].chunk.document_id, "d1")
        self.assertEqual(results[0].chunk.source_type, "SYNTHETIC")

    def test_empty_groups_do_not_make_a_network_request(self) -> None:
        def fail(*_: Any, **__: Any) -> Response:
            raise AssertionError("network request must not run")

        retriever = AzureSearchRetriever("https://search.example.net", "u15-demo", lambda: "token",
                                         lambda _: (1.0,), opener=fail)
        self.assertEqual(retriever.search("query", RetrievalFilters((), date(2026, 10, 14))), ())

    def test_invalid_embedding_fails_closed(self) -> None:
        retriever = AzureSearchRetriever("https://search.example.net", "u15-demo", lambda: "token", lambda _: ())
        with self.assertRaisesRegex(SearchUnavailable, "empty vector"):
            retriever.search("query", RetrievalFilters(("PLANNER",), date(2026, 10, 14)))


if __name__ == "__main__":
    unittest.main()
