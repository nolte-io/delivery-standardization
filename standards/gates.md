# Gates — Catalog

Every gate the delivery system enforces. A **gate** is a check that fires at a specific point in a ticket's lifecycle and either passes, blocks with a remediation, or records a flag for the grader rollup.

This doc is the authoritative target for every implementation:
- Jira-side: workflow validators + Automation rules satisfy these gates (see [`../rollout/jira-workflow-rules.md`](../rollout/jira-workflow-rules.md)).
- Markdown-side: Claude Code pre-write hooks + CI satisfy these gates (see `product-management/.claude/`).

Both implementations must emit the same [evidence codes](evidence-codes.md) for the same situations. All status values referenced here are `SCREAMING_SNAKE_CASE` per [`workflow.md`](workflow.md).

---

## Gate types

- **D — Deterministic.** Field/section presence, git log check, enum membership, reference resolvability. Runs fast. Safe to block at transition time.
- **J — Judge.** Claude reads text against a prompt from [`../prompts/`](../prompts/). Semantic. Slower and API-cost-incurring. Can block at transition OR run retrospectively.
- **S — System-wide.** Requires scanning all tickets in the instance (e.g. WIP counts). Not per-ticket.
- **R — Retrospective only.** Cannot fire at transition time (depends on post-transition data). Grader-only.

---

## Gate catalog

### Commitment gates — fire on `DONE_SPECIFYING → READY`

| Code | Name | Type | Check | Evidence codes |
|---|---|---|---|---|
| **C1** | Commitment transition exists | D | The transition is reaching `READY` from `DONE_SPECIFYING` (not a skip or backfill). | `COMMITMENT_TRANSITION_FOUND`, `COMMITMENT_TRANSITION_MISSING` |
| **C3** | Gate approver recorded | D | `spec_approver` is populated, is in `authorized_approvers` for the project, and is not the `assignee`. | `APPROVER_RECORDED_AND_AUTHORIZED`, `APPROVER_FIELD_EMPTY`, `APPROVER_NOT_AUTHORIZED`, `APPROVER_IS_BUILDER` |
| **C2** | BDD quality at commitment | J | Scenarios are Given/When/Then, cover the core rule (not just edge cases), not placeholder. Prompt: [`../prompts/C2.md`](../prompts/C2.md). | `SCENARIOS_COVER_CORE_RULE`, `SCENARIOS_COVER_ONLY_EDGE_CASES`, `SCENARIOS_PLACEHOLDER_OR_EMPTY`, `SCENARIOS_NOT_GIVEN_WHEN_THEN` |
| **Y1** | Business Objective nameable | D+J | Section populated; judge evaluates whether stated in business terms. Prompt: [`../prompts/Y1.md`](../prompts/Y1.md). | See [`evidence-codes.md#Y1`](evidence-codes.md). |
| **Y2** | Observable Impact describable | D+J | Section has metric + threshold + observation point. Prompt: [`../prompts/Y2.md`](../prompts/Y2.md). | See [`evidence-codes.md#Y2`](evidence-codes.md). |
| **Y3** | AC in plain language, pre-commit | D+J | Section populated, written before `READY` (git timestamp), plain language. Prompt: [`../prompts/Y3b.md`](../prompts/Y3b.md). | See [`evidence-codes.md#Y3`](evidence-codes.md). |
| **U12** | Risks surfaced | D | `Risks` section present and non-empty. `"None identified"` passes; blank/placeholder fails. | `RISKS_POPULATED`, `RISKS_EMPTY_OR_MISSING`, `RISKS_PLACEHOLDER` |

### Commitment-adjacent — fire on `READY → IN_IMPLEMENTATION`

| Code | Name | Type | Check | Evidence codes |
|---|---|---|---|---|
| **W1** | Spec workflow not bypassed | D | Prior status history for this ticket contains `DONE_SPECIFYING` and `READY` in order. Blocks direct jumps from any earlier state. | `WORKFLOW_COMPLETED`, `WORKFLOW_BYPASSED` |
| **D2** | Design artifact for non-trivial work | D+J | If ticket is non-trivial (judge), `design_artifact_link` is populated. Prompt: [`../prompts/D2.md`](../prompts/D2.md). | `DESIGN_NOT_REQUIRED_WORK_TRIVIAL`, `DESIGN_PRESENT_AS_REQUIRED`, `DESIGN_MISSING_FOR_COMPLEX_WORK` |
| **D7** | WIP respected | S | Count of tickets in `IN_IMPLEMENTATION` (per-assignee and system-wide) after this transition ≤ configured limits, OR `wip_exception` populated. | `WIP_WITHIN_LIMITS`, `WIP_EXCEEDED_PER_ENGINEER`, `WIP_EXCEEDED_SYSTEM` |

### Build-complete gates — fire on `IN_IMPLEMENTATION → DONE_IMPLEMENTING`

| Code | Name | Type | Check | Evidence codes |
|---|---|---|---|---|
| **D1** | Sub-tasks created after commit | D | All linked sub-task tickets have `created_at` ≥ the `READY → IN_IMPLEMENTATION` timestamp for this ticket. | `SUBTASKS_CREATED_POST_COMMIT`, `SUBTASKS_CREATED_PRE_COMMIT`, `SUBTASKS_ABSENT_ON_NON_TRIVIAL` |
| **D4** | Sub-tasks closed | D | All linked sub-tasks have `status: DONE`. | `ALL_SUBTASKS_CLOSED_AT_DONE_IMPL`, `OPEN_SUBTASK_AT_DONE_IMPL` |
| **D5** | Tests passing with evidence | D | A sub-task of type `TEST` is closed and has a `ci_runs` link resolving to a green run. | `TEST_SUBTASK_CLOSED_WITH_CI_LINK`, `TEST_SUBTASK_MISSING`, `TEST_SUBTASK_OPEN`, `TEST_SUBTASK_MISSING_CI_LINK` |
| **D6** | Operationally shippable | D | `production_release_reference` populated with a URL that is not staging/localhost. | `DEPLOY_REFERENCE_PRESENT`, `DEPLOY_REFERENCE_EMPTY`, `DEPLOY_REFERENCE_LOCAL_ONLY` |

### Done-gates — fire on `IN_VALIDATION → DONE`

| Code | Name | Type | Check | Evidence codes |
|---|---|---|---|---|
| **Y4** | Non-builder validates | D | `validator` is populated and is not the `assignee`. | `VALIDATOR_INDEPENDENT`, `VALIDATOR_IS_BUILDER` |
| **Y5** | Live in production at Done | D | `production_release_reference` is a production URL (not staging). | `PRODUCTION_REFERENCE_PRESENT_AT_DONE`, `PRODUCTION_REFERENCE_EMPTY`, `PRODUCTION_REFERENCE_STAGING_ONLY`, `PRODUCTION_REFERENCE_POST_DONE` |
| **U10** | Impact measurement infrastructure | D | `impact_measurement_link` is populated and resolves (HTTP 2xx/3xx). | `IMPACT_LINK_PRESENT_AND_RESOLVABLE`, `IMPACT_LINK_UNREACHABLE`, `IMPACT_LINK_MISSING`, `IMPACT_LINK_BROKEN` |

### Invariants — fire on any edit that violates

| Code | Name | Type | Trigger | Check | Evidence codes |
|---|---|---|---|---|---|
| **U7** | No scope evolution after commitment | D | Edit to `Acceptance Criteria` or `Scenarios` body section | Current status must be ≤ `READY`. Editing these sections at `IN_IMPLEMENTATION` or later is a block. | `NO_POST_COMMIT_AC_EDITS`, `AC_EDITED_POST_COMMIT`, `SCENARIOS_EDITED_POST_COMMIT` |
| **U8** | Validation outputs in contract | D | New ticket created that links to this one while this one is `IN_VALIDATION` | New ticket's `type` must be `STORY_DEFECT`. `STORY`, `TASK`, `BUG` created during validation fail. | `VALIDATION_OUTPUTS_IN_CONTRACT`, `NEW_STORY_CREATED_DURING_VALIDATION`, `NEW_TASK_CREATED_DURING_VALIDATION`, `NEW_BUG_CREATED_DURING_VALIDATION` |
| **D10** | Backward transitions documented | D | Any backward status change | `reason_for_backward_move` populated on the same edit. | `FORWARD_ONLY_TRANSITIONS`, `BACKWARD_TRANSITION_DETECTED` |
| **U11** | Correct issue-type classification | J | Any edit (ideally pre-`READY`) | Judge evaluates whether `type` matches content. Prompt: [`../prompts/U11.md`](../prompts/U11.md). | `TYPE_CORRECT`, `TYPE_MISMATCH` |

### Retrospective only — no hook, grader-only

| Code | Name | Type | Check |
|---|---|---|---|
| **Y6** | Completable in one cycle | R | Cycle time `READY → DONE_IMPLEMENTING` ≤ 7 calendar days. |
| **U9** | Story defect classification | J/R | On `STORY_DEFECT` tickets, judge classifies as in-scope vs scope-evolution. Prompt: [`../prompts/U9.md`](../prompts/U9.md). |
| **D3** | Violations surfaced, not absorbed | J/R | Judge evaluates whether deviations were documented vs silently absorbed. Prompt: [`../prompts/D3.md`](../prompts/D3.md). |
| **D8** | Cycle time within norm | R | Per-engagement cycle-time distribution. |
| **D9** | Story defect rate | R | Story Defects per N Stories. |

---

## Implementation notes

### Ordering within a single edit

When an edit touches multiple gates (e.g. moving to `READY` fires C1, C3, U12 deterministic and C2, Y1, Y2, Y3 judge), evaluate in this order:

1. **Deterministic first.** If any fail, block with the failing-codes summary. Don't burn a judge call.
2. **Judge next, in parallel if possible.** Each judge prompt runs independently. Aggregate results.
3. **System-wide last.** WIP checks need the full tickets directory; run once at the end.

### Block messaging

Block messages must name the gate code, the evidence code, and the remediation. Example:

```
Blocked by C3 (APPROVER_FIELD_EMPTY).
Moving to READY requires `spec_approver` populated with an authorized approver.
Authorized for BBIT: jeffrey, yanna-proxy. See product-management/.claude/scripts/config.json.
```

### Versioning

Adding a gate: minor bump. Changing an existing gate's check or evidence codes: breaking, requires prompt-version bump and migration note.

### What is not a gate

- Anything in [`system-rules.md`](system-rules.md) is an operating constraint. Many are enforced by gates (Rule 2 by W1/C1, Rule 3 by U7/U8, Rule 4 by D7); others are human discipline (Rule 1 single decision-maker, Rule 6 priority tradeoffs, Rule 11 pause on repeated ambiguity). Gates do not replace the rules; they enforce the ones that can be enforced mechanically.
