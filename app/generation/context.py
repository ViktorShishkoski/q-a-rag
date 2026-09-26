"""Token-budgeted context assembly.

Greedily includes ranked chunks until the next one would exceed the token
budget. Never sends an empty context: if even the top chunk doesn't fit
whole, it is truncated to the budget and included anyway (flagged truncated).
"""

from __future__ import annotations

from app.ingestion.chunking import count_tokens, decode_tokens, encode_tokens
from app.models.domain import Chunk, ContextBundle, ScoredChunk


def render_chunk(chunk: Chunk) -> str:
    if chunk.page_start is not None:
        page_label = f" p.{chunk.page_start}" if chunk.page_start == chunk.page_end else f" p.{chunk.page_start}-{chunk.page_end}"
        tag = f"[{chunk.filename}{page_label}]"
    else:
        tag = f"[{chunk.filename}]"
    return f"{tag}\n{chunk.text}\n---\n"


def build_context(chunks: list[ScoredChunk], budget_tokens: int) -> ContextBundle:
    if not chunks:
        return ContextBundle(text="", included_chunks=[], truncated=False)

    included: list[Chunk] = []
    pieces: list[str] = []
    used = 0

    for scored in chunks:
        piece = render_chunk(scored.chunk)
        piece_tokens = count_tokens(piece)

        if used + piece_tokens <= budget_tokens:
            pieces.append(piece)
            included.append(scored.chunk)
            used += piece_tokens
            continue

        if not included:
            # Nothing fits yet - truncate the top chunk down to the budget
            # rather than sending an empty context.
            truncated_chunk = _truncate_chunk(scored.chunk, budget_tokens)
            piece = render_chunk(truncated_chunk)
            return ContextBundle(text=piece, included_chunks=[truncated_chunk], truncated=True)

        break

    return ContextBundle(text="".join(pieces), included_chunks=included, truncated=len(included) < len(chunks))


def _truncate_chunk(chunk: Chunk, budget_tokens: int) -> Chunk:
    tag_overhead = count_tokens(f"[{chunk.filename} p.999-999]\n\n---\n")
    available = max(budget_tokens - tag_overhead, 10)
    tokens = encode_tokens(chunk.text)[:available]
    truncated_text = decode_tokens(tokens)
    return chunk.model_copy(update={"text": truncated_text, "token_count": len(tokens)})
