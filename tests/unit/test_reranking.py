from app.models.domain import Chunk, ScoredChunk
from app.retrieval.reranking import NoOpReranker


def _scored(chunk_id: str, rank: int) -> ScoredChunk:
    chunk = Chunk(
        chunk_id=chunk_id,
        document_id="d1",
        chunk_index=0,
        filename="f.md",
        text=f"text-{chunk_id}",
        token_count=2,
        char_start=0,
        char_end=10,
    )
    return ScoredChunk(chunk=chunk, fused_score=1.0, rank=rank)


def test_noop_reranker_truncates_to_top_k_without_reordering():
    chunks = [_scored("A", 1), _scored("B", 2), _scored("C", 3)]
    result = NoOpReranker().rerank("irrelevant query", chunks, top_k=2)
    assert [sc.chunk.chunk_id for sc in result] == ["A", "B"]


def test_noop_reranker_empty_input():
    assert NoOpReranker().rerank("q", [], top_k=5) == []
