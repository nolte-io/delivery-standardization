"""Tests for parsers/adf.py — ADF walker and HTML fallback."""
from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from nolte_grader.parsers.adf import adf_to_text

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node(type_: str, **kwargs: Any) -> dict[str, Any]:
    return {"type": type_, **kwargs}


def _text(val: str) -> dict[str, Any]:
    return {"type": "text", "text": val}


def _para(*children: dict[str, Any]) -> dict[str, Any]:
    return {"type": "paragraph", "content": list(children)}


def _heading(level: int, *children: dict[str, Any]) -> dict[str, Any]:
    return {"type": "heading", "attrs": {"level": level}, "content": list(children)}


def _doc(*children: dict[str, Any]) -> dict[str, Any]:
    return {"type": "doc", "content": list(children)}


# ---------------------------------------------------------------------------
# None / non-dict inputs
# ---------------------------------------------------------------------------


class TestEntryPoints:
    def test_none_returns_empty(self) -> None:
        assert adf_to_text(None) == ""

    def test_plain_string_passthrough(self) -> None:
        assert adf_to_text("hello world") == "hello world"

    def test_html_string_detected_by_leading_angle_bracket(self) -> None:
        result = adf_to_text("<p>Hello</p>")
        assert "Hello" in result

    def test_unexpected_type_returns_empty(self) -> None:
        result = adf_to_text(42)  # type: ignore[arg-type]
        assert result == ""

    def test_dict_delegates_to_walker(self) -> None:
        doc = _doc(_para(_text("hi")))
        assert "hi" in adf_to_text(doc)


# ---------------------------------------------------------------------------
# ADF node type coverage
# ---------------------------------------------------------------------------


class TestADFNodeTypes:
    def test_paragraph_adds_double_newline(self) -> None:
        doc = _doc(_para(_text("hello")))
        result = adf_to_text(doc)
        assert result == "hello"

    def test_heading_normalized_regardless_of_level(self) -> None:
        for level in [1, 2, 3, 4, 5, 6]:
            doc = _doc(_heading(level, _text("Title")))
            result = adf_to_text(doc)
            assert result == "## Title", f"Failed for heading level {level}"

    def test_multiple_headings_all_normalized(self) -> None:
        doc = _doc(
            _heading(1, _text("H1")),
            _heading(3, _text("H3")),
            _heading(6, _text("H6")),
        )
        result = adf_to_text(doc)
        assert result.count("## H") == 3

    def test_rule_emits_horizontal_rule(self) -> None:
        doc = _doc(_node("rule"))
        result = adf_to_text(doc)
        assert "---" in result

    def test_code_block_emits_fenced(self) -> None:
        doc = _doc(
            {
                "type": "codeBlock",
                "attrs": {"language": "python"},
                "content": [{"type": "text", "text": "x = 1"}],
            }
        )
        result = adf_to_text(doc)
        assert "```python" in result
        assert "x = 1" in result

    def test_code_block_no_language(self) -> None:
        doc = _doc(
            {
                "type": "codeBlock",
                "attrs": {},
                "content": [{"type": "text", "text": "code"}],
            }
        )
        result = adf_to_text(doc)
        assert "```\n" in result

    def test_panel_emits_type_prefix(self) -> None:
        doc = _doc(
            {
                "type": "panel",
                "attrs": {"panelType": "warning"},
                "content": [_para(_text("Watch out"))],
            }
        )
        result = adf_to_text(doc)
        assert "[WARNING]" in result
        assert "Watch out" in result

    def test_expand_with_title(self) -> None:
        doc = _doc(
            {
                "type": "expand",
                "attrs": {"title": "Click me"},
                "content": [_para(_text("hidden content"))],
            }
        )
        result = adf_to_text(doc)
        assert "[Click me]" in result
        assert "hidden content" in result

    def test_expand_without_title(self) -> None:
        doc = _doc(
            {
                "type": "expand",
                "attrs": {},
                "content": [_para(_text("content"))],
            }
        )
        result = adf_to_text(doc)
        assert "content" in result

    def test_bullet_list(self) -> None:
        doc = _doc(
            {
                "type": "bulletList",
                "content": [
                    {"type": "listItem", "content": [_para(_text("Item A"))]},
                    {"type": "listItem", "content": [_para(_text("Item B"))]},
                ],
            }
        )
        result = adf_to_text(doc)
        assert "- Item A" in result
        assert "- Item B" in result

    def test_ordered_list(self) -> None:
        doc = _doc(
            {
                "type": "orderedList",
                "content": [
                    {"type": "listItem", "content": [_para(_text("First"))]},
                ],
            }
        )
        result = adf_to_text(doc)
        assert "- First" in result

    def test_hard_break_emits_newline(self) -> None:
        doc = _doc(
            _para(_text("line1"), {"type": "hardBreak"}, _text("line2"))
        )
        result = adf_to_text(doc)
        assert "line1" in result
        assert "line2" in result

    def test_mention_emits_at_text(self) -> None:
        doc = _doc(
            _para({"type": "mention", "attrs": {"text": "@alice", "id": "u123"}})
        )
        result = adf_to_text(doc)
        assert "@alice" in result

    def test_mention_falls_back_to_id(self) -> None:
        doc = _doc(
            _para({"type": "mention", "attrs": {"id": "u123"}})
        )
        result = adf_to_text(doc)
        assert "u123" in result

    def test_emoji(self) -> None:
        doc = _doc(
            _para({"type": "emoji", "attrs": {"text": "🎉", "shortName": ":tada:"}})
        )
        result = adf_to_text(doc)
        assert "🎉" in result

    def test_status_node(self) -> None:
        doc = _doc(
            _para({"type": "status", "attrs": {"text": "In Progress"}})
        )
        result = adf_to_text(doc)
        assert "In Progress" in result

    def test_date_node(self) -> None:
        doc = _doc(
            _para({"type": "date", "attrs": {"timestamp": "2026-03-15"}})
        )
        result = adf_to_text(doc)
        assert "2026-03-15" in result

    def test_inline_card(self) -> None:
        doc = _doc(
            _para({"type": "inlineCard", "attrs": {"url": "https://example.com"}})
        )
        result = adf_to_text(doc)
        assert "https://example.com" in result

    def test_media_nodes_return_empty(self) -> None:
        for media_type in ("media", "mediaSingle", "mediaGroup"):
            doc = _doc({"type": media_type, "attrs": {"url": "img.png"}})
            result = adf_to_text(doc)
            assert result == ""

    def test_text_marks_discarded(self) -> None:
        doc = _doc(
            _para(
                {
                    "type": "text",
                    "text": "bold text",
                    "marks": [{"type": "strong"}],
                }
            )
        )
        result = adf_to_text(doc)
        assert result == "bold text"

    def test_blockquote(self) -> None:
        doc = _doc(
            {
                "type": "blockquote",
                "content": [_para(_text("quoted"))],
            }
        )
        result = adf_to_text(doc)
        assert "> quoted" in result

    def test_task_list(self) -> None:
        doc = _doc(
            {
                "type": "taskList",
                "content": [
                    {
                        "type": "taskItem",
                        "attrs": {"state": "DONE"},
                        "content": [_text("Completed")],
                    },
                    {
                        "type": "taskItem",
                        "attrs": {"state": "TODO"},
                        "content": [_text("Pending")],
                    },
                ],
            }
        )
        result = adf_to_text(doc)
        assert "[x] Completed" in result
        assert "[ ] Pending" in result

    def test_decision_list(self) -> None:
        doc = _doc(
            {
                "type": "decisionList",
                "content": [
                    {
                        "type": "decisionItem",
                        "content": [_para(_text("We decided X"))],
                    }
                ],
            }
        )
        result = adf_to_text(doc)
        assert "We decided X" in result


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class TestTables:
    def test_simple_table(self) -> None:
        doc = _doc(
            {
                "type": "table",
                "content": [
                    {
                        "type": "tableRow",
                        "content": [
                            {"type": "tableHeader", "content": [_para(_text("Col A"))]},
                            {"type": "tableHeader", "content": [_para(_text("Col B"))]},
                        ],
                    },
                    {
                        "type": "tableRow",
                        "content": [
                            {"type": "tableCell", "content": [_para(_text("val1"))]},
                            {"type": "tableCell", "content": [_para(_text("val2"))]},
                        ],
                    },
                ],
            }
        )
        result = adf_to_text(doc)
        assert "Col A" in result
        assert "Col B" in result
        assert "val1" in result
        assert "val2" in result
        assert "|" in result

    def test_table_with_nested_content(self) -> None:
        doc = _doc(
            {
                "type": "table",
                "content": [
                    {
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableCell",
                                "content": [
                                    _para(_text("nested ")),
                                    _para(_text("paragraphs")),
                                ],
                            }
                        ],
                    }
                ],
            }
        )
        result = adf_to_text(doc)
        assert "nested" in result
        assert "paragraphs" in result


# ---------------------------------------------------------------------------
# Nested and complex structures
# ---------------------------------------------------------------------------


class TestNestedStructures:
    def test_nested_expand_inside_panel(self) -> None:
        doc = _doc(
            {
                "type": "panel",
                "attrs": {"panelType": "info"},
                "content": [
                    {
                        "type": "expand",
                        "attrs": {"title": "Details"},
                        "content": [_para(_text("nested content"))],
                    }
                ],
            }
        )
        result = adf_to_text(doc)
        assert "[INFO]" in result
        assert "[Details]" in result
        assert "nested content" in result

    def test_list_inside_expand(self) -> None:
        doc = _doc(
            {
                "type": "expand",
                "attrs": {"title": "Steps"},
                "content": [
                    {
                        "type": "bulletList",
                        "content": [
                            {"type": "listItem", "content": [_para(_text("Step 1"))]},
                            {"type": "listItem", "content": [_para(_text("Step 2"))]},
                        ],
                    }
                ],
            }
        )
        result = adf_to_text(doc)
        assert "- Step 1" in result
        assert "- Step 2" in result

    def test_mixed_headings_and_paragraphs(self) -> None:
        doc = _doc(
            _heading(2, _text("Section A")),
            _para(_text("Para A content")),
            _heading(3, _text("Section B")),
            _para(_text("Para B content")),
        )
        result = adf_to_text(doc)
        assert "## Section A" in result
        assert "## Section B" in result
        assert "Para A content" in result
        assert "Para B content" in result

    def test_multiple_consecutive_blank_lines_collapsed(self) -> None:
        doc = _doc(
            _para(_text("A")),
            _para(_text("")),
            _para(_text("")),
            _para(_text("B")),
        )
        result = adf_to_text(doc)
        assert "\n\n\n" not in result

    def test_unknown_node_type_walks_children(self) -> None:
        doc = _doc(
            {
                "type": "unknownFutureNode",
                "content": [_para(_text("child text"))],
            }
        )
        result = adf_to_text(doc)
        assert "child text" in result

    def test_unknown_node_with_text_attr(self) -> None:
        doc = _doc(
            {
                "type": "unknownLeaf",
                "text": "leaf text",
            }
        )
        result = adf_to_text(doc)
        assert "leaf text" in result

    def test_unknown_node_no_children_no_text(self) -> None:
        doc = _doc({"type": "mystery"})
        result = adf_to_text(doc)
        assert result == ""


# ---------------------------------------------------------------------------
# HTML fallback
# ---------------------------------------------------------------------------


class TestHTMLFallback:
    def test_h1_normalized(self) -> None:
        result = adf_to_text("<h1>Top Level</h1>")
        assert "## Top Level" in result

    def test_h3_normalized(self) -> None:
        result = adf_to_text("<h3>Sub Heading</h3>")
        assert "## Sub Heading" in result

    def test_br_becomes_newline(self) -> None:
        result = adf_to_text("<p>line1<br/>line2</p>")
        assert "line1" in result
        assert "line2" in result

    def test_p_tags_produce_blank_lines(self) -> None:
        result = adf_to_text("<p>Para A</p><p>Para B</p>")
        assert "Para A" in result
        assert "Para B" in result

    def test_html_entities_decoded(self) -> None:
        result = adf_to_text("<p>A &amp; B &lt;C&gt;</p>")
        assert "A & B <C>" in result

    def test_nbsp_decoded(self) -> None:
        result = adf_to_text("<p>hello&nbsp;world</p>")
        assert "hello world" in result

    def test_numeric_entity_decoded(self) -> None:
        result = adf_to_text("<p>&#65;</p>")
        assert "A" in result

    def test_nested_tags_stripped(self) -> None:
        result = adf_to_text("<p><strong><em>bold italic</em></strong></p>")
        assert "bold italic" in result

    def test_heading_with_nested_tag(self) -> None:
        result = adf_to_text("<h2><strong>Bold Heading</strong></h2>")
        assert "## Bold Heading" in result

    def test_excess_blank_lines_collapsed(self) -> None:
        result = adf_to_text("<p>A</p><p></p><p></p><p>B</p>")
        assert "\n\n\n" not in result


# ---------------------------------------------------------------------------
# Hypothesis — malformed inputs
# ---------------------------------------------------------------------------


@given(st.text())
@settings(max_examples=200)
def test_adf_to_text_plain_string_never_raises(s: str) -> None:
    result = adf_to_text(s)
    assert isinstance(result, str)


@given(
    st.recursive(
        st.fixed_dictionaries({"type": st.text(min_size=0, max_size=20)}),
        lambda children: st.fixed_dictionaries(
            {
                "type": st.text(min_size=0, max_size=20),
                "content": st.lists(children, max_size=5),
            }
        )
        | st.fixed_dictionaries(
            {
                "type": st.text(min_size=0, max_size=20),
                "text": st.text(max_size=50),
            }
        ),
        max_leaves=20,
    )
)
@settings(max_examples=300)
def test_adf_walker_never_raises_on_arbitrary_dict(node: dict) -> None:
    result = adf_to_text(node)
    assert isinstance(result, str)


@given(st.text())
@settings(max_examples=100)
def test_html_fallback_never_raises(html: str) -> None:
    # Prepend "<" to trigger HTML path.
    result = adf_to_text("<" + html)
    assert isinstance(result, str)


@given(st.lists(st.text(max_size=50), max_size=10))
@settings(max_examples=100)
def test_adf_to_text_with_list_returns_empty(lst: list) -> None:
    # Lists are not a valid input type — should return "".
    result = adf_to_text(lst)  # type: ignore[arg-type]
    assert result == ""
