from app.analysis.outline import build_outline, flatten_outline
from app.models.domain import TextBlock


def _heading(text: str, section: str, page: int | None = None) -> TextBlock:
    return TextBlock(text=text, page=page, section=section, is_heading=True)


def _body(text: str, section: str, page: int | None = None) -> TextBlock:
    return TextBlock(text=text, page=page, section=section, is_heading=False)


def test_empty_blocks_yield_empty_outline():
    assert build_outline([]) == []


def test_body_only_blocks_yield_empty_outline():
    assert build_outline([_body("just prose", "Intro", 1)]) == []


def test_markdown_breadcrumbs_build_nested_tree():
    blocks = [
        _heading("Widget Framework", "Widget Framework"),
        _body("intro prose", "Widget Framework"),
        _heading("Installation", "Widget Framework > Installation"),
        _heading("Requirements", "Widget Framework > Installation > Requirements"),
        _heading("Configuration", "Widget Framework > Configuration"),
    ]
    outline = build_outline(blocks)

    assert len(outline) == 1
    root = outline[0]
    assert root.title == "Widget Framework"
    assert root.level == 1
    assert [c.title for c in root.children] == ["Installation", "Configuration"]

    installation = root.children[0]
    assert installation.level == 2
    assert [c.title for c in installation.children] == ["Requirements"]
    assert installation.children[0].level == 3
    assert installation.children[0].section_path == (
        "Widget Framework > Installation > Requirements"
    )


def test_pdf_numeric_prefixes_set_levels():
    blocks = [
        _heading("1. Introduction", "1. Introduction", page=1),
        _heading("2. Method", "2. Method", page=2),
        _heading("2.1 Retrieval", "2.1 Retrieval", page=2),
        _heading("3. Results", "3. Results", page=3),
    ]
    outline = build_outline(blocks)

    assert [n.title for n in outline] == ["1. Introduction", "2. Method", "3. Results"]
    method = outline[1]
    assert method.page == 2
    assert [c.title for c in method.children] == ["2.1 Retrieval"]
    assert method.children[0].level == 2


def test_consecutive_duplicate_headings_are_collapsed():
    blocks = [
        _heading("2. Method", "2. Method", page=2),
        _heading("2. Method", "2. Method", page=3),  # loader re-emitted on next page
        _heading("3. Results", "3. Results", page=4),
    ]
    outline = build_outline(blocks)
    assert [n.title for n in outline] == ["2. Method", "3. Results"]


def test_flatten_outline_is_depth_first():
    blocks = [
        _heading("A", "A"),
        _heading("A > B", "A > B"),
        _heading("A > B > C", "A > B > C"),
        _heading("D", "D"),
    ]
    flat = flatten_outline(build_outline(blocks))
    assert [n.title for n in flat] == ["A", "A > B", "A > B > C", "D"]


def test_headings_without_structure_are_all_top_level():
    blocks = [
        _heading("Overview", "Overview", page=1),
        _heading("Details", "Details", page=2),
    ]
    outline = build_outline(blocks)
    assert [n.level for n in outline] == [1, 1]
    assert all(not n.children for n in outline)
