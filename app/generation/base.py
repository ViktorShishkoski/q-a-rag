from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models.domain import GenerationResult


@runtime_checkable
class GenerationProvider(Protocol):
    def generate(self, prompt: str, *, system: str | None = None, max_tokens: int | None = None) -> GenerationResult: ...

    def health_check(self) -> bool: ...

    def is_model_available(self, model: str) -> bool: ...
