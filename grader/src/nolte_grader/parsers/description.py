"""Description section extractor — spec §12.1/4.

Splits normalized text (from ``adf_to_text()``) into the five Nolte template
sections by matching ``## <Section Heading>`` markers.

Section headings recognized (case-insensitive, leading/trailing whitespace
stripped):
  - "Why" (or any heading that starts with "Why")
  - "What" (or any heading that starts with "What")
  - "Acceptance Criteria"
  - "BDD Scenarios" / "Scenarios"
  - "Out of Scope" / "Out Of Scope"

Rules:
  - First occurrence wins; duplicates are ignored.
  - A section whose text body is empty OR whose only content is a
    case-insensitive match of ``"none identified"`` (or ``"none"`` / ``"n/a"``)
    is treated as *populated* for presence purposes — the caller decides
    whether the content is substantive.
  - Text before the first ``##`` heading is collected under the key
    ``"preamble"`` (not a template section; exposed for debugging).
  - Returned dict always contains all five section keys; missing sections
    map to ``None``.

Designed to be input-agnostic: works on ADF-normalized text, HTML-normalized
text, or plain text that already uses ``##`` headings.
"""
from __future__ import annotations

import re
from typing import TypedDict

# ---------------------------------------------------------------------------
# Section mapping
# ---------------------------------------------------------------------------

# Maps canonical section name → list of lowercase heading aliases that map to it.
_SECTION_ALIASES: dict[str, list[str]] = {
    "why": ["why"],
    "what": ["what"],
    "acceptance_criteria": ["acceptance criteria", "ac"],
    "bdd_scenarios": ["bdd scenarios", "scenarios", "bdd"],
    "out_of_scope": ["out of scope", "out-of-scope"],
}

# Pre-compile a regex that maps any normalized heading to a canonical key.
# Each pattern anchors to start-of-heading-text and allows trailing words.
_HEADING_TO_SECTION: list[tuple[re.Pattern[str], str]] = []
for _canon, _aliases in _SECTION_ALIASES.items():
    for _alias in _aliases:
        # Match the alias at start of heading text (allowing trailing content).
        _HEADING_TO_SECTION.append(
            (re.compile(r"^" + re.escape(_alias) + r"(\b|$)", re.IGNORECASE), _canon)
        )

_HEADING_RE = re.compile(r"^## (.+)$", re.MULTILINE)

SECTION_KEYS = ("why", "what", "acceptance_criteria", "bdd_scenarios", "out_of_scope")


class ExtractedSections(TypedDict, total=False):
    preamble: str | None
    why: str | None
    what: str | None
    acceptance_criteria: str | None
    bdd_scenarios: str | None
    out_of_scope: str | None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_sections(text: str | None) -> ExtractedSections:
    """Extract the five Nolte template sections from normalized text.

    Args:
        text: Normalized text produced by ``adf_to_text()``, or any text
              that uses ``## Heading`` markers. ``None`` or empty string
              returns all sections as ``None``.

    Returns:
        ``ExtractedSections`` dict with keys:
        ``preamble``, ``why``, ``what``, ``acceptance_criteria``,
        ``bdd_scenarios``, ``out_of_scope``.
        Missing sections are ``None``; found sections are stripped strings
        (possibly empty string ``""`` if the section body is blank).
    """
    result: ExtractedSections = {
        "preamble": None,
        "why": None,
        "what": None,
        "acceptance_criteria": None,
        "bdd_scenarios": None,
        "out_of_scope": None,
    }
    if not text:
        return result

    # Split text at every ## heading, preserving heading text.
    # Pattern captures: everything before first heading (chunk[0]),
    # then alternating (heading_text, body) pairs.
    parts = _HEADING_RE.split(text)
    # parts[0] = text before first heading (preamble)
    # parts[1], parts[2] = first heading text, body after it
    # parts[3], parts[4] = second heading text, body after it … etc.

    preamble = parts[0].strip() if parts[0].strip() else None
    result["preamble"] = preamble

    # Walk heading/body pairs.
    i = 1
    while i + 1 <= len(parts) - 1:
        heading_text = parts[i].strip()
        body = parts[i + 1].strip()
        i += 2

        canon = _resolve_section(heading_text)
        if canon is None:
            continue
        # First occurrence wins — do not overwrite already-set sections.
        if result.get(canon) is not None:  # type: ignore[literal-required]
            continue
        result[canon] = body  # type: ignore[literal-required]

    return result


def section_present(sections: ExtractedSections, key: str) -> bool:
    """Return True if ``key`` exists in ``sections`` (even if body is empty or 'none identified').

    'Present' means the heading was found in the document.  Whether the
    content is *substantive* is a separate evaluator concern.
    """
    return sections.get(key) is not None  # type: ignore[literal-required]


def section_has_content(sections: ExtractedSections, key: str) -> bool:
    """Return True if the section is present AND has non-empty, non-placeholder content.

    Placeholder patterns treated as empty: ``"none"``, ``"none identified"``,
    ``"n/a"``, ``"na"`` (case-insensitive, stripped).
    """
    body = sections.get(key)  # type: ignore[literal-required]
    if body is None:
        return False
    stripped = body.strip()
    if not stripped:
        return False
    return stripped.lower() not in {"none", "none identified", "n/a", "na"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_section(heading_text: str) -> str | None:
    """Map a raw heading string to a canonical section key, or None if unrecognized."""
    normalized = heading_text.strip()
    for pattern, canon in _HEADING_TO_SECTION:
        if pattern.search(normalized):
            return canon
    return None
