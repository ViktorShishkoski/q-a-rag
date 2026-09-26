from __future__ import annotations

from app.models.domain import ScoredChunk
from app.storage.bm25_store import SparseIndex


class SparseRetriever:
    def __init__(self, sparse_index: SparseIndex) -> None:
        self._sparse_index = sparse_index

    def retrieve(self, query: str, top_k: int) -> list[ScoredChunk]:
        return self._sparse_index.search(query, top_k)
