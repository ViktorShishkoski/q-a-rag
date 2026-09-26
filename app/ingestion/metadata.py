"""Helpers for turning loader/chunker output into persisted domain objects
with deterministic, content-addressed IDs (idempotent ingestion)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from app.models.domain import Chunk, ChunkDraft, Document


def compute_document_id(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def compute_chunk_id(document_id: str, chunk_index: int, text: str) -> str:
    payload = f"{document_id}:{chunk_index}:{text}".encode()
    return hashlib.sha256(payload).hexdigest()


def build_document(
    *,
    file_bytes: bytes,
    filename: str,
    source_path: str,
    doc_type: str,
    page_count: int | None,
) -> Document:
    document_id = compute_document_id(file_bytes)
    return Document(
        document_id=document_id,
        filename=filename,
        source_path=source_path,
        doc_type=doc_type,  # type: ignore[arg-type]
        page_count=page_count,
        ingested_at=datetime.now(UTC),
        content_hash=document_id,
    )


def build_chunks(document: Document, drafts: list[ChunkDraft]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for idx, draft in enumerate(drafts):
        chunk_id = compute_chunk_id(document.document_id, idx, draft.text)
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                document_id=document.document_id,
                chunk_index=idx,
                filename=document.filename,
                page_start=draft.page_start,
                page_end=draft.page_end,
                section=draft.section,
                text=draft.text,
                token_count=draft.token_count,
                char_start=draft.char_start,
                char_end=draft.char_end,
            )
        )
    return chunks
