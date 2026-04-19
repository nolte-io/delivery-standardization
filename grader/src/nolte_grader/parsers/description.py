"""Description section extractor — spec §12.1/4.

Splits normalized text (from ``adf_to_text()``) into the five Nolte template
sections by matching ``## <Section Heading>`` markers.

Section headings match the actual Nolte Jira template (spec §5.3, §10):
  - "Business Objective" — on Epics (Y1)
  - "Observable Impact" — on Stories (Y2)
  - "Acceptance Criteria" / "AC"
  - "Scenarios" / "BDD Scenarios" / "BDD"
  - "Risks"

Rules:
  - First occurrence wins; duplicates are ignored.
  - A section whose body is empty OR whose only content is a placeholder
    ("none identified", "n/a", etc.) is still *present* — ``section_present``
    returns True.  Whether the content is *substantive* is a separate evaluator
    concern (see ``section_has_content``).
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
# Section mapping — canonical keys match spec §5.3 / §10 template headings
# ---------------------------------------------------------------------------

# Maps canonical key → list of lowercase heading aliases.
_SECTION_ALIASES: dict[str, list[str]] = {
    "business_objective": ["business objective"],
    "observable_impact": ["observable impact"],
    "acceptance_criteria": ["acceptance criteria", "ac"],
    "scenarios": ["scenarios", "bdd scenarios", "bdd"],
    "risks": ["risks"],
}

_HEADING_TO_SECTION: list[tuple[re.Pattern[str], str]] = []
for _canon, _aliases in _SECTION_ALIASES.items():
    for _alias in _aliases:
        _HEADING_TO_SECTION.append(
            (re.compile(r"^" + re.escape(_alias) + r"(\b|$)", re.IGNORECASE), _canon)
        )

_HEADING_RE = re.compile(r"^## (.+)$", re.MULTILINE)

SECTION_KEYS = (
    "business_objective",
    "observable_impact",
    "acceptance_criteria",
    "scenarios",
    "risks",
)


class ExtractedSections(TypedDict, total=False):
    preamble: str | None
    business_objective: str | None
    observable_impact: str | None
    acceptance_criteria: str | None
    scenarios: str | None
    risks: str | None


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
        ``preamble``, ``business_objective``, ``observable_impact``,
        ``acceptance_criteria``, ``scenarios``, ``risks``.
        Missing sections are ``None``; found sections are stripped strings
        (possibly empty string ``""`` if the section body is blank).
    """
    result: ExtractedSections = {
        "preamble": None,
        "business_objective": None,
        "observable_impact": None,
        "acceptance_criteria": None,
        "scenarios": None,
        "risks": None,
    }
    if not text:
        return result

    parts = _HEADING_RE.split(text)
    preamble = parts[0].strip() if parts[0].strip() else None
    result["preamble"] = preamble

    i = 1
    while i + 1 <= len(parts) - 1:
        heading_text = parts[i].strip()
        body = parts[i + 1].strip()
        i += 2

        canon = _resolve_section(heading_text)
        if canon is None:
            continue
        if result.get(canon) is not None:  # type: ignore[literal-required]
            continue
        result[canon] = body  # type: ignore[literal-required]

    return result


def section_present(sections: ExtractedSections, key: str) -> bool:
    """Return True if ``key`` was found in the document (even if body is placeholder)."""
    return sections.get(key) is not None  # type: ignore[literal-required]


def section_has_content(sections: ExtractedSections, key: str) -> bool:
    """Return True if section is present AND has non-empty, non-placeholder content.

    Placeholders treated as empty: ``"none"``, ``"none identified"``,
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
    """Map a raw heading string to a canonical key, or None if unrecognized."""
    normalized = heading_text.strip()
    for pattern, canon in _HEADING_TO_SECTION:
        if pattern.search(normalized):
            return canon
    return None
