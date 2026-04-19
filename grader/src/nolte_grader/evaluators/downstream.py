"""Deterministic downstream evaluators — D1, D4, D5, D6, D7, D8, D9, D10.

Judge-only dimensions (D2, D3) and the D+J dimension D2 are not here.
All functions are pure: no I/O, no side effects.

NOT_APPLICABLE semantics: all downstream dimensions are NOT_APPLICABLE when
the Story never reached the relevant gate (e.g., never committed → D1–D10 NA;
never reached Done Implementing → D4–D6 NA).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

from nolte_grader.core.models import DimensionResult, Verdict
from nolte_grader.parsers.changelog import ParsedChangelog

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_LOCAL_ADDR_RE = re.compile(r"(localhost|127\.0\.0\.1|0\.0\.0\.0)", re.IGNORECASE)


def _r(
    code: str,
    verdict: Verdict,
    evidence_code: str,
    rationale: str,
) -> DimensionResult:
    return DimensionResult(
        code=code,
        verdict=verdict,
        evidence_code=evidence_code,
        rationale=rationale,
    )


def _na(code: str, reason: str) -> DimensionResult:
    return _r(code, Verdict.NOT_APPLICABLE, "NOT_APPLICABLE", reason)


# ---------------------------------------------------------------------------
# D1 — Sub-tasks created after Story review (commitment)
# ---------------------------------------------------------------------------


def eval_d1(
    subtask_creation_times: list[datetime],
    commit_ts: datetime | None,
    is_trivial: bool = False,
) -> DimensionResult:
    """D1 — Sub-tasks created after commitment, not before.

    Args:
        subtask_creation_times: ``fields.created`` timestamps for all sub-tasks.
        commit_ts: Story commitment timestamp. None → NOT_APPLICABLE.
        is_trivial: If True (D2 judge classified as trivial), absence of
            sub-tasks is acceptable.
    """
    if commit_ts is None:
        return _na("D1", "Story never committed; D1 not applicable.")
    if not subtask_creation_times:
        if is_trivial:
            return _r("D1", Verdict.PASS, "SUBTASKS_CREATED_POST_COMMIT",
                      "No sub-tasks; Story classified as trivial.")
        return _r("D1", Verdict.FAIL, "SUBTASKS_ABSENT_ON_NON_TRIVIAL",
                  "No sub-tasks present on committed Story.")
    pre_commit = [t for t in subtask_creation_times if t < commit_ts]
    if pre_commit:
        return _r("D1", Verdict.FAIL, "SUBTASKS_CREATED_PRE_COMMIT",
                  f"{len(pre_commit)} sub-task(s) created before commitment.")
    return _r("D1", Verdict.PASS, "SUBTASKS_CREATED_POST_COMMIT",
              "All sub-tasks created after commitment.")


# ---------------------------------------------------------------------------
# D4 — All sub-tasks closed at Done Implementing
# ---------------------------------------------------------------------------


def eval_d4(
    open_subtask_keys_at_done_impl: list[str],
    done_implementing_ts: datetime | None,
) -> DimensionResult:
    """D4 — No open sub-tasks when Story transitions to Done Implementing.

    Args:
        open_subtask_keys_at_done_impl: Keys of sub-tasks that were not in
            a closed/done status at the Done Implementing moment. Grader
            computes this from sub-task changelogs.
        done_implementing_ts: Timestamp of Done Implementing transition. None → NA.
    """
    if done_implementing_ts is None:
        return _na("D4", "Story never reached Done Implementing; D4 not applicable.")
    if not open_subtask_keys_at_done_impl:
        return _r("D4", Verdict.PASS, "ALL_SUBTASKS_CLOSED_AT_DONE_IMPL",
                  "All sub-tasks closed at Done Implementing.")
    sample = ", ".join(open_subtask_keys_at_done_impl[:3])
    extra = f" (+{len(open_subtask_keys_at_done_impl) - 3} more)" if len(open_subtask_keys_at_done_impl) > 3 else ""
    return _r("D4", Verdict.FAIL, "OPEN_SUBTASK_AT_DONE_IMPL",
              f"Open sub-task(s) at Done Implementing: {sample}{extra}.")


# ---------------------------------------------------------------------------
# D5 — Tests passing with evidence
# ---------------------------------------------------------------------------


def eval_d5(
    test_subtask_found: bool,
    test_subtask_closed: bool,
    test_subtask_description: str | None,
    done_implementing_ts: datetime | None,
) -> DimensionResult:
    """D5 — Test sub-task present, closed, and contains a CI run link.

    Args:
        test_subtask_found: True if a sub-task matching the test title
            convention exists (config ``conventions.test_subtask_title_pattern``).
        test_subtask_closed: True if the test sub-task's status is Done/closed.
        test_subtask_description: Description text of the test sub-task.
            Checked for any http(s) URL (CI run link). None = no description.
        done_implementing_ts: Timestamp of Done Implementing. None → NA.
    """
    if done_implementing_ts is None:
        return _na("D5", "Story never reached Done Implementing; D5 not applicable.")
    if not test_subtask_found:
        return _r("D5", Verdict.FAIL, "TEST_SUBTASK_MISSING",
                  "No test sub-task matching title convention found.")
    if not test_subtask_closed:
        return _r("D5", Verdict.FAIL, "TEST_SUBTASK_OPEN",
                  "Test sub-task found but not closed.")
    if not test_subtask_description or not _URL_RE.search(test_subtask_description):
        return _r("D5", Verdict.FAIL, "TEST_SUBTASK_MISSING_CI_LINK",
                  "Test sub-task closed but no CI run link in description.")
    return _r("D5", Verdict.PASS, "TEST_SUBTASK_CLOSED_WITH_CI_LINK",
              "Test sub-task closed with CI run link present.")


# ---------------------------------------------------------------------------
# D6 — Operationally shippable
# ---------------------------------------------------------------------------


def eval_d6(
    deploy_reference: str | None,
    done_implementing_ts: datetime | None,
) -> DimensionResult:
    """D6 — Production Release Reference populated with a non-local reference at Done Implementing."""
    if done_implementing_ts is None:
        return _na("D6", "Story never reached Done Implementing; D6 not applicable.")
    if not deploy_reference:
        return _r("D6", Verdict.FAIL, "DEPLOY_REFERENCE_EMPTY",
                  "Production Release Reference field empty at Done Implementing.")
    if _LOCAL_ADDR_RE.search(deploy_reference):
        return _r("D6", Verdict.FAIL, "DEPLOY_REFERENCE_LOCAL_ONLY",
                  "Production Release Reference points to local-only address.")
    return _r("D6", Verdict.PASS, "DEPLOY_REFERENCE_PRESENT",
              "Production Release Reference populated with non-local reference.")


# ---------------------------------------------------------------------------
# D7 — WIP respected during In Implementation
# ---------------------------------------------------------------------------


def eval_d7(
    per_engineer_violated_days: list[date],
    system_violated_days: list[date],
    has_wip_exception: bool,
    commit_ts: datetime | None,
) -> DimensionResult:
    """D7 — WIP limits respected on every day this Story was In Implementation.

    Args:
        per_engineer_violated_days: Days where the per-engineer In Implementation
            count exceeded the config limit. Grader computes from cross-issue daily
            WIP state.
        system_violated_days: Days where the system-wide In Implementation count
            exceeded the config limit.
        has_wip_exception: True if a comment containing the exact phrase
            ``WIP exception:`` (system-rules.md §4) from an authorized approver
            was found during the In Implementation window.
        commit_ts: Commitment timestamp. None → NOT_APPLICABLE.
    """
    if commit_ts is None:
        return _na("D7", "Story never committed; D7 not applicable.")
    if has_wip_exception:
        return _r("D7", Verdict.PASS, "WIP_WITHIN_LIMITS",
                  "WIP exception logged by authorized approver.")
    if per_engineer_violated_days:
        return _r("D7", Verdict.FAIL, "WIP_EXCEEDED_PER_ENGINEER",
                  f"Per-engineer WIP exceeded on {len(per_engineer_violated_days)} day(s) without exception.")
    if system_violated_days:
        return _r("D7", Verdict.FAIL, "WIP_EXCEEDED_SYSTEM",
                  f"System WIP exceeded on {len(system_violated_days)} day(s) without exception.")
    return _r("D7", Verdict.PASS, "WIP_WITHIN_LIMITS",
              "WIP limits respected throughout In Implementation.")


# ---------------------------------------------------------------------------
# D8 — Cycle time within norm
# ---------------------------------------------------------------------------


def eval_d8(
    commit_ts: datetime | None,
    done_implementing_ts: datetime | None,
    threshold_days: int = 7,
) -> DimensionResult:
    """D8 — Ready → Done Implementing elapsed time within configured norm.

    Mirrors Y6's computation but applies in the downstream lane (Hector's view).
    """
    if commit_ts is None or done_implementing_ts is None:
        return _na("D8", "No complete Ready → Done Implementing window; D8 not applicable.")
    elapsed = (done_implementing_ts - commit_ts).total_seconds() / 86400
    if elapsed <= threshold_days:
        return _r("D8", Verdict.PASS, "CYCLE_TIME_WITHIN_NORM",
                  f"Cycle time {elapsed:.1f} days within {threshold_days}-day norm.")
    return _r("D8", Verdict.FAIL, "CYCLE_TIME_EXCEEDS_NORM",
              f"Cycle time {elapsed:.1f} days exceeds {threshold_days}-day norm.")


# ---------------------------------------------------------------------------
# D9 — Story defect rate
# ---------------------------------------------------------------------------


def eval_d9(
    in_scope_defect_count: int,
    done_implementing_ts: datetime | None,
) -> DimensionResult:
    """D9 — Zero Story Defects for this Story (in-scope defects only).

    Args:
        in_scope_defect_count: Count of linked Story Defects that map to
            agreed scenarios (scope-evolution defects excluded per U9).
            Pass the raw defect count when U9 has not run yet.
        done_implementing_ts: None → NOT_APPLICABLE.
    """
    if done_implementing_ts is None:
        return _na("D9", "Story never reached Done Implementing; D9 not applicable.")
    if in_scope_defect_count == 0:
        return _r("D9", Verdict.PASS, "ZERO_DEFECTS",
                  "No Story Defects reported.")
    return _r("D9", Verdict.FAIL, "DEFECTS_PRESENT",
              f"{in_scope_defect_count} Story Defect(s) reported.")


# ---------------------------------------------------------------------------
# D10 — No backward transitions
# ---------------------------------------------------------------------------


def eval_d10(changelog: ParsedChangelog) -> DimensionResult:
    """D10 — All status transitions are forward in the kanban order."""
    backward = changelog.backward_transitions()
    if not backward:
        return _r("D10", Verdict.PASS, "FORWARD_ONLY_TRANSITIONS",
                  "All status transitions are forward.")
    first = backward[0]
    return _r("D10", Verdict.FAIL, "BACKWARD_TRANSITION_DETECTED",
              f"{len(backward)} backward transition(s); first: {first.from_status} → {first.to_status}.")
