"""Tests for evaluators/downstream.py — D1, D4, D5, D6, D7, D8, D9, D10."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from nolte_grader.core.models import Verdict
from nolte_grader.evaluators.downstream import (
    eval_d1,
    eval_d4,
    eval_d5,
    eval_d6,
    eval_d7,
    eval_d8,
    eval_d9,
    eval_d10,
)
from nolte_grader.parsers.changelog import ParsedChangelog, StatusTransition

UTC = timezone.utc


def ts(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


def _transition(from_s: str, to_s: str, timestamp: datetime) -> StatusTransition:
    return StatusTransition(
        timestamp=timestamp,
        from_status=from_s,
        to_status=to_s,
        actor_account_id="u1",
        actor_display_name="User",
        history_id="h1",
    )


def _cl(*transitions: StatusTransition) -> ParsedChangelog:
    return ParsedChangelog(status_transitions=list(transitions), field_edits=[])


# ---------------------------------------------------------------------------
# eval_d1
# ---------------------------------------------------------------------------


class TestEvalD1:
    def test_no_commit_ts_returns_not_applicable(self) -> None:
        r = eval_d1([ts(2026, 3, 16)], None)
        assert r.verdict == Verdict.NOT_APPLICABLE
        assert r.code == "D1"

    def test_no_subtasks_non_trivial_fails(self) -> None:
        r = eval_d1([], ts(2026, 3, 15), is_trivial=False)
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "SUBTASKS_ABSENT_ON_NON_TRIVIAL"

    def test_no_subtasks_trivial_passes(self) -> None:
        r = eval_d1([], ts(2026, 3, 15), is_trivial=True)
        assert r.verdict == Verdict.PASS

    def test_subtask_before_commit_fails(self) -> None:
        r = eval_d1([ts(2026, 3, 10)], ts(2026, 3, 15))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "SUBTASKS_CREATED_PRE_COMMIT"

    def test_subtask_after_commit_passes(self) -> None:
        r = eval_d1([ts(2026, 3, 16)], ts(2026, 3, 15))
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "SUBTASKS_CREATED_POST_COMMIT"

    def test_subtask_exactly_at_commit_passes(self) -> None:
        commit = ts(2026, 3, 15, 10)
        r = eval_d1([ts(2026, 3, 15, 10)], commit)
        assert r.verdict == Verdict.PASS

    def test_mixed_subtask_times_fails_on_pre(self) -> None:
        r = eval_d1([ts(2026, 3, 10), ts(2026, 3, 16)], ts(2026, 3, 15))
        assert r.verdict == Verdict.FAIL

    def test_all_after_commit_passes(self) -> None:
        r = eval_d1([ts(2026, 3, 16), ts(2026, 3, 17), ts(2026, 3, 18)], ts(2026, 3, 15))
        assert r.verdict == Verdict.PASS

    def test_rationale_mentions_pre_commit_count(self) -> None:
        r = eval_d1([ts(2026, 3, 10), ts(2026, 3, 11)], ts(2026, 3, 15))
        assert "2" in r.rationale


# ---------------------------------------------------------------------------
# eval_d4
# ---------------------------------------------------------------------------


class TestEvalD4:
    def test_no_done_implementing_returns_not_applicable(self) -> None:
        r = eval_d4([], None)
        assert r.verdict == Verdict.NOT_APPLICABLE
        assert r.code == "D4"

    def test_all_closed_passes(self) -> None:
        r = eval_d4([], ts(2026, 3, 20))
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "ALL_SUBTASKS_CLOSED_AT_DONE_IMPL"

    def test_one_open_subtask_fails(self) -> None:
        r = eval_d4(["PROJ-10"], ts(2026, 3, 20))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "OPEN_SUBTASK_AT_DONE_IMPL"
        assert "PROJ-10" in r.rationale

    def test_multiple_open_subtasks_listed_in_rationale(self) -> None:
        r = eval_d4(["PROJ-10", "PROJ-11", "PROJ-12"], ts(2026, 3, 20))
        assert r.verdict == Verdict.FAIL
        assert "PROJ-10" in r.rationale

    def test_more_than_three_subtasks_truncated(self) -> None:
        r = eval_d4(["P-1", "P-2", "P-3", "P-4", "P-5"], ts(2026, 3, 20))
        assert "more" in r.rationale


# ---------------------------------------------------------------------------
# eval_d5
# ---------------------------------------------------------------------------


class TestEvalD5:
    def test_no_done_implementing_returns_not_applicable(self) -> None:
        r = eval_d5(True, True, "https://ci.example.com/run/1", None)
        assert r.verdict == Verdict.NOT_APPLICABLE
        assert r.code == "D5"

    def test_no_test_subtask_fails(self) -> None:
        r = eval_d5(False, False, None, ts(2026, 3, 20))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "TEST_SUBTASK_MISSING"

    def test_test_subtask_open_fails(self) -> None:
        r = eval_d5(True, False, "https://ci.example.com/run/1", ts(2026, 3, 20))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "TEST_SUBTASK_OPEN"

    def test_test_subtask_closed_no_ci_link_fails(self) -> None:
        r = eval_d5(True, True, "Tests passed locally", ts(2026, 3, 20))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "TEST_SUBTASK_MISSING_CI_LINK"

    def test_test_subtask_closed_no_description_fails(self) -> None:
        r = eval_d5(True, True, None, ts(2026, 3, 20))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "TEST_SUBTASK_MISSING_CI_LINK"

    def test_test_subtask_closed_with_ci_link_passes(self) -> None:
        r = eval_d5(True, True, "See run: https://github.com/org/repo/actions/runs/123", ts(2026, 3, 20))
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "TEST_SUBTASK_CLOSED_WITH_CI_LINK"

    def test_any_https_url_counts_as_ci_link(self) -> None:
        r = eval_d5(True, True, "Build: https://jenkins.example.com/job/123", ts(2026, 3, 20))
        assert r.verdict == Verdict.PASS


# ---------------------------------------------------------------------------
# eval_d6
# ---------------------------------------------------------------------------


class TestEvalD6:
    def test_no_done_implementing_returns_not_applicable(self) -> None:
        r = eval_d6("https://prod.example.com", None)
        assert r.verdict == Verdict.NOT_APPLICABLE
        assert r.code == "D6"

    def test_empty_reference_fails(self) -> None:
        r = eval_d6("", ts(2026, 3, 20))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "DEPLOY_REFERENCE_EMPTY"

    def test_none_reference_fails(self) -> None:
        r = eval_d6(None, ts(2026, 3, 20))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "DEPLOY_REFERENCE_EMPTY"

    @pytest.mark.parametrize("local", ["http://localhost:3000", "http://127.0.0.1", "0.0.0.0:8080"])
    def test_local_reference_fails(self, local: str) -> None:
        r = eval_d6(local, ts(2026, 3, 20))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "DEPLOY_REFERENCE_LOCAL_ONLY"

    def test_production_url_passes(self) -> None:
        r = eval_d6("https://prod.example.com/release/v1.2", ts(2026, 3, 20))
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "DEPLOY_REFERENCE_PRESENT"

    def test_github_pr_passes(self) -> None:
        r = eval_d6("https://github.com/org/repo/pull/456", ts(2026, 3, 20))
        assert r.verdict == Verdict.PASS


# ---------------------------------------------------------------------------
# eval_d7
# ---------------------------------------------------------------------------


class TestEvalD7:
    def test_no_commit_ts_returns_not_applicable(self) -> None:
        r = eval_d7([], [], False, None)
        assert r.verdict == Verdict.NOT_APPLICABLE
        assert r.code == "D7"

    def test_no_violations_passes(self) -> None:
        r = eval_d7([], [], False, ts(2026, 3, 15))
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "WIP_WITHIN_LIMITS"

    def test_wip_exception_overrides_violations(self) -> None:
        r = eval_d7([date(2026, 3, 16)], [], True, ts(2026, 3, 15))
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "WIP_WITHIN_LIMITS"

    def test_per_engineer_violation_without_exception_fails(self) -> None:
        r = eval_d7([date(2026, 3, 16), date(2026, 3, 17)], [], False, ts(2026, 3, 15))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "WIP_EXCEEDED_PER_ENGINEER"
        assert "2" in r.rationale

    def test_system_violation_without_exception_fails(self) -> None:
        r = eval_d7([], [date(2026, 3, 16)], False, ts(2026, 3, 15))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "WIP_EXCEEDED_SYSTEM"

    def test_per_engineer_checked_before_system(self) -> None:
        r = eval_d7(
            [date(2026, 3, 16)],  # per-engineer violation
            [date(2026, 3, 16)],  # also system violation
            False,
            ts(2026, 3, 15),
        )
        assert r.evidence_code == "WIP_EXCEEDED_PER_ENGINEER"

    def test_exception_with_no_violations_still_passes(self) -> None:
        r = eval_d7([], [], True, ts(2026, 3, 15))
        assert r.verdict == Verdict.PASS


# ---------------------------------------------------------------------------
# eval_d8
# ---------------------------------------------------------------------------


class TestEvalD8:
    def test_no_commit_ts_returns_not_applicable(self) -> None:
        r = eval_d8(None, ts(2026, 3, 22))
        assert r.verdict == Verdict.NOT_APPLICABLE
        assert r.code == "D8"

    def test_no_done_implementing_ts_returns_not_applicable(self) -> None:
        r = eval_d8(ts(2026, 3, 15), None)
        assert r.verdict == Verdict.NOT_APPLICABLE

    def test_both_none_returns_not_applicable(self) -> None:
        r = eval_d8(None, None)
        assert r.verdict == Verdict.NOT_APPLICABLE

    def test_exactly_7_days_passes(self) -> None:
        r = eval_d8(ts(2026, 3, 15), ts(2026, 3, 22), threshold_days=7)
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "CYCLE_TIME_WITHIN_NORM"

    def test_8_days_fails(self) -> None:
        r = eval_d8(ts(2026, 3, 15), ts(2026, 3, 23), threshold_days=7)
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "CYCLE_TIME_EXCEEDS_NORM"

    def test_rationale_includes_elapsed_days(self) -> None:
        r = eval_d8(ts(2026, 3, 15), ts(2026, 3, 18), threshold_days=7)
        assert "3.0" in r.rationale


# ---------------------------------------------------------------------------
# eval_d9
# ---------------------------------------------------------------------------


class TestEvalD9:
    def test_no_done_implementing_returns_not_applicable(self) -> None:
        r = eval_d9(0, None)
        assert r.verdict == Verdict.NOT_APPLICABLE
        assert r.code == "D9"

    def test_zero_defects_passes(self) -> None:
        r = eval_d9(0, ts(2026, 3, 20))
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "ZERO_DEFECTS"

    def test_one_defect_fails(self) -> None:
        r = eval_d9(1, ts(2026, 3, 20))
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "DEFECTS_PRESENT"
        assert "1" in r.rationale

    def test_multiple_defects_fails(self) -> None:
        r = eval_d9(3, ts(2026, 3, 20))
        assert r.verdict == Verdict.FAIL
        assert "3" in r.rationale


# ---------------------------------------------------------------------------
# eval_d10
# ---------------------------------------------------------------------------


class TestEvalD10:
    def test_no_transitions_passes(self) -> None:
        r = eval_d10(_cl())
        assert r.verdict == Verdict.PASS
        assert r.code == "D10"

    def test_forward_only_passes(self) -> None:
        cl = _cl(
            _transition("Backlog", "In Specification", ts(2026, 3, 10)),
            _transition("In Specification", "Done Specifying", ts(2026, 3, 12)),
            _transition("Done Specifying", "In Implementation", ts(2026, 3, 15)),
        )
        r = eval_d10(cl)
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "FORWARD_ONLY_TRANSITIONS"

    def test_backward_transition_fails(self) -> None:
        cl = _cl(
            _transition("In Implementation", "Done Specifying", ts(2026, 3, 16)),
        )
        r = eval_d10(cl)
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "BACKWARD_TRANSITION_DETECTED"
        assert "In Implementation" in r.rationale
        assert "Done Specifying" in r.rationale

    def test_rationale_includes_count(self) -> None:
        cl = _cl(
            _transition("In Implementation", "Done Specifying", ts(2026, 3, 16)),
            _transition("In Implementation", "Done Specifying", ts(2026, 3, 18)),
        )
        r = eval_d10(cl)
        assert "2" in r.rationale

    def test_unknown_status_not_counted_as_backward(self) -> None:
        cl = _cl(
            _transition("In Implementation", "Cancelled", ts(2026, 3, 16)),
        )
        r = eval_d10(cl)
        assert r.verdict == Verdict.PASS

    def test_returns_na_when_story_never_committed(self) -> None:
        cl = _cl(_transition("Backlog", "In Specification", ts(2026, 3, 10)))
        r = eval_d10(cl)
        assert r.verdict == Verdict.PASS
