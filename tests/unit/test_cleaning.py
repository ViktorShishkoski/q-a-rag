from app.ingestion.cleaning import clean_text, strip_repeated_headers_footers


def test_dehyphenates_line_wrapped_words():
    assert clean_text("This is a demon-\nstration of hyphenation.") == "This is a demonstration of hyphenation."


def test_collapses_multiple_blank_lines():
    result = clean_text("Paragraph one.\n\n\n\n\nParagraph two.")
    assert result == "Paragraph one.\n\nParagraph two."


def test_collapses_repeated_spaces():
    assert clean_text("Too    many     spaces") == "Too many spaces"


def test_strips_bare_page_number_lines():
    result = clean_text("Some content.\n42\nMore content.")
    assert "42" not in result.split("\n")


def test_normalizes_unicode_nfkc():
    # Full-width digits normalize to ASCII under NFKC. Embedded in a sentence
    # so the standalone-page-number stripping rule doesn't also apply here.
    assert clean_text("Section １２３ overview.") == "Section 123 overview."


def test_strips_leading_trailing_whitespace():
    assert clean_text("   padded text   ") == "padded text"


def test_strip_repeated_headers_footers_removes_common_lines():
    pages = [
        "Running Header\nContent for page one.\nPage Footer",
        "Running Header\nContent for page two.\nPage Footer",
        "Running Header\nContent for page three.\nPage Footer",
    ]
    cleaned = strip_repeated_headers_footers(pages)
    for page in cleaned:
        assert "Running Header" not in page
        assert "Page Footer" not in page
    assert "Content for page one." in cleaned[0]


def test_strip_repeated_headers_footers_noop_for_few_pages():
    pages = ["only page"]
    assert strip_repeated_headers_footers(pages) == pages
