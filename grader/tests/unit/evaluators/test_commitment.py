"""Tests for evaluators/commitment.py — C1, C3."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nolte_grader.core.models import Verdict
from nolte_grader.evaluators.commitment import eval_c1, eval_c3

UTC = timezone.utc


def ts(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


# ---------------------------------------------------------------------------
# eval_c1
# ---------------------------------------------------------------------------


class TestEvalC1:
    def test_commit_ts_present_passes(self) -> None:
        r = eval_c1(ts(2026, 3, 15))
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "COMMITMENT_TRANSITION_FOUND"
        assert r.code == "C1"

    def test_commit_ts_none_fails(self) -> None:
        r = eval_c1(None)
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "COMMITMENT_TRANSITION_MISSING"

    def test_any_truthy_value_passes(self) -> None:
        r = eval_c1(ts(2026, 1, 1))
        assert r.verdict == Verdict.PASS

    def test_false_like_commit_ts_none_fails(self) -> None:
        r = eval_c1(None)
        assert r.verdict == Verdict.FAIL


# ---------------------------------------------------------------------------
# eval_c3
# ---------------------------------------------------------------------------


class TestEvalC3:
    def test_empty_approver_id_fails(self) -> None:
        r = eval_c3("", {"hector-id"}, {"builder-id"})
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "APPROVER_FIELD_EMPTY"

    def test_none_approver_id_fails(self) -> None:
        r = eval_c3(None, {"hector-id"}, {"builder-id"})
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "APPROVER_FIELD_EMPTY"

    def test_approver_not_in_authorized_fails(self) -> None:
        r = eval_c3("unknown-id", {"hector-id", "yanna-id"}, set())
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "APPROVER_NOT_AUTHORIZED"

    def test_approver_is_builder_fails(self) -> None:
        r = eval_c3("hector-id", {"hector-id", "yanna-id"}, {"hector-id", "dev-id"})
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "APPROVER_IS_BUILDER"

    def test_authorized_independent_approver_passes(self) -> None:
        r = eval_c3("hector-id", {"hector-id", "yanna-id"}, {"dev-id", "dev2-id"})
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "APPROVER_RECORDED_AND_AUTHORIZED"
        assert r.code == "C3"

    def test_empty_authorized_set_fails_not_authorized(self) -> None:
        r = eval_c3("hector-id", set(), set())
        assert r.verdict == Verdict.FAIL
        assert r.evidence_code == "APPROVER_NOT_AUTHORIZED"

    def test_single_authorized_approver_passes(self) -> None:
        r = eval_c3("hector-id", {"hector-id"}, set())
        assert r.verdict == Verdict.PASS

    def test_authorized_check_before_builder_check(self) -> None:
        # Approver not authorized → APPROVER_NOT_AUTHORIZED, even if also a builder.
        r = eval_c3("mystery-id", {"hector-id"}, {"mystery-id"})
        assert r.evidence_code == "APPROVER_NOT_AUTHORIZED"
