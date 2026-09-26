from app.ingestion.chunking import chunk_text, count_tokens
from app.models.domain import TextBlock


def _long_block(page: int, section: str, n_sentences: int = 60) -> TextBlock:
    text = " ".join(f"This is sentence number {i} in the document body." for i in range(n_sentences))
    return TextBlock(text=text, page=page, section=section)


def test_empty_blocks_returns_no_chunks():
    assert chunk_text([], chunk_size=400, overlap=60, min_tokens=40) == []


def test_single_short_block_yields_one_chunk():
    block = TextBlock(text="A short paragraph.", page=1, section="Intro")
    drafts = chunk_text([block], chunk_size=400, overlap=60, min_tokens=40)
    assert len(drafts) == 1
    assert drafts[0].text == "A short paragraph."
    assert drafts[0].page_start == 1
    assert drafts[0].page_end == 1
    assert drafts[0].section == "Intro"


def test_long_block_splits_into_multiple_chunks_with_overlap():
    block = _long_block(page=1, section="Body", n_sentences=200)
    drafts = chunk_text([block], chunk_size=100, overlap=20, min_tokens=10)
    assert len(drafts) > 1
    for d in drafts:
        assert d.token_count <= 100
        assert d.token_count >= 10 or d is drafts[-1]

    # Overlap: some trailing words of chunk N should reappear at the start of chunk N+1.
    first_chunk_tail_words = drafts[0].text.split()[-5:]
    second_chunk_text = drafts[1].text
    assert any(word in second_chunk_text for word in first_chunk_tail_words)


def test_tiny_trailing_chunk_is_merged_into_previous():
    # Construct text whose length forces a small remainder window.
    block = _long_block(page=2, section="Body", n_sentences=45)
    total_tokens = count_tokens(block.text)
    drafts = chunk_text([block], chunk_size=total_tokens - 5, overlap=0, min_tokens=20)
    # The remainder (5 tokens) is below min_tokens=20, so it must be merged, not
    # emitted as its own chunk.
    assert len(drafts) == 1


def test_chunk_spans_multiple_blocks_records_page_range():
    block1 = TextBlock(text="Content on page one about setup.", page=1, section="Setup")
    block2 = TextBlock(text="Content on page two continuing the setup discussion.", page=2, section="Setup")
    drafts = chunk_text([block1, block2], chunk_size=400, overlap=0, min_tokens=5)
    assert len(drafts) == 1
    assert drafts[0].page_start == 1
    assert drafts[0].page_end == 2
    assert drafts[0].section == "Setup"


def test_adjacent_blocks_are_not_glued_together():
    # A chunk spanning two blocks must keep a whitespace boundary between them,
    # not run the last word of one block into the first word of the next.
    block1 = TextBlock(text="Introduction", page=1, section="Introduction", is_heading=True)
    block2 = TextBlock(
        text="The system uses reciprocal rank fusion.", page=1, section="Introduction"
    )
    drafts = chunk_text([block1, block2], chunk_size=400, overlap=0, min_tokens=1)
    assert len(drafts) == 1
    assert "IntroductionThe" not in drafts[0].text
    assert drafts[0].text == "Introduction\n\nThe system uses reciprocal rank fusion."


def test_char_offsets_locate_multi_block_chunk_in_full_text():
    block1 = TextBlock(text="First paragraph about setup.", page=1, section="Setup")
    block2 = TextBlock(text="Second paragraph about teardown.", page=2, section="Setup")
    full_text = "\n\n".join(b.text for b in (block1, block2))
    drafts = chunk_text([block1, block2], chunk_size=400, overlap=0, min_tokens=1)
    assert len(drafts) == 1
    d = drafts[0]
    assert full_text[d.char_start : d.char_end] == d.text


def test_section_none_for_markdown_style_blocks_without_page():
    block = TextBlock(text="Some markdown paragraph text.", page=None, section="Intro > Details")
    drafts = chunk_text([block], chunk_size=400, overlap=0, min_tokens=5)
    assert drafts[0].page_start is None
    assert drafts[0].page_end is None
    assert drafts[0].section == "Intro > Details"


def test_count_tokens_is_positive_for_nonempty_text():
    assert count_tokens("hello world") > 0
    assert count_tokens("") == 0
