from pathlib import Path

import pytest

from app.embeddings.mock import MockEmbeddingProvider
from app.ingestion.service import DocumentService, IngestionService, Manifest
from app.storage.bm25_store import BM25Store
from app.storage.qdrant_store import QdrantVectorStore

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def services(tmp_path: Path):
    embedder = MockEmbeddingProvider()
    vector_store = QdrantVectorStore(path=tmp_path / "qdrant", collection="documents", dimension=embedder.dimension)
    sparse_index = BM25Store(tmp_path / "bm25" / "index.pkl")
    manifest = Manifest(tmp_path / "manifest.json")

    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    ingestion = IngestionService(
        embedding_provider=embedder,
        vector_store=vector_store,
        sparse_index=sparse_index,
        manifest=manifest,
        chunk_size_tokens=200,
        chunk_overlap_tokens=30,
        chunk_min_tokens=20,
        embedding_batch_size=8,
        raw_dir=raw_dir,
        processed_dir=processed_dir,
    )
    documents = DocumentService(
        vector_store=vector_store,
        sparse_index=sparse_index,
        manifest=manifest,
        raw_dir=raw_dir,
        processed_dir=processed_dir,
    )
    return ingestion, documents, vector_store, sparse_index, raw_dir


def test_ingest_pdf_creates_chunks_with_metadata(services):
    ingestion, _documents, vector_store, _sparse, _raw_dir = services
    file_bytes = (FIXTURES / "sample.pdf").read_bytes()

    document, chunks, skipped = ingestion.ingest_document(file_bytes, "sample.pdf")

    assert skipped is False
    assert document.doc_type == "pdf"
    assert document.page_count == 3
    assert len(chunks) > 0
    assert all(c.filename == "sample.pdf" for c in chunks)
    assert all(c.document_id == document.document_id for c in chunks)
    assert any(c.page_start is not None for c in chunks)
    assert vector_store.count() == len(chunks)


def test_ingest_markdown_creates_chunks_without_pages(services):
    ingestion, _documents, vector_store, _sparse, _raw_dir = services
    file_bytes = (FIXTURES / "sample.md").read_bytes()

    document, chunks, skipped = ingestion.ingest_document(file_bytes, "sample.md")

    assert skipped is False
    assert document.doc_type == "markdown"
    assert document.page_count is None
    assert len(chunks) > 0
    assert all(c.page_start is None for c in chunks)
    assert any(c.section is not None for c in chunks)


def test_reingesting_same_bytes_is_a_noop(services):
    ingestion, _documents, vector_store, _sparse, _raw_dir = services
    file_bytes = (FIXTURES / "sample.md").read_bytes()

    _doc1, chunks1, skipped1 = ingestion.ingest_document(file_bytes, "sample.md")
    count_after_first = vector_store.count()

    _doc2, chunks2, skipped2 = ingestion.ingest_document(file_bytes, "sample.md")

    assert skipped1 is False
    assert skipped2 is True
    assert chunks2 == []
    assert vector_store.count() == count_after_first == len(chunks1)


def test_list_and_delete_document(services):
    ingestion, documents, vector_store, sparse, _raw_dir = services
    file_bytes = (FIXTURES / "sample.md").read_bytes()
    document, chunks, _skipped = ingestion.ingest_document(file_bytes, "sample.md")

    listed = documents.list_documents()
    assert len(listed) == 1
    assert listed[0].document_id == document.document_id
    assert listed[0].chunk_count == len(chunks)

    deleted_count = documents.delete_document(document.document_id)
    assert deleted_count == len(chunks)
    assert vector_store.count() == 0
    assert documents.list_documents() == []
    assert sparse.search("widget", top_k=5) == []


def test_ingest_persists_raw_file_and_delete_removes_it(services):
    ingestion, documents, _vector_store, _sparse, raw_dir = services
    file_bytes = (FIXTURES / "sample.pdf").read_bytes()

    document, _chunks, _skipped = ingestion.ingest_document(file_bytes, "sample.pdf")

    raw_path = raw_dir / f"{document.document_id}.pdf"
    assert raw_path.exists()
    assert raw_path.read_bytes() == file_bytes

    found_path, doc_type = documents.raw_file(document.document_id)
    assert found_path == raw_path
    assert doc_type == "pdf"

    documents.delete_document(document.document_id)
    assert not raw_path.exists()


def test_raw_file_for_unknown_document_raises(services):
    from app.core.errors import DocumentNotFoundError

    _ingestion, documents, _vector_store, _sparse, _raw_dir = services
    with pytest.raises(DocumentNotFoundError):
        documents.raw_file("does-not-exist")
