"""System prompt and citation-tag format.

CITATION_TAG_PATTERN is the single source of truth for the citation format,
shared between prompt rendering (generation/context.py::render_chunk) and
extraction (generation/citations.py) so the two can never drift apart.
"""

from __future__ import annotations

import re

from app.models.domain import ContextBundle

SYSTEM_PROMPT = (
    "You are a technical documentation assistant. Answer only using the provided context. "
    "Cite every factual claim using the exact source tag shown before each excerpt, in the "
    "form [filename p.N] for PDFs or [filename] for documents without pages. "
    "If the context does not contain the answer, say so explicitly instead of guessing."
)

# Matches "[filename p.N]", "[filename p.N-M]", or "[filename]".
CITATION_TAG_PATTERN = re.compile(r"\[([^\[\]]+?)(?:\s+p\.(\d+)(?:-(\d+))?)?\]")


def build_prompt(question: str, context: ContextBundle) -> str:
    return f"Context:\n{context.text}\nQuestion: {question}\nAnswer:"
