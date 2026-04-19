"""Integration test: grade BBIT-495 from fixture data (deterministic only).

Commit 6 checkpoint: confirms the full deterministic pipeline produces a
well-formed IssueGrade for a known-good fixture.  Jeffrey reviews the
printed JSON output before proceeding to the judge adapter (commit 7).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from nolte_grader.core.config import GraderConfig
from nolte_grader.core.grader import Grader
from nolte_grader.core.models import IssueGrade, Verdict

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "BBIT-495.json"

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
            "Y3", "Y4", "Y5", "Y6",
            "U7", "U8", "U10", "U12",
            "C1", "C3",
            "D1", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
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


@pytest.fixture(scope="module")
def config() -> GraderConfig:
    return GraderConfig.model_validate(_FIXTURE_CONFIG)


@pytest.fixture(scope="module")
def fixture_data() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text())


@pytest.fixture(scope="module")
def grade(config: GraderConfig, fixture_data: dict[str, Any]) -> IssueGrade:
    grader = Grader(config)
    issue = fixture_data
    subtasks = fixture_data.get("_subtasks_full", [])
    return grader.grade_issue_from_data(issue, subtasks)


# ---------------------------------------------------------------------------
# Structural assertions
# ---------------------------------------------------------------------------


class TestFixtureGradeStructure:
    def test_issue_key(self, grade: IssueGrade) -> None:
        assert grade.issue_key == "BBIT-495"

    def test_issue_type(self, grade: IssueGrade) -> None:
        assert grade.issue_type == "Story"

    def test_project_key(self, grade: IssueGrade) -> None:
        assert grade.project_key == "BBIT"

    def test_epic_key(self, grade: IssueGrade) -> None:
        assert grade.epic_key == "BBIT-100"

    def test_config_hash_present(self, grade: IssueGrade) -> None:
        assert grade.config_hash.startswith("sha256:")

    def test_commitment_timestamp_set(self, grade: IssueGrade) -> None:
        assert grade.commitment_timestamp is not None
        assert grade.commitment_timestamp.year == 2026

    def test_done_timestamp_set(self, grade: IssueGrade) -> None:
        assert grade.done_timestamp is not None

    def test_cycle_time_days_set(self, grade: IssueGrade) -> None:
        assert grade.cycle_time_days is not None
        assert grade.cycle_time_days == pytest.approx(5.17, abs=0.1)

    def test_spec_approver_set(self, grade: IssueGrade) -> None:
        assert grade.spec_approver == "hector-id"

    def test_all_enabled_dimensions_present(self, grade: IssueGrade) -> None:
        expected = {
            "Y3", "Y4", "Y5", "Y6",
            "U7", "U8", "U10", "U12",
            "C1", "C3",
            "D1", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
        }
        assert set(grade.dimensions.keys()) == expected


# ---------------------------------------------------------------------------
# Per-dimension verdicts (fixture is designed to PASS all deterministic dims)
# ---------------------------------------------------------------------------


class TestFixtureVerdicts:
    @pytest.mark.parametrize("code", [
        "Y3", "Y4", "Y5", "Y6",
        "U7", "U8", "U12",
        "C1", "C3",
        "D1", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
    ])
    def test_dimension_passes(self, grade: IssueGrade, code: str) -> None:
        r = grade.dimensions[code]
        assert r.verdict == Verdict.PASS, (
            f"{code} expected PASS but got {r.verdict!r}: {r.evidence_code} — {r.rationale}"
        )

    def test_u10_passes_with_unreachable_flag(self, grade: IssueGrade) -> None:
        r = grade.dimensions["U10"]
        assert r.verdict == Verdict.PASS
        assert r.evidence_code == "IMPACT_LINK_UNREACHABLE"

    def test_six_yes_overall_not_applicable(self, grade: IssueGrade) -> None:
        # Y1 and Y2 (judge-only) not evaluated → overall based only on what was graded.
        # Y3/Y4/Y5/Y6 all PASS → six_yes_overall PASS (judge dims missing, not NA).
        assert grade.six_yes_overall == Verdict.PASS

    def test_upstream_overall_pass(self, grade: IssueGrade) -> None:
        assert grade.upstream_overall == Verdict.PASS

    def test_downstream_overall_pass(self, grade: IssueGrade) -> None:
        assert grade.downstream_overall == Verdict.PASS

    def test_story_overall_pass(self, grade: IssueGrade) -> None:
        assert grade.story_overall == Verdict.PASS


# ---------------------------------------------------------------------------
# Print IssueGrade JSON for Jeffrey's review (visible when running with -s)
# ---------------------------------------------------------------------------


def test_print_issue_grade_json(grade: IssueGrade, capsys: pytest.CaptureFixture[str]) -> None:
    """Print the full IssueGrade JSON to stdout for commit 6 checkpoint review."""
    output = grade.model_dump(mode="json")
    with capsys.disabled():
        print("\n" + "=" * 70)
        print("COMMIT 6 CHECKPOINT — IssueGrade output for BBIT-495")
        print("=" * 70)
        print(json.dumps(output, indent=2, default=str))
        print("=" * 70)
