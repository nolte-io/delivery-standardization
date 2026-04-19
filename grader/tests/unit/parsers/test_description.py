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
## Business Objective
Drive activation by 10%.

## Observable Impact
MAU increases by 10% within 30 days; measured in Amplitude.

## Acceptance Criteria
- Button renders in the header
- Clicking button opens modal
- Modal closes on Escape

## Scenarios
Given a logged-in user
When they click the header button
Then the modal opens

## Risks
None identified
"""


# ---------------------------------------------------------------------------
# Basic extraction
# ---------------------------------------------------------------------------


class TestExtractSections:
    def test_none_input_returns_all_none(self) -> None:
        s = extract_sections(None)
        assert s["business_objective"] is None
        assert s["observable_impact"] is None
        assert s["acceptance_criteria"] is None
        assert s["scenarios"] is None
        assert s["risks"] is None

    def test_empty_string_returns_all_none(self) -> None:
        s = extract_sections("")
        for key in ("business_objective", "observable_impact", "acceptance_criteria", "scenarios", "risks"):
            assert s[key] is None

    def test_full_template_extracts_all_five(self) -> None:
        s = extract_sections(_FULL_TEMPLATE)
        assert s["business_objective"] is not None
        assert s["observable_impact"] is not None
        assert s["acceptance_criteria"] is not None
        assert s["scenarios"] is not None
        assert s["risks"] is not None

    def test_business_objective_content_correct(self) -> None:
        s = extract_sections(_FULL_TEMPLATE)
        assert "activation" in s["business_objective"]  # type: ignore[operator]

    def test_observable_impact_content_correct(self) -> None:
        s = extract_sections(_FULL_TEMPLATE)
        assert "Amplitude" in s["observable_impact"]  # type: ignore[operator]

    def test_acceptance_criteria_content_correct(self) -> None:
        s = extract_sections(_FULL_TEMPLATE)
        assert "Button renders" in s["acceptance_criteria"]  # type: ignore[operator]

    def test_scenarios_content_correct(self) -> None:
        s = extract_sections(_FULL_TEMPLATE)
        assert "Given a logged-in user" in s["scenarios"]  # type: ignore[operator]

    def test_risks_content_correct(self) -> None:
        s = extract_sections(_FULL_TEMPLATE)
        assert "None identified" in s["risks"]  # type: ignore[operator]

    def test_preamble_collected(self) -> None:
        text = "Some intro text before any heading.\n\n## Business Objective\nDrive revenue.\n"
        s = extract_sections(text)
        assert s["preamble"] == "Some intro text before any heading."

    def test_preamble_none_when_starts_with_heading(self) -> None:
        text = "## Business Objective\nDrive revenue.\n"
        s = extract_sections(text)
        assert s["preamble"] is None

    def test_missing_section_returns_none(self) -> None:
        text = "## Business Objective\nDrive revenue.\n## Observable Impact\nMetric.\n"
        s = extract_sections(text)
        assert s["acceptance_criteria"] is None
        assert s["scenarios"] is None
        assert s["risks"] is None


# ---------------------------------------------------------------------------
# Heading alias matching
# ---------------------------------------------------------------------------


class TestHeadingAliases:
    def test_ac_alias(self) -> None:
        s = extract_sections("## AC\nMust work\n")
        assert s["acceptance_criteria"] is not None

    def test_scenarios_alias(self) -> None:
        s = extract_sections("## Scenarios\nGiven...\n")
        assert s["scenarios"] is not None

    def test_bdd_scenarios_alias(self) -> None:
        s = extract_sections("## BDD Scenarios\nGiven...\n")
        assert s["scenarios"] is not None

    def test_bdd_alias(self) -> None:
        s = extract_sections("## BDD\nGiven...\n")
        assert s["scenarios"] is not None

    def test_case_insensitive_risks(self) -> None:
        s = extract_sections("## RISKS\nSome risk\n")
        assert s["risks"] is not None

    def test_case_insensitive_acceptance_criteria(self) -> None:
        s = extract_sections("## ACCEPTANCE CRITERIA\nMust work\n")
        assert s["acceptance_criteria"] is not None

    def test_business_objective_exact_match(self) -> None:
        s = extract_sections("## Business Objective\nIncrease revenue.\n")
        assert s["business_objective"] is not None

    def test_observable_impact_exact_match(self) -> None:
        s = extract_sections("## Observable Impact\nMAU +10%\n")
        assert s["observable_impact"] is not None


# ---------------------------------------------------------------------------
# Duplicate headers — first occurrence wins
# ---------------------------------------------------------------------------


class TestDuplicateHeaders:
    def test_first_ac_wins(self) -> None:
        text = "## Acceptance Criteria\nFirst AC.\n\n## Acceptance Criteria\nSecond AC.\n"
        s = extract_sections(text)
        assert s["acceptance_criteria"] == "First AC."

    def test_first_risks_wins(self) -> None:
        text = "## Risks\nFirst risks.\n\n## Risks\nSecond risks.\n"
        s = extract_sections(text)
        assert s["risks"] == "First risks."

    def test_alias_and_full_name_first_wins(self) -> None:
        text = "## AC\nFirst.\n\n## Acceptance Criteria\nSecond.\n"
        s = extract_sections(text)
        assert s["acceptance_criteria"] == "First."


# ---------------------------------------------------------------------------
# Empty and placeholder sections
# ---------------------------------------------------------------------------


class TestEmptyAndPlaceholderSections:
    def test_empty_section_body_is_present(self) -> None:
        text = "## Risks\n\n## Acceptance Criteria\nAC here.\n"
        s = extract_sections(text)
        assert section_present(s, "risks") is True
        assert s["risks"] == ""

    def test_none_identified_treated_as_present(self) -> None:
        text = "## Risks\nNone identified\n"
        s = extract_sections(text)
        assert section_present(s, "risks") is True
        assert s["risks"] == "None identified"

    def test_section_has_content_empty_is_false(self) -> None:
        text = "## Risks\n\n"
        s = extract_sections(text)
        assert section_has_content(s, "risks") is False

    def test_section_has_content_none_identified_is_false(self) -> None:
        text = "## Risks\nnone identified\n"
        s = extract_sections(text)
        assert section_has_content(s, "risks") is False

    def test_section_has_content_none_is_false(self) -> None:
        text = "## Risks\nNone\n"
        s = extract_sections(text)
        assert section_has_content(s, "risks") is False

    def test_section_has_content_na_is_false(self) -> None:
        text = "## Risks\nN/A\n"
        s = extract_sections(text)
        assert section_has_content(s, "risks") is False

    def test_section_has_content_with_real_text(self) -> None:
        text = "## Risks\nAPI rate limit may cause issues under high load.\n"
        s = extract_sections(text)
        assert section_has_content(s, "risks") is True

    def test_missing_section_has_content_is_false(self) -> None:
        s = extract_sections("## Risks\nSome risk.\n")
        assert section_has_content(s, "acceptance_criteria") is False


# ---------------------------------------------------------------------------
# section_present helper
# ---------------------------------------------------------------------------


class TestSectionPresent:
    def test_present_returns_true(self) -> None:
        s = extract_sections("## Risks\nSome risk.\n")
        assert section_present(s, "risks") is True

    def test_missing_returns_false(self) -> None:
        s = extract_sections("## Risks\nSome risk.\n")
        assert section_present(s, "acceptance_criteria") is False

    def test_empty_body_still_present(self) -> None:
        s = extract_sections("## Risks\n\n## Acceptance Criteria\nAC.\n")
        assert section_present(s, "risks") is True


# ---------------------------------------------------------------------------
# Unrecognized headings
# ---------------------------------------------------------------------------


class TestUnrecognizedHeadings:
    def test_unrecognized_heading_ignored(self) -> None:
        text = "## Technical Notes\nSome notes.\n\n## Risks\nSome risk.\n"
        s = extract_sections(text)
        assert s["risks"] == "Some risk."

    def test_only_unrecognized_headings(self) -> None:
        text = "## Notes\nSomething.\n## Background\nOther.\n"
        s = extract_sections(text)
        for key in ("business_objective", "observable_impact", "acceptance_criteria", "scenarios", "risks"):
            assert s[key] is None


# ---------------------------------------------------------------------------
# Real-world shapes (ADF-normalized)
# ---------------------------------------------------------------------------


class TestRealWorldShapes:
    def test_scenarios_with_multiple_givens(self) -> None:
        text = (
            "## Scenarios\n"
            "Given a logged-in user\n"
            "When they visit the dashboard\n"
            "Then they see their widgets\n\n"
            "Given a guest\n"
            "When they visit the dashboard\n"
            "Then they are redirected\n"
        )
        s = extract_sections(text)
        assert "Given a logged-in user" in s["scenarios"]  # type: ignore[operator]
        assert "Given a guest" in s["scenarios"]  # type: ignore[operator]

    def test_ac_with_table_text(self) -> None:
        text = (
            "## Acceptance Criteria\n"
            "| Condition | Expected |\n"
            "| Happy path | 200 OK |\n"
        )
        s = extract_sections(text)
        assert "Condition" in s["acceptance_criteria"]  # type: ignore[operator]

    def test_full_template_from_adf_normalized(self) -> None:
        normalized = (
            "## Business Objective\n\nIncrease activation by 10%.\n\n"
            "## Observable Impact\n\nMAU +10% in 30 days.\n\n"
            "## Acceptance Criteria\n\n- Works\n\n"
            "## Scenarios\n\nGiven X\nWhen Y\nThen Z\n\n"
            "## Risks\n\nNone identified\n\n"
        )
        s = extract_sections(normalized)
        assert section_present(s, "business_objective")
        assert section_present(s, "observable_impact")
        assert section_present(s, "acceptance_criteria")
        assert section_present(s, "scenarios")
        assert section_present(s, "risks")
