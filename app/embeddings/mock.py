"""Deterministic, dependency-free embedding provider for offline tests.

Vectors are derived from a hash of the text so the same input always yields
the same output (needed for reproducible retrieval-pipeline tests), without
pulling in torch/sentence-transformers.
"""

from __future__ import annotations

import hashlib
import math


class MockEmbeddingProvider:
    dimension: int = 32
    model_name: str = "mock-hash-embedding"

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dimension
        tokens = text.lower().split() or [text.lower()]
        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            for i in range(self.dimension):
                vec[i] += digest[i % len(digest)] / 255.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    def health_check(self) -> bool:
        return True
