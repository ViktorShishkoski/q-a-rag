"""Alternative embedding provider that routes through Ollama's /api/embed,
avoiding a torch dependency entirely. Requires the user to `ollama pull
<model>` themselves - this app never pulls Ollama models automatically."""

from __future__ import annotations

import httpx

from app.core.errors import EmbeddingError, OllamaUnavailableError


class OllamaEmbeddingProvider:
    def __init__(
        self,
        base_url: str,
        model_name: str,
        expected_dim: int,
        timeout_s: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.dimension = expected_dim
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout_s)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        try:
            resp = self._client.post("/api/embed", json={"model": self.model_name, "input": texts})
        except httpx.ConnectError as exc:
            raise OllamaUnavailableError(
                f"Could not reach Ollama at {self.base_url} for embeddings: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise OllamaUnavailableError(f"Ollama embedding request timed out: {exc}") from exc

        if resp.status_code != 200:
            raise EmbeddingError(f"Ollama /api/embed returned {resp.status_code}: {resp.text}")

        data = resp.json()
        embeddings = data.get("embeddings")
        if not embeddings:
            raise EmbeddingError(f"Ollama /api/embed response missing 'embeddings': {data}")
        return embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]

    def health_check(self) -> bool:
        try:
            resp = self._client.get("/api/tags")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
