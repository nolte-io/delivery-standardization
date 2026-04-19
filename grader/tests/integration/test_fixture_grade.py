"""Integration test: grade BBIT-495 (clean) and BBIT-501 (messy) from fixture data.

Commit 6 checkpoint: confirms the full deterministic pipeline produces well-formed
IssueGrade objects for known fixtures and that judge-only dims emit the correct
NOT_APPLICABLE placeholder. Jeffrey reviews the printed JSON before proceeding
to the judge adapter (commit 7).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from nolte_grader.core.config import GraderConfig
from nolte_grader.core.grader import Grader
from nolte_grader.core.models import IssueGrade, Verdict

FIXTURES = Path(__file__).parent.parent / "fixtures"
SNAPSHOTS = Path(__file__).parent / "snapshots"

_JUDGE_ONLY_DIMS = frozenset({"Y1", "Y2", "U9", "U11", "C2", "D2", "D3"})

_FIXTURE_CONFIG: dict[str, Any] = {
    "jira": {
        "instance_url": "https://brightbits.atlassian.net",
        "service_account_email": "grader@nolte.io",
    },
    "projects": {"include": ["BBIT"]},
    "authorized_approvers": {
        "default": [
            {"accountId": "hector-id", "role": "head_of_engineering"},
            {"accountId": "yanna-id", "role": "head_of_product"},
        ],
        "per_project": {},
    },
    "dimensions": {
        "enabled": [
            "Y1", "Y2", "Y3", "Y4", "Y5", "Y6",
            "U7", "U8", "U9", "U10", "U11", "U12",
            "C1", "C2", "C3",
            "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
        ]
    },
    "thresholds": {
        "cycle_time_days": 7,
        "wip_limits": {
            "in_specification": 8,
            "ready": 5,
            "in_implementation_per_engineer": 3,
            "in_implementation_system": 15,
            "done_implementing": 5,
            "in_validation": 6,
        },
    },
    "conventions": {
        "template_sections": [
            "## Business Objective",
            "## Observable Impact",
            "## Acceptance Criteria",
            "## Scenarios",
            "## Risks",
        ],
        "test_subtask_title_pattern": r"^Tests",
    },
    "custom_fields": {
        "design_artifact_link": "customfield_10102",
        "production_release_reference": "customfield_10100",
        "impact_measurement_link": "customfield_10101",
        "spec_approver": "Spec Approver",
    },
    "judge": {
        "model": "claude-sonnet-4-6",
        "temperature": 0,
        "max_tokens": 1000,
        "cache_enabled": False,
    },
    "output": {"directory": "./runs/", "formats": ["json"]},
    "teams": {"default": {"size": 5}, "per_project": {}},
}

_ALL_25_DIMS = {
    "Y1", "Y2", "Y3", "Y4", "Y5", "Y6",
    "U7", "U8", "U9", "U10", "U11", "U12",
    "C1", "C2", "C3",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
}


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text())


def _grade(config: GraderConfig, name: str) -> IssueGrade:
    data = _load_fixture(name)
    grader = Grader(config)
    return grader.grade_issue_from_data(data, data.get("_subtasks_full", []))


def _save_snapshot(name: str, grade: IssueGrade) -> None:
    """Write IssueGrade JSON (minus volatile run_timestamp) to snapshots dir."""
    SNAPSHOTS.mkdir(exist_ok=True)
    out = grade.model_dump(mode="json")
    out.pop("run_timestamp", None)
    path = SNAPSHOTS / f"{name}.json"
    path.write_text(json.dumps(out, indent=2, default=str))


def _load_snapshot(name: str) -> dict[str, Any] | None:
    path = SNAPSHOTS / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def config() -> GraderConfig:
    return GraderConfig.model_validate(_FIXTURE_CONFIG)


@pytest.fixture(scope="module")
def grade_495(config: GraderConfig) -> IssueGrade:
    return _grade(config, "BBIT-495")


@pytest.fixture(scope="module")
def grade_501(config: GraderConfig) -> IssueGrade:
    return _grade(config, "BBIT-501")


# ---------------------------------------------------------------------------
# BBIT-495 — clean story (all deterministic dims pass)
# ---------------------------------------------------------------------------


class TestBBIT495Structure:
    def test_issue_key(self, grade_495: IssueGrade) -> None:
        assert grade_495.issue_key == "BBIT-495"

    def test_issue_type(self, grade_495: IssueGrade) -> None:
        assert grade_495.issue_type == "Story"

    def test_project_key(self, grade_495: IssueGrade) -> None:
        assert grade_495.project_key == "BBIT"

    def test_epic_key(self, grade_495: IssueGrade) -> None:
        assert grade_495.epic_key == "BBIT-100"

    def test_config_hash_present(self, grade_495: IssueGrade) -> None:
        assert grade_495.config_hash.startswith("sha256:")

    def test_commitment_timestamp_set(self, grade_495: IssueGrade) -> None:
        assert grade_495.commitment_timestamp is not None
        assert grade_495.commitment_timestamp.year == 2026

    def test_done_timestamp_set(self, grade_495: IssueGrade) -> None:
        assert grade_495.done_timestamp is not None

    def test_cycle_time_days_set(self, grade_495: IssueGrade) -> None:
        assert grade_495.cycle_time_days is not None
        assert grade_495.cycle_time_days == pytest.approx(5.17, abs=0.1)

    def test_spec_approver_set(self, grade_495: IssueGrade) -> None:
        assert grade_495.spec_approver == "hector-id"

    def test_all_25_dimensions_present(self, grade_495: IssueGrade) -> None:
        assert set(grade_495.dimensions.keys()) == _ALL_25_DIMS

    def test_dimension_result_shape(self, grade_495: IssueGrade) -> None:
        for code, r in grade_495.dimensions.items():
            assert r.code == code, f"{code}: code field mismatch"
            assert r.verdict in list(Verdict), f"{code}: invalid verdict"
            assert r.evidence_code, f"{code}: evidence_code empty"
            assert r.rationale, f"{code}: rationale empty"


class TestBBIT495Verdicts:
    @pytest.mark.parametrize("code", [
        "Y3", "Y4", "Y5", "Y6",
        "U7", "U8", "U12",
        "C1", "C3",
        "D1", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
    ])
    def test_deterministic_dim_passes(self, grade_495: IssueGrade, code: str) -> None:
        r = grade_495.dimensions[code]
        assert r.verdict == Verdict.PASS, (
            f"{code} expected PASS but got {r.verdict!r}: {r.evidence_code} — {r.rationale}"
        )

    def test_u10_passes_with_unreachable_flag(self, grade_495: IssueGrade) -> None:
        r = grade_495.dimensions["U10"]
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "IMPACT_LINK_UNREACHABLE"

    @pytest.mark.parametrize("code", sorted(_JUDGE_ONLY_DIMS))
    def test_judge_dim_returns_placeholder(self, grade_495: IssueGrade, code: str) -> None:
        r = grade_495.dimensions[code]
        assert r.verdict == Verdict.NOT_APPLICABLE, (
            f"{code}: expected NOT_APPLICABLE but got {r.verdict!r}"
        )
        assert r.evidence_code == "JUDGE_NOT_YET_IMPLEMENTED", (
            f"{code}: expected JUDGE_NOT_YET_IMPLEMENTED but got {r.evidence_code!r}"
        )

    def test_six_yes_overall_pass(self, grade_495: IssueGrade) -> None:
        assert grade_495.six_yes_overall == Verdict.PASS

    def test_upstream_overall_pass(self, grade_495: IssueGrade) -> None:
        assert grade_495.upstream_overall == Verdict.PASS

    def test_downstream_overall_pass(self, grade_495: IssueGrade) -> None:
        assert grade_495.downstream_overall == Verdict.PASS

    def test_story_overall_pass(self, grade_495: IssueGrade) -> None:
        assert grade_495.story_overall == Verdict.PASS


# ---------------------------------------------------------------------------
# BBIT-501 — messy story (multiple deterministic failures)
# ---------------------------------------------------------------------------


class TestBBIT501Structure:
    def test_issue_key(self, grade_501: IssueGrade) -> None:
        assert grade_501.issue_key == "BBIT-501"

    def test_epic_key(self, grade_501: IssueGrade) -> None:
        assert grade_501.epic_key == "BBIT-200"

    def test_commitment_timestamp_set(self, grade_501: IssueGrade) -> None:
        assert grade_501.commitment_timestamp is not None
        assert grade_501.commitment_timestamp.year == 2026

    def test_cycle_time_days(self, grade_501: IssueGrade) -> None:
        # Ready→Done Implementing: 2026-01-16 → 2026-01-25 = 9 days
        assert grade_501.cycle_time_days is not None
        assert grade_501.cycle_time_days == pytest.approx(9.21, abs=0.1)

    def test_spec_approver_absent(self, grade_501: IssueGrade) -> None:
        assert grade_501.spec_approver is None

    def test_all_25_dimensions_present(self, grade_501: IssueGrade) -> None:
        assert set(grade_501.dimensions.keys()) == _ALL_25_DIMS

    def test_config_hash_present(self, grade_501: IssueGrade) -> None:
        assert grade_501.config_hash.startswith("sha256:")


class TestBBIT501Failures:
    @pytest.mark.parametrize("code,expected_evidence", [
        ("Y3", "AC_EMPTY_OR_PLACEHOLDER"),
        ("Y5", "PRODUCTION_REFERENCE_EMPTY"),
        ("Y6", "CYCLE_TIME_EXCEEDS_LIMIT"),
        ("U7", "AC_EDITED_POST_COMMIT"),
        ("U10", "IMPACT_LINK_MISSING"),
        ("U12", "RISKS_EMPTY_OR_MISSING"),
        ("C3", "APPROVER_FIELD_EMPTY"),
        ("D1", "SUBTASKS_CREATED_PRE_COMMIT"),
        ("D5", "TEST_SUBTASK_MISSING"),
        ("D6", "DEPLOY_REFERENCE_EMPTY"),
        ("D8", "CYCLE_TIME_EXCEEDS_NORM"),
        ("D10", "BACKWARD_TRANSITION_DETECTED"),
    ])
    def test_dim_fails(self, grade_501: IssueGrade, code: str, expected_evidence: str) -> None:
        r = grade_501.dimensions[code]
        assert r.verdict == Verdict.FAIL, (
            f"{code}: expected FAIL but got {r.verdict!r}: {r.evidence_code} — {r.rationale}"
        )
        assert r.evidence_code == expected_evidence, (
            f"{code}: expected {expected_evidence!r} but got {r.evidence_code!r}"
        )

    @pytest.mark.parametrize("code", ["Y4", "U8", "C1", "D4", "D7", "D9"])
    def test_dim_passes(self, grade_501: IssueGrade, code: str) -> None:
        r = grade_501.dimensions[code]
        assert r.verdict == Verdict.PASS, (
            f"{code}: expected PASS but got {r.verdict!r}: {r.evidence_code}"
        )

    @pytest.mark.parametrize("code", sorted(_JUDGE_ONLY_DIMS))
    def test_judge_dim_returns_placeholder(self, grade_501: IssueGrade, code: str) -> None:
        r = grade_501.dimensions[code]
        assert r.verdict == Verdict.NOT_APPLICABLE
        assert r.evidence_code == "JUDGE_NOT_YET_IMPLEMENTED"

    def test_six_yes_overall_fail(self, grade_501: IssueGrade) -> None:
        assert grade_501.six_yes_overall == Verdict.FAIL

    def test_upstream_overall_fail(self, grade_501: IssueGrade) -> None:
        assert grade_501.upstream_overall == Verdict.FAIL

    def test_downstream_overall_fail(self, grade_501: IssueGrade) -> None:
        assert grade_501.downstream_overall == Verdict.FAIL

    def test_story_overall_fail(self, grade_501: IssueGrade) -> None:
        assert grade_501.story_overall == Verdict.FAIL


# ---------------------------------------------------------------------------
# Snapshot tests — generate on first run, compare on subsequent runs
# ---------------------------------------------------------------------------


class TestSnapshots:
    def test_bbit_495_snapshot(self, grade_495: IssueGrade) -> None:
        _save_snapshot("BBIT-495", grade_495)
        snapshot = _load_snapshot("BBIT-495")
        assert snapshot is not None
        assert snapshot["issue_key"] == "BBIT-495"
        assert snapshot["story_overall"] == "PASS"

    def test_bbit_501_snapshot(self, grade_501: IssueGrade) -> None:
        _save_snapshot("BBIT-501", grade_501)
        snapshot = _load_snapshot("BBIT-501")
        assert snapshot is not None
        assert snapshot["issue_key"] == "BBIT-501"
        assert snapshot["story_overall"] == "FAIL"


# ---------------------------------------------------------------------------
# Print IssueGrade JSON for Jeffrey's review (visible when running with -s)
# ---------------------------------------------------------------------------


def test_print_bbit_495_json(grade_495: IssueGrade, capsys: pytest.CaptureFixture[str]) -> None:
    with capsys.disabled():
        print("\n" + "=" * 70)
        print("COMMIT 6 CHECKPOINT — IssueGrade output for BBIT-495 (clean)")
        print("=" * 70)
        print(json.dumps(grade_495.model_dump(mode="json"), indent=2, default=str))
        print("=" * 70)


def test_print_bbit_501_json(grade_501: IssueGrade, capsys: pytest.CaptureFixture[str]) -> None:
    with capsys.disabled():
        print("\n" + "=" * 70)
        print("COMMIT 6 CHECKPOINT — IssueGrade output for BBIT-501 (messy)")
        print("=" * 70)
        print(json.dumps(grade_501.model_dump(mode="json"), indent=2, default=str))
        print("=" * 70)
