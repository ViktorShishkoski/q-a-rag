"""Ties context assembly, prompting, generation, and citation extraction
together. Not in the user's literal required file list, but added (like
generation/mock.py) so the API layer stays a thin translation of HTTP <->
service calls rather than duplicating orchestration logic."""

from __future__ import annotations

from app.generation.base import GenerationProvider
from app.generation.citations import extract_citations
from app.generation.context import build_context
from app.generation.prompts import SYSTEM_PROMPT, build_prompt
from app.models.domain import Citation, ScoredChunk


class AnswerResult:
    def __init__(
        self,
        answer: str,
        citations: list[Citation],
        model: str,
        context_truncated: bool,
        chunks_used: int,
        included_chunk_ids: list[str],
    ) -> None:
        self.answer = answer
        self.citations = citations
        self.model = model
        self.context_truncated = context_truncated
        self.chunks_used = chunks_used
        self.included_chunk_ids = included_chunk_ids


class GenerationService:
    def __init__(self, *, generation_provider: GenerationProvider, context_budget_tokens: int) -> None:
        self._provider = generation_provider
        self._budget = context_budget_tokens

    def answer(self, question: str, retrieved_chunks: list[ScoredChunk]) -> AnswerResult:
        context = build_context(retrieved_chunks, self._budget)
        prompt = build_prompt(question, context)
        result = self._provider.generate(prompt, system=SYSTEM_PROMPT)
        citations = extract_citations(result.text, context.included_chunks)
        return AnswerResult(
            answer=result.text,
            citations=citations,
            model=result.model,
            context_truncated=context.truncated,
            chunks_used=len(context.included_chunks),
            included_chunk_ids=[c.chunk_id for c in context.included_chunks],
        )
