"""Integration test: aggregator + markdown formatter against 10 synthesized IssueGrade records.

10 stories with mixed pass/fail patterns exercise every aggregator path:
- six-yes pass rate
- per-dimension fail rates (including NA exclusion for judge dims)
- cycle time distribution (p50, p90, max, stories above threshold)
- upstream/downstream owner breakdown
- spec approver stats
- markdown formatter output (snapshot)
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from nolte_grader.core.aggregator import aggregate
from nolte_grader.core.models import (
    DimensionResult,
    IssueGrade,
    RollupReport,
    RollupWindow,
    Verdict,
)
from nolte_grader.formatters.markdown import format_rollup

SNAPSHOTS = Path(__file__).parent / "snapshots"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_JUDGE_DIMS = frozenset({"Y1", "Y2", "U9", "U11", "C2", "D2", "D3"})
_DET_DIMS = frozenset({
    "Y3", "Y4", "Y5", "Y6",
    "U7", "U8", "U10", "U12",
    "C1", "C3",
    "D1", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
})
_ALL_DIMS = _JUDGE_DIMS | _DET_DIMS

_CONFIG_HASH = "sha256:cafebabe"

_PASS_EVIDENCE: dict[str, str] = {
    "Y3": "AC_PRESENT_AND_PRE_COMMIT",
    "Y4": "VALIDATOR_INDEPENDENT",
    "Y5": "PRODUCTION_REFERENCE_PRESENT_AT_DONE",
    "Y6": "CYCLE_TIME_WITHIN_LIMIT",
    "U7": "NO_POST_COMMIT_AC_EDITS",
    "U8": "VALIDATION_OUTPUTS_IN_CONTRACT",
    "U10": "IMPACT_LINK_UNREACHABLE",
    "U12": "RISKS_POPULATED",
    "C1": "COMMITMENT_TRANSITION_FOUND",
    "C3": "APPROVER_RECORDED_AND_AUTHORIZED",
    "D1": "SUBTASKS_CREATED_POST_COMMIT",
    "D4": "ALL_SUBTASKS_CLOSED_AT_DONE_IMPL",
    "D5": "TEST_SUBTASK_CLOSED_WITH_CI_LINK",
    "D6": "DEPLOY_REFERENCE_PRESENT",
    "D7": "WIP_WITHIN_LIMITS",
    "D8": "CYCLE_TIME_WITHIN_NORM",
    "D9": "ZERO_DEFECTS",
    "D10": "FORWARD_ONLY_TRANSITIONS",
}

_FAIL_EVIDENCE: dict[str, str] = {
    "Y3": "AC_EMPTY_OR_PLACEHOLDER",
    "Y5": "PRODUCTION_REFERENCE_EMPTY",
    "Y6": "CYCLE_TIME_EXCEEDS_LIMIT",
    "U12": "RISKS_EMPTY_OR_MISSING",
    "C3": "APPROVER_FIELD_EMPTY",
    "D8": "CYCLE_TIME_EXCEEDS_NORM",
    "D10": "BACKWARD_TRANSITION_DETECTED",
}

_SIX_YES_CODES = ("Y1", "Y2", "Y3", "Y4", "Y5", "Y6")
_UPSTREAM_CODES = ("Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "U7", "U8", "U9", "U10", "U11", "U12", "C1", "C2", "C3")
_DOWNSTREAM_CODES = ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10")


def _dim_result(code: str, verdict: Verdict, evidence: str) -> DimensionResult:
    return DimensionResult(
        code=code,
        verdict=verdict,
        evidence_code=evidence,
        rationale=f"{code}: {evidence}",
    )


def _judge_placeholder(code: str) -> DimensionResult:
    return DimensionResult(
        code=code,
        verdict=Verdict.NOT_APPLICABLE,
        evidence_code="JUDGE_NOT_YET_IMPLEMENTED",
        rationale="Judge evaluation not wired in this build.",
    )


def _build_dims(failing: frozenset[str]) -> dict[str, DimensionResult]:
    dims: dict[str, DimensionResult] = {}
    for code in _JUDGE_DIMS:
        dims[code] = _judge_placeholder(code)
    for code in _DET_DIMS:
        if code in failing:
            ev = _FAIL_EVIDENCE.get(code, "FAIL")
            dims[code] = _dim_result(code, Verdict.FAIL, ev)
        else:
            ev = _PASS_EVIDENCE.get(code, "PASS")
            dims[code] = _dim_result(code, Verdict.PASS, ev)
    return dims


def _overall(dims: dict[str, DimensionResult], codes: tuple[str, ...]) -> Verdict:
    verdicts = [
        dims[c].verdict for c in codes
        if c in dims and dims[c].verdict != Verdict.NOT_APPLICABLE
    ]
    if not verdicts:
        return Verdict.NOT_APPLICABLE
    if any(v in (Verdict.FAIL, Verdict.INSUFFICIENT_EVIDENCE) for v in verdicts):
        return Verdict.FAIL
    return Verdict.PASS


def _grade(
    key: str,
    failing: frozenset[str] = frozenset(),
    *,
    cycle_time_days: float | None = None,
    upstream_owner: str | None = None,
    downstream_owner: str | None = None,
    spec_approver: str | None = None,
    commitment_date: date = date(2026, 4, 2),
    done_date: date = date(2026, 4, 15),
) -> IssueGrade:
    dims = _build_dims(failing)
    six_yes = _overall(dims, _SIX_YES_CODES)
    upstream = _overall(dims, _UPSTREAM_CODES)
    downstream = _overall(dims, _DOWNSTREAM_CODES)
    if upstream == Verdict.PASS and downstream == Verdict.PASS:
        story = Verdict.PASS
    elif Verdict.FAIL in (upstream, downstream):
        story = Verdict.FAIL
    else:
        story = Verdict.NOT_APPLICABLE

    return IssueGrade(
        issue_key=key,
        issue_type="Story",
        project_key="BBIT",
        epic_key="BBIT-000",
        title=f"Story {key}",
        run_timestamp=datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc),
        commitment_timestamp=datetime.combine(commitment_date, datetime.min.time()).replace(tzinfo=timezone.utc),
        done_timestamp=datetime.combine(done_date, datetime.min.time()).replace(tzinfo=timezone.utc),
        cycle_time_days=cycle_time_days,
        upstream_owner=upstream_owner,
        downstream_owner=downstream_owner,
        spec_approver=spec_approver,
        dimensions=dims,
        six_yes_overall=six_yes,
        upstream_overall=upstream,
        downstream_overall=downstream,
        story_overall=story,
        config_hash=_CONFIG_HASH,
    )


# 10 synthesized stories — cycle times: 3.5, 4.2, 5.0, 5.5, 6.1, 7.2, 8.4, 9.2, 10.1, 12.5
# Failing dims per story:
#   BBIT-100: none                        → six_yes PASS, story PASS
#   BBIT-101: U12                         → six_yes PASS, story FAIL (upstream)
#   BBIT-102: U12, C3                     → six_yes PASS, story FAIL
#   BBIT-103: U12, D10                    → six_yes PASS, story FAIL (up+down)
#   BBIT-104: Y3                          → six_yes FAIL, story FAIL
#   BBIT-105: Y3, D10                     → six_yes FAIL, story FAIL
#   BBIT-106: Y5                          → six_yes FAIL, story FAIL
#   BBIT-107: Y5, D8                      → six_yes FAIL, story FAIL
#   BBIT-108: D10, D8                     → six_yes PASS, story FAIL (downstream)
#   BBIT-109: none                        → six_yes PASS, story PASS
# six_yes PASS: 100,101,102,103,108,109 = 6/10 = 60%

_GRADES: list[IssueGrade] = [
    _grade("BBIT-100", frozenset(), cycle_time_days=3.5,
           upstream_owner="Yanna Lopes", downstream_owner="Dulce Hernandez Cruz",
           spec_approver="hector-id"),
    _grade("BBIT-101", frozenset({"U12"}), cycle_time_days=4.2,
           upstream_owner="Yanna Lopes", downstream_owner="Dulce Hernandez Cruz",
           spec_approver="hector-id"),
    _grade("BBIT-102", frozenset({"U12", "C3"}), cycle_time_days=5.0,
           upstream_owner="Yanna Lopes", downstream_owner="Rafael Moreno",
           spec_approver="hector-id"),
    _grade("BBIT-103", frozenset({"U12", "D10"}), cycle_time_days=5.5,
           upstream_owner="Yanna Lopes", downstream_owner="Rafael Moreno",
           spec_approver="hector-id"),
    _grade("BBIT-104", frozenset({"Y3"}), cycle_time_days=6.1,
           upstream_owner="Hector Sanchez", downstream_owner="Dulce Hernandez Cruz",
           spec_approver="yanna-id"),
    _grade("BBIT-105", frozenset({"Y3", "D10"}), cycle_time_days=7.2,
           upstream_owner="Hector Sanchez", downstream_owner="Dulce Hernandez Cruz",
           spec_approver="yanna-id"),
    _grade("BBIT-106", frozenset({"Y5"}), cycle_time_days=8.4,
           upstream_owner="Hector Sanchez", downstream_owner="Dulce Hernandez Cruz",
           spec_approver="yanna-id"),
    _grade("BBIT-107", frozenset({"Y5", "D8"}), cycle_time_days=9.2,
           upstream_owner="Hector Sanchez", downstream_owner="Dulce Hernandez Cruz",
           spec_approver="yanna-id"),
    _grade("BBIT-108", frozenset({"D10", "D8"}), cycle_time_days=10.1,
           upstream_owner="Yanna Lopes", downstream_owner="Rafael Moreno",
           spec_approver="hector-id"),
    _grade("BBIT-109", frozenset(), cycle_time_days=12.5,
           upstream_owner="Yanna Lopes", downstream_owner="Dulce Hernandez Cruz",
           spec_approver="hector-id"),
]

_WINDOW = RollupWindow(from_date=date(2026, 4, 2), to_date=date(2026, 4, 15))
_RUN_ID = "test-rollup-commit9"


@pytest.fixture(scope="module")
def report() -> RollupReport:
    return aggregate(_GRADES, run_id=_RUN_ID, window=_WINDOW, cycle_time_threshold_days=7)


@pytest.fixture(scope="module")
def md(report: RollupReport) -> str:
    return format_rollup(report)


# ---------------------------------------------------------------------------
# System view
# ---------------------------------------------------------------------------


class TestSystemView:
    def test_story_count(self, report: RollupReport) -> None:
        assert report.system.story_count == 10

    def test_six_yes_pass_rate(self, report: RollupReport) -> None:
        # 6/10 stories have six_yes_overall == PASS
        assert report.system.six_yes_pass_rate == pytest.approx(0.6)

    def test_config_hash(self, report: RollupReport) -> None:
        assert report.config_hash == _CONFIG_HASH

    def test_pending_judge_dimensions(self, report: RollupReport) -> None:
        # 7 judge-only dims (Y1, Y2, U9, U11, C2, D2, D3) are all NOT_APPLICABLE
        assert report.system.pending_judge_dimensions == 7

    def test_judge_dims_excluded_from_fail_rate_denominator(self, report: RollupReport) -> None:
        for code in _JUDGE_DIMS:
            dr = report.system.dimension_fail_rates[code]
            assert dr.graded == 0, f"{code}: graded should be 0 (all NA)"
            assert dr.not_applicable == 10

    def test_dimension_fail_rates_present(self, report: RollupReport) -> None:
        assert set(report.system.dimension_fail_rates.keys()) == _ALL_DIMS

    def test_u12_fail_rate(self, report: RollupReport) -> None:
        # Stories 101, 102, 103 fail U12 → 3/10
        dr = report.system.dimension_fail_rates["U12"]
        assert dr.fails == 3
        assert dr.graded == 10
        assert dr.fail_rate == pytest.approx(0.3)

    def test_d10_fail_rate(self, report: RollupReport) -> None:
        # Stories 103, 105, 108 fail D10 → 3/10
        dr = report.system.dimension_fail_rates["D10"]
        assert dr.fails == 3
        assert dr.fail_rate == pytest.approx(0.3)

    def test_y3_fail_rate(self, report: RollupReport) -> None:
        # Stories 104, 105 fail Y3 → 2/10
        dr = report.system.dimension_fail_rates["Y3"]
        assert dr.fails == 2
        assert dr.fail_rate == pytest.approx(0.2)

    def test_y4_zero_failures(self, report: RollupReport) -> None:
        dr = report.system.dimension_fail_rates["Y4"]
        assert dr.fails == 0
        assert dr.fail_rate == 0.0

    def test_top_failing_dimensions(self, report: RollupReport) -> None:
        top = report.system.top_failing_dimensions
        assert "U12" in top
        assert "D10" in top
        assert len(top) <= 5

    def test_cycle_time_p50(self, report: RollupReport) -> None:
        # sorted: 3.5,4.2,5.0,5.5,6.1,7.2,8.4,9.2,10.1,12.5 → p50 ≈ 6.65
        assert report.system.cycle_time_p50 == pytest.approx(6.65, abs=0.05)

    def test_cycle_time_p90(self, report: RollupReport) -> None:
        # p90 ≈ 10.34
        assert report.system.cycle_time_p90 == pytest.approx(10.34, abs=0.05)

    def test_cycle_time_max(self, report: RollupReport) -> None:
        assert report.system.cycle_time_max == pytest.approx(12.5)

    def test_cycle_time_stories_above_threshold(self, report: RollupReport) -> None:
        # > 7 days: 7.2, 8.4, 9.2, 10.1, 12.5 = 5 stories
        assert report.system.cycle_time_stories_above_threshold == 5


# ---------------------------------------------------------------------------
# Owner view
# ---------------------------------------------------------------------------


class TestOwnerView:
    def test_upstream_owners_present(self, report: RollupReport) -> None:
        assert set(report.owner.upstream.keys()) == {"Yanna Lopes", "Hector Sanchez"}

    def test_yanna_upstream_story_count(self, report: RollupReport) -> None:
        # 100, 101, 102, 103, 108, 109 → 6
        assert report.owner.upstream["Yanna Lopes"].stories == 6

    def test_hector_upstream_story_count(self, report: RollupReport) -> None:
        # 104, 105, 106, 107 → 4
        assert report.owner.upstream["Hector Sanchez"].stories == 4

    def test_downstream_owners_present(self, report: RollupReport) -> None:
        assert set(report.owner.downstream_by_owner.keys()) == {
            "Dulce Hernandez Cruz", "Rafael Moreno"
        }

    def test_approvers_present(self, report: RollupReport) -> None:
        assert set(report.owner.approvers.keys()) == {"hector-id", "yanna-id"}

    def test_hector_approver_count(self, report: RollupReport) -> None:
        # Stories 100-103, 108, 109 → 6 approved by hector
        assert report.owner.approvers["hector-id"].approved == 6

    def test_yanna_approver_count(self, report: RollupReport) -> None:
        # Stories 104-107 → 4 approved by yanna
        assert report.owner.approvers["yanna-id"].approved == 4

    def test_hector_approver_downstream_pass_rate(self, report: RollupReport) -> None:
        # hector approved: 100, 101, 102, 103, 108, 109
        # U12/C3 are upstream dims → 101, 102 have downstream PASS
        # downstream PASS: 100, 101, 102, 109 = 4/6
        assert report.owner.approvers["hector-id"].downstream_pass_rate_of_approved == pytest.approx(4 / 6, abs=0.01)


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------


class TestMarkdownFormatter:
    def test_header_contains_dates(self, md: str) -> None:
        assert "2 Apr 2026" in md
        assert "15 Apr 2026" in md

    def test_six_yes_rate_shown(self, md: str) -> None:
        assert "60%" in md

    def test_top_failing_dims_in_table(self, md: str) -> None:
        assert "U12" in md
        assert "D10" in md

    def test_pending_judge_section_present(self, md: str) -> None:
        assert "7 dimensions pending judge layer" in md
        assert "Y1" in md
        assert "Y2" in md

    def test_cycle_time_section_present(self, md: str) -> None:
        assert "Cycle Time" in md
        assert "p50" in md
        assert "p90" in md

    def test_owner_breakdown_present(self, md: str) -> None:
        assert "Yanna Lopes" in md
        assert "Dulce Hernandez Cruz" in md

    def test_recommendations_section_present(self, md: str) -> None:
        assert "## Recommendations" in md

    def test_exactly_three_recommendations(self, md: str) -> None:
        recs_section = md.split("## Recommendations")[-1]
        # Count numbered list items starting at column 0
        numbered = [l for l in recs_section.splitlines() if l.startswith(("1.", "2.", "3."))]
        assert len(numbered) == 3

    def test_no_hedging_language(self, md: str) -> None:
        hedges = ["it depends", "consider", "might want", "could be", "perhaps"]
        lower = md.lower()
        for hedge in hedges:
            assert hedge not in lower, f"Hedging language found: {hedge!r}"

    def test_snapshot(self, md: str) -> None:
        SNAPSHOTS.mkdir(exist_ok=True)
        path = SNAPSHOTS / "rollup.md"
        path.write_text(md)
        assert path.read_text() == md


# ---------------------------------------------------------------------------
# Print markdown for Jeffrey's review (visible with -s)
# ---------------------------------------------------------------------------


def test_print_rollup_md(md: str, capsys: pytest.CaptureFixture[str]) -> None:
    with capsys.disabled():
        print("\n" + "=" * 70)
        print("COMMIT 9 CHECKPOINT — rollup.md output")
        print("=" * 70)
        print(md)
        print("=" * 70)
