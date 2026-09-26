"""Ollama generation adapter over httpx.

OLLAMA_NUM_PARALLEL is intentionally NOT sent as a per-request field: Ollama
only honors it as an OS environment variable set before `ollama serve`
starts, not as a runtime /api/generate option. It is read from Settings only
so it can be surfaced in docs/OLLAMA.md and validated at startup - sending it
in the request body would silently do nothing and misrepresent what the
adapter controls.
"""

from __future__ import annotations

import httpx

from app.core.errors import OllamaGenerationError, OllamaModelNotFoundError, OllamaUnavailableError
from app.models.domain import GenerationResult


class OllamaGenerationProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        context_length: int,
        num_predict: int,
        keep_alive: int,
        think: bool,
        timeout_s: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._context_length = context_length
        self._num_predict = num_predict
        self._keep_alive = keep_alive
        self._think = think
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout_s)

    def health_check(self) -> bool:
        try:
            resp = self._client.get("/api/tags")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def _list_models(self) -> list[str]:
        try:
            resp = self._client.get("/api/tags")
        except httpx.ConnectError as exc:
            raise OllamaUnavailableError(f"Could not reach Ollama at {self.base_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise OllamaUnavailableError(f"Ollama request to /api/tags timed out: {exc}") from exc

        if resp.status_code != 200:
            raise OllamaUnavailableError(f"Ollama /api/tags returned {resp.status_code}: {resp.text}")

        data = resp.json()
        return [m["name"] for m in data.get("models", [])]

    def is_model_available(self, model: str) -> bool:
        available = self._list_models()
        return model in available or any(name.split(":")[0] == model for name in available)

    def generate(
        self, prompt: str, *, system: str | None = None, max_tokens: int | None = None
    ) -> GenerationResult:
        if not self.is_model_available(self.model):
            raise OllamaModelNotFoundError(
                f"Model '{self.model}' is not available in Ollama. "
                f"Pull it first with: ollama pull {self.model}"
            )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": self._think,
            "keep_alive": self._keep_alive,
            "options": {
                "num_ctx": self._context_length,
                "num_predict": max_tokens or self._num_predict,
            },
        }
        if system:
            payload["system"] = system

        try:
            resp = self._client.post("/api/generate", json=payload)
        except httpx.ConnectError as exc:
            raise OllamaUnavailableError(f"Could not reach Ollama at {self.base_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise OllamaUnavailableError(f"Ollama /api/generate request timed out: {exc}") from exc

        if resp.status_code != 200:
            raise OllamaGenerationError(f"Ollama /api/generate returned {resp.status_code}: {resp.text}")

        data = resp.json()
        return GenerationResult(
            text=data.get("response", ""),
            model=self.model,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
        )
