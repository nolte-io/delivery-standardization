"""Markdown formatter — renders a RollupReport as rollup.md.

Voice: declarative, concrete, load-bearing. No "it depends", no hedging.
Three specific recommendations at the end, derived from the actual data.
"""
from __future__ import annotations

from nolte_grader.core.models import RollupReport

_DIM_LABELS: dict[str, str] = {
    "Y1": "Business objective nameable",
    "Y2": "Observable business difference describable",
    "Y3": "AC in plain language, pre-implementation",
    "Y4": "Non-builder validates",
    "Y5": "Live in production at Done",
    "Y6": "One cycle (retrospective)",
    "U7": "No scope evolution after commitment",
    "U8": "Validation outputs in contract",
    "U9": "Story defect classification",
    "U10": "Impact measurement infrastructure",
    "U11": "Issue-type classification",
    "U12": "Risks surfaced",
    "C1": "Commitment transition exists",
    "C2": "BDD quality at commitment",
    "C3": "Gate approver recorded",
    "D1": "Sub-tasks created after commit",
    "D2": "Design artifact present",
    "D3": "Violations surfaced",
    "D4": "Sub-tasks closed at Done Implementing",
    "D5": "Tests passing with evidence",
    "D6": "Operationally shippable",
    "D7": "WIP respected",
    "D8": "Cycle time within norm",
    "D9": "Story defect rate",
    "D10": "No backward transitions",
}

_DIM_ACTION: dict[str, str] = {
    "U12": "Add 'Risks: None identified' as the minimum floor; block Done Specifying if this section is missing.",
    "D10": "Enforce the Done Implementing checklist before moving stories to In Validation to eliminate re-work loops.",
    "Y3": "Gate In Implementation on AC presence; reject stories at the Ready transition if the section is absent.",
    "Y5": "Require the production release reference before the Done Implementing → In Validation move, not after.",
    "D8": "Scope and WIP violations are the usual cause; review D7 and U7 for the outlier stories.",
    "Y6": "Investigate the specific stories for scope expansion or dependency wait; do not raise the threshold without data.",
    "C3": "Ensure spec approvers set the field at the Done Specifying → In Implementation gate, not retroactively.",
    "D1": "Sub-tasks must be created during In Implementation. Move task decomposition after the commitment gate.",
    "D5": "Add a 'Tests — [story key]' sub-task at commitment; close it with a CI run link before Done Implementing.",
    "D6": "Populate the production release reference field at the same time as the Done Implementing transition.",
    "U7": "Post-commit AC edits signal scope evolution; escalate to the upstream owner before re-entering Implementation.",
    "U10": "Set the Impact Measurement Link at commitment, not post-launch.",
}


def format_rollup(report: RollupReport) -> str:
    """Render a RollupReport to a markdown string."""
    s = report.system
    lines: list[str] = []

    # Header
    from_str = s.window.from_date.strftime("%-d %b %Y")
    to_str = s.window.to_date.strftime("%-d %b %Y")
    lines.append(f"# Delivery Report · {from_str} – {to_str}")
    lines.append("")

    six_yes_n = round(s.six_yes_pass_rate * s.story_count)
    lines.append(
        f"{s.story_count} stories graded · six-yes gate: "
        f"**{s.six_yes_pass_rate:.0%} pass rate** ({six_yes_n}/{s.story_count})."
    )
    lines.append("")

    # Dimension failures
    lines.append("## Dimension Failures")
    lines.append("")

    failing = [
        dr for dr in s.dimension_fail_rates.values()
        if dr.graded > 0 and dr.fail_rate > 0
    ]
    failing.sort(key=lambda d: (-d.fail_rate, d.code))

    if failing:
        lines.append("| Code | Dimension | Fail rate | Failed / Graded |")
        lines.append("|------|-----------|-----------|-----------------|")
        for dr in failing:
            label = _DIM_LABELS.get(dr.code, dr.code)
            lines.append(
                f"| {dr.code} | {label} | {dr.fail_rate:.0%} | {dr.fails} / {dr.graded} |"
            )
        lines.append("")

        clean_count = sum(
            1 for dr in s.dimension_fail_rates.values()
            if dr.graded > 0 and dr.fail_rate == 0
        )
        if clean_count:
            lines.append(
                f"{clean_count} dimension{'s' if clean_count > 1 else ''} with zero failures "
                f"not shown."
            )
            lines.append("")
    else:
        lines.append("All graded dimensions passed.")
        lines.append("")

    if s.pending_judge_dimensions > 0:
        pending_codes = sorted(
            code
            for code, dr in s.dimension_fail_rates.items()
            if dr.graded == 0 and dr.not_applicable > 0
        )
        lines.append(
            f"{s.pending_judge_dimensions} dimension"
            f"{'s' if s.pending_judge_dimensions > 1 else ''} pending judge layer "
            f"({', '.join(pending_codes)}) — excluded from scoring in this run."
        )
        lines.append("")

    # Cycle time
    if s.cycle_time_p50 is not None:
        lines.append("## Cycle Time (In Implementation → Done)")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| p50 | {s.cycle_time_p50} days |")
        lines.append(f"| p90 | {s.cycle_time_p90} days |")
        lines.append(f"| max | {s.cycle_time_max} days |")
        lines.append("")
        if s.cycle_time_stories_above_threshold > 0:
            lines.append(
                f"{s.cycle_time_stories_above_threshold} of {s.story_count} stories "
                f"exceeded the {s.cycle_time_threshold_days}-day threshold."
            )
            lines.append("")

    # Owner breakdown
    o = report.owner
    has_upstream = bool(o.upstream)
    has_downstream = bool(o.downstream_by_owner)
    has_approvers = bool(o.approvers)

    if has_upstream or has_downstream or has_approvers:
        lines.append("## Owner Breakdown")
        lines.append("")

    if has_upstream:
        lines.append("### Upstream (spec authors)")
        lines.append("")
        lines.append("| Owner | Stories | Top failures |")
        lines.append("|-------|---------|--------------|")
        for owner, stats in sorted(o.upstream.items()):
            top = ", ".join(stats.top_fails) if stats.top_fails else "—"
            lines.append(f"| {owner} | {stats.stories} | {top} |")
        lines.append("")

    if has_downstream:
        lines.append("### Downstream (engineers)")
        lines.append("")
        lines.append("| Engineer | Stories | Top failures |")
        lines.append("|----------|---------|--------------|")
        for owner, stats in sorted(o.downstream_by_owner.items()):
            top = ", ".join(stats.top_fails) if stats.top_fails else "—"
            lines.append(f"| {owner} | {stats.stories} | {top} |")
        lines.append("")

    if has_approvers:
        lines.append("### Spec Approvers")
        lines.append("")
        lines.append("| Approver | Approved | Downstream pass rate |")
        lines.append("|----------|----------|----------------------|")
        for approver, stats in sorted(o.approvers.items()):
            lines.append(
                f"| {approver} | {stats.approved} | "
                f"{stats.downstream_pass_rate_of_approved:.0%} |"
            )
        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    recs = _build_recommendations(report)
    for i, rec in enumerate(recs, 1):
        lines.append(f"{i}. {rec}")
        lines.append("")

    return "\n".join(lines)


def _build_recommendations(report: RollupReport) -> list[str]:
    s = report.system
    recs: list[str] = []

    # Rec 1: top failing deterministic dimension
    det_failing = [
        dr for dr in s.dimension_fail_rates.values()
        if dr.graded > 0 and dr.fail_rate > 0
    ]
    det_failing.sort(key=lambda d: (-d.fail_rate, d.code))

    if det_failing:
        top = det_failing[0]
        label = _DIM_LABELS.get(top.code, top.code)
        action = _DIM_ACTION.get(top.code, f"Review the {top.code} failures before the next sprint.")
        recs.append(
            f"**Fix {top.code} — {label} ({top.fail_rate:.0%} fail rate, "
            f"{top.fails} of {top.graded} stories).** {action}"
        )

    # Rec 2: cycle time if above threshold
    if (
        s.cycle_time_p90 is not None
        and s.cycle_time_stories_above_threshold > 0
    ):
        recs.append(
            f"**Investigate cycle time: {s.cycle_time_stories_above_threshold} of "
            f"{s.story_count} stories exceeded the {s.cycle_time_threshold_days}-day threshold "
            f"(p90 {s.cycle_time_p90} days, max {s.cycle_time_max} days).** "
            f"Pull D8 and Y6 for those stories and identify the blocker pattern — scope "
            f"expansion, WIP overload, or dependency wait — before the next sprint."
        )
    elif len(recs) < 2:
        # Fallback rec 2 when cycle time is clean
        if len(det_failing) > 1:
            second = det_failing[1]
            label = _DIM_LABELS.get(second.code, second.code)
            action = _DIM_ACTION.get(second.code, f"Review {second.code} failures.")
            recs.append(
                f"**Address {second.code} — {label} ({second.fail_rate:.0%} fail rate).** "
                f"{action}"
            )

    # Rec 3: judge layer pending
    if s.pending_judge_dimensions > 0:
        pending_codes = sorted(
            code
            for code, dr in s.dimension_fail_rates.items()
            if dr.graded == 0 and dr.not_applicable > 0
        )
        recs.append(
            f"**Wire the judge adapter to unlock {s.pending_judge_dimensions} pending "
            f"dimensions ({', '.join(pending_codes)}).** These cover business-objective "
            f"quality, BDD correctness, design artifact presence, and issue classification "
            f"— the dimensions most likely to surface spec-quality failures that deterministic "
            f"checks miss."
        )

    return recs[:3]
