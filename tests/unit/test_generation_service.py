from app.generation.mock import MockGenerationProvider
from app.generation.service import GenerationService
from app.models.domain import Chunk, ScoredChunk


def _scored(filename: str, page: int, text: str) -> ScoredChunk:
    chunk = Chunk(
        chunk_id=f"c-{filename}-{page}",
        document_id="d1",
        chunk_index=0,
        filename=filename,
        page_start=page,
        page_end=page,
        section="Intro",
        text=text,
        token_count=len(text.split()),
        char_start=0,
        char_end=len(text),
    )
    return ScoredChunk(chunk=chunk, fused_score=1.0, rank=1)


def test_generation_service_end_to_end_with_mock_provider():
    service = GenerationService(generation_provider=MockGenerationProvider(), context_budget_tokens=500)
    chunks = [_scored("paper.pdf", 4, "Reciprocal rank fusion merges ranked lists.")]

    result = service.answer("How does fusion work?", chunks)

    assert result.answer != ""
    assert result.model == "mock-generation"
    assert result.chunks_used == 1
    assert result.context_truncated is False
    assert len(result.citations) == 1
    assert result.citations[0].filename == "paper.pdf"
    assert result.citations[0].page == 4


def test_generation_service_no_chunks_produces_empty_context_answer():
    service = GenerationService(generation_provider=MockGenerationProvider(), context_budget_tokens=500)
    result = service.answer("Unanswerable question", [])
    assert result.chunks_used == 0
    assert result.citations == []
