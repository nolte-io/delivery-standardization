# Grader Triage — GitHub Issues

25 issues, one per graded dimension. This file contains the bodies plus the `gh` CLI commands to create them in bulk.

## Prereqs

```bash
# Install GitHub CLI if needed
brew install gh

# Authenticate once
gh auth login

# cd into the repo
cd /path/to/delivery-standardization
```

## One-time label setup

```bash
gh label create "dim:Y1" --color "c2e0c6"
gh label create "dim:Y2" --color "c2e0c6"
gh label create "dim:Y3" --color "c2e0c6"
gh label create "dim:Y4" --color "c2e0c6"
gh label create "dim:Y5" --color "c2e0c6"
gh label create "dim:Y6" --color "c2e0c6"
gh label create "dim:U7" --color "bfd4f2"
gh label create "dim:U8" --color "bfd4f2"
gh label create "dim:U9" --color "bfd4f2"
gh label create "dim:U10" --color "bfd4f2"
gh label create "dim:U11" --color "bfd4f2"
gh label create "dim:U12" --color "bfd4f2"
gh label create "dim:C1" --color "fef2c0"
gh label create "dim:C2" --color "fef2c0"
gh label create "dim:C3" --color "fef2c0"
gh label create "dim:D1" --color "f9d0c4"
gh label create "dim:D2" --color "f9d0c4"
gh label create "dim:D3" --color "f9d0c4"
gh label create "dim:D4" --color "f9d0c4"
gh label create "dim:D5" --color "f9d0c4"
gh label create "dim:D6" --color "f9d0c4"
gh label create "dim:D7" --color "f9d0c4"
gh label create "dim:D8" --color "f9d0c4"
gh label create "dim:D9" --color "f9d0c4"
gh label create "dim:D10" --color "f9d0c4"

gh label create "lane:upstream" --color "0366d6"
gh label create "lane:downstream" --color "5319e7"
gh label create "lane:system" --color "6f42c1"

gh label create "type:infrastructure" --color "b60205"
gh label create "type:discipline" --color "d93f0b"
gh label create "type:judge-pending" --color "cccccc"

gh label create "status:triage" --color "fbca04"
gh label create "status:in-progress" --color "0e8a16"
gh label create "status:decided" --color "ededed"

gh label create "blocking-next-rollup" --color "b60205"
```

## Create all 25 issues

Paste and run each block. Or concatenate and pipe to bash if you prefer one-shot creation. Replace `@yannalopes` and `@hectorsanchez` with the actual GitHub usernames before running.

---

### Y1 — Business objective nameable (judge pending)

```bash
gh issue create \
  --title "Y1 — Business objective nameable" \
  --label "dim:Y1,lane:upstream,type:judge-pending,status:triage" \
  --assignee "yannalopes" \
  --body 'See [standards/dimensions/Y1.md](../standards/dimensions/Y1.md).

## Observed impact (20 Mar – 19 Apr 2026)

Judge layer not yet shipped. No scores in this run.

## Owner
Yanna (upstream)

## Classification
Judge-pending

## Proposed response
Defer until Phase 1 judge adapter ships (commits 7–8). Once online, first run will establish baseline.

## Decision needed at Thursday triage
Confirm owner, confirm deferred status until judge ships.'
```

### Y2 — Observable business difference describable (judge pending)

```bash
gh issue create \
  --title "Y2 — Observable business difference describable" \
  --label "dim:Y2,lane:upstream,type:infrastructure,status:triage,blocking-next-rollup" \
  --assignee "yannalopes" \
  --body 'See [standards/dimensions/Y2.md](../standards/dimensions/Y2.md).

## Observed impact

Judge dimension. The deterministic precursor (## Observable Impact section present) fails on 100% of current Stories — the section is not yet in the Story template.

## Owner
Yanna (upstream)

## Classification
Infrastructure (template missing)

## Proposed response
- Add `## Observable Impact` to the Story template this week
- Document the metric / threshold / observation-point convention in the rollout doc
- Team announcement with before/after example

## Decision needed at Thursday triage
Template update deadline. Convention documented.'
```

### Y3 — AC in plain language, pre-implementation

```bash
gh issue create \
  --title "Y3 — AC in plain language, pre-implementation" \
  --label "dim:Y3,lane:upstream,type:discipline,status:triage,blocking-next-rollup" \
  --assignee "yannalopes" \
  --body 'See [standards/dimensions/Y3.md](../standards/dimensions/Y3.md).

## Observed impact

Fail rate: 100% (57 / 58 graded Stories).

Near-universal failure. Root cause needs investigation — could be any of:
- Template does not use `## Acceptance Criteria` header
- AC is being added post-commitment (scope evolution)
- Header format differs from what the grader parses

## Owner
Yanna (upstream)

## Classification
Likely infrastructure (header convention), possibly discipline (post-commit edits)

## Proposed response
Pull 3 recent Stories. Inspect manually for header format and timing of AC population. Determine whether the fix is template enforcement or discipline intervention.

## Decision needed at Thursday triage
Owner pulls 3 Stories and reports back with root cause by EOW Friday.'
```

### Y4 — Non-builder validates

```bash
gh issue create \
  --title "Y4 — Non-builder validates" \
  --label "dim:Y4,lane:upstream,type:discipline,status:triage" \
  --assignee "yannalopes" \
  --body 'See [standards/dimensions/Y4.md](../standards/dimensions/Y4.md).

## Observed impact

Fail rate: 2% (1 / 59). One Story had the builder also performing validation.

## Owner
Yanna (upstream)

## Classification
Discipline — specific case, not systemic

## Proposed response
Identify the failing Story. Determine whether this was an exception (team-size constraint, urgent production fix) or a discipline gap.

## Decision needed at Thursday triage
Confirm whether this is a one-off or a pattern that needs discipline reinforcement.'
```

### Y5 — Live in production at Done

```bash
gh issue create \
  --title "Y5 — Live in production at Done" \
  --label "dim:Y5,lane:upstream,type:infrastructure,status:triage,blocking-next-rollup" \
  --assignee "yannalopes" \
  --body 'See [standards/dimensions/Y5.md](../standards/dimensions/Y5.md).

## Observed impact

Fail rate: 100% (59 / 59). `Production Release Reference` custom field does not exist.

## Owner
Yanna (upstream) for field creation; Hector (downstream) for convention enforcement — this is the same field as D6.

## Classification
Infrastructure (field missing)

## Proposed response
Create `Production Release Reference` custom field. One field resolves both Y5 and D6. See [rollout/jira-fields-checklist.md](../rollout/jira-fields-checklist.md).

## Decision needed at Thursday triage
Jira admin task scheduled, field live date.'
```

### Y6 — Completable in one cycle

```bash
gh issue create \
  --title "Y6 — Completable in one cycle (retrospective)" \
  --label "dim:Y6,lane:upstream,type:discipline,status:triage" \
  --assignee "yannalopes" \
  --body 'See [standards/dimensions/Y6.md](../standards/dimensions/Y6.md).

## Observed impact

Fail rate: 14% (8 / 58).
p50: 1.41 days · p90: 9.07 days · max: 32.49 days.

## Owner
Yanna (upstream) + Hector (downstream) — overlaps with D8.

## Classification
Discipline — scope, WIP, or dependency driven.

## Proposed response
Pull the 8 over-threshold Stories. Cross-reference with D8. Classify each: scope expansion, dependency wait, WIP overload, or specification gap. Consolidate into one report.

## Decision needed at Thursday triage
Consolidated investigation with D8. Due by EOW Friday.'
```

### U7 — No scope evolution after commitment

```bash
gh issue create \
  --title "U7 — No scope evolution after commitment" \
  --label "dim:U7,lane:upstream,status:triage" \
  --assignee "yannalopes" \
  --body 'See [standards/dimensions/U7.md](../standards/dimensions/U7.md).

## Observed impact

Fail rate: 0%.

Currently clean, but this dimension only activates once Y3 (AC present pre-commit) is passing. Y3 is at 100% fail, so U7 has little to diff against.

## Owner
Yanna

## Classification
Deferred dependency

## Proposed response
Defer triage until Y3 infrastructure lands. Re-evaluate after next rollup.

## Decision needed at Thursday triage
Confirm deferral.'
```

### U8 — Validation outputs

```bash
gh issue create \
  --title "U8 — Validation outputs are Acceptance or Story Defect only" \
  --label "dim:U8,lane:upstream,status:triage" \
  --assignee "yannalopes" \
  --body 'See [standards/dimensions/U8.md](../standards/dimensions/U8.md).

## Observed impact

Fail rate: 0%.

Clean. But worth cross-referencing against D9 (Story defect rate at 0% with only 2 defects logged) — if defects are not being logged, U8 is silently clean because discovery during validation is not being recorded.

## Owner
Yanna

## Classification
Verification

## Proposed response
Cross-reference with D9 investigation. Validate that Story Defect logging is actually happening.

## Decision needed at Thursday triage
Part of D9 triage conversation.'
```

### U9 — Story defects classified (judge pending)

```bash
gh issue create \
  --title "U9 — Story defects classified" \
  --label "dim:U9,lane:upstream,type:judge-pending,status:triage" \
  --assignee "yannalopes" \
  --body 'See [standards/dimensions/U9.md](../standards/dimensions/U9.md).

## Observed impact

Judge-pending. Only 2 Story Defects in 30 days — likely underreporting.

## Owner
Yanna

## Classification
Judge-pending + discipline

## Proposed response
Defer judge evaluation until adapter ships. In parallel, address underreporting via D9 discipline.

## Decision needed at Thursday triage
Owner confirmed. Deferred judge portion.'
```

### U10 — Impact measurement infrastructure

```bash
gh issue create \
  --title "U10 — Impact measurement infrastructure at Done" \
  --label "dim:U10,lane:upstream,type:infrastructure,status:triage,blocking-next-rollup" \
  --assignee "yannalopes" \
  --body 'See [standards/dimensions/U10.md](../standards/dimensions/U10.md).

## Observed impact

Fail rate: 100% (59 / 59). `Impact Measurement Link` custom field does not exist.

## Owner
Yanna

## Classification
Infrastructure

## Proposed response
Create `Impact Measurement Link` custom field. Part of the same Jira admin session as Y5 and C3.

## Decision needed at Thursday triage
Field live date.'
```

### U11 — Issue-type classification (judge pending)

```bash
gh issue create \
  --title "U11 — Issue-type classification" \
  --label "dim:U11,lane:system,type:judge-pending,status:triage" \
  --body 'See [standards/dimensions/U11.md](../standards/dimensions/U11.md).

## Observed impact

Judge-pending. Historical context: Tasks outnumber Stories 2.3:1 in the data. Playbook says Tasks should be rare.

## Owner
Yanna + Hector (joint)

## Classification
Judge-pending + infrastructure (classification audit)

## Proposed response
Classification audit on the open backlog: walk every open Task and determine whether it is operational (correctly Task) or value-delivery work (should be Story). Document reclassification counts.

## Decision needed at Thursday triage
Audit owner and due date.'
```

### U12 — Risks surfaced

```bash
gh issue create \
  --title "U12 — Risks surfaced" \
  --label "dim:U12,lane:upstream,type:infrastructure,status:triage,blocking-next-rollup" \
  --assignee "yannalopes" \
  --body 'See [standards/dimensions/U12.md](../standards/dimensions/U12.md).

## Observed impact

Fail rate: 100% (59 / 59). `## Risks` section not in Story template.

## Owner
Yanna

## Classification
Infrastructure (template missing)

## Proposed response
Add `## Risks` to the Story template. Document "None identified" as acceptable explicit value.

## Decision needed at Thursday triage
Template update deadline.'
```

### C1 — Commitment transition exists

```bash
gh issue create \
  --title "C1 — Commitment transition exists" \
  --label "dim:C1,lane:system,status:triage" \
  --body 'See [standards/dimensions/C1.md](../standards/dimensions/C1.md).

## Observed impact

Fail rate: 2% (1 / 59). One Story bypassed the workflow.

## Owner
System (Hector investigates)

## Classification
Discipline — one-off

## Proposed response
Identify the failing Story. Confirm workflow integrity, no systemic issue.

## Decision needed at Thursday triage
Hector pulls the one Story and reports.'
```

### C2 — BDD quality at commitment (judge pending)

```bash
gh issue create \
  --title "C2 — BDD quality at commitment" \
  --label "dim:C2,lane:upstream,type:judge-pending,status:triage" \
  --assignee "yannalopes" \
  --body 'See [standards/dimensions/C2.md](../standards/dimensions/C2.md).

## Observed impact

Judge-pending. Prerequisite: Y3 template adoption.

## Owner
Yanna

## Classification
Judge-pending

## Proposed response
Defer until judge ships and Y3 is resolved.

## Decision needed at Thursday triage
Confirm deferral.'
```

### C3 — Gate approver recorded

```bash
gh issue create \
  --title "C3 — Gate approver recorded" \
  --label "dim:C3,lane:system,type:infrastructure,status:triage,blocking-next-rollup" \
  --body 'See [standards/dimensions/C3.md](../standards/dimensions/C3.md).

## Observed impact

Fail rate: 100% (59 / 59). `Spec Approver` field does not exist.

## Owner
Yanna (field creation) + Hector (workflow validator)

## Classification
Infrastructure

## Proposed response
- Create `Spec Approver` user-picker field
- Add workflow validator: Done Specifying → In Implementation requires field populated
- Define authorized approver list per project in grader config

## Decision needed at Thursday triage
Field creation date. Workflow validator date.'
```

### D1 — Sub-tasks created after commit

```bash
gh issue create \
  --title "D1 — Sub-tasks created after commit" \
  --label "dim:D1,lane:downstream,type:discipline,status:triage,blocking-next-rollup" \
  --assignee "hectorsanchez" \
  --body 'See [standards/dimensions/D1.md](../standards/dimensions/D1.md).

## Observed impact

Fail rate: 98% (57 / 58). Sub-tasks being created before commitment on nearly every Story.

## Owner
Hector

## Classification
Discipline — or automation/tooling creating sub-tasks prematurely

## Proposed response
Determine: is this engineer behavior, a Jira automation, or a template? Fix the root cause. Sub-tasks are execution artifacts, not planning artifacts.

## Decision needed at Thursday triage
Root cause identification + fix date.'
```

### D2 — Design artifact (judge pending)

```bash
gh issue create \
  --title "D2 — Design artifact for non-trivial work" \
  --label "dim:D2,lane:downstream,type:judge-pending,status:triage" \
  --assignee "hectorsanchez" \
  --body 'See [standards/dimensions/D2.md](../standards/dimensions/D2.md).

## Observed impact

Judge-pending. `Design Artifact Link` field does not exist.

## Owner
Hector

## Classification
Judge-pending + infrastructure

## Proposed response
Create `Design Artifact Link` field. Defer discipline conversation until judge ships.

## Decision needed at Thursday triage
Field creation date.'
```

### D3 — Violations surfaced (judge pending)

```bash
gh issue create \
  --title "D3 — Violations surfaced, not absorbed" \
  --label "dim:D3,lane:downstream,type:judge-pending,status:triage" \
  --assignee "hectorsanchez" \
  --body 'See [standards/dimensions/D3.md](../standards/dimensions/D3.md).

## Observed impact

Judge-pending. Noisiest dimension by design. Candidate for Opus upgrade during calibration.

## Owner
Hector

## Classification
Judge-pending

## Proposed response
Defer until judge ships. Plan for careful calibration on first real run.

## Decision needed at Thursday triage
Confirm deferral.'
```

### D4 — Sub-tasks closed at Done Implementing

```bash
gh issue create \
  --title "D4 — All sub-tasks closed at Done Implementing" \
  --label "dim:D4,lane:downstream,type:discipline,status:triage" \
  --assignee "hectorsanchez" \
  --body 'See [standards/dimensions/D4.md](../standards/dimensions/D4.md).

## Observed impact

Fail rate: 7% (2 / 29). Two Stories moved to Done Implementing with open sub-tasks.

## Owner
Hector

## Classification
Discipline — specific cases

## Proposed response
Review the 2 failing Stories. Close or delete orphaned sub-tasks. Establish transition rule.

## Decision needed at Thursday triage
Resolution date.'
```

### D5 — Tests passing with evidence

```bash
gh issue create \
  --title "D5 — Tests passing with evidence" \
  --label "dim:D5,lane:downstream,type:infrastructure,status:triage,blocking-next-rollup" \
  --assignee "hectorsanchez" \
  --body 'See [standards/dimensions/D5.md](../standards/dimensions/D5.md).

## Observed impact

Fail rate: 100% (29 / 29). Test sub-task convention does not exist.

## Owner
Hector

## Classification
Infrastructure (convention) + discipline (enforcement)

## Proposed response
- Document the `Tests — [Story key]` convention with CI link requirement
- Establish transition rule: sub-task closed before Done Implementing
- Phase 2: CI webhook writes status to a dedicated field

## Decision needed at Thursday triage
Convention documented, effective date, enforcement mechanism.'
```

### D6 — Operationally shippable

```bash
gh issue create \
  --title "D6 — Operationally shippable" \
  --label "dim:D6,lane:downstream,type:infrastructure,status:triage,blocking-next-rollup" \
  --assignee "hectorsanchez" \
  --body 'See [standards/dimensions/D6.md](../standards/dimensions/D6.md).

## Observed impact

Fail rate: 100% (29 / 29). Same field gap as Y5.

## Owner
Hector (convention) + Yanna (field creation)

## Classification
Infrastructure

## Proposed response
Resolves via the same field as Y5. One Jira admin action, two dimensions clear.

## Decision needed at Thursday triage
Merge with Y5 issue or confirm field live date.'
```

### D7 — WIP respected

```bash
gh issue create \
  --title "D7 — WIP respected" \
  --label "dim:D7,lane:system,status:triage" \
  --assignee "hectorsanchez" \
  --body 'See [standards/dimensions/D7.md](../standards/dimensions/D7.md).

## Observed impact

Fail rate: 0%. Either discipline is strong or limits are too permissive for current throughput.

## Owner
Hector

## Classification
Verification

## Proposed response
Defer. Re-evaluate once target throughput (100/month) is reached.

## Decision needed at Thursday triage
Confirm deferral.'
```

### D8 — Cycle time within norm

```bash
gh issue create \
  --title "D8 — Cycle time within norm" \
  --label "dim:D8,lane:system,type:discipline,status:triage" \
  --assignee "hectorsanchez" \
  --body 'See [standards/dimensions/D8.md](../standards/dimensions/D8.md).

## Observed impact

Fail rate: 14% (8 / 58). Same 8 Stories as Y6.

## Owner
Hector (downstream execution lens)

## Classification
Discipline — execution, WIP, or dependency

## Proposed response
Consolidate with Y6 investigation. One report, two dimensions.

## Decision needed at Thursday triage
Joint investigation with Yanna. Due by EOW Friday.'
```

### D9 — Story defect rate

```bash
gh issue create \
  --title "D9 — Story defect rate" \
  --label "dim:D9,lane:downstream,type:discipline,status:triage" \
  --assignee "hectorsanchez" \
  --body 'See [standards/dimensions/D9.md](../standards/dimensions/D9.md).

## Observed impact

Fail rate: 0%. Only 2 Story Defects logged in 30 days across 59 Stories. Likely underreporting.

Cross-reference with D10: 19 Stories had backward transitions (silent rework) but only 2 defects logged. The gap is the measure.

## Owner
Hector

## Classification
Discipline — defect logging hygiene

## Proposed response
- Enforce rule: backward transition is not allowed; raise a Story Defect instead
- Audit recent rework to catch unlogged defects
- Track defect logging as an explicit engineering habit

## Decision needed at Thursday triage
Rule effective date. Related to D10 workflow change.'
```

### D10 — No backward transitions

```bash
gh issue create \
  --title "D10 — No backward transitions" \
  --label "dim:D10,lane:system,type:discipline,status:triage,blocking-next-rollup" \
  --body 'See [standards/dimensions/D10.md](../standards/dimensions/D10.md).

## Observed impact

Fail rate: 32% (19 / 59). Nearly a third of Stories moved backward silently.

## Owner
Hector + Yanna (joint)

## Classification
Infrastructure (workflow change) + discipline

## Proposed response
Configure Jira workflow to prevent backward transitions. Any regression must be raised as a Story Defect.

This is the single most impactful workflow change available. It resolves D10 directly and makes D9 (defect reporting) observable.

## Decision needed at Thursday triage
Workflow change date.'
```

---

## Recommended Thursday output

After the meeting, every issue above should have:

1. Status label updated (`status:in-progress` or `status:decided`).
2. Assignee confirmed.
3. Due date in the milestone or as a comment.
4. Related PRs linked when applicable.

If an issue leaves Thursday in `status:triage` without a decision, it goes back to the next week's review.
