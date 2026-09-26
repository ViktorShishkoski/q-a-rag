"""Document outline (table-of-contents) extraction.

Pure function over the loader's TextBlock stream - no I/O, unit-testable on
plain data. Consumes the `is_heading` blocks the loaders already produce
(PDF: font-size heuristic; Markdown: heading-stack scanner) and turns them
into a nested OutlineNode tree.

Level detection:
- Markdown headings carry a " > "-joined breadcrumb in `section`; depth is the
  number of segments.
- PDF headings are flat (section == heading text). A leading numeric prefix
  ("2." -> level 2, "3.1.4" -> level 3) sets depth; otherwise level 1.
"""

from __future__ import annotations

import re

from app.models.domain import OutlineNode, TextBlock

_NUMERIC_PREFIX = re.compile(r"^\s*(\d+(?:\.\d+)*)[.)]?\s+\S")


def _level_for(section_path: str, title: str) -> int:
    if " > " in section_path:
        return section_path.count(" > ") + 1
    match = _NUMERIC_PREFIX.match(title)
    if match:
        return match.group(1).count(".") + 1
    return 1


def build_outline(blocks: list[TextBlock]) -> list[OutlineNode]:
    """Build a nested outline from the heading blocks in `blocks`.

    Returns the list of top-level nodes. Non-heading blocks are ignored.
    Consecutive duplicate headings (same breadcrumb) are collapsed - the PDF
    loader can re-emit an unchanged running section on a later page.
    """
    roots: list[OutlineNode] = []
    # stack of (level, node) for the current open path down the tree
    stack: list[tuple[int, OutlineNode]] = []
    last_section_path: str | None = None

    for block in blocks:
        if not block.is_heading:
            continue
        title = block.text.strip()
        if not title:
            continue
        section_path = (block.section or title).strip()
        if section_path == last_section_path:
            continue
        last_section_path = section_path

        level = _level_for(section_path, title)
        node = OutlineNode(
            title=title,
            level=level,
            page=block.page,
            section_path=section_path,
        )

        while stack and stack[-1][0] >= level:
            stack.pop()

        if stack:
            stack[-1][1].children.append(node)
        else:
            roots.append(node)
        stack.append((level, node))

    return roots


def flatten_outline(nodes: list[OutlineNode]) -> list[OutlineNode]:
    """Depth-first flattening - handy for tests and simple list rendering."""
    out: list[OutlineNode] = []
    for node in nodes:
        out.append(node)
        out.extend(flatten_outline(node.children))
    return out
