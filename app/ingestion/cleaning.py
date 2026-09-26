"""Pure text-cleaning helpers. No file I/O - unit-testable on plain strings."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

_HYPHEN_LINEBREAK = re.compile(r"(\w)-\n(\w)")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_TRAILING_WS = re.compile(r"[ \t]+\n")
_PAGE_NUMBER_LINE = re.compile(r"^\s*\d{1,4}\s*$")


def clean_text(text: str) -> str:
    """Normalize raw extracted text: de-hyphenate wrapped words, collapse
    whitespace, strip bare page-number lines, normalize unicode to NFKC."""
    text = unicodedata.normalize("NFKC", text)
    text = _HYPHEN_LINEBREAK.sub(r"\1\2", text)
    text = _TRAILING_WS.sub("\n", text)

    lines = [line for line in text.split("\n") if not _PAGE_NUMBER_LINE.match(line)]
    text = "\n".join(lines)

    text = _MULTI_SPACE.sub(" ", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def strip_repeated_headers_footers(pages: list[str], *, min_repeat_ratio: float = 0.6) -> list[str]:
    """Remove lines that repeat identically across a large fraction of pages
    (running headers/footers). Operates on a list of already-extracted page
    texts and returns the same list with such lines removed."""
    if len(pages) < 3:
        return pages

    line_counts: Counter[str] = Counter()
    for page in pages:
        first_last = {line.strip() for line in page.split("\n")[:2] + page.split("\n")[-2:] if line.strip()}
        line_counts.update(first_last)

    threshold = max(2, int(len(pages) * min_repeat_ratio))
    repeated = {line for line, count in line_counts.items() if count >= threshold}
    if not repeated:
        return pages

    cleaned_pages = []
    for page in pages:
        kept = [line for line in page.split("\n") if line.strip() not in repeated]
        cleaned_pages.append("\n".join(kept))
    return cleaned_pages
