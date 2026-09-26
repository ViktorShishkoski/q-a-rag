"""Optional cross-encoder reranking, gated by RERANK_ENABLED.

The cross-encoder model is loaded lazily (only on first rerank() call) so
processes that never enable reranking don't pay its memory cost.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.models.domain import ScoredChunk


@runtime_checkable
class Reranker(Protocol):
    def rerank(self, query: str, chunks: list[ScoredChunk], top_k: int) -> list[ScoredChunk]: ...


class NoOpReranker:
    """Identity passthrough - used when RERANK_ENABLED=false or in fast unit tests."""

    def rerank(self, query: str, chunks: list[ScoredChunk], top_k: int) -> list[ScoredChunk]:
        return chunks[:top_k]


class CrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: Any = None

    def _load(self) -> Any:  # noqa: ANN202
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name)
        return self._model

    def rerank(self, query: str, chunks: list[ScoredChunk], top_k: int) -> list[ScoredChunk]:
        if not chunks:
            return []
        model = self._load()
        pairs = [(query, sc.chunk.text) for sc in chunks]
        scores = model.predict(pairs)

        reranked = sorted(zip(chunks, scores, strict=True), key=lambda pair: pair[1], reverse=True)
        result: list[ScoredChunk] = []
        for rank, (scored, score) in enumerate(reranked[:top_k], start=1):
            result.append(scored.model_copy(update={"rerank_score": float(score), "rank": rank}))
        return result
