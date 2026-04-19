# Delivery Grader — Team Prep

**Owner of this document:** Jeffrey
**Owners of execution:** Yanna (upstream), Hector (downstream)
**Target: grader operational within 2 weeks.** First real run scores the 30 days following that date.

---

## Why this exists

We are building a grader that objectively scores every Story against Nolte's published 6-yes and our delivery system rules. It grades two sides:

- **Upstream** (Yanna): business objective, AC quality, spec readiness, classification integrity, risks surfaced, impact signal, scope evolution.
- **Downstream** (Hector): sub-task hygiene, design artifacts, test evidence, shippable state, WIP discipline, cycle time, defect rate.

The grader is not a performance review. It is a system-health instrument. It will expose where the delivery system leaks. That is the point.

**First run will score badly. Do not flinch.** The baseline is the baseline. Improvement month-over-month is the metric.

---

## What has to be true before the grader runs

### 1. Jira template updates (owner: Yanna)

Add the following sections to the Story template. Template: see `rollout/jira-template.md`. Non-negotiable after the template lands.

```
## Business Objective
## Observable Impact
## Acceptance Criteria
## Scenarios
## Risks
```

**Deadline:** Template updated within 3 days. Announced to the team. Every new Story from that date forward uses it.

### 2. New Jira custom fields (owner: Yanna, with Jira admin)

Four fields. One field, one purpose. See `rollout/jira-fields-checklist.md` for configuration details.

| Field name | Type | Used by |
|---|---|---|
| Design Artifact Link | URL (multi-value) | Hector / downstream |
| Production Release Reference | URL or text | Yanna / upstream Y5 and D6 |
| Impact Measurement Link | URL | Yanna / upstream U10 |
| Spec Approver | User picker | System / C3 — required at Done Specifying → Ready transition |

**Deadline:** Fields created within 5 days. Added to the Story screen. Required on every Story from creation date forward.

### 3. Workflow enforcement (owner: Hector + Yanna)

- **No backward status transitions.** Jira workflow should prevent them. If a Story needs to go back, it becomes a Story Defect, not a status revert.
- **Commitment point = Ready → In Implementation.** Lock this as the timestamp the grader uses. Any AC edits after this timestamp are scope evolution and will fail U7.
- **Spec Approver required at Done Specifying → Ready.** Workflow enforces the field is populated before the transition can complete. Authorized approvers: Head of Engineering (Hector) or delegates; Nolte POC when Nolte is the trusted Product Owner; client POC when ownership sits with the client.

**Deadline:** Workflow updated within 5 days.

### 4. Classification audit (owner: Yanna + Hector, joint)

Current data shows Tasks heavily outnumbering Stories. The playbook says Tasks should be rare. Before the grader runs, walk through every open Task in the backlog and current work and answer:

- Is this operational/one-off work (correctly a Task)?
- Or is this value-delivery work that should be a Story?

Reclassify ruthlessly. If the delivery system has been absorbing Stories as Tasks, the forecast has been running on bad sizing.

**Deadline:** Audit complete within 7 days. Document the reclassification counts — this becomes the baseline for U11.

### 5. Story Defect discipline (owner: Yanna)

Going forward:
- Any issue found during In Validation that was not in the original AC = Story Defect.
- Classify by type: functional, design, UX, regulatory, performance.
- Do not bounce the Story back to In Implementation without a Story Defect record.

**Deadline:** Effective immediately on existing In Validation work.

### 6. Test evidence convention (owner: Hector)

Every Story requires a test sub-task with a CI run link before transitioning to Done Implementing.

- Sub-task title: `Tests — [Story key]`
- Description includes link to the CI run / test report
- Sub-task closed only when tests pass

**Deadline:** Convention documented within 5 days. Enforced within 10 days.

---

## WIP limits — Phase 1

Starting limits. Will evolve as throughput grows. Configured in the grader; not manually enforced by shame.

| Stage | WIP limit |
|---|---|
| In Specification | 8 |
| Ready | 5 |
| In Implementation | 3 per engineer, 15 system-wide |
| Done Implementing | 5 |
| In Validation | 6 |

Exceptions require Head of Product approval and are logged. Chronic violations trigger a system review.

---

## What the grader will NOT do on day one

- Determine whether business impact actually occurred (monthly review, not per-Story grade).
- Grade Stories created before the template/field changes land (baseline is forward-only).
- Replace judgment at gates. Gate decisions remain with Yanna and Hector. The grader provides evidence.

---

## Sequence check

1. Template updated → Week 1
2. Custom fields created (four) → Week 1
3. Workflow hardened (no backward transitions, Spec Approver required) → Week 1
4. Classification audit → Week 2
5. Story Defect discipline active → Week 2
6. Test evidence convention → Week 2
7. Grader deployed (Claude Code build) → Week 3
8. First real scoring run → End of Week 6 (30 days after grader deployment)

Any slippage in weeks 1–2 pushes the first run back. Do not skip steps to hit the date.

---

## What success looks like 90 days in

- Task:Story ratio inverts (Stories > Tasks)
- Story cycle time median trends toward 7 days
- Story Defect count per Story is tracked and trending with visibility
- Impact signals captured on ≥80% of Stories at commit
- Grader rollup month-over-month shows fewer red dimensions

If three months in the numbers haven't moved, the problem isn't the grader. It's that the system rules aren't being enforced. That's a leadership call, not an instrumentation call.
