"""Reciprocal Rank Fusion: combine multiple ranked lists into one ranking
without needing the lists' scores to be on comparable scales.

score(chunk) = sum over lists containing chunk of 1 / (k + rank_in_list)

A chunk that appears in only one list still receives a (smaller) score, so
dense-only or sparse-only hits aren't dropped - they just rank lower than
chunks both retrievers agree on.
"""

from __future__ import annotations

from app.models.domain import ScoredChunk


def reciprocal_rank_fusion(ranked_lists: list[list[ScoredChunk]], k: int = 60) -> list[ScoredChunk]:
    fused_scores: dict[str, float] = {}
    best_scored_chunk: dict[str, ScoredChunk] = {}
    dense_scores: dict[str, float] = {}
    sparse_scores: dict[str, float] = {}

    for ranked_list in ranked_lists:
        for scored in ranked_list:
            chunk_id = scored.chunk.chunk_id
            contribution = 1.0 / (k + scored.rank)
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + contribution
            best_scored_chunk[chunk_id] = scored
            if scored.dense_score is not None:
                dense_scores[chunk_id] = scored.dense_score
            if scored.sparse_score is not None:
                sparse_scores[chunk_id] = scored.sparse_score

    ordered_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)

    fused: list[ScoredChunk] = []
    for rank, chunk_id in enumerate(ordered_ids, start=1):
        base = best_scored_chunk[chunk_id]
        fused.append(
            ScoredChunk(
                chunk=base.chunk,
                dense_score=dense_scores.get(chunk_id),
                sparse_score=sparse_scores.get(chunk_id),
                fused_score=fused_scores[chunk_id],
                rerank_score=None,
                rank=rank,
            )
        )
    return fused
