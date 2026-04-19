"""Deterministic upstream evaluators — Y3a, Y4, Y5, Y6, U7, U8, U10, U12.

Each function is pure: same inputs → same DimensionResult. No I/O, no side effects.
Judge-only dimensions (Y1, Y2, Y3b, U9, U11) are not here — those live in the
judge runner (commit 7).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from nolte_grader.core.models import DimensionResult, Verdict
from nolte_grader.parsers.description import extract_sections, section_present

if TYPE_CHECKING:
    from nolte_grader.parsers.changelog import FieldEdit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STAGING_RE = re.compile(
    r"(staging|stage\.|\.stage\b|dev\.|\.dev\b|\.test\b|test\.|qa\.|\.qa\b"
    r"|uat\.|\.uat\b|preprod|pre-prod|localhost|127\.0\.0\.1)",
    re.IGNORECASE,
)

_LOCAL_ADDR_RE = re.compile(r"(localhost|127\.0\.0\.1|0\.0\.0\.0)", re.IGNORECASE)

_RISKS_PLACEHOLDER_RE = re.compile(
    r"^(todo|tbd|tbc|fill\s*(in|here|this)?|placeholder|add\s*here|n/a|na)$",
    re.IGNORECASE,
)


def _r(
    code: str,
    verdict: Verdict,
    evidence_code: str,
    rationale: str,
    **kwargs: object,
) -> DimensionResult:
    return DimensionResult(
        code=code,
        verdict=verdict,
        evidence_code=evidence_code,
        rationale=rationale,
        **kwargs,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Y3a — AC present and pre-commit (deterministic part of Y3)
# ---------------------------------------------------------------------------


def eval_y3a(
    description_at_commit: str | None,
    commit_ts: datetime | None,
) -> DimensionResult:
    """Y3.a — Acceptance Criteria section present at commitment.

    Caller contract (spec §7.2 U7, §7.3 C2): when ``description_at_commit``
    is None because no description edits exist in the changelog, the caller
    must pass ``fields.description`` as the fallback.  A Story that was
    written correctly and never edited post-spec must not be penalized for
    the absence of changelog edit history.  Pass None only when the caller
    genuinely cannot determine the description at commit time.
    """
    if commit_ts is None:
        return _r("Y3", Verdict.NOT_APPLICABLE, "NOT_APPLICABLE",
                  "Story never committed; Y3.a not applicable.")
    if description_at_commit is None:
        return _r("Y3", Verdict.INSUFFICIENT_EVIDENCE, "EVIDENCE_INSUFFICIENT_TO_JUDGE",
                  "Cannot determine description at commitment time.")
    sections = extract_sections(description_at_commit)
    if not section_present(sections, "acceptance_criteria"):
        return _r("Y3", Verdict.FAIL, "AC_EMPTY_OR_PLACEHOLDER",
                  "Acceptance Criteria section absent from description at commitment.")
    return _r("Y3", Verdict.PASS, "AC_PRESENT_AND_PRE_COMMIT",
              "Acceptance Criteria section present in description at commitment.")


# ---------------------------------------------------------------------------
# Y4 — Non-builder validates
# ---------------------------------------------------------------------------


def eval_y4(
    validator_account_id: str | None,
    builder_account_ids: set[str],
    team_size: int,
) -> DimensionResult:
    """Y4 — Account that executed Done transition is not a Story builder.

    Args:
        validator_account_id: accountId of actor who moved Story to Done.
            None if no In Validation → Done transition exists.
        builder_account_ids: accountIds assigned to any In Implementation
            sub-task on this Story.
        team_size: Team size from config (TeamsConfig.size_for). When 1,
            the single-person team exception applies.
    """
    if validator_account_id is None:
        return _r("Y4", Verdict.INSUFFICIENT_EVIDENCE, "EVIDENCE_INSUFFICIENT_TO_JUDGE",
                  "No In Validation → Done transition found; validator unknown.")
    if team_size == 1:
        return _r("Y4", Verdict.PASS, "TEAM_SIZE_EXCEPTION",
                  "Single-person team; non-builder validation not enforced.")
    if validator_account_id in builder_account_ids:
        return _r("Y4", Verdict.FAIL, "VALIDATOR_IS_BUILDER",
                  "Account that validated is also a Story builder.")
    return _r("Y4", Verdict.PASS, "VALIDATOR_INDEPENDENT",
              "Validator is independent from Story builders.")


# ---------------------------------------------------------------------------
# Y5 — Live in production when called Done
# ---------------------------------------------------------------------------


def eval_y5(
    production_reference: str | None,
    done_ts: datetime | None,
    reference_added_after_done: bool = False,
) -> DimensionResult:
    """Y5 — Production Release Reference populated at Done.

    Args:
        production_reference: Current value of the Production Release Reference
            custom field. Empty string or None → FAIL.
        done_ts: Timestamp of Done transition. None → NOT_APPLICABLE.
        reference_added_after_done: True if changelog shows the field was first
            set after ``done_ts`` (grader computes this from field edits).
    """
    if done_ts is None:
        return _r("Y5", Verdict.NOT_APPLICABLE, "NOT_APPLICABLE",
                  "Story not yet Done.")
    if not production_reference:
        return _r("Y5", Verdict.FAIL, "PRODUCTION_REFERENCE_EMPTY",
                  "Production Release Reference field is empty.")
    if reference_added_after_done:
        return _r("Y5", Verdict.FAIL, "PRODUCTION_REFERENCE_POST_DONE",
                  "Production Release Reference populated after Done transition.")
    if _STAGING_RE.search(production_reference):
        return _r("Y5", Verdict.FAIL, "PRODUCTION_REFERENCE_STAGING_ONLY",
                  "Production Release Reference contains staging/dev indicator.")
    return _r("Y5", Verdict.PASS, "PRODUCTION_REFERENCE_PRESENT_AT_DONE",
              "Production Release Reference populated with non-staging reference at Done.")


# ---------------------------------------------------------------------------
# Y6 — Cycle time ≤ threshold (retrospective)
# ---------------------------------------------------------------------------


def eval_y6(
    commit_ts: datetime | None,
    done_implementing_ts: datetime | None,
    threshold_days: int = 7,
) -> DimensionResult:
    """Y6 — Ready → Done Implementing elapsed time ≤ threshold."""
    if commit_ts is None or done_implementing_ts is None:
        return _r("Y6", Verdict.NOT_APPLICABLE, "NOT_APPLICABLE",
                  "No complete Ready → Done Implementing window; Y6 not applicable.")
    elapsed = (done_implementing_ts - commit_ts).total_seconds() / 86400
    if elapsed <= threshold_days:
        return _r("Y6", Verdict.PASS, "CYCLE_TIME_WITHIN_LIMIT",
                  f"Cycle time {elapsed:.1f} days within {threshold_days}-day limit.")
    return _r("Y6", Verdict.FAIL, "CYCLE_TIME_EXCEEDS_LIMIT",
              f"Cycle time {elapsed:.1f} days exceeds {threshold_days}-day limit.")


# ---------------------------------------------------------------------------
# U7 — No scope evolution after commitment
# ---------------------------------------------------------------------------


def eval_u7(
    post_commit_description_edits: list[FieldEdit],
) -> DimensionResult:
    """U7 — No edits to AC or Scenarios sections after commitment.

    Whitespace-only changes are ignored (sections are stripped before compare).
    Jira changelog stores description edits as text representations of ADF;
    ``extract_sections()`` is applied directly to those strings.
    """
    for edit in post_commit_description_edits:
        from_secs = extract_sections(edit.from_value)
        to_secs = extract_sections(edit.to_value)
        checks = (
            ("acceptance_criteria", "AC_EDITED_POST_COMMIT"),
            ("scenarios", "SCENARIOS_EDITED_POST_COMMIT"),
        )
        for key, evidence_code in checks:
            before = (from_secs.get(key) or "").strip()  # type: ignore[literal-required]
            after = (to_secs.get(key) or "").strip()  # type: ignore[literal-required]
            if before != after:
                label = "Acceptance Criteria" if key == "acceptance_criteria" else "Scenarios"
                return _r("U7", Verdict.FAIL, evidence_code,
                          f"{label} section changed after commitment.")
    return _r("U7", Verdict.PASS, "NO_POST_COMMIT_AC_EDITS",
              "No AC or Scenarios changes found after commitment.")


# ---------------------------------------------------------------------------
# U8 — Validation outputs are Acceptance or Story Defect only
# ---------------------------------------------------------------------------


def eval_u8(
    in_validation_start: datetime | None,
    in_validation_end: datetime | None,
    linked_issue_types_and_times: list[tuple[str, datetime]],
) -> DimensionResult:
    """U8 — No new Stories, Tasks, or Bugs created during In Validation.

    Args:
        in_validation_start: When Story entered In Validation. None → NOT_APPLICABLE.
        in_validation_end: When Story left In Validation. None = still in window.
        linked_issue_types_and_times: (issue_type, created_at) for all child/
            linked issues on this Story. The grader provides all types; this
            evaluator filters to forbidden ones.
    """
    if in_validation_start is None:
        return _r("U8", Verdict.NOT_APPLICABLE, "NOT_APPLICABLE",
                  "Story never entered In Validation.")
    _FORBIDDEN: dict[str, str] = {
        "Story": "NEW_STORY_CREATED_DURING_VALIDATION",
        "Task": "NEW_TASK_CREATED_DURING_VALIDATION",
        "Bug": "NEW_BUG_CREATED_DURING_VALIDATION",
    }
    window_end = in_validation_end or datetime.now(timezone.utc)
    for issue_type, created_at in linked_issue_types_and_times:
        code = _FORBIDDEN.get(issue_type)
        if code is None:
            continue
        if in_validation_start <= created_at <= window_end:
            return _r("U8", Verdict.FAIL, code,
                      f"{issue_type} created during In Validation window.")
    return _r("U8", Verdict.PASS, "VALIDATION_OUTPUTS_IN_CONTRACT",
              "No forbidden issue types created during In Validation.")


# ---------------------------------------------------------------------------
# U10 — Impact measurement infrastructure present at Done
# ---------------------------------------------------------------------------


def eval_u10(
    impact_link: str | None,
    link_resolvable: bool | None = None,
) -> DimensionResult:
    """U10 — Impact Measurement Link field populated with a resolvable URL.

    Args:
        impact_link: Field value. Empty/None → FAIL IMPACT_LINK_MISSING.
        link_resolvable: Result of HTTP HEAD check (non-blocking, 5s timeout).
            True = 2xx/3xx. False = 4xx/5xx. None = check not performed or
            timed out → PASS with IMPACT_LINK_UNREACHABLE flag.
    """
    if not impact_link:
        return _r("U10", Verdict.FAIL, "IMPACT_LINK_MISSING",
                  "Impact Measurement Link field is empty.")
    if link_resolvable is False:
        return _r("U10", Verdict.FAIL, "IMPACT_LINK_BROKEN",
                  "Impact Measurement Link resolved to an error response.")
    if link_resolvable is None:
        return _r("U10", Verdict.PASS, "IMPACT_LINK_UNREACHABLE",
                  "Impact Measurement Link present; reachability not confirmed.")
    return _r("U10", Verdict.PASS, "IMPACT_LINK_PRESENT_AND_RESOLVABLE",
              "Impact Measurement Link present and resolvable.")


# ---------------------------------------------------------------------------
# U12 — Risks section populated
# ---------------------------------------------------------------------------


def eval_u12(
    risks_section: str | None,
) -> DimensionResult:
    """U12 — Risks section present in description.

    Per spec §7.2: section populated, even with "None identified," passes.
    Only genuinely absent, blank, or placeholder text (TODO/TBD/N/A) fails.
    """
    if risks_section is None:
        return _r("U12", Verdict.FAIL, "RISKS_EMPTY_OR_MISSING",
                  "Risks section absent from description.")
    stripped = risks_section.strip()
    if not stripped:
        return _r("U12", Verdict.FAIL, "RISKS_EMPTY_OR_MISSING",
                  "Risks section present but empty.")
    if _RISKS_PLACEHOLDER_RE.match(stripped):
        return _r("U12", Verdict.FAIL, "RISKS_PLACEHOLDER",
                  "Risks section contains placeholder text only.")
    return _r("U12", Verdict.PASS, "RISKS_POPULATED",
              "Risks section populated with content.")
