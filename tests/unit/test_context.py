from app.generation.context import build_context, render_chunk
from app.ingestion.chunking import count_tokens
from app.models.domain import Chunk, ScoredChunk


def _chunk(chunk_id: str, text: str, page: int | None = 1) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id="d1",
        chunk_index=0,
        filename="doc.pdf" if page is not None else "doc.md",
        page_start=page,
        page_end=page,
        section="Intro",
        text=text,
        token_count=count_tokens(text),
        char_start=0,
        char_end=len(text),
    )


def _scored(chunk: Chunk, rank: int) -> ScoredChunk:
    return ScoredChunk(chunk=chunk, fused_score=1.0, rank=rank)


def test_empty_chunks_returns_empty_context():
    result = build_context([], budget_tokens=500)
    assert result.text == ""
    assert result.included_chunks == []
    assert result.truncated is False


def test_all_chunks_fit_within_budget():
    chunks = [_scored(_chunk("c1", "short text one"), 1), _scored(_chunk("c2", "short text two"), 2)]
    result = build_context(chunks, budget_tokens=1000)
    assert len(result.included_chunks) == 2
    assert result.truncated is False
    assert "doc.pdf p.1" in result.text


def test_stops_including_once_budget_exceeded():
    big_text = " ".join(f"word{i}" for i in range(500))
    chunks = [_scored(_chunk("c1", big_text), 1), _scored(_chunk("c2", "small"), 2)]
    result = build_context(chunks, budget_tokens=count_tokens(render_chunk(chunks[0].chunk)) + 2)
    assert len(result.included_chunks) == 1
    assert result.truncated is True


def test_truncates_single_oversized_top_chunk_rather_than_send_empty():
    big_text = " ".join(f"word{i}" for i in range(2000))
    chunks = [_scored(_chunk("c1", big_text), 1)]
    result = build_context(chunks, budget_tokens=50)
    assert len(result.included_chunks) == 1
    assert result.truncated is True
    assert result.text != ""
    assert count_tokens(result.included_chunks[0].text) <= 50


def test_render_chunk_uses_page_range_for_multi_page_chunk():
    chunk = Chunk(
        chunk_id="c1",
        document_id="d1",
        chunk_index=0,
        filename="paper.pdf",
        page_start=2,
        page_end=3,
        section=None,
        text="spans two pages",
        token_count=4,
        char_start=0,
        char_end=10,
    )
    rendered = render_chunk(chunk)
    assert "[paper.pdf p.2-3]" in rendered


def test_render_chunk_no_page_tag_for_markdown():
    chunk = _chunk("c1", "markdown content", page=None)
    rendered = render_chunk(chunk)
    assert "[doc.md]" in rendered
    assert "p." not in rendered.split("\n")[0]
