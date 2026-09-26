from pathlib import Path

import pytest

from app.embeddings.mock import MockEmbeddingProvider
from app.evaluation.benchmark import run_benchmark
from app.evaluation.dataset import load_dataset
from app.evaluation.reporting import write_report
from app.generation.mock import MockGenerationProvider
from app.generation.service import GenerationService
from app.ingestion.service import IngestionService, Manifest
from app.retrieval.dense import DenseRetriever
from app.retrieval.reranking import NoOpReranker
from app.retrieval.service import RetrievalService
from app.retrieval.sparse import SparseRetriever
from app.storage.bm25_store import BM25Store
from app.storage.qdrant_store import QdrantVectorStore

FIXTURES = Path(__file__).parent.parent / "fixtures"
EVAL_DATASET = Path(__file__).parent.parent.parent / "data" / "evaluation" / "eval_dataset.json"


@pytest.fixture
def benchmark_services(tmp_path: Path):
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

    retrieval = RetrievalService(
        dense_retriever=DenseRetriever(embedder, vector_store),
        sparse_retriever=SparseRetriever(sparse_index),
        reranker=NoOpReranker(),
        rrf_k=60,
        candidate_k=10,
        rerank_enabled=False,
    )
    generation = GenerationService(generation_provider=MockGenerationProvider(), context_budget_tokens=800)
    return retrieval, generation


def test_run_benchmark_produces_metrics_for_each_case(benchmark_services):
    retrieval, generation = benchmark_services
    cases = load_dataset(EVAL_DATASET)

    report = run_benchmark(cases, retrieval, generation, top_k=5)

    assert len(report.case_results) == len(cases)
    assert 0.0 <= report.mean_recall_at_k <= 1.0
    assert 0.0 <= report.mean_mrr <= 1.0


def test_write_report_creates_json_and_markdown_files(benchmark_services, tmp_path: Path):
    retrieval, generation = benchmark_services
    cases = load_dataset(EVAL_DATASET)
    report = run_benchmark(cases, retrieval, generation, top_k=5)

    json_path, md_path = write_report(report, tmp_path / "eval_out")

    assert json_path.exists()
    assert md_path.exists()
    assert "Mean recall@k" in md_path.read_text(encoding="utf-8")
