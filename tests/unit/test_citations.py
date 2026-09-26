from app.generation.citations import extract_citations
from app.models.domain import Chunk


def _chunk(filename: str, page: int | None, text: str = "some source text") -> Chunk:
    return Chunk(
        chunk_id=f"chunk-{filename}-{page}",
        document_id="d1",
        chunk_index=0,
        filename=filename,
        page_start=page,
        page_end=page,
        section="Intro",
        text=text,
        token_count=3,
        char_start=0,
        char_end=len(text),
    )


def test_extracts_citation_with_page():
    chunks = [_chunk("paper.pdf", 4)]
    answer = "The system uses fusion [paper.pdf p.4] to combine rankings."
    citations = extract_citations(answer, chunks)
    assert len(citations) == 1
    assert citations[0].filename == "paper.pdf"
    assert citations[0].page == 4
    assert citations[0].chunk_id == chunks[0].chunk_id


def test_extracts_citation_without_page_for_markdown():
    chunks = [_chunk("readme.md", None)]
    answer = "Configuration is described in [readme.md]."
    citations = extract_citations(answer, chunks)
    assert len(citations) == 1
    assert citations[0].filename == "readme.md"
    assert citations[0].page is None


def test_drops_citation_not_in_included_chunks():
    chunks = [_chunk("paper.pdf", 4)]
    answer = "This references [other.pdf p.9] which was never shown to the model."
    citations = extract_citations(answer, chunks)
    assert citations == []


def test_drops_citation_with_page_outside_chunk_range():
    chunks = [_chunk("paper.pdf", 4)]
    answer = "This claims [paper.pdf p.99] incorrectly."
    citations = extract_citations(answer, chunks)
    assert citations == []


def test_deduplicates_repeated_citation_tags():
    chunks = [_chunk("paper.pdf", 4)]
    answer = "First mention [paper.pdf p.4] and again [paper.pdf p.4]."
    citations = extract_citations(answer, chunks)
    assert len(citations) == 1


def test_no_citations_when_answer_has_no_tags():
    chunks = [_chunk("paper.pdf", 4)]
    answer = "This answer cites nothing at all."
    assert extract_citations(answer, chunks) == []


def test_multi_page_chunk_matches_page_within_range():
    chunk = Chunk(
        chunk_id="c1",
        document_id="d1",
        chunk_index=0,
        filename="paper.pdf",
        page_start=2,
        page_end=4,
        section=None,
        text="text",
        token_count=1,
        char_start=0,
        char_end=4,
    )
    answer = "See [paper.pdf p.3] for details."
    citations = extract_citations(answer, [chunk])
    assert len(citations) == 1
    assert citations[0].page == 3
