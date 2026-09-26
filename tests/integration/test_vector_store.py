from pathlib import Path

import pytest

from app.embeddings.mock import MockEmbeddingProvider
from app.models.domain import Chunk, DocumentFilter
from app.storage.qdrant_store import QdrantVectorStore

EMBEDDER = MockEmbeddingProvider()


def _chunk(chunk_id: str, document_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        filename=f"{document_id}.md",
        page_start=1,
        page_end=1,
        section="Intro",
        text=text,
        token_count=len(text.split()),
        char_start=0,
        char_end=len(text),
    )


@pytest.fixture
def store(tmp_path: Path) -> QdrantVectorStore:
    return QdrantVectorStore(path=tmp_path / "qdrant", collection="documents", dimension=EMBEDDER.dimension)


def test_empty_store_count_is_zero(store: QdrantVectorStore):
    assert store.count() == 0


def test_upsert_and_search_round_trip(store: QdrantVectorStore):
    chunks = [
        _chunk("c1", "d1", "reciprocal rank fusion merges dense and sparse rankings"),
        _chunk("c2", "d1", "the weather today is sunny and warm"),
    ]
    vectors = EMBEDDER.embed_documents([c.text for c in chunks])
    store.upsert(chunks, vectors)

    assert store.count() == 2

    query_vector = EMBEDDER.embed_query("how does rank fusion work")
    results = store.search(query_vector, top_k=2)
    assert len(results) == 2
    assert results[0].chunk.chunk_id == "c1"
    assert results[0].dense_score is not None
    assert results[0].rank == 1


def test_upsert_is_idempotent_for_same_chunk_id(store: QdrantVectorStore):
    chunk = _chunk("c1", "d1", "some content")
    vector = EMBEDDER.embed_documents([chunk.text])
    store.upsert([chunk], vector)
    store.upsert([chunk], vector)
    assert store.count() == 1


def test_delete_document_removes_only_its_chunks(store: QdrantVectorStore):
    chunks = [
        _chunk("c1", "d1", "belongs to document one"),
        _chunk("c2", "d2", "belongs to document two"),
    ]
    vectors = EMBEDDER.embed_documents([c.text for c in chunks])
    store.upsert(chunks, vectors)

    deleted = store.delete_document("d1")
    assert deleted == 1
    assert store.count() == 1


def test_search_with_document_filter(store: QdrantVectorStore):
    chunks = [
        _chunk("c1", "d1", "alpha content about retrieval"),
        _chunk("c2", "d2", "alpha content about retrieval"),
    ]
    vectors = EMBEDDER.embed_documents([c.text for c in chunks])
    store.upsert(chunks, vectors)

    query_vector = EMBEDDER.embed_query("alpha content about retrieval")
    results = store.search(query_vector, top_k=5, filters=DocumentFilter(document_ids=["d2"]))
    assert len(results) == 1
    assert results[0].chunk.document_id == "d2"
