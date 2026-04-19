"""Tests for parsers/description.py — section extractor."""
from __future__ import annotations

import pytest

from nolte_grader.parsers.description import (
    ExtractedSections,
    extract_sections,
    section_has_content,
    section_present,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FULL_TEMPLATE = """\
## Why
We need this because customers are frustrated.

## What
Build a button that does the thing.

## Acceptance Criteria
- It works
- It is tested

## BDD Scenarios
Given a user
When they click
Then stuff happens

## Out of Scope
Mobile support
"""


# ---------------------------------------------------------------------------
# Basic extraction
# ---------------------------------------------------------------------------


class TestExtractSections:
    def test_none_input_returns_all_none(self) -> None:
        s = extract_sections(None)
        assert s["why"] is None
        assert s["what"] is None
        assert s["acceptance_criteria"] is None
        assert s["bdd_scenarios"] is None
        assert s["out_of_scope"] is None

    def test_empty_string_returns_all_none(self) -> None:
        s = extract_sections("")
        for key in ("why", "what", "acceptance_criteria", "bdd_scenarios", "out_of_scope"):
            assert s[key] is None

    def test_full_template_extracts_all_five(self) -> None:
        s = extract_sections(_FULL_TEMPLATE)
        assert s["why"] is not None
        assert s["what"] is not None
        assert s["acceptance_criteria"] is not None
        assert s["bdd_scenarios"] is not None
        assert s["out_of_scope"] is not None

    def test_why_content_correct(self) -> None:
        s = extract_sections(_FULL_TEMPLATE)
        assert "customers are frustrated" in s["why"]  # type: ignore[operator]

    def test_what_content_correct(self) -> None:
        s = extract_sections(_FULL_TEMPLATE)
        assert "button" in s["what"]  # type: ignore[operator]

    def test_acceptance_criteria_content_correct(self) -> None:
        s = extract_sections(_FULL_TEMPLATE)
        assert "It works" in s["acceptance_criteria"]  # type: ignore[operator]

    def test_bdd_scenarios_content_correct(self) -> None:
        s = extract_sections(_FULL_TEMPLATE)
        assert "Given a user" in s["bdd_scenarios"]  # type: ignore[operator]

    def test_out_of_scope_content_correct(self) -> None:
        s = extract_sections(_FULL_TEMPLATE)
        assert "Mobile support" in s["out_of_scope"]  # type: ignore[operator]

    def test_preamble_collected(self) -> None:
        text = "Some intro text before any heading.\n\n## Why\nBecause.\n"
        s = extract_sections(text)
        assert s["preamble"] == "Some intro text before any heading."

    def test_preamble_none_when_starts_with_heading(self) -> None:
        text = "## Why\nBecause.\n"
        s = extract_sections(text)
        assert s["preamble"] is None

    def test_missing_section_returns_none(self) -> None:
        text = "## Why\nBecause.\n## What\nThe thing.\n"
        s = extract_sections(text)
        assert s["acceptance_criteria"] is None
        assert s["bdd_scenarios"] is None
        assert s["out_of_scope"] is None


# ---------------------------------------------------------------------------
# Heading alias matching
# ---------------------------------------------------------------------------


class TestHeadingAliases:
    def test_ac_alias(self) -> None:
        s = extract_sections("## AC\nMust work\n")
        assert s["acceptance_criteria"] is not None

    def test_scenarios_alias(self) -> None:
        s = extract_sections("## Scenarios\nGiven...\n")
        assert s["bdd_scenarios"] is not None

    def test_bdd_alias(self) -> None:
        s = extract_sections("## BDD\nGiven...\n")
        assert s["bdd_scenarios"] is not None

    def test_out_of_scope_hyphenated(self) -> None:
        s = extract_sections("## Out-of-Scope\nNothing here\n")
        assert s["out_of_scope"] is not None

    def test_case_insensitive_why(self) -> None:
        s = extract_sections("## WHY\nReason\n")
        assert s["why"] is not None

    def test_case_insensitive_what(self) -> None:
        s = extract_sections("## WHAT\nSpec\n")
        assert s["what"] is not None

    def test_why_with_trailing_words(self) -> None:
        s = extract_sections("## Why we are doing this\nBecause.\n")
        assert s["why"] is not None

    def test_what_with_trailing_words(self) -> None:
        s = extract_sections("## What we are building\nThe widget.\n")
        assert s["what"] is not None


# ---------------------------------------------------------------------------
# Duplicate headers — first occurrence wins
# ---------------------------------------------------------------------------


class TestDuplicateHeaders:
    def test_first_occurrence_wins(self) -> None:
        text = "## Why\nFirst why.\n\n## Why\nSecond why.\n"
        s = extract_sections(text)
        assert s["why"] == "First why."

    def test_duplicate_ac_first_wins(self) -> None:
        text = "## Acceptance Criteria\nFirst AC.\n\n## Acceptance Criteria\nSecond AC.\n"
        s = extract_sections(text)
        assert s["acceptance_criteria"] == "First AC."


# ---------------------------------------------------------------------------
# Empty and placeholder sections
# ---------------------------------------------------------------------------


class TestEmptyAndPlaceholderSections:
    def test_empty_section_body_is_present(self) -> None:
        text = "## Why\n\n## What\nSpec here.\n"
        s = extract_sections(text)
        assert section_present(s, "why") is True
        assert s["why"] == ""

    def test_none_identified_treated_as_present(self) -> None:
        text = "## Out of Scope\nNone identified\n"
        s = extract_sections(text)
        assert section_present(s, "out_of_scope") is True
        assert s["out_of_scope"] == "None identified"

    def test_section_has_content_empty_is_false(self) -> None:
        text = "## Why\n\n"
        s = extract_sections(text)
        assert section_has_content(s, "why") is False

    def test_section_has_content_none_identified_is_false(self) -> None:
        text = "## Why\nnone identified\n"
        s = extract_sections(text)
        assert section_has_content(s, "why") is False

    def test_section_has_content_none_is_false(self) -> None:
        text = "## Why\nNone\n"
        s = extract_sections(text)
        assert section_has_content(s, "why") is False

    def test_section_has_content_na_is_false(self) -> None:
        text = "## Why\nN/A\n"
        s = extract_sections(text)
        assert section_has_content(s, "why") is False

    def test_section_has_content_with_real_text(self) -> None:
        text = "## Why\nWe need this for compliance reasons.\n"
        s = extract_sections(text)
        assert section_has_content(s, "why") is True

    def test_missing_section_has_content_is_false(self) -> None:
        s = extract_sections("## Why\nBecause.\n")
        assert section_has_content(s, "out_of_scope") is False


# ---------------------------------------------------------------------------
# section_present helper
# ---------------------------------------------------------------------------


class TestSectionPresent:
    def test_present_returns_true(self) -> None:
        s = extract_sections("## Why\nBecause.\n")
        assert section_present(s, "why") is True

    def test_missing_returns_false(self) -> None:
        s = extract_sections("## Why\nBecause.\n")
        assert section_present(s, "what") is False

    def test_empty_body_still_present(self) -> None:
        s = extract_sections("## What\n\n## Why\nBecause.\n")
        assert section_present(s, "what") is True


# ---------------------------------------------------------------------------
# Unrecognized headings
# ---------------------------------------------------------------------------


class TestUnrecognizedHeadings:
    def test_unrecognized_heading_ignored(self) -> None:
        text = "## Technical Notes\nSome notes.\n\n## Why\nBecause.\n"
        s = extract_sections(text)
        assert s["why"] == "Because."

    def test_only_unrecognized_headings(self) -> None:
        text = "## Notes\nSomething.\n## Background\nOther thing.\n"
        s = extract_sections(text)
        for key in ("why", "what", "acceptance_criteria", "bdd_scenarios", "out_of_scope"):
            assert s[key] is None


# ---------------------------------------------------------------------------
# Real-world shapes (ADF-normalized)
# ---------------------------------------------------------------------------


class TestRealWorldShapes:
    def test_bdd_section_with_multiple_scenarios(self) -> None:
        text = (
            "## BDD Scenarios\n"
            "Given a logged-in user\n"
            "When they visit the dashboard\n"
            "Then they see their widgets\n\n"
            "Given a guest\n"
            "When they visit the dashboard\n"
            "Then they are redirected\n"
        )
        s = extract_sections(text)
        assert "Given a logged-in user" in s["bdd_scenarios"]  # type: ignore[operator]
        assert "Given a guest" in s["bdd_scenarios"]  # type: ignore[operator]

    def test_ac_with_table_text(self) -> None:
        text = (
            "## Acceptance Criteria\n"
            "| Condition | Expected |\n"
            "| Happy path | 200 OK |\n"
            "| Bad input | 400 |\n"
        )
        s = extract_sections(text)
        assert "Condition" in s["acceptance_criteria"]  # type: ignore[operator]

    def test_full_template_from_adf_normalized(self) -> None:
        normalized = (
            "## Why\n\nCustomers need it.\n\n"
            "## What\n\nA feature.\n\n"
            "## Acceptance Criteria\n\n- Works\n\n"
            "## BDD Scenarios\n\nGiven X\nWhen Y\nThen Z\n\n"
            "## Out of Scope\n\nMobile.\n\n"
        )
        s = extract_sections(normalized)
        assert section_present(s, "why")
        assert section_present(s, "what")
        assert section_present(s, "acceptance_criteria")
        assert section_present(s, "bdd_scenarios")
        assert section_present(s, "out_of_scope")
