"""Tests against a real, running Ollama instance with qwen3:1.7b pulled.

Skipped unless RUN_LIVE_OLLAMA_TESTS=1 is set, since CI/offline environments
won't have Ollama running. keep_alive=0 means every call reloads the model
(~20-30s on this machine), so these are intentionally few and coarse-grained.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.core.errors import OllamaModelNotFoundError, OllamaUnavailableError
from app.generation.ollama import OllamaGenerationProvider
from app.generation.service import GenerationService
from app.ingestion.service import IngestionService, Manifest
from app.storage.bm25_store import BM25Store
from app.storage.qdrant_store import QdrantVectorStore

pytestmark = pytest.mark.live_ollama

if not os.environ.get("RUN_LIVE_OLLAMA_TESTS"):
    pytest.skip("Set RUN_LIVE_OLLAMA_TESTS=1 to run tests against a real Ollama instance", allow_module_level=True)

BASE_URL = "http://localhost:11434"
MODEL = "qwen3:1.7b"
FIXTURES = Path(__file__).parent.parent / "fixtures"


def _provider(model: str = MODEL) -> OllamaGenerationProvider:
    return OllamaGenerationProvider(
        base_url=BASE_URL,
        model=model,
        context_length=2048,
        num_predict=64,
        keep_alive=0,
        think=False,
        timeout_s=90.0,
    )


def test_health_check_true_when_ollama_running():
    assert _provider().health_check() is True


def test_is_model_available_true_for_pulled_model():
    assert _provider().is_model_available(MODEL) is True


def test_is_model_available_false_for_nonexistent_model():
    assert _provider().is_model_available("definitely-not-a-real-model:latest") is False


def test_generate_returns_nonempty_text_for_trivial_prompt():
    result = _provider().generate("Reply with exactly one word: hello", system=None, max_tokens=16)
    assert result.text.strip() != ""
    assert result.model == MODEL


def test_generate_raises_model_not_found_for_missing_model():
    provider = _provider(model="definitely-not-a-real-model:latest")
    with pytest.raises(OllamaModelNotFoundError):
        provider.generate("hello")


def test_generate_raises_unavailable_for_unreachable_host():
    provider = OllamaGenerationProvider(
        base_url="http://localhost:1",
        model=MODEL,
        context_length=2048,
        num_predict=16,
        keep_alive=0,
        think=False,
        timeout_s=3.0,
    )
    with pytest.raises(OllamaUnavailableError):
        provider.generate("hello")


def test_full_pipeline_real_embeddings_real_qdrant_real_ollama_produces_citations(tmp_path):
    from app.embeddings.sentence_transformers import SentenceTransformersEmbeddingProvider
    from app.retrieval.dense import DenseRetriever
    from app.retrieval.reranking import NoOpReranker
    from app.retrieval.service import RetrievalService
    from app.retrieval.sparse import SparseRetriever

    embedder = SentenceTransformersEmbeddingProvider(
        model_name="BAAI/bge-small-en-v1.5", expected_dim=384, batch_size=8
    )
    vector_store = QdrantVectorStore(path=tmp_path / "qdrant", collection="documents", dimension=embedder.dimension)
    sparse_index = BM25Store(tmp_path / "bm25" / "index.pkl")
    manifest = Manifest(tmp_path / "manifest.json")

    ingestion = IngestionService(
        embedding_provider=embedder,
        vector_store=vector_store,
        sparse_index=sparse_index,
        manifest=manifest,
        chunk_size_tokens=200,
        chunk_overlap_tokens=30,
        chunk_min_tokens=20,
        embedding_batch_size=8,
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
    )
    ingestion.ingest_document((FIXTURES / "sample.pdf").read_bytes(), "sample.pdf")

    retrieval = RetrievalService(
        dense_retriever=DenseRetriever(embedder, vector_store),
        sparse_retriever=SparseRetriever(sparse_index),
        reranker=NoOpReranker(),
        rrf_k=60,
        candidate_k=10,
        rerank_enabled=False,
    )
    generation = GenerationService(generation_provider=_provider(), context_budget_tokens=1500)

    chunks = retrieval.search("What method combines dense and sparse retrieval?", top_k=3)
    assert len(chunks) > 0

    result = generation.answer("What method combines dense and sparse retrieval?", chunks)
    assert result.answer.strip() != ""
    assert result.model == MODEL
