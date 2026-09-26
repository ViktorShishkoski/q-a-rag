"""Structure-aware, token-accurate chunking.

Chunks are built over a sequence of TextBlock (each already tagged with page
and section from the loader) using a sliding window measured in tokens (via
tiktoken cl100k_base - an approximate but offline, dependency-light stand-in
for the real generation-model tokenizer; see docs/ARCHITECTURE.md). Overlap
re-includes the trailing N tokens of the previous chunk so semantic context
isn't lost at boundaries.

char_start/char_end are best-effort offsets into the blocks' concatenated
text (joined with "\\n\\n"), useful for debugging/highlighting; they are not
relied on for citation correctness, which is filename+page+section+text based.
"""

from __future__ import annotations

import tiktoken

from app.models.domain import ChunkDraft, TextBlock

_ENCODING = tiktoken.get_encoding("cl100k_base")

# Blocks are joined with a blank line both in `full_text` (for char offsets) and
# in the token stream, so a chunk that spans a block boundary reads as separate
# paragraphs instead of gluing the last word of one block to the first of the
# next ("results.Chapter Two" -> "results.\n\nChapter Two").
_BLOCK_SEPARATOR = "\n\n"
_SEPARATOR_TOKENS = _ENCODING.encode(_BLOCK_SEPARATOR)


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def encode_tokens(text: str) -> list[int]:
    return _ENCODING.encode(text)


def decode_tokens(tokens: list[int]) -> str:
    return _ENCODING.decode(tokens)


def chunk_text(
    blocks: list[TextBlock],
    *,
    chunk_size: int,
    overlap: int,
    min_tokens: int,
) -> list[ChunkDraft]:
    """Chunk a list of text blocks into token-bounded ChunkDrafts."""
    if not blocks:
        return []

    token_owner: list[int] = []  # token index -> index into `blocks`
    all_tokens: list[int] = []
    for block_idx, block in enumerate(blocks):
        if block_idx > 0:
            # Separator tokens belong (arbitrarily) to the preceding block for
            # page/section attribution; they only ever sit between two blocks.
            all_tokens.extend(_SEPARATOR_TOKENS)
            token_owner.extend([block_idx - 1] * len(_SEPARATOR_TOKENS))
        toks = _ENCODING.encode(block.text)
        all_tokens.extend(toks)
        token_owner.extend([block_idx] * len(toks))

    if not all_tokens:
        return []

    full_text = "\n\n".join(block.text for block in blocks)
    n = len(all_tokens)
    step = max(chunk_size - overlap, 1)

    windows: list[tuple[int, int]] = []
    start = 0
    while start < n:
        end = min(start + chunk_size, n)
        windows.append((start, end))
        if end == n:
            break
        start += step

    # Merge a too-small trailing window into its predecessor rather than
    # emitting a fragment chunk on its own.
    if len(windows) > 1:
        last_start, last_end = windows[-1]
        if last_end - last_start < min_tokens:
            prev_start, _ = windows[-2]
            windows[-2] = (prev_start, last_end)
            windows.pop()

    drafts: list[ChunkDraft] = []
    search_from = 0
    for w_start, w_end in windows:
        text_piece = _ENCODING.decode(all_tokens[w_start:w_end]).strip()
        if not text_piece:
            continue

        needle = text_piece[:40]
        char_start = full_text.find(needle, search_from)
        if char_start == -1:
            char_start = search_from
        char_end = char_start + len(text_piece)
        search_from = max(search_from, char_start + 1)

        owner_start = token_owner[w_start]
        owner_end = token_owner[w_end - 1]
        owned_blocks = blocks[owner_start : owner_end + 1]
        pages = [b.page for b in owned_blocks if b.page is not None]
        section = next((b.section for b in owned_blocks if b.section is not None), None)

        drafts.append(
            ChunkDraft(
                text=text_piece,
                page_start=min(pages) if pages else None,
                page_end=max(pages) if pages else None,
                section=section,
                token_count=count_tokens(text_piece),
                char_start=char_start,
                char_end=char_end,
            )
        )

    return drafts
