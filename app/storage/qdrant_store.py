"""Qdrant vector store in embedded local-persistent mode (no server, no
Docker) - QdrantClient(path=...) writes straight to a local directory."""

from __future__ import annotations

import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.models.domain import Chunk, DocumentFilter, ScoredChunk

_ID_NAMESPACE = uuid.UUID("a3f5e6d0-4b1a-4b8a-9c2a-6b0e1e2f3a4b")


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(_ID_NAMESPACE, chunk_id))


class QdrantVectorStore:
    def __init__(self, path: Path, collection: str, dimension: int) -> None:
        self._client = QdrantClient(path=str(path))
        self._collection = collection
        self._dimension = dimension
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=self._dimension, distance=Distance.COSINE),
            )

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if not chunks:
            return
        points = [
            PointStruct(
                id=_point_id(chunk.chunk_id),
                vector=vector,
                payload=chunk.model_dump(mode="json"),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self._client.upsert(collection_name=self._collection, points=points, wait=True)

    def search(
        self, query_vector: list[float], top_k: int, filters: DocumentFilter | None = None
    ) -> list[ScoredChunk]:
        qdrant_filter = None
        if filters and filters.document_ids:
            qdrant_filter = Filter(
                should=[
                    FieldCondition(key="document_id", match=MatchValue(value=doc_id))
                    for doc_id in filters.document_ids
                ]
            )

        results = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
        ).points

        scored: list[ScoredChunk] = []
        for rank, point in enumerate(results, start=1):
            chunk = Chunk.model_validate(point.payload)
            scored.append(ScoredChunk(chunk=chunk, dense_score=point.score, rank=rank))
        return scored

    def delete_document(self, document_id: str) -> int:
        before = self.count()
        self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            ),
        )
        after = self.count()
        return before - after

    def count(self) -> int:
        return self._client.count(collection_name=self._collection, exact=True).count

    def scroll_all(self) -> list[Chunk]:
        """Return every chunk currently stored, regardless of document.
        Used by scripts/rebuild_index.py to recover BM25 from Qdrant as the
        source of truth."""
        chunks: list[Chunk] = []
        offset = None
        while True:
            points, offset = self._client.scroll(
                collection_name=self._collection, limit=256, offset=offset, with_payload=True
            )
            if not points:
                break
            chunks.extend(Chunk.model_validate(point.payload) for point in points)
            if offset is None:
                break
        return chunks
