"""Grader — the library's public entry point. Spec §3.2.

Adapters are injected at construction so NolteOS can swap any of them.
Each has a default implementation for standalone use; see
``nolte_grader.adapters`` (wired in later commits).

Embeddability invariants (spec §3.4):
- No module-level state.
- Never reads os.environ, working directory, or config files.
- No print statements — structlog only.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any

from nolte_grader.core.config import GraderConfig, config_hash
from nolte_grader.core.errors import EvaluatorError
from nolte_grader.core.logging import get_logger
from nolte_grader.core.models import (
    DimensionResult,
    IssueGrade,
    RollupReport,
    Verdict,
)
from nolte_grader.evaluators import (
    eval_c1,
    eval_c3,
    eval_d1,
    eval_d4,
    eval_d5,
    eval_d6,
    eval_d7,
    eval_d8,
    eval_d9,
    eval_d10,
    eval_u7,
    eval_u8,
    eval_u10,
    eval_u12,
    eval_y3a,
    eval_y4,
    eval_y5,
    eval_y6,
)
from nolte_grader.parsers.adf import adf_to_text
from nolte_grader.parsers.changelog import ParsedChangelog, parse_changelog
from nolte_grader.parsers.description import extract_sections

if TYPE_CHECKING:
    from nolte_grader.core.protocols import (
        JiraClientProtocol,
        JudgeClientProtocol,
        MetricsSinkProtocol,
        SecretsProviderProtocol,
        StorageProtocol,
    )

log = get_logger(__name__)

# Dimensions that are J-only in this build (no deterministic part).
# They are skipped silently in commit 6; the judge runner adds them in commit 7+.
_JUDGE_ONLY_DIMS = frozenset({"Y1", "Y2", "U9", "U11", "C2", "D2", "D3"})

# Dimensions whose Y3 overall represents the deterministic gate only (Y3.a).
# Y3.b (judge quality) is added when the judge runner is wired.
_SIX_YES_CODES = ("Y1", "Y2", "Y3", "Y4", "Y5", "Y6")
_UPSTREAM_CODES = ("Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "U7", "U8", "U9", "U10", "U11", "U12")
_COMMITMENT_CODES = ("C1", "C2", "C3")
_DOWNSTREAM_CODES = ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10")


class Grader:
    """Core grading engine.

    Instantiate with a ``GraderConfig``. Adapters are optional at
    construction; missing adapters raise ``NotImplementedError`` when
    the corresponding method is called.
    """

    def __init__(
        self,
        config: GraderConfig,
        *,
        jira_client: JiraClientProtocol | None = None,
        judge_client: JudgeClientProtocol | None = None,
        storage: StorageProtocol | None = None,
        secrets: SecretsProviderProtocol | None = None,
        metrics: MetricsSinkProtocol | None = None,
    ) -> None:
        self._config = config
        self._jira_client = jira_client
        self._judge_client = judge_client
        self._storage = storage
        self._secrets = secrets
        self._metrics = metrics

    @property
    def config(self) -> GraderConfig:
        return self._config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def grade_issue(self, issue_key: str) -> IssueGrade:
        """Grade a single issue via the Jira adapter.

        Requires ``jira_client`` to be set. Fetches the issue and all
        subtasks, then delegates to ``grade_issue_from_data``.
        """
        if self._jira_client is None:
            raise NotImplementedError(
                "grade_issue requires a jira_client adapter. "
                "Use grade_issue_from_data() to grade pre-fetched data."
            )
        log.info("grading issue", issue_key=issue_key)
        issue = self._jira_client.get_issue(issue_key)
        subtask_refs = issue.get("fields", {}).get("subtasks") or []
        subtasks = []
        for ref in subtask_refs:
            st_key = ref.get("key", "")
            if st_key:
                subtasks.append(self._jira_client.get_issue(st_key))
        return self.grade_issue_from_data(issue, subtasks)

    def grade_issue_from_data(
        self,
        issue: dict[str, Any],
        subtasks: list[dict[str, Any]],
    ) -> IssueGrade:
        """Grade a pre-fetched issue dict (used directly by tests and fixtures).

        Args:
            issue: Raw Jira issue dict (from ``get_issue()`` or a fixture file).
            subtasks: Full Jira dicts for each sub-task (same shape as ``issue``).
        """
        return self._grade(issue, subtasks)

    def grade_issues(self, keys: list[str]) -> list[IssueGrade]:
        """Grade multiple issues. Delegates to grade_issue."""
        return [self.grade_issue(k) for k in keys]

    def grade_by_window(
        self,
        from_date: date,
        to_date: date,
        project_keys: list[str],
    ) -> list[IssueGrade]:
        """Grade all eligible issues in [from_date, to_date] across project_keys.

        Wired in: commit 2 (Jira adapter, JQL search).
        """
        raise NotImplementedError(
            "grade_by_window requires the Jira adapter from commit 2."
        )

    def rollup(self, grades: list[IssueGrade]) -> RollupReport:
        """Aggregate per-issue grades into a run-level report.

        Wired in: commit 10 (aggregator + rollup).
        """
        raise NotImplementedError("rollup is wired in commit 10.")

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _grade(
        self,
        issue: dict[str, Any],
        subtasks: list[dict[str, Any]],
    ) -> IssueGrade:
        fields = issue.get("fields") or {}
        issue_key: str = issue.get("key", "")
        project_key: str = (fields.get("project") or {}).get("key", "")
        issue_type: str = (fields.get("issuetype") or {}).get("name", "")
        title: str = fields.get("summary", "")
        epic_key: str | None = (fields.get("parent") or {}).get("key") or None

        # Parse changelog
        changelog = parse_changelog(
            (issue.get("changelog") or {}).get("histories") or []
        )

        # Normalize description
        raw_desc = fields.get("description")
        rendered_desc = (issue.get("renderedFields") or {}).get("description")
        description = adf_to_text(raw_desc or rendered_desc)
        sections = extract_sections(description)

        # Gate timestamps
        commit_ts = changelog.commitment_timestamp()
        done_implementing_ts = changelog.done_implementing_timestamp()
        done_ts = changelog.done_timestamp()

        # Cycle time
        cycle_time_days: float | None = None
        if commit_ts and done_implementing_ts:
            cycle_time_days = round(
                (done_implementing_ts - commit_ts).total_seconds() / 86400, 2
            )

        # Description at commitment (spec §7.2 U7, §7.3 C2):
        # No edit history → current description was always the description; never penalize.
        desc_at_commit: str | None = None
        if commit_ts is not None:
            desc_at_commit = changelog.description_at(commit_ts)
            if desc_at_commit is None:
                desc_at_commit = description  # fallback: unchanged since spec was written

        # Validator (actor who moved Story to Done)
        validator_id = changelog.actor_who_transitioned_to("Done")

        # Builder account IDs (subtask assignees)
        builder_ids: set[str] = {
            (st.get("fields") or {}).get("assignee", {}).get("accountId", "")
            for st in subtasks
            if (st.get("fields") or {}).get("assignee")
        }
        builder_ids.discard("")

        # Custom field access (field ID from config)
        prod_ref = _get_field(fields, self._config.custom_fields.production_release_reference)
        impact_link = _get_field(fields, self._config.custom_fields.impact_measurement_link)

        # Was production reference added after Done?
        ref_after_done = _field_added_after(
            changelog,
            self._config.custom_fields.production_release_reference,
            done_ts,
        )

        # Post-commit description edits (U7)
        post_commit_edits = (
            changelog.field_edits_after("description", commit_ts)
            if commit_ts else []
        )

        # In Validation window (U8)
        in_val_start: datetime | None = None
        in_val_end: datetime | None = None
        for status, entered, left in changelog.status_intervals():
            if status == "In Validation":
                in_val_start = entered
                in_val_end = left
                break

        # Linked issue types and creation times (U8)
        linked_types_times: list[tuple[str, datetime]] = _extract_linked_issues(fields)

        # Spec Approver (C3)
        spec_approver_id = changelog.spec_approver_at_ready_transition(
            self._config.custom_fields.spec_approver
        )
        authorized_ids: set[str] = {
            a.accountId
            for a in self._config.authorized_approvers.for_project(project_key)
        }

        # Team size (Y4)
        team_size = self._config.teams.size_for(project_key)

        # Subtask creation times (D1)
        subtask_creation_times = [
            _parse_ts(st.get("fields", {}).get("created", ""))
            for st in subtasks
            if st.get("fields", {}).get("created")
        ]

        # Open subtasks at Done Implementing (D4)
        open_at_done_impl = _open_subtask_keys_at(subtasks, done_implementing_ts)

        # Test subtask (D5)
        test_pattern = self._config.conventions.test_subtask_title_pattern
        test_subtask = _find_test_subtask(subtasks, test_pattern)
        test_found = test_subtask is not None
        test_closed = False
        test_description: str | None = None
        if test_subtask is not None:
            st_cl = parse_changelog(
                (test_subtask.get("changelog") or {}).get("histories") or []
            )
            test_closed = st_cl.done_timestamp() is not None
            test_description = adf_to_text(
                test_subtask.get("fields", {}).get("description")
            ) or None

        # Deploy reference (D6) — same field as Y5
        deploy_reference = prod_ref

        # WIP violations (D7): cross-issue data — not available per-issue; grader
        # must be called from grade_by_window() which computes this from all issues.
        # Per-issue grading defaults to no violation; override via rollup path.
        per_eng_violations: list[date] = []
        sys_violations: list[date] = []
        has_wip_exception = False

        # Story defect count (D9)
        defect_count = sum(
            1
            for link in (fields.get("issueLinks") or [])
            if _is_story_defect_link(link)
        )

        # Enabled dimension set
        enabled = set(self._config.dimensions.enabled)

        # Run deterministic evaluators
        dims: dict[str, DimensionResult] = {}

        if "Y3" in enabled:
            dims["Y3"] = eval_y3a(desc_at_commit, commit_ts)
        if "Y4" in enabled:
            dims["Y4"] = eval_y4(validator_id, builder_ids, team_size)
        if "Y5" in enabled:
            dims["Y5"] = eval_y5(prod_ref, done_ts, ref_after_done)
        if "Y6" in enabled:
            dims["Y6"] = eval_y6(commit_ts, done_implementing_ts, self._config.thresholds.cycle_time_days)
        if "U7" in enabled:
            dims["U7"] = eval_u7(post_commit_edits)
        if "U8" in enabled:
            dims["U8"] = eval_u8(in_val_start, in_val_end, linked_types_times)
        if "U10" in enabled:
            dims["U10"] = eval_u10(impact_link, link_resolvable=None)
        if "U12" in enabled:
            dims["U12"] = eval_u12(sections.get("risks"))
        if "C1" in enabled:
            dims["C1"] = eval_c1(commit_ts)
        if "C3" in enabled:
            dims["C3"] = eval_c3(spec_approver_id, authorized_ids, builder_ids)
        if "D1" in enabled:
            dims["D1"] = eval_d1(subtask_creation_times, commit_ts)
        if "D4" in enabled:
            dims["D4"] = eval_d4(open_at_done_impl, done_implementing_ts)
        if "D5" in enabled:
            dims["D5"] = eval_d5(test_found, test_closed, test_description, done_implementing_ts)
        if "D6" in enabled:
            dims["D6"] = eval_d6(deploy_reference, done_implementing_ts)
        if "D7" in enabled:
            dims["D7"] = eval_d7(per_eng_violations, sys_violations, has_wip_exception, commit_ts)
        if "D8" in enabled:
            dims["D8"] = eval_d8(commit_ts, done_implementing_ts, self._config.thresholds.cycle_time_days)
        if "D9" in enabled:
            dims["D9"] = eval_d9(defect_count, done_implementing_ts)
        if "D10" in enabled:
            dims["D10"] = eval_d10(changelog)

        # Compute overalls
        six_yes_overall = _compute_overall(dims, _SIX_YES_CODES)
        upstream_overall = _compute_overall(dims, _UPSTREAM_CODES)
        downstream_overall = _compute_overall(dims, _DOWNSTREAM_CODES)
        story_overall = _combine_overalls(upstream_overall, downstream_overall)

        # Flags
        flags: list[str] = []
        if any(r.evidence_code == "TEAM_SIZE_EXCEPTION" for r in dims.values()):
            flags.append("TEAM_SIZE_EXCEPTION")

        return IssueGrade(
            issue_key=issue_key,
            issue_type=issue_type,
            project_key=project_key,
            epic_key=epic_key,
            title=title,
            run_timestamp=datetime.now(timezone.utc),
            commitment_timestamp=commit_ts,
            done_timestamp=done_ts,
            cycle_time_days=cycle_time_days,
            upstream_owner=None,
            downstream_owner=(fields.get("assignee") or {}).get("displayName"),
            validator=validator_id,
            spec_approver=spec_approver_id,
            dimensions=dims,
            six_yes_overall=six_yes_overall,
            upstream_overall=upstream_overall,
            downstream_overall=downstream_overall,
            story_overall=story_overall,
            flags=flags,
            config_hash=config_hash(self._config),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_field(fields: dict[str, Any], field_id: str) -> str | None:
    """Read a field by ID from the Jira fields dict. Returns None if absent/null."""
    val = fields.get(field_id)
    if val is None:
        return None
    if isinstance(val, str):
        return val or None
    # Some custom fields are objects (user pickers, etc.) — extract text value
    if isinstance(val, dict):
        return val.get("value") or val.get("name") or str(val)
    return str(val)


def _field_added_after(
    changelog: ParsedChangelog,
    field_id: str,
    gate_ts: datetime | None,
) -> bool:
    """True if the field's first non-null value was set AFTER gate_ts."""
    if gate_ts is None:
        return False
    edits = changelog.field_edits_for(field_id)
    for edit in edits:
        if edit.to_value:
            return edit.timestamp > gate_ts
    return False


def _extract_linked_issues(
    fields: dict[str, Any],
) -> list[tuple[str, datetime]]:
    """Extract (issue_type, created_at) for linked issues."""
    result: list[tuple[str, datetime]] = []
    for link in fields.get("issueLinks") or []:
        for direction in ("inwardIssue", "outwardIssue"):
            linked = link.get(direction)
            if linked is None:
                continue
            issue_type = (linked.get("fields") or {}).get("issuetype", {}).get("name", "")
            created_raw = (linked.get("fields") or {}).get("created")
            if issue_type and created_raw:
                ts = _parse_ts(created_raw)
                if ts is not None:
                    result.append((issue_type, ts))
    return result


def _is_story_defect_link(link: dict[str, Any]) -> bool:
    link_type = (link.get("type") or {}).get("name", "").lower()
    return "defect" in link_type or "story defect" in link_type


def _parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    try:
        from dateutil import parser as du
        dt = du.parse(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def _open_subtask_keys_at(
    subtasks: list[dict[str, Any]],
    done_implementing_ts: datetime | None,
) -> list[str]:
    """Return keys of subtasks that were not Done at done_implementing_ts."""
    if done_implementing_ts is None:
        return []
    open_keys: list[str] = []
    for st in subtasks:
        st_cl = parse_changelog(
            (st.get("changelog") or {}).get("histories") or []
        )
        done_at = st_cl.done_timestamp()
        if done_at is None or done_at > done_implementing_ts:
            open_keys.append(st.get("key", "?"))
    return open_keys


def _find_test_subtask(
    subtasks: list[dict[str, Any]],
    pattern: str,
) -> dict[str, Any] | None:
    compiled = re.compile(pattern)
    for st in subtasks:
        summary = (st.get("fields") or {}).get("summary", "")
        if compiled.search(summary):
            return st
    return None


def _compute_overall(
    dims: dict[str, DimensionResult],
    codes: tuple[str, ...],
) -> Verdict:
    """Compute overall verdict for a group of dimension codes.

    NOT_APPLICABLE results are excluded from the denominator.
    INSUFFICIENT_EVIDENCE counts as FAIL.
    If no dimensions in the group were evaluated (all missing or NA) → NOT_APPLICABLE.
    """
    verdicts = [
        dims[c].verdict
        for c in codes
        if c in dims and dims[c].verdict != Verdict.NOT_APPLICABLE
    ]
    if not verdicts:
        return Verdict.NOT_APPLICABLE
    if any(v in (Verdict.FAIL, Verdict.INSUFFICIENT_EVIDENCE) for v in verdicts):
        return Verdict.FAIL
    return Verdict.PASS


def _combine_overalls(upstream: Verdict, downstream: Verdict) -> Verdict:
    """story_overall = PASS only if both upstream and downstream are PASS."""
    if upstream == Verdict.PASS and downstream == Verdict.PASS:
        return Verdict.PASS
    if Verdict.FAIL in (upstream, downstream):
        return Verdict.FAIL
    return Verdict.NOT_APPLICABLE
