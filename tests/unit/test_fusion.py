from app.models.domain import Chunk, ScoredChunk
from app.retrieval.fusion import reciprocal_rank_fusion


def _chunk(chunk_id: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id="d1",
        chunk_index=0,
        filename="f.md",
        text=f"text-{chunk_id}",
        token_count=2,
        char_start=0,
        char_end=10,
    )


def test_rrf_scores_match_hand_computed_formula():
    # dense ranks: A=1, B=2 ; sparse ranks: B=1, A=2
    dense = [ScoredChunk(chunk=_chunk("A"), dense_score=0.9, rank=1), ScoredChunk(chunk=_chunk("B"), dense_score=0.8, rank=2)]
    sparse = [ScoredChunk(chunk=_chunk("B"), sparse_score=5.0, rank=1), ScoredChunk(chunk=_chunk("A"), sparse_score=4.0, rank=2)]

    fused = reciprocal_rank_fusion([dense, sparse], k=60)
    scores_by_id = {sc.chunk.chunk_id: sc.fused_score for sc in fused}

    expected_a = 1 / (60 + 1) + 1 / (60 + 2)
    expected_b = 1 / (60 + 2) + 1 / (60 + 1)
    assert abs(scores_by_id["A"] - expected_a) < 1e-9
    assert abs(scores_by_id["B"] - expected_b) < 1e-9
    # A and B are symmetric here, so scores tie exactly.
    assert scores_by_id["A"] == scores_by_id["B"]


def test_rrf_chunk_present_in_only_one_list_still_scored():
    dense = [ScoredChunk(chunk=_chunk("A"), dense_score=0.9, rank=1)]
    sparse: list[ScoredChunk] = []

    fused = reciprocal_rank_fusion([dense, sparse], k=60)
    assert len(fused) == 1
    assert fused[0].chunk.chunk_id == "A"
    assert abs(fused[0].fused_score - 1 / 61) < 1e-9


def test_rrf_orders_by_combined_score_descending():
    dense = [
        ScoredChunk(chunk=_chunk("A"), dense_score=0.9, rank=1),
        ScoredChunk(chunk=_chunk("B"), dense_score=0.7, rank=2),
        ScoredChunk(chunk=_chunk("C"), dense_score=0.5, rank=3),
    ]
    sparse = [
        ScoredChunk(chunk=_chunk("A"), sparse_score=3.0, rank=1),
        ScoredChunk(chunk=_chunk("C"), sparse_score=2.0, rank=2),
    ]
    fused = reciprocal_rank_fusion([dense, sparse], k=60)
    ids_in_order = [sc.chunk.chunk_id for sc in fused]
    assert ids_in_order == ["A", "C", "B"]
    assert [sc.rank for sc in fused] == [1, 2, 3]


def test_rrf_preserves_original_dense_and_sparse_scores_on_fused_result():
    dense = [ScoredChunk(chunk=_chunk("A"), dense_score=0.42, rank=1)]
    sparse = [ScoredChunk(chunk=_chunk("A"), sparse_score=7.1, rank=1)]
    fused = reciprocal_rank_fusion([dense, sparse], k=60)
    assert fused[0].dense_score == 0.42
    assert fused[0].sparse_score == 7.1


def test_rrf_empty_lists_returns_empty():
    assert reciprocal_rank_fusion([[], []], k=60) == []
