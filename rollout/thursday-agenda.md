# Thursday Meeting — Agenda

**Date:** Thursday, 23 April 2026
**Duration:** 60 minutes
**Attendees:** Jeffrey, Yanna, Hector
**Pre-read:** Email sent Tuesday with rollup and repo link. Both attendees read it before the meeting.

---

## Purpose

This is not a walkthrough of what was built. The email covered that.

This is a triage meeting. The grader produced a 30-day rollup. Yanna and Hector have had 48 hours to read the dimension pages and pre-filled GitHub issues. We walk the issues, decide on each, and leave with a dated plan.

## Ground rules

- No walkthroughs.
- No debate on whether to do this.
- No softening of standards.
- Decisions happen in the meeting or are explicitly deferred with a date.
- Every decision is captured on the relevant GitHub issue during or immediately after the meeting.

## Agenda

### 0:00 – 0:05 · Frame

Jeffrey names the shift: the grader replaces Jeffrey spotting problems. Yanna and Hector own dimension-level triage going forward. Jeffrey approves changes to standards.

### 0:05 – 0:20 · Infrastructure decisions (Yanna leads)

Six dimensions failed at 100% because the supporting Jira infrastructure does not exist yet:

- **Y2** — needs `## Observable Impact` section in Story template
- **Y3** — needs `## Acceptance Criteria` header convention enforced
- **Y5 / D6** — needs `Production Release Reference` custom field
- **U10** — needs `Impact Measurement Link` custom field
- **U12** — needs `## Risks` section in Story template
- **C3** — needs `Spec Approver` custom field + workflow validator

**Decision needed:** Yanna commits to a date for template + field deployment. Hector commits to a date for workflow validators. Jeffrey confirms no blockers.

Expected output: two dates on the calendar, Jira admin tasked, template announced to team.

### 0:20 – 0:35 · Discipline decisions (Hector leads)

Three dimensions failed at meaningful rates because of discipline, not infrastructure:

- **D1 at 98%** — sub-tasks created before commitment. Planning artifacts.
- **D10 at 32%** — backward status transitions. Silent rework.
- **D9 at 0%, with only 2 Story Defects logged** — defect underreporting likely; cross-reference with D10.

**Decision needed:** Hector names the specific engineering discipline changes and dates. D10 is the most impactful — Jira workflow can simply prevent backward transitions. If D10 is fixed at the workflow level, D9 becomes observable.

Expected output: workflow change dated, team-level coaching dated, D9 reporting convention documented.

### 0:35 – 0:45 · Cycle time outliers (joint)

Y6 and D8 at 14% fail rate. 8 Stories exceeded the 7-day one-cycle rule. Max cycle time: 32.5 days.

**Decision needed:** Yanna and Hector pull the 8 Stories and name the pattern — scope expansion, dependency wait, or WIP overload. Not today; by next Friday. Each gets an issue opened with the root cause.

Expected output: list of 8 Stories in a GitHub issue, owner assigned to categorize, due date.

### 0:45 – 0:55 · Operating rhythm going forward

Jeffrey walks the monthly rhythm doc ([`how-we-manage-delivery-quality.md`](how-we-manage-delivery-quality.md)):

- Grader runs monthly (or on-demand).
- Week 1: triage in issues.
- Week 2: infrastructure fixes.
- Week 3: discipline work.
- Week 4: re-run, compare numbers.

**Decision needed:** Agreement on the rhythm. Disagreements raised here, resolved here.

### 0:55 – 1:00 · Close

- Every decision written on the correct GitHub issue before leaving the meeting.
- Jeffrey's next standards-level approval items flagged.
- Next rollup date set.

## What this meeting does not do

- It does not debate whether the standards are right. If a standard is wrong, that's a PR, not a meeting topic.
- It does not evaluate specific engineers. The rollup's per-engineer breakdown is a tool for Hector, not for group conversation.
- It does not set OKRs or goals. It sets next-30-day operational work.

## Post-meeting artifacts

Within 24 hours of the meeting:

1. All decisions captured on their respective GitHub issues (labels applied, assignees set, due dates added).
2. Jira admin work scheduled for the week.
3. Template + workflow change announcement posted to the engineering channel.
4. Next rollup run date on Jeffrey's calendar.

If those four things don't happen within 24 hours, the meeting failed its purpose.
