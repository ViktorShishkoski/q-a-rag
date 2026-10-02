"""Default embedding provider: a local sentence-transformers model.

Weights are downloaded from Hugging Face on first use and cached locally
under the standard HF cache directory - a one-time network fetch, not a
per-run download, and distinct from the "never auto-pull Ollama models" rule
(see docs/OLLAMA.md for the full tradeoff discussion vs. EMBEDDING_PROVIDER=ollama).
"""

from __future__ import annotations

import threading
from typing import Any

from app.core.errors import EmbeddingError


class SentenceTransformersEmbeddingProvider:
    def __init__(self, model_name: str, expected_dim: int, batch_size: int = 32) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model: Any = None
        # The startup warm-up thread and a request thread may race to load.
        self._load_lock = threading.Lock()
        self._expected_dim = expected_dim
        self.dimension = expected_dim

    def _load(self) -> Any:  # noqa: ANN202
        with self._load_lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                model = SentenceTransformer(self.model_name)
                get_dim = (
                    getattr(model, "get_embedding_dimension", None)
                    or model.get_sentence_embedding_dimension
                )
                actual_dim = get_dim()
                if actual_dim != self._expected_dim:
                    raise EmbeddingError(
                        f"EMBEDDING_DIM={self._expected_dim} does not match the actual "
                        f"output dimension of '{self.model_name}' ({actual_dim}). "
                        "Update EMBEDDING_DIM in your .env to match."
                    )
                self.dimension = actual_dim
                self._model = model
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        embeddings = model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        model = self._load()
        embedding = model.encode([text], normalize_embeddings=True, show_progress_bar=False)
        return embedding[0].tolist()

    def health_check(self) -> bool:
        try:
            self._load()
            return True
        except Exception:
            return False
