from pathlib import Path

import pytest

from app.models.domain import Chunk
from app.storage.bm25_store import BM25Store


def _chunk(chunk_id: str, document_id: str, text: str, idx: int = 0) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=idx,
        filename=f"{document_id}.md",
        page_start=None,
        page_end=None,
        section=None,
        text=text,
        token_count=len(text.split()),
        char_start=0,
        char_end=len(text),
    )


@pytest.fixture
def store(tmp_path: Path) -> BM25Store:
    return BM25Store(tmp_path / "bm25" / "index.pkl")


def test_empty_store_search_returns_nothing(store: BM25Store):
    assert store.search("anything", top_k=5) == []


def test_upsert_and_search_ranks_relevant_chunk_first(store: BM25Store):
    # Note: BM25's classic idf formula (log((N-n+0.5)/(n+0.5))) is exactly zero
    # when a term appears in precisely half of a 2-document corpus, so this
    # test uses a slightly larger corpus to avoid that degenerate edge case.
    store.upsert(
        [
            _chunk("c1", "d1", "The cat sat on the mat in the sunny afternoon."),
            _chunk("c2", "d1", "Quantum computing uses qubits and superposition."),
            _chunk("c3", "d1", "Bread dough needs yeast, flour, water, and salt."),
            _chunk("c4", "d1", "Migratory birds fly south before the winter cold."),
        ]
    )
    results = store.search("qubits and quantum superposition", top_k=4)
    assert results[0].chunk.chunk_id == "c2"
    assert results[0].sparse_score is not None
    assert results[0].sparse_score >= results[1].sparse_score


def test_upsert_is_idempotent_for_same_chunk_id(store: BM25Store):
    store.upsert([_chunk("c1", "d1", "original text about widgets")])
    store.upsert([_chunk("c1", "d1", "original text about widgets")])
    # Same chunk_id shouldn't be duplicated in the corpus.
    assert len(store._chunks) == 1  # noqa: SLF001


def test_delete_document_removes_its_chunks(store: BM25Store):
    store.upsert(
        [
            _chunk("c1", "d1", "alpha beta gamma"),
            _chunk("c2", "d2", "delta epsilon zeta"),
        ]
    )
    deleted = store.delete_document("d1")
    assert deleted == 1
    remaining_ids = {c.chunk_id for c in store._chunks}  # noqa: SLF001
    assert remaining_ids == {"c2"}


def test_save_and_load_round_trip(tmp_path: Path):
    path = tmp_path / "bm25" / "index.pkl"
    store = BM25Store(path)
    store.upsert([_chunk("c1", "d1", "persisted content about retrieval systems")])
    store.save()

    reloaded = BM25Store(path)
    results = reloaded.search("retrieval systems", top_k=1)
    assert len(results) == 1
    assert results[0].chunk.chunk_id == "c1"


def test_tokenizer_drops_single_char_tokens_and_lowercases():
    from app.storage.bm25_store import _tokenize

    assert _tokenize("A Cat, and a DOG!") == ["cat", "and", "dog"]
