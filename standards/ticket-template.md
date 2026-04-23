# Ticket Template — Schema

Canonical structure for a ticket in Nolte's delivery system. Applies to any implementation (Jira issues, markdown files in `product-management/tickets/`, or future substrates). When a ticket satisfies this schema and every gate in [`gates.md`](gates.md) that applies at its current status, it conforms.

All machine-readable enum values (`status`, `type`, evidence codes) are `SCREAMING_SNAKE_CASE`. See [`workflow.md`](workflow.md) for the canonical enumerations and the display-label mapping.

Source of truth. When an implementation disagrees with this file, the implementation is wrong.

---

## Frontmatter schema

Every ticket carries structured metadata. In Jira, these are issue fields; in markdown, they are YAML frontmatter. Names are normative.

### Always required

| Field | Type | Description |
|---|---|---|
| `id` | string | Project-prefixed identifier, e.g. `BBIT-123`. Prefix matches `project`. |
| `project` | string | Project code, e.g. `BBIT`, `SCPG`. |
| `type` | enum | One of: `STORY`, `TASK`, `BUG`, `STORY_DEFECT`. Graded by U11. |
| `status` | enum | One of the nine workflow statuses — see [`workflow.md`](workflow.md). |
| `title` | string | One-line summary. |
| `assignee` | string | The builder. Used by Y4 to ensure validator ≠ builder. |
| `created_at` | ISO-8601 date | Ticket creation timestamp. |

### Required at specific transitions

| Field | Type | Required at | Graded by |
|---|---|---|---|
| `spec_approver` | string (user id) | `DONE_SPECIFYING → READY` | C3 |
| `approved_at` | ISO-8601 date | `DONE_SPECIFYING → READY` | C3 |
| `design_artifact_link` | URL | `IN_IMPLEMENTATION` entry if non-trivial | D2 |
| `production_release_reference` | URL | `DONE_IMPLEMENTING` and `DONE` | D6, Y5 |
| `impact_measurement_link` | URL | `DONE` | U10 |
| `validator` | string (user id) | `DONE` | Y4 |

### Required only for exceptional transitions

| Field | Type | Description |
|---|---|---|
| `reason_for_backward_move` | string | Free text. Required when status moves backward. Graded by D10. |
| `wip_exception` | string | Free text justification. Required when the transition would exceed the WIP limit. Graded by D7. |

### Optional / derived

| Field | Type | Description |
|---|---|---|
| `epic` | string (id) | Parent epic, if any. Y1 requires an epic link for Stories. |
| `subtasks` | array of ticket ids | Links to sub-task tickets. D1/D4/D5 read these. |
| `story_defects` | array of ticket ids | Links to `STORY_DEFECT` tickets filed against this ticket. |
| `merged_prs` | array of URLs | Appended by engineering-repo automation on merge. |
| `ci_runs` | array of URLs | Appended by engineering-repo automation on CI pass. |

---

## Body sections

Five sections, in order. **Do not delete section headers.** If not applicable, write `"None identified"` or `"N/A — <reason>"` so the grader sees explicit intent rather than a missing section.

### 1. Business Objective

Link to Epic. Outcome in business terms: revenue, retention, activation, risk reduction, cost savings, time savings, compliance. Name the mechanism.

Graded by **Y1**.

Example: *"Reduce P50 claim intake time from 8min to <3min to handle 30% more claim volume without adding headcount."*

### 2. Observable Impact

One sentence. The metric, the threshold, and either the measurement location or the observability mechanism.

Graded by **Y2**.

Example: *"P50 claim intake time drops from 8min to <3min in Datadog dashboard X, observed within 2 weeks of release."*

### 3. Acceptance Criteria

Plain language. Verifiable by a non-engineer. Written before implementation.

Graded by **Y3**.

### 4. Scenarios

BDD Given/When/Then covering the highest-value rules. Not every rule — the core behavior.

Graded by **C2**.

### 5. Risks

Regulatory, technical, dependency, data. `"None identified"` is allowed and must be explicit. Blank is not.

Graded by **U12**.

---

## Rules

- **Never delete a section header.** The grader looks for each by name. A missing section fails that dimension.
- **`"None identified"` is a valid answer** for Risks, and for Observable Impact when the work is a non-user-facing operational task. Not valid for Business Objective, AC, or Scenarios.
- **Write AC before Scenarios, and both before commitment** (`DONE_SPECIFYING → READY`). Edits to these sections after commitment fail U7 (no scope evolution).
- **For operational `TASK` tickets (rare):** only Business Objective and Observable Impact are required. AC and Scenarios may be minimal. Risks still required.
- **Status changes are one concern per edit.** An edit that moves `status` should not also edit AC, Scenarios, or Risks. The gate will block mixed edits so the git history reflects one transition per commit.

---

## Versioning

This schema is versioned. Breaking changes — renamed field, new required field, new section — require a PR here, prompt-version bump where judge prompts reference section names, and a migration note in any implementation that consumed the previous version.

Additive changes — new optional field, new evidence code — are minor.

---

## Implementations

- **Markdown (primary going forward):** `product-management/tickets/*.md`. YAML frontmatter uses `SCREAMING_SNAKE_CASE` enum values. Gates enforced by `.claude/` hooks pre-commit; grader reads git log for retrospective checks.
- **Jira (legacy / bridge period):** fields created per [`../rollout/jira-fields-checklist.md`](../rollout/jira-fields-checklist.md); workflow rules per [`../rollout/jira-workflow-rules.md`](../rollout/jira-workflow-rules.md); template per [`../rollout/jira-template.md`](../rollout/jira-template.md). Jira uses the display-label column from [`workflow.md`](workflow.md#display-labels); the grader normalizes on read.

Both implementations must satisfy every gate in [`gates.md`](gates.md) that applies at the ticket's current status.
