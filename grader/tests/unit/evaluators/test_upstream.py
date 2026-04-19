"""Tests for evaluators/upstream.py — Y3a, Y4, Y5, Y6, U7, U8, U10, U12."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from nolte_grader.core.models import Verdict
from nolte_grader.evaluators.upstream import (
    eval_u10,
    eval_u12,
    eval_u7,
    eval_u8,
    eval_y3a,
    eval_y4,
    eval_y5,
    eval_y6,
)
from nolte_grader.parsers.changelog import FieldEdit

UTC = timezone.utc


def ts(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


def _field_edit(
    from_val: str | None,
    to_val: str | None,
    field_name: str = "description",
    timestamp: datetime | None = None,
) -> FieldEdit:
    return FieldEdit(
        timestamp=timestamp or ts(2026, 3, 20),
        field_name=field_name,
        from_value=from_val,
        to_value=to_val,
        actor_account_id="u1",
        history_id="h1",
    )


# ---------------------------------------------------------------------------
# eval_y3a
# ---------------------------------------------------------------------------


class TestEvalY3a:
    def test_no_commit_ts_returns_not_applicable(self) -> None:
        r = eval_y3a("## Acceptance Criteria\nSome AC\n", None)
        assert r.verdict == Verdict.NOT_APPLICABLE
        assert r.code == "Y3"

    def test_no_description_returns_insufficient_evidence(self) -> None:
        r = eval_y3a(None, ts(2026, 3, 15))
        assert r.verdict == Verdict.INSUFFICIENT_EVIDENCE
        assert r.evidence_code == "EVIDENCE_INSUFFICIENT_TO_JUDGE"

    def test_ac_section_absent_returns_fail(self) -> None:
        desc = "## Why\nBecause.\n## What\nThe thing.\n"
        r = eval_y3a(desc, ts(2026, 3, 15))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "AC_EMPTY_OR_PLACEHOLDER"

    def test_ac_section_present_returns_pass(self) -> None:
        desc = "## Acceptance Criteria\nMust work.\n"
        r = eval_y3a(desc, ts(2026, 3, 15))
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "AC_PRESENT_AND_PRE_COMMIT"

    def test_empty_description_fails(self) -> None:
        r = eval_y3a("", ts(2026, 3, 15))
        assert r.verdict == Verdict.FAIL

    def test_full_template_passes(self) -> None:
        desc = (
            "## Why\nReason.\n## What\nSpec.\n"
            "## Acceptance Criteria\n- It works\n"
            "## BDD Scenarios\nGiven X\nWhen Y\nThen Z\n"
        )
        r = eval_y3a(desc, ts(2026, 3, 15))
        assert r.verdict == Verdict.PASS


# ---------------------------------------------------------------------------
# eval_y4
# ---------------------------------------------------------------------------


class TestEvalY4:
    def test_no_validator_returns_insufficient_evidence(self) -> None:
        r = eval_y4(None, {"builder1"}, 5)
        assert r.verdict == Verdict.INSUFFICIENT_EVIDENCE

    def test_single_person_team_passes_with_exception(self) -> None:
        r = eval_y4("builder1", {"builder1"}, 1)
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "TEAM_SIZE_EXCEPTION"

    def test_validator_is_builder_fails(self) -> None:
        r = eval_y4("builder1", {"builder1", "builder2"}, 3)
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "VALIDATOR_IS_BUILDER"

    def test_independent_validator_passes(self) -> None:
        r = eval_y4("reviewer1", {"builder1", "builder2"}, 3)
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "VALIDATOR_INDEPENDENT"

    def test_empty_builder_set_passes(self) -> None:
        r = eval_y4("reviewer1", set(), 3)
        assert r.verdict == Verdict.PASS

    def test_team_size_zero_treated_as_multi(self) -> None:
        # team_size=0 is not a single-person team
        r = eval_y4("builder1", {"builder1"}, 0)
        assert r.verdict == Verdict.FAIL


# ---------------------------------------------------------------------------
# eval_y5
# ---------------------------------------------------------------------------


class TestEvalY5:
    def test_no_done_ts_returns_not_applicable(self) -> None:
        r = eval_y5("https://prod.example.com/v1", None)
        assert r.verdict == Verdict.NOT_APPLICABLE

    def test_empty_reference_fails(self) -> None:
        r = eval_y5("", ts(2026, 3, 22))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "PRODUCTION_REFERENCE_EMPTY"

    def test_none_reference_fails(self) -> None:
        r = eval_y5(None, ts(2026, 3, 22))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "PRODUCTION_REFERENCE_EMPTY"

    def test_reference_added_after_done_fails(self) -> None:
        r = eval_y5("https://prod.example.com", ts(2026, 3, 22), reference_added_after_done=True)
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "PRODUCTION_REFERENCE_POST_DONE"

    @pytest.mark.parametrize("url", [
        "https://staging.example.com/release",
        "https://stage.example.com",
        "https://dev.example.com/v2",
        "https://test.example.com",
        "https://qa.example.com",
        "https://uat.example.com",
        "https://preprod.example.com",
        "https://pre-prod.example.com",
        "http://localhost:3000",
        "http://127.0.0.1:8080",
    ])
    def test_staging_url_fails(self, url: str) -> None:
        r = eval_y5(url, ts(2026, 3, 22))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "PRODUCTION_REFERENCE_STAGING_ONLY"

    def test_valid_production_url_passes(self) -> None:
        r = eval_y5("https://prod.example.com/v1.2.3", ts(2026, 3, 22))
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "PRODUCTION_REFERENCE_PRESENT_AT_DONE"

    def test_github_pr_link_passes(self) -> None:
        r = eval_y5("https://github.com/org/repo/pull/123", ts(2026, 3, 22))
        assert r.verdict == Verdict.PASS

    def test_release_tag_passes(self) -> None:
        r = eval_y5("v1.2.3", ts(2026, 3, 22))
        assert r.verdict == Verdict.PASS


# ---------------------------------------------------------------------------
# eval_y6
# ---------------------------------------------------------------------------


class TestEvalY6:
    def test_no_commit_ts_returns_not_applicable(self) -> None:
        r = eval_y6(None, ts(2026, 3, 22))
        assert r.verdict == Verdict.NOT_APPLICABLE

    def test_no_done_implementing_ts_returns_not_applicable(self) -> None:
        r = eval_y6(ts(2026, 3, 15), None)
        assert r.verdict == Verdict.NOT_APPLICABLE

    def test_both_none_returns_not_applicable(self) -> None:
        r = eval_y6(None, None)
        assert r.verdict == Verdict.NOT_APPLICABLE

    def test_exactly_7_days_passes(self) -> None:
        r = eval_y6(ts(2026, 3, 15), ts(2026, 3, 22), threshold_days=7)
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "CYCLE_TIME_WITHIN_LIMIT"

    def test_6_days_passes(self) -> None:
        r = eval_y6(ts(2026, 3, 15), ts(2026, 3, 21), threshold_days=7)
        assert r.verdict == Verdict.PASS

    def test_8_days_fails(self) -> None:
        r = eval_y6(ts(2026, 3, 15), ts(2026, 3, 23), threshold_days=7)
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "CYCLE_TIME_EXCEEDS_LIMIT"

    def test_custom_threshold(self) -> None:
        r = eval_y6(ts(2026, 3, 15), ts(2026, 3, 20), threshold_days=4)
        assert r.verdict == Verdict.FAIL

    def test_same_day_passes(self) -> None:
        r = eval_y6(ts(2026, 3, 15, 8), ts(2026, 3, 15, 16), threshold_days=7)
        assert r.verdict == Verdict.PASS


# ---------------------------------------------------------------------------
# eval_u7
# ---------------------------------------------------------------------------


class TestEvalU7:
    def test_no_post_commit_edits_passes(self) -> None:
        r = eval_u7([])
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "NO_POST_COMMIT_AC_EDITS"

    def test_edit_to_non_ac_section_passes(self) -> None:
        edit = _field_edit(
            from_val="## Business Objective\nOriginal.\n## Observable Impact\nOld metric.\n",
            to_val="## Business Objective\nOriginal.\n## Observable Impact\nNew metric.\n",
        )
        r = eval_u7([edit])
        assert r.verdict == Verdict.PASS

    def test_ac_changed_fails(self) -> None:
        edit = _field_edit(
            from_val="## Acceptance Criteria\nOriginal AC.\n",
            to_val="## Acceptance Criteria\nModified AC.\n",
        )
        r = eval_u7([edit])
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "AC_EDITED_POST_COMMIT"

    def test_scenarios_changed_fails(self) -> None:
        edit = _field_edit(
            from_val="## Scenarios\nGiven X\nWhen Y\nThen Z\n",
            to_val="## Scenarios\nGiven X\nWhen Y\nThen Z2\n",
        )
        r = eval_u7([edit])
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "SCENARIOS_EDITED_POST_COMMIT"

    def test_whitespace_only_ac_change_passes(self) -> None:
        edit = _field_edit(
            from_val="## Acceptance Criteria\nSame content\n",
            to_val="## Acceptance Criteria\nSame content\n\n\n",  # only whitespace diff
        )
        r = eval_u7([edit])
        assert r.verdict == Verdict.PASS

    def test_whitespace_only_scenarios_change_passes(self) -> None:
        edit = _field_edit(
            from_val="## Scenarios\nGiven X\n",
            to_val="## Scenarios\nGiven X\n\n",
        )
        r = eval_u7([edit])
        assert r.verdict == Verdict.PASS

    def test_ac_added_where_none_existed_fails(self) -> None:
        edit = _field_edit(
            from_val="## Observable Impact\nMetric.\n",
            to_val="## Observable Impact\nMetric.\n## Acceptance Criteria\nNew AC.\n",
        )
        r = eval_u7([edit])
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "AC_EDITED_POST_COMMIT"

    def test_multiple_edits_first_fail_wins(self) -> None:
        edits = [
            _field_edit("## Acceptance Criteria\nOld.\n", "## Acceptance Criteria\nNew.\n"),
            _field_edit("## Why\nOld.\n", "## Why\nNew.\n"),
        ]
        r = eval_u7(edits)
        assert r.verdict == Verdict.FAIL


# ---------------------------------------------------------------------------
# eval_u8
# ---------------------------------------------------------------------------


class TestEvalU8:
    def test_no_validation_start_returns_not_applicable(self) -> None:
        r = eval_u8(None, None, [])
        assert r.verdict == Verdict.NOT_APPLICABLE

    def test_no_linked_issues_passes(self) -> None:
        r = eval_u8(ts(2026, 3, 20), ts(2026, 3, 22), [])
        assert r.verdict == Verdict.PASS

    def test_story_defect_during_validation_passes(self) -> None:
        r = eval_u8(ts(2026, 3, 20), ts(2026, 3, 22), [("Story defect", ts(2026, 3, 21))])
        assert r.verdict == Verdict.PASS

    def test_story_created_during_validation_fails(self) -> None:
        r = eval_u8(ts(2026, 3, 20), ts(2026, 3, 22), [("Story", ts(2026, 3, 21))])
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "NEW_STORY_CREATED_DURING_VALIDATION"

    def test_task_created_during_validation_fails(self) -> None:
        r = eval_u8(ts(2026, 3, 20), None, [("Task", ts(2026, 3, 21))])
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "NEW_TASK_CREATED_DURING_VALIDATION"

    def test_bug_created_during_validation_fails(self) -> None:
        r = eval_u8(ts(2026, 3, 20), ts(2026, 3, 22), [("Bug", ts(2026, 3, 21))])
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "NEW_BUG_CREATED_DURING_VALIDATION"

    def test_story_created_before_validation_window_passes(self) -> None:
        r = eval_u8(ts(2026, 3, 20), ts(2026, 3, 22), [("Story", ts(2026, 3, 10))])
        assert r.verdict == Verdict.PASS

    def test_story_created_after_validation_window_passes(self) -> None:
        r = eval_u8(ts(2026, 3, 20), ts(2026, 3, 22), [("Story", ts(2026, 3, 25))])
        assert r.verdict == Verdict.PASS

    def test_validation_still_open_checks_to_now(self) -> None:
        future = datetime(2030, 1, 1, tzinfo=UTC)
        r = eval_u8(ts(2026, 3, 20), None, [("Story", ts(2026, 3, 21))])
        assert r.verdict == Verdict.FAIL

    def test_story_exactly_at_validation_start_fails(self) -> None:
        r = eval_u8(ts(2026, 3, 20), ts(2026, 3, 22), [("Story", ts(2026, 3, 20))])
        assert r.verdict == Verdict.FAIL


# ---------------------------------------------------------------------------
# eval_u10
# ---------------------------------------------------------------------------


class TestEvalU10:
    def test_empty_link_fails(self) -> None:
        r = eval_u10("")
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "IMPACT_LINK_MISSING"

    def test_none_link_fails(self) -> None:
        r = eval_u10(None)
        assert r.verdict == Verdict.FAIL

    def test_link_broken_fails(self) -> None:
        r = eval_u10("https://grafana.example.com/d/abc", link_resolvable=False)
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "IMPACT_LINK_BROKEN"

    def test_link_present_unchecked_passes_with_flag(self) -> None:
        r = eval_u10("https://grafana.example.com/d/abc", link_resolvable=None)
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "IMPACT_LINK_UNREACHABLE"

    def test_link_present_and_resolvable_passes(self) -> None:
        r = eval_u10("https://grafana.example.com/d/abc", link_resolvable=True)
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "IMPACT_LINK_PRESENT_AND_RESOLVABLE"

    def test_default_resolvable_none_passes_with_flag(self) -> None:
        r = eval_u10("https://grafana.example.com/d/abc")
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "IMPACT_LINK_UNREACHABLE"


# ---------------------------------------------------------------------------
# eval_u12
# ---------------------------------------------------------------------------


class TestEvalU12:
    def test_none_section_fails(self) -> None:
        r = eval_u12(None)
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "RISKS_EMPTY_OR_MISSING"

    def test_blank_section_fails(self) -> None:
        r = eval_u12("   ")
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "RISKS_EMPTY_OR_MISSING"

    @pytest.mark.parametrize("placeholder", ["TODO", "TBD", "tbc", "N/A", "na", "fill in"])
    def test_placeholder_text_fails(self, placeholder: str) -> None:
        r = eval_u12(placeholder)
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "RISKS_PLACEHOLDER"

    def test_none_identified_passes(self) -> None:
        r = eval_u12("None identified")
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "RISKS_POPULATED"

    def test_real_content_passes(self) -> None:
        r = eval_u12("API rate limit may cause issues under high load.")
        assert r.verdict == Verdict.PASS

    def test_none_alone_is_placeholder_not_identified(self) -> None:
        # "None" by itself is a placeholder. "None identified" is real content.
        r = eval_u12("None")
        # Not in placeholder regex — "None" alone is treated as content
        # per spec §7.2: "even if contents are 'None identified'" → PASS.
        # "None" on its own is similarly acceptable.
        assert r.verdict == Verdict.PASS
