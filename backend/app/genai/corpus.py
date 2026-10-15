"""Load the explicitly synthetic U15 demo corpus and split it by Markdown section."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from .retrieval import DocumentChunk

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def load_markdown_corpus(manifest_path: str | Path, *, max_chars: int = 1200, overlap_chars: int = 160) -> tuple[DocumentChunk, ...]:
    """Read a JSON manifest of Markdown sources and create citation-preserving chunks."""
    if max_chars < 100 or not 0 <= overlap_chars < max_chars:
        raise ValueError("invalid chunk size or overlap")
    manifest_file = Path(manifest_path).resolve()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("source_type") != "SYNTHETIC":
        raise ValueError("U15 corpus must be explicitly marked SYNTHETIC")
    documents = manifest.get("documents")
    if not isinstance(documents, list) or not documents:
        raise ValueError("corpus manifest must include documents")

    chunks: list[DocumentChunk] = []
    for document in documents:
        relative_path = Path(document["path"])
        source_path = (manifest_file.parent / relative_path).resolve()
        if manifest_file.parent not in source_path.parents or source_path.suffix.lower() != ".md":
            raise ValueError("corpus source must be a Markdown file under the manifest directory")
        text = source_path.read_text(encoding="utf-8").strip()
        for section, body in _sections(text):
            for index, content in enumerate(_split(section, body, max_chars, overlap_chars)):
                chunks.append(DocumentChunk(
                    id=f"{document['id']}:{_slug(section)}:{index + 1}",
                    content=content,
                    title=document["title"],
                    document_id=document["id"],
                    section=section,
                    document_type=document["document_type"],
                    effective_date=_optional_date(document.get("effective_date")),
                    expiry_date=_optional_date(document.get("expiry_date")),
                    security_groups=tuple(document["security_groups"]),
                    source_url=f"knowledge/search_corpus/{relative_path.as_posix()}#{_slug(section)}",
                    source_type="SYNTHETIC",
                ))
    return tuple(chunks)


def _sections(text: str) -> tuple[tuple[str, str], ...]:
    headings = list(HEADING.finditer(text))
    if not headings:
        return (("Documento", text),)
    result: list[tuple[str, str]] = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[heading.end():end].strip()
        if body:
            result.append((heading.group(2), body))
    preamble = text[:headings[0].start()].strip()
    if preamble:
        result.insert(0, ("Introducción", preamble))
    return tuple(result)


def _split(section: str, body: str, max_chars: int, overlap_chars: int) -> tuple[str, ...]:
    prefix = f"{section}\n"
    body_limit = max_chars - len(prefix)
    if len(body) <= body_limit:
        return (prefix + body,)
    result: list[str] = []
    start = 0
    while start < len(body):
        end = min(len(body), start + body_limit)
        if end < len(body):
            boundary = body.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        result.append(prefix + body[start:end].strip())
        if end == len(body):
            break
        start = max(start + 1, end - overlap_chars)
    return tuple(result)


def _optional_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "section"
