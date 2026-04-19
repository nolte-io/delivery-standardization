"""ADF (Atlassian Document Format) walker and HTML fallback — spec §12.1/4.

Converts a Jira description into normalized text where:
  - All heading levels emit as ``## <text>`` for uniform section matching.
  - Paragraphs are separated by blank lines (``\\n\\n``).
  - Tables are flattened to pipe-delimited rows.
  - Panels and expands are annotated with a bracketed type prefix.
  - Inline formatting marks (bold, italic, code) are discarded — only text
    content is preserved for judge consumption.
  - Unknown ADF node types: walk children if present, otherwise skip.

Two entry points, same output shape:
  - ``adf_to_text(doc)`` — handles ADF dict, HTML str, plain str, or None.

The section extractor (``parsers/description.py``) operates on this
normalized form. Keep them separate: the ADF walker never knows what
sections mean; the section extractor never knows what ADF looks like.

Known Phase 1 limitation (approved 2026-04-19): heading normalization
loses heading level. If an author uses ``##`` inside a template section
(e.g., BDD sub-headings), the section extractor will truncate that section
early. Watch during calibration; revisit only if it bites real grader runs.
"""
from __future__ import annotations

import re
from typing import Any

from nolte_grader.core.logging import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def adf_to_text(doc: dict[str, Any] | str | None) -> str:
    """Convert an ADF document, HTML string, or plain text to normalized text.

    Args:
        doc: One of:
             - ``dict`` — raw ADF document from ``fields.description``.
             - HTML ``str`` — from ``renderedFields.description``.
             - Plain ``str`` — changelog description snapshots (already text).
             - ``None`` — empty description; returns empty string.

    Returns:
        Normalized text string. Headings are ``## <text>``. Paragraphs
        separated by ``\\n\\n``. Safe to pass directly to ``extract_sections()``.
    """
    if doc is None:
        return ""
    if isinstance(doc, dict):
        return _walk_doc(doc)
    if isinstance(doc, str):
        if doc.lstrip().startswith("<"):
            return _html_to_text(doc)
        return doc
    log.warning("adf_to_text received unexpected type", doc_type=type(doc).__name__)
    return ""


# ---------------------------------------------------------------------------
# ADF walker
# ---------------------------------------------------------------------------


def _walk_doc(node: dict[str, Any]) -> str:
    result = _walk_node(node)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _walk_node(node: dict[str, Any]) -> str:  # noqa: PLR0911, PLR0912
    """Recursively walk one ADF node and return its normalized text."""
    if not isinstance(node, dict):
        return ""

    node_type: str = node.get("type", "")
    content: list[dict[str, Any]] = node.get("content") or []
    attrs: dict[str, Any] = node.get("attrs") or {}
    text_val: str = node.get("text") or ""

    # --- Document root ---
    if node_type == "doc":
        return _join_blocks(content)

    # --- Block nodes ---
    if node_type == "paragraph":
        return _join_inline(content) + "\n\n"

    if node_type == "heading":
        return f"## {_join_inline(content)}\n\n"

    if node_type == "rule":
        return "---\n\n"

    if node_type == "blockquote":
        inner = _join_blocks(content)
        quoted = "\n".join(f"> {line}" for line in inner.splitlines())
        return quoted + "\n\n"

    if node_type == "codeBlock":
        lang = attrs.get("language") or ""
        code = "".join(c.get("text") or "" for c in content)
        return f"```{lang}\n{code}\n```\n\n"

    if node_type == "panel":
        panel_type = (attrs.get("panelType") or "info").upper()
        return f"[{panel_type}]\n{_join_blocks(content)}\n"

    if node_type in ("expand", "nestedExpand"):
        title = attrs.get("title") or ""
        prefix = f"[{title}]\n" if title else ""
        return prefix + _join_blocks(content)

    # --- Lists ---
    if node_type in ("bulletList", "orderedList"):
        items = [_walk_node(c) for c in content]
        return "\n".join(items) + "\n\n"

    if node_type == "listItem":
        inner = _join_blocks(content).strip()
        return f"- {inner}"

    if node_type == "taskList":
        return "\n".join(_walk_node(c) for c in content) + "\n\n"

    if node_type == "taskItem":
        state = attrs.get("state") or "TODO"
        checkbox = "[x]" if state == "DONE" else "[ ]"
        return f"{checkbox} {_join_inline(content)}"

    if node_type in ("decisionList", "decisionItem"):
        return _join_blocks(content)

    # --- Tables ---
    if node_type == "table":
        return _walk_table(content) + "\n\n"

    if node_type == "tableRow":
        cells = [_walk_node(c).strip() for c in content]
        return "| " + " | ".join(cells) + " |"

    if node_type in ("tableCell", "tableHeader"):
        return _join_blocks(content).strip()

    # --- Inline nodes ---
    if node_type == "text":
        # Marks (bold, italic, code, link, etc.) are discarded — text only.
        return text_val

    if node_type == "hardBreak":
        return "\n"

    if node_type == "mention":
        return f"@{attrs.get('text') or attrs.get('id') or ''}"

    if node_type == "emoji":
        return attrs.get("text") or attrs.get("shortName") or ""

    if node_type == "status":
        return attrs.get("text") or ""

    if node_type == "date":
        return attrs.get("timestamp") or ""

    if node_type in ("inlineCard", "blockCard"):
        return attrs.get("url") or ""

    if node_type in ("media", "mediaSingle", "mediaGroup"):
        return ""

    # --- Unknown type ---
    if content:
        log.debug("unknown ADF node type — walking children", node_type=node_type)
        return _join_blocks(content)
    if text_val:
        return text_val
    return ""


def _join_blocks(nodes: list[dict[str, Any]]) -> str:
    return "".join(_walk_node(n) for n in nodes)


def _join_inline(nodes: list[dict[str, Any]]) -> str:
    return "".join(_walk_node(n) for n in nodes)


def _walk_table(rows: list[dict[str, Any]]) -> str:
    return "\n".join(_walk_node(r) for r in rows)


# ---------------------------------------------------------------------------
# HTML fallback
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>", re.IGNORECASE | re.DOTALL)
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_P_OPEN_RE = re.compile(r"<p[^>]*>", re.IGNORECASE)
_P_CLOSE_RE = re.compile(r"</p\s*>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_ENTITY_RE = re.compile(r"&([a-zA-Z]+|#\d+);")

_HTML_ENTITIES: dict[str, str] = {
    "amp": "&",
    "lt": "<",
    "gt": ">",
    "quot": '"',
    "apos": "'",
    "nbsp": " ",
    "ndash": "–",
    "mdash": "—",
    "hellip": "…",
    "lsquo": "\u2018",
    "rsquo": "\u2019",
    "ldquo": "\u201c",
    "rdquo": "\u201d",
}


def _html_to_text(html: str) -> str:
    """Convert rendered Jira HTML to normalized text with ``## heading`` re-emit."""
    def _heading_sub(m: re.Match[str]) -> str:
        inner = _TAG_RE.sub("", m.group(1)).strip()
        return f"\n## {inner}\n\n"

    text = _HEADING_RE.sub(_heading_sub, html)
    text = _BR_RE.sub("\n", text)
    text = _P_OPEN_RE.sub("", text)
    text = _P_CLOSE_RE.sub("\n\n", text)
    text = _TAG_RE.sub("", text)

    def _entity_sub(m: re.Match[str]) -> str:
        name = m.group(1)
        if name.startswith("#"):
            try:
                return chr(int(name[1:]))
            except ValueError:
                return m.group(0)
        return _HTML_ENTITIES.get(name.lower(), m.group(0))

    text = _ENTITY_RE.sub(_entity_sub, text)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
