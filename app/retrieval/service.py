from __future__ import annotations

from app.models.domain import DocumentFilter, ScoredChunk
from app.retrieval.dense import DenseRetriever
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.reranking import Reranker
from app.retrieval.sparse import SparseRetriever


class RetrievalService:
    def __init__(
        self,
        *,
        dense_retriever: DenseRetriever,
        sparse_retriever: SparseRetriever,
        reranker: Reranker,
        rrf_k: int,
        candidate_k: int,
        rerank_enabled: bool,
    ) -> None:
        self._dense = dense_retriever
        self._sparse = sparse_retriever
        self._reranker = reranker
        self._rrf_k = rrf_k
        self._candidate_k = candidate_k
        self._rerank_enabled = rerank_enabled

    def search(
        self,
        query: str,
        top_k: int,
        *,
        filters: DocumentFilter | None = None,
        rerank: bool | None = None,
    ) -> list[ScoredChunk]:
        dense_results = self._dense.retrieve(query, self._candidate_k, filters=filters)
        sparse_results = self._sparse.retrieve(query, self._candidate_k)

        fused = reciprocal_rank_fusion([dense_results, sparse_results], k=self._rrf_k)

        use_rerank = self._rerank_enabled if rerank is None else rerank
        if use_rerank:
            return self._reranker.rerank(query, fused, top_k)

        return fused[:top_k]
