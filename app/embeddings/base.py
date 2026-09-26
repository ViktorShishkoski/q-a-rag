"""Embedding provider interface. Every concrete provider (sentence-transformers,
Ollama, mock) implements this Protocol so the rest of the app never depends on
a specific embedding backend - swap via EMBEDDING_PROVIDER."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    dimension: int
    model_name: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of chunk texts for indexing."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string for retrieval."""
        ...

    def health_check(self) -> bool:
        """Return True if the provider is ready to embed (model loaded / service reachable)."""
        ...
