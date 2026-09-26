from app.evaluation.metrics import citation_presence, lexical_overlap, mrr, ndcg_at_k, recall_at_k
from app.models.domain import Chunk, Citation


def _chunk(document_id: str, filename: str) -> Chunk:
    return Chunk(
        chunk_id=f"{document_id}-c1",
        document_id=document_id,
        chunk_index=0,
        filename=filename,
        text="x",
        token_count=1,
        char_start=0,
        char_end=1,
    )


def test_recall_at_k_hit():
    retrieved = [_chunk("d1", "a.pdf"), _chunk("d2", "b.pdf")]
    assert recall_at_k(retrieved, "d2", k=2) == 1.0


def test_recall_at_k_miss_outside_k():
    retrieved = [_chunk("d1", "a.pdf"), _chunk("d2", "b.pdf"), _chunk("d3", "c.pdf")]
    assert recall_at_k(retrieved, "d3", k=2) == 0.0


def test_recall_at_k_no_expected_document_defaults_true():
    assert recall_at_k([], "", k=5) == 1.0


def test_mrr_first_position():
    retrieved = [_chunk("d1", "a.pdf")]
    assert mrr(retrieved, "d1") == 1.0


def test_mrr_third_position():
    retrieved = [_chunk("d1", "a.pdf"), _chunk("d2", "b.pdf"), _chunk("d3", "c.pdf")]
    assert abs(mrr(retrieved, "d3") - (1 / 3)) < 1e-9


def test_mrr_not_found():
    retrieved = [_chunk("d1", "a.pdf")]
    assert mrr(retrieved, "d99") == 0.0


def test_ndcg_perfect_ranking_is_one():
    retrieved = [_chunk("d1", "a.pdf"), _chunk("d2", "b.pdf")]
    relevances = {"d1": 1.0, "d2": 0.5}
    assert abs(ndcg_at_k(retrieved, relevances, k=2) - 1.0) < 1e-9


def test_ndcg_no_relevances_is_zero():
    retrieved = [_chunk("d1", "a.pdf")]
    assert ndcg_at_k(retrieved, {}, k=2) == 0.0


def test_lexical_overlap_partial_match():
    assert lexical_overlap("Uses reciprocal rank fusion here", ["reciprocal", "cross-encoder"]) == 0.5


def test_lexical_overlap_no_keywords_defaults_true():
    assert lexical_overlap("anything", []) == 1.0


def test_citation_presence_true_when_document_and_page_match():
    citations = [Citation(document_id="d1", filename="a.pdf", page=4, section=None, chunk_id="c1", quote="q")]
    assert citation_presence(citations, "d1", 4) is True


def test_citation_presence_false_when_page_mismatches():
    citations = [Citation(document_id="d1", filename="a.pdf", page=4, section=None, chunk_id="c1", quote="q")]
    assert citation_presence(citations, "d1", 9) is False


def test_citation_presence_no_expected_document_checks_nonempty():
    citations = [Citation(document_id="d1", filename="a.pdf", page=None, section=None, chunk_id="c1", quote="q")]
    assert citation_presence(citations, None, None) is True
    assert citation_presence([], None, None) is False
