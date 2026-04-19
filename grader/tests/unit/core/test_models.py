"""Tests for core/models.py — stable output schema contracts."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from nolte_grader.core.models import DimensionResult, IssueGrade, Verdict


class TestVerdict:
    def test_has_exactly_four_states(self) -> None:
        assert {v.value for v in Verdict} == {
            "PASS",
            "FAIL",
            "INSUFFICIENT_EVIDENCE",
            "NOT_APPLICABLE",
        }

    def test_is_string_comparable(self) -> None:
        assert Verdict.PASS == "PASS"
        assert Verdict.NOT_APPLICABLE == "NOT_APPLICABLE"


class TestDimensionResult:
    def _minimal(self, **overrides: object) -> DimensionResult:
        base: dict[str, object] = {
            "code": "Y1",
            "verdict": Verdict.PASS,
            "evidence_code": "BUSINESS_OBJECTIVE_IN_BUSINESS_TERMS",
            "rationale": "Epic names retention metric.",
        }
        base.update(overrides)
        return DimensionResult(**base)  # type: ignore[arg-type]

    def test_builds_from_minimal(self) -> None:
        r = self._minimal()
        assert r.quotes == []
        assert r.recommended_type is None
        assert r.cached is False
        assert r.model is None
        assert r.prompt_version is None

    def test_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            self._minimal(unknown_field="oops")

    def test_recommended_type_allows_four_values(self) -> None:
        for t in ("Story", "Task", "Bug", "Sub-task"):
            self._minimal(recommended_type=t)

    def test_recommended_type_rejects_unknown_value(self) -> None:
        with pytest.raises(ValidationError):
            self._minimal(recommended_type="Epic")

    def test_recommended_type_allows_none(self) -> None:
        r = self._minimal(recommended_type=None)
        assert r.recommended_type is None

    def test_frozen_rejects_mutation(self) -> None:
        r = self._minimal()
        with pytest.raises(ValidationError):
            r.verdict = Verdict.FAIL  # type: ignore[misc]

    def test_judge_provenance_fields_round_trip(self) -> None:
        r = self._minimal(model="claude-sonnet-4-6", prompt_version="0.1", cached=True)
        assert r.model == "claude-sonnet-4-6"
        assert r.prompt_version == "0.1"
        assert r.cached is True

    def test_quotes_stored_as_list(self) -> None:
        r = self._minimal(quotes=["exact quote A", "exact quote B"])
        assert len(r.quotes) == 2


class TestIssueGrade:
    def _dim(self, verdict: Verdict = Verdict.PASS) -> DimensionResult:
        return DimensionResult(
            code="Y1",
            verdict=verdict,
            evidence_code="X",
            rationale="ok",
        )

    def _minimal(self, **overrides: object) -> IssueGrade:
        base: dict[str, object] = {
            "issue_key": "TEST-1",
            "issue_type": "Story",
            "project_key": "TEST",
            "title": "Example story",
            "run_timestamp": datetime(2026, 4, 19, 20, 30, tzinfo=timezone.utc),
            "dimensions": {"Y1": self._dim()},
            "six_yes_overall": Verdict.FAIL,
            "upstream_overall": Verdict.FAIL,
            "downstream_overall": Verdict.PASS,
            "story_overall": Verdict.FAIL,
            "config_hash": "sha256:abc123",
        }
        base.update(overrides)
        return IssueGrade(**base)  # type: ignore[arg-type]

    def test_builds_from_minimal(self) -> None:
        g = self._minimal()
        assert g.issue_key == "TEST-1"
        assert g.flags == []
        assert g.epic_key is None
        assert g.commitment_timestamp is None

    def test_config_hash_is_required(self) -> None:
        with pytest.raises(ValidationError):
            IssueGrade(
                issue_key="TEST-1",
                issue_type="Story",
                project_key="TEST",
                title="x",
                run_timestamp=datetime.now(tz=timezone.utc),
                dimensions={},
                six_yes_overall=Verdict.FAIL,
                upstream_overall=Verdict.FAIL,
                downstream_overall=Verdict.FAIL,
                story_overall=Verdict.FAIL,
            )  # type: ignore[call-arg]

    def test_not_applicable_is_a_valid_overall_verdict(self) -> None:
        g = self._minimal(downstream_overall=Verdict.NOT_APPLICABLE)
        assert g.downstream_overall == Verdict.NOT_APPLICABLE

    def test_optional_timestamps(self) -> None:
        g = self._minimal(
            commitment_timestamp=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
            done_timestamp=datetime(2026, 3, 22, 14, 0, tzinfo=timezone.utc),
            cycle_time_days=7.2,
        )
        assert g.cycle_time_days == 7.2

    def test_serializes_and_deserializes(self) -> None:
        g = self._minimal()
        payload = g.model_dump(mode="json")
        restored = IssueGrade.model_validate(payload)
        assert restored == g

    def test_flags_list_is_mutable(self) -> None:
        g = self._minimal()
        g.flags.append("TEAM_SIZE_EXCEPTION")
        assert "TEAM_SIZE_EXCEPTION" in g.flags
