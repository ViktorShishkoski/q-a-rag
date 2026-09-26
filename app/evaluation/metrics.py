"""Pure retrieval/answer metrics. No external LLM-judge dependency."""

from __future__ import annotations

import math

from app.models.domain import Chunk, Citation


def recall_at_k(retrieved: list[Chunk], expected_document: str, k: int) -> float:
    if not expected_document:
        return 1.0
    top_k = retrieved[:k]
    return 1.0 if any(c.document_id == expected_document or c.filename == expected_document for c in top_k) else 0.0


def mrr(retrieved: list[Chunk], expected_document: str) -> float:
    if not expected_document:
        return 1.0
    for rank, chunk in enumerate(retrieved, start=1):
        if chunk.document_id == expected_document or chunk.filename == expected_document:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: list[Chunk], relevances: dict[str, float], k: int) -> float:
    """relevances maps document_id or filename -> relevance grade (e.g. 1.0 relevant)."""
    top_k = retrieved[:k]

    def _relevance(chunk: Chunk) -> float:
        return relevances.get(chunk.document_id, relevances.get(chunk.filename, 0.0))

    dcg = sum(_relevance(c) / math.log2(i + 2) for i, c in enumerate(top_k))
    ideal_gains = sorted(relevances.values(), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal_gains))
    return dcg / idcg if idcg > 0 else 0.0


def lexical_overlap(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    answer_lower = answer.lower()
    hits = sum(1 for kw in keywords if kw.lower() in answer_lower)
    return hits / len(keywords)


def citation_presence(citations: list[Citation], expected_document: str | None, expected_page: int | None) -> bool:
    if not expected_document:
        return len(citations) > 0
    for c in citations:
        matches_document = c.document_id == expected_document or c.filename == expected_document
        if matches_document and (expected_page is None or c.page == expected_page):
            return True
    return False
