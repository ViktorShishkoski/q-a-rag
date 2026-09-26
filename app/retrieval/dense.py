from __future__ import annotations

from app.embeddings.base import EmbeddingProvider
from app.models.domain import DocumentFilter, ScoredChunk
from app.storage.vector_store import VectorStore


class DenseRetriever:
    def __init__(self, embedding_provider: EmbeddingProvider, vector_store: VectorStore) -> None:
        self._embeddings = embedding_provider
        self._vector_store = vector_store

    def retrieve(self, query: str, top_k: int, filters: DocumentFilter | None = None) -> list[ScoredChunk]:
        query_vector = self._embeddings.embed_query(query)
        return self._vector_store.search(query_vector, top_k, filters=filters)
