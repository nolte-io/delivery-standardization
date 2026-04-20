"""Unit tests for W1 — spec workflow stages observed."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nolte_grader.core.models import Verdict
from nolte_grader.evaluators.workflow import eval_w1

_T1 = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
_T2 = datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc)


class TestEvalW1:
    def test_pass_when_commit_ts_present(self):
        result = eval_w1(commit_ts=_T1, impl_entry_ts=_T1)
        assert result.verdict == Verdict.PASS
        assert result.evidence_code == "SPEC_STAGES_OBSERVED"

    def test_fail_when_impl_reached_without_commit(self):
        result = eval_w1(commit_ts=None, impl_entry_ts=_T2)
        assert result.verdict == Verdict.FAIL
        assert result.evidence_code == "SPEC_STAGES_BYPASSED"

    def test_not_applicable_when_never_reached_impl(self):
        result = eval_w1(commit_ts=None, impl_entry_ts=None)
        assert result.verdict == Verdict.NOT_APPLICABLE
        assert result.evidence_code == "NEVER_REACHED_IMPLEMENTATION"

    def test_not_applicable_even_if_commit_ts_somehow_set(self):
        # commit_ts present but impl_entry_ts None is a degenerate case; NA wins
        result = eval_w1(commit_ts=_T1, impl_entry_ts=None)
        assert result.verdict == Verdict.NOT_APPLICABLE
