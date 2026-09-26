"""Dependency injection wiring.

ServiceContainer bundles every concrete provider/service built from Settings.
build_services(settings) constructs one; core/main.py's lifespan builds the
production container (or a caller-supplied factory, e.g. in tests) and
stores it on app.state, and the get_* Depends functions below read from it.
FastAPI routes depend on these functions (not on ServiceContainer directly)
so tests can override each one independently if needed - though overriding
`get_services` alone is usually enough since everything else derives from it.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, Request

from app.analysis.compare import DocumentComparer, NoOpDocumentComparer
from app.analysis.extraction import NoOpStructuredExtractor, StructuredExtractor
from app.core.config import Settings
from app.core.config import get_settings as _get_settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.mock import MockEmbeddingProvider
from app.embeddings.ollama import OllamaEmbeddingProvider
from app.embeddings.sentence_transformers import SentenceTransformersEmbeddingProvider
from app.generation.base import GenerationProvider
from app.generation.mock import MockGenerationProvider
from app.generation.ollama import OllamaGenerationProvider
from app.generation.service import GenerationService
from app.ingestion.ocr import NoOpOcrEngine, OcrEngine
from app.ingestion.service import DocumentService, IngestionService, Manifest
from app.ingestion.tables import NoOpTableExtractor, TableExtractor
from app.retrieval.dense import DenseRetriever
from app.retrieval.reranking import CrossEncoderReranker, NoOpReranker, Reranker
from app.retrieval.service import RetrievalService
from app.retrieval.sparse import SparseRetriever
from app.storage.bm25_store import BM25Store, SparseIndex
from app.storage.qdrant_store import QdrantVectorStore
from app.storage.vector_store import VectorStore


@lru_cache
def get_settings() -> Settings:
    return _get_settings()


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "mock":
        return MockEmbeddingProvider()
    if settings.embedding_provider == "ollama":
        return OllamaEmbeddingProvider(
            settings.ollama_base_url,
            settings.embedding_ollama_model,
            settings.embedding_dim,
            settings.ollama_timeout_s,
        )
    return SentenceTransformersEmbeddingProvider(
        settings.embedding_model, settings.embedding_dim, settings.embedding_batch_size
    )


def build_vector_store(settings: Settings, dimension: int) -> VectorStore:
    return QdrantVectorStore(
        path=settings.qdrant_path, collection=settings.qdrant_collection, dimension=dimension
    )


def build_sparse_index(settings: Settings) -> SparseIndex:
    return BM25Store(settings.bm25_index_path)


def build_manifest(settings: Settings) -> Manifest:
    return Manifest(settings.manifest_path)


def build_reranker(settings: Settings) -> Reranker:
    if settings.rerank_enabled:
        return CrossEncoderReranker(settings.rerank_model)
    return NoOpReranker()


def build_ocr_engine(settings: Settings) -> OcrEngine:
    # V2 seam: no real OCR backend is wired yet. When one is, branch on
    # settings.ocr_enabled here and return it (loading its model lazily).
    return NoOpOcrEngine()


def build_table_extractor(settings: Settings) -> TableExtractor:
    # V2 seam: branch on settings.table_extraction_enabled once a real
    # extractor (PyMuPDF find_tables / Camelot / layout model) exists.
    return NoOpTableExtractor()


def build_structured_extractor(settings: Settings) -> StructuredExtractor:
    # V2 seam: branch on settings.structured_extraction_enabled once the
    # retrieval-backed extractor is implemented.
    return NoOpStructuredExtractor()


def build_document_comparer(settings: Settings) -> DocumentComparer:
    # V2 seam: branch on settings.compare_enabled once the per-document
    # retrieval + shared-context comparer is implemented.
    return NoOpDocumentComparer()


def build_generation_provider(settings: Settings) -> GenerationProvider:
    if settings.generation_provider == "mock":
        return MockGenerationProvider()
    return OllamaGenerationProvider(
        settings.ollama_base_url,
        settings.ollama_generation_model,
        context_length=settings.ollama_context_length,
        num_predict=settings.ollama_num_predict,
        keep_alive=settings.ollama_keep_alive,
        think=settings.ollama_think,
        timeout_s=settings.ollama_timeout_s,
    )


class ServiceContainer:
    """Everything the API/CLI layer needs, built once from Settings."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embedding_provider = build_embedding_provider(settings)
        self.vector_store = build_vector_store(settings, self.embedding_provider.dimension)
        self.sparse_index = build_sparse_index(settings)
        self.manifest = build_manifest(settings)
        self.reranker = build_reranker(settings)
        self.generation_provider = build_generation_provider(settings)
        self.ocr_engine = build_ocr_engine(settings)
        self.table_extractor = build_table_extractor(settings)
        self.structured_extractor = build_structured_extractor(settings)
        self.document_comparer = build_document_comparer(settings)

        self.ingestion_service = IngestionService(
            embedding_provider=self.embedding_provider,
            vector_store=self.vector_store,
            sparse_index=self.sparse_index,
            manifest=self.manifest,
            chunk_size_tokens=settings.chunk_size_tokens,
            chunk_overlap_tokens=settings.chunk_overlap_tokens,
            chunk_min_tokens=settings.chunk_min_tokens,
            embedding_batch_size=settings.embedding_batch_size,
            raw_dir=settings.raw_storage_path,
            processed_dir=settings.processed_storage_path,
            ocr_engine=self.ocr_engine,
            table_extractor=self.table_extractor,
        )
        self.document_service = DocumentService(
            vector_store=self.vector_store,
            sparse_index=self.sparse_index,
            manifest=self.manifest,
            raw_dir=settings.raw_storage_path,
            processed_dir=settings.processed_storage_path,
        )
        self.retrieval_service = RetrievalService(
            dense_retriever=DenseRetriever(self.embedding_provider, self.vector_store),
            sparse_retriever=SparseRetriever(self.sparse_index),
            reranker=self.reranker,
            rrf_k=settings.rrf_k,
            candidate_k=settings.retrieval_candidate_k,
            rerank_enabled=settings.rerank_enabled,
        )

        reserved = settings.ollama_num_predict + settings.prompt_overhead_tokens
        budget = int((settings.ollama_context_length - reserved) * settings.context_safety_margin)
        self.generation_service = GenerationService(
            generation_provider=self.generation_provider, context_budget_tokens=max(budget, 100)
        )


def build_services(settings: Settings) -> ServiceContainer:
    return ServiceContainer(settings)


def get_services(request: Request) -> ServiceContainer:
    return request.app.state.services


def get_ingestion_service(services: ServiceContainer = Depends(get_services)) -> IngestionService:
    return services.ingestion_service


def get_document_service(services: ServiceContainer = Depends(get_services)) -> DocumentService:
    return services.document_service


def get_retrieval_service(services: ServiceContainer = Depends(get_services)) -> RetrievalService:
    return services.retrieval_service


def get_generation_service(services: ServiceContainer = Depends(get_services)) -> GenerationService:
    return services.generation_service


def get_generation_provider(
    services: ServiceContainer = Depends(get_services),
) -> GenerationProvider:
    return services.generation_provider


def get_vector_store(services: ServiceContainer = Depends(get_services)) -> VectorStore:
    return services.vector_store


def get_structured_extractor(
    services: ServiceContainer = Depends(get_services),
) -> StructuredExtractor:
    return services.structured_extractor


def get_document_comparer(services: ServiceContainer = Depends(get_services)) -> DocumentComparer:
    return services.document_comparer
