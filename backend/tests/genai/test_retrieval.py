from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from app.genai import DocumentChunk, InMemoryDocumentRetriever, RetrievalFilters
from app.genai.corpus import load_markdown_corpus
from app.genai.evaluation import evaluate_retriever

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "knowledge" / "search_corpus" / "manifest.json"
GROUP = "U15-DEMO-READERS"


def vectorize(text: str) -> tuple[float, float, float]:
    lowered = text.casefold()
    return (float("cifra" in lowered or "datos" in lowered),
            float("política" in lowered or "provisional" in lowered),
            float("asistente" in lowered or "preguntas" in lowered))


class CorpusTest(unittest.TestCase):
    def test_manifest_marks_all_documents_synthetic_and_chunks_keep_citations(self) -> None:
        chunks = load_markdown_corpus(CORPUS, max_chars=180, overlap_chars=24)
        self.assertGreater(len(chunks), 3)
        self.assertTrue(all(chunk.source_type == "SYNTHETIC" for chunk in chunks))
        self.assertTrue(all(chunk.document_id and chunk.section and "#" in chunk.source_url for chunk in chunks))
        self.assertTrue(all(chunk.security_groups == (GROUP,) for chunk in chunks))
        self.assertTrue(all(len(chunk.content) <= 180 for chunk in chunks))

    def test_rejects_corpus_not_explicitly_synthetic(self) -> None:
        manifest = json.loads(CORPUS.read_text(encoding="utf-8"))
        manifest["source_type"] = "REAL"
        temporary = CORPUS.with_name("manifest.invalid.tmp")
        try:
            temporary.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SYNTHETIC"):
                load_markdown_corpus(temporary)
        finally:
            temporary.unlink(missing_ok=True)


class InMemoryRetrieverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.chunks = load_markdown_corpus(CORPUS)
        self.retriever = InMemoryDocumentRetriever(self.chunks, vectorize)
        self.filters = RetrievalFilters((GROUP,), date(2026, 10, 14))

    def test_hybrid_search_returns_citable_relevant_document(self) -> None:
        result = self.retriever.search("¿De dónde salen las cifras de inventario?", self.filters)
        self.assertTrue(result)
        self.assertEqual(result[0].chunk.document_id, "U15-SYN-002")
        self.assertEqual(result[0].chunk.source_type, "SYNTHETIC")
        self.assertIn("#", result[0].chunk.source_url)

    def test_empty_acl_returns_no_documents(self) -> None:
        self.assertEqual(self.retriever.search("inventario", RetrievalFilters((), date(2026, 10, 14))), ())

    def test_expired_or_unauthorized_documents_are_not_returned(self) -> None:
        hidden = DocumentChunk(
            "hidden", "inventario política", "Privado", "private", "Sección", "manual", date(2020, 1, 1),
            date(2020, 1, 2), ("OTHER-GROUP",), "private.md#section", content_vector=(1, 0, 0),
        )
        retriever = InMemoryDocumentRetriever((*self.chunks, hidden), vectorize)
        result = retriever.search("inventario política", self.filters)
        self.assertNotIn("private", {entry.chunk.document_id for entry in result})

    def test_rejects_empty_query_and_invalid_top_k(self) -> None:
        with self.assertRaises(ValueError):
            self.retriever.search(" ", self.filters)
        with self.assertRaises(ValueError):
            self.retriever.search("inventario", self.filters, top_k=21)

    def test_fixed_evaluation_set_runs_and_reports_hit_rate_without_claiming_threshold(self) -> None:
        cases = json.loads((CORPUS.parent / "evaluation.json").read_text(encoding="utf-8"))["cases"]
        report = evaluate_retriever(self.retriever, cases, self.filters)
        self.assertEqual(len(report), 6)
        self.assertTrue(all(result.retrieved_document_ids for result in report))
        self.assertTrue(any(result.hit for result in report))


if __name__ == "__main__":
    unittest.main()
