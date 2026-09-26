"""Vector store interface. QdrantVectorStore (storage/qdrant_store.py) is the
concrete implementation used by the app; the Protocol exists so retrieval and
ingestion code never depend on Qdrant directly."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models.domain import Chunk, DocumentFilter, ScoredChunk


@runtime_checkable
class VectorStore(Protocol):
    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Insert or overwrite chunks (idempotent: same chunk_id -> same point)."""
        ...

    def search(
        self, query_vector: list[float], top_k: int, filters: DocumentFilter | None = None
    ) -> list[ScoredChunk]:
        ...

    def delete_document(self, document_id: str) -> int:
        """Delete all chunks belonging to a document. Returns count deleted."""
        ...

    def count(self) -> int:
        ...
