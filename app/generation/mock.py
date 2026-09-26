"""Deterministic generation provider for offline tests.

Returns text that references the filenames of whatever chunks were embedded
in the prompt (parsed back out of the prompt's citation tags), so citation
extraction is exercisable end-to-end without a live Ollama.
"""

from __future__ import annotations

from app.generation.prompts import CITATION_TAG_PATTERN
from app.models.domain import GenerationResult


class MockGenerationProvider:
    model_name: str = "mock-generation"

    def generate(self, prompt: str, *, system: str | None = None, max_tokens: int | None = None) -> GenerationResult:
        tags = [m.group(0) for m in CITATION_TAG_PATTERN.finditer(prompt)]
        if tags:
            body = " ".join(f"This is answered by {tag}." for tag in tags[:2])
        else:
            body = "The provided context does not contain the answer."
        return GenerationResult(text=body, model=self.model_name, prompt_tokens=len(prompt.split()), completion_tokens=len(body.split()))

    def health_check(self) -> bool:
        return True

    def is_model_available(self, model: str) -> bool:
        return True
