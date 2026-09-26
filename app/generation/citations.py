"""Extract citations from generated answer text.

Only tags that resolve against a chunk actually included in the context are
kept - a citation-looking tag the model hallucinated (referencing a filename
or page never shown to it) is dropped and logged, never fabricated into a
Citation object.
"""

from __future__ import annotations

import logging

from app.generation.prompts import CITATION_TAG_PATTERN
from app.models.domain import Chunk, Citation

logger = logging.getLogger(__name__)


def extract_citations(answer_text: str, included_chunks: list[Chunk]) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, int | None]] = set()

    for match in CITATION_TAG_PATTERN.finditer(answer_text):
        filename = match.group(1).strip()
        page = int(match.group(2)) if match.group(2) else None

        candidates = [c for c in included_chunks if c.filename == filename]
        if page is not None:
            candidates = [c for c in candidates if c.page_start is not None and c.page_start <= page <= (c.page_end or c.page_start)]

        if not candidates:
            logger.warning("Dropping unresolvable citation tag: %s", match.group(0))
            continue

        chunk = candidates[0]
        key = (chunk.filename, page)
        if key in seen:
            continue
        seen.add(key)

        citations.append(
            Citation(
                document_id=chunk.document_id,
                filename=chunk.filename,
                page=page if page is not None else chunk.page_start,
                section=chunk.section,
                chunk_id=chunk.chunk_id,
                quote=chunk.text[:120],
                char_start=chunk.char_start,
                char_end=chunk.char_end,
            )
        )

    return citations
