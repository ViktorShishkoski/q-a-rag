from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Ollama (generation) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_generation_model: str = "qwen3:1.7b"
    ollama_context_length: int = 2048
    ollama_num_predict: int = 256
    ollama_num_parallel: int = 1
    ollama_keep_alive: int = 300
    ollama_think: bool = False
    ollama_timeout_s: float = 60.0

    # --- Embeddings ---
    embedding_provider: Literal["sentence_transformers", "ollama", "mock"] = "sentence_transformers"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_ollama_model: str = "nomic-embed-text"
    embedding_dim: int = 384
    embedding_batch_size: int = 32

    # --- Storage ---
    qdrant_path: Path = Path("./data/indexes/qdrant")
    qdrant_collection: str = "documents"
    bm25_index_path: Path = Path("./data/indexes/bm25/index.pkl")
    manifest_path: Path = Path("./data/indexes/manifest.json")
    raw_storage_path: Path = Path("./data/raw")
    # Per-document derived artefacts (outline, extracted tables): one JSON
    # sidecar per document, named <document_id>.<kind>.json.
    processed_storage_path: Path = Path("./data/processed")

    # --- Document analysis (V2 seams; all default off - NoOp implementations) ---
    ocr_enabled: bool = False
    table_extraction_enabled: bool = False
    structured_extraction_enabled: bool = False
    compare_enabled: bool = False

    # --- Chunking ---
    chunk_size_tokens: int = 400
    chunk_overlap_tokens: int = 60
    chunk_min_tokens: int = 40

    # --- Retrieval ---
    retrieval_candidate_k: int = 20
    rrf_k: int = 60
    rerank_enabled: bool = False
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_candidate_pool: int = 20

    # --- Generation / context budgeting ---
    generation_provider: Literal["ollama", "mock"] = "ollama"
    prompt_overhead_tokens: int = 150
    context_safety_margin: float = 0.85

    # --- Misc ---
    log_level: str = "INFO"
    # Load the embedding model and the LLM in a background thread at server start
    # so the first query doesn't pay the (tens of seconds) cold-load cost.
    warmup_on_startup: bool = True


def get_settings() -> Settings:
    return Settings()
