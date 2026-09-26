from pathlib import Path

import pytest

from app.embeddings.mock import MockEmbeddingProvider
from app.ingestion.service import IngestionService, Manifest
from app.retrieval.dense import DenseRetriever
from app.retrieval.reranking import NoOpReranker
from app.retrieval.service import RetrievalService
from app.retrieval.sparse import SparseRetriever
from app.storage.bm25_store import BM25Store
from app.storage.qdrant_store import QdrantVectorStore

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def retrieval_service(tmp_path: Path):
    embedder = MockEmbeddingProvider()
    vector_store = QdrantVectorStore(path=tmp_path / "qdrant", collection="documents", dimension=embedder.dimension)
    sparse_index = BM25Store(tmp_path / "bm25" / "index.pkl")
    manifest = Manifest(tmp_path / "manifest.json")

    ingestion = IngestionService(
        embedding_provider=embedder,
        vector_store=vector_store,
        sparse_index=sparse_index,
        manifest=manifest,
        chunk_size_tokens=150,
        chunk_overlap_tokens=20,
        chunk_min_tokens=15,
        embedding_batch_size=8,
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
    )
    ingestion.ingest_document((FIXTURES / "sample.pdf").read_bytes(), "sample.pdf")
    ingestion.ingest_document((FIXTURES / "sample.md").read_bytes(), "sample.md")

    return RetrievalService(
        dense_retriever=DenseRetriever(embedder, vector_store),
        sparse_retriever=SparseRetriever(sparse_index),
        reranker=NoOpReranker(),
        rrf_k=60,
        candidate_k=10,
        rerank_enabled=False,
    )


def test_search_returns_ranked_fused_results(retrieval_service: RetrievalService):
    results = retrieval_service.search("reciprocal rank fusion merges ranked lists", top_k=5)
    assert len(results) > 0
    assert all(r.fused_score is not None for r in results)
    scores = [r.fused_score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_search_finds_content_from_both_documents(retrieval_service: RetrievalService):
    pdf_hit = retrieval_service.search("reciprocal rank fusion", top_k=10)
    md_hit = retrieval_service.search("widget.toml configuration file", top_k=10)

    assert any(r.chunk.filename == "sample.pdf" for r in pdf_hit)
    assert any(r.chunk.filename == "sample.md" for r in md_hit)


def test_search_respects_top_k(retrieval_service: RetrievalService):
    results = retrieval_service.search("configuration", top_k=1)
    assert len(results) <= 1


def test_search_rerank_override_uses_noop_reranker(retrieval_service: RetrievalService):
    # rerank=True forces NoOpReranker.rerank(), which just truncates - still
    # returns valid ranked results without erroring.
    results = retrieval_service.search("widget installation requirements", top_k=3, rerank=True)
    assert len(results) <= 3
