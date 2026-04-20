"""Aggregator — reduces list[IssueGrade] to RollupReport.

Pure function: no I/O, no side effects. Called by Grader.rollup().
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, datetime, timezone

from nolte_grader.core.models import (
    ApproverStats,
    ClassificationCorrections,
    DimensionFailRate,
    IssueGrade,
    OwnerStats,
    OwnerView,
    RollupReport,
    RollupWindow,
    SystemView,
    Verdict,
)


def aggregate(
    grades: list[IssueGrade],
    *,
    run_id: str | None = None,
    window: RollupWindow | None = None,
    cycle_time_threshold_days: int = 7,
) -> RollupReport:
    """Reduce a list of IssueGrade records to a RollupReport.

    Args:
        grades: Non-empty list of per-issue grades from the same config run.
        run_id: Stable identifier for this rollup run. Generated as UUID4 if omitted.
        window: Date window the grades cover. Inferred from grade timestamps if omitted.
        cycle_time_threshold_days: Threshold used to count stories above cycle time norm.
    """
    if not grades:
        raise ValueError("Cannot aggregate zero grades.")

    run_id = run_id or str(uuid.uuid4())
    window = window or _infer_window(grades)
    cfg_hash = grades[0].config_hash

    system = _build_system_view(
        grades,
        run_id=run_id,
        window=window,
        cycle_time_threshold_days=cycle_time_threshold_days,
    )
    owner = _build_owner_view(grades)

    return RollupReport(system=system, owner=owner, config_hash=cfg_hash)


# ---------------------------------------------------------------------------
# System view
# ---------------------------------------------------------------------------


def _build_system_view(
    grades: list[IssueGrade],
    *,
    run_id: str,
    window: RollupWindow,
    cycle_time_threshold_days: int,
) -> SystemView:
    story_count = len(grades)

    # Six-yes pass rate
    six_yes_passes = sum(1 for g in grades if g.six_yes_overall == Verdict.PASS)
    six_yes_pass_rate = round(six_yes_passes / story_count, 4) if story_count else 0.0

    # Per-dimension counters
    counters: dict[str, dict[str, int]] = defaultdict(
        lambda: {"passes": 0, "fails": 0, "insufficient": 0, "na": 0}
    )
    for grade in grades:
        for code, result in grade.dimensions.items():
            c = counters[code]
            if result.verdict == Verdict.NOT_APPLICABLE:
                c["na"] += 1
            elif result.verdict == Verdict.PASS:
                c["passes"] += 1
            elif result.verdict == Verdict.FAIL:
                c["fails"] += 1
            else:  # INSUFFICIENT_EVIDENCE
                c["insufficient"] += 1

    dimension_fail_rates: dict[str, DimensionFailRate] = {}
    for code in sorted(counters):
        c = counters[code]
        graded = c["passes"] + c["fails"] + c["insufficient"]
        fail_rate = round((c["fails"] + c["insufficient"]) / graded, 4) if graded else 0.0
        dimension_fail_rates[code] = DimensionFailRate(
            code=code,
            graded=graded,
            passes=c["passes"],
            fails=c["fails"],
            insufficient_evidence=c["insufficient"],
            not_applicable=c["na"],
            fail_rate=fail_rate,
        )

    # Top failing dimensions — graded ≥ 1 and fail_rate > 0, sorted desc
    top_failing = sorted(
        (dr for dr in dimension_fail_rates.values() if dr.graded > 0 and dr.fail_rate > 0),
        key=lambda d: (-d.fail_rate, d.code),
    )
    top_failing_dimensions = [d.code for d in top_failing[:5]]

    # Pending judge dimensions: present in all grades as NOT_APPLICABLE and never graded
    pending_judge_dimensions = sum(
        1
        for dr in dimension_fail_rates.values()
        if dr.graded == 0 and dr.not_applicable > 0
    )

    # Spec workflow bypasses: issues where W1=FAIL (reached impl without Done Specifying)
    spec_workflow_bypasses = sorted(
        g.issue_key for g in grades
        if (w1 := g.dimensions.get("W1")) and w1.verdict == Verdict.FAIL
    )

    # Cycle time stats
    cycle_times = [g.cycle_time_days for g in grades if g.cycle_time_days is not None]
    ct_p50 = round(_percentile(cycle_times, 50), 2) if cycle_times else None
    ct_p90 = round(_percentile(cycle_times, 90), 2) if cycle_times else None
    ct_max = round(max(cycle_times), 2) if cycle_times else None
    ct_above = sum(
        1 for ct in cycle_times if ct > cycle_time_threshold_days
    )

    return SystemView(
        run_id=run_id,
        window=window,
        story_count=story_count,
        issue_count_all_types=story_count,
        six_yes_pass_rate=six_yes_pass_rate,
        dimension_fail_rates=dimension_fail_rates,
        top_failing_dimensions=top_failing_dimensions,
        classification_corrections=ClassificationCorrections(),
        cycle_time_p50=ct_p50,
        cycle_time_p90=ct_p90,
        cycle_time_max=ct_max,
        cycle_time_stories_above_threshold=ct_above,
        cycle_time_threshold_days=cycle_time_threshold_days,
        pending_judge_dimensions=pending_judge_dimensions,
        spec_workflow_bypasses=spec_workflow_bypasses,
    )


# ---------------------------------------------------------------------------
# Owner view
# ---------------------------------------------------------------------------


def _build_owner_view(grades: list[IssueGrade]) -> OwnerView:
    # upstream: keyed by upstream_owner
    up_stories: dict[str, int] = defaultdict(int)
    up_fails: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for g in grades:
        if g.upstream_owner:
            up_stories[g.upstream_owner] += 1
            for code, result in g.dimensions.items():
                if result.verdict == Verdict.FAIL:
                    up_fails[g.upstream_owner][code] += 1

    upstream = {
        owner: OwnerStats(
            stories=up_stories[owner],
            top_fails=_top_fail_codes(up_fails[owner]),
        )
        for owner in up_stories
    }

    # downstream: keyed by downstream_owner
    dn_stories: dict[str, int] = defaultdict(int)
    dn_fails: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for g in grades:
        if g.downstream_owner:
            dn_stories[g.downstream_owner] += 1
            for code, result in g.dimensions.items():
                if result.verdict == Verdict.FAIL:
                    dn_fails[g.downstream_owner][code] += 1

    downstream_by_owner = {
        owner: OwnerStats(
            stories=dn_stories[owner],
            top_fails=_top_fail_codes(dn_fails[owner]),
        )
        for owner in dn_stories
    }

    # approvers: keyed by spec_approver id
    ap_approved: dict[str, int] = defaultdict(int)
    ap_dn_passes: dict[str, int] = defaultdict(int)
    for g in grades:
        if g.spec_approver:
            ap_approved[g.spec_approver] += 1
            if g.downstream_overall == Verdict.PASS:
                ap_dn_passes[g.spec_approver] += 1

    approvers = {
        approver: ApproverStats(
            approved=ap_approved[approver],
            downstream_pass_rate_of_approved=round(
                ap_dn_passes[approver] / ap_approved[approver], 4
            ),
        )
        for approver in ap_approved
    }

    return OwnerView(
        upstream=upstream,
        downstream_by_owner=downstream_by_owner,
        downstream_by_engineer=downstream_by_owner,
        approvers=approvers,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_window(grades: list[IssueGrade]) -> RollupWindow:
    dates: list[date] = []
    for g in grades:
        for ts in (g.commitment_timestamp, g.done_timestamp):
            if ts is not None:
                dates.append(ts.date())
    if dates:
        return RollupWindow(from_date=min(dates), to_date=max(dates))
    today = datetime.now(timezone.utc).date()
    return RollupWindow(from_date=today, to_date=today)


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sv = sorted(values)
    idx = (p / 100) * (len(sv) - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= len(sv):
        return sv[lo]
    return sv[lo] + (idx - lo) * (sv[hi] - sv[lo])


def _top_fail_codes(fails: dict[str, int], n: int = 3) -> list[str]:
    return sorted(fails, key=lambda c: (-fails[c], c))[:n]
