# Workflow — State Graph and Transitions

Canonical state graph for every ticket. Defines the nine statuses, legal transitions, and which [gates](gates.md) fire on each edge. Both Jira and markdown implementations conform to this graph — the only difference is substrate.

All machine-readable status and type values are `SCREAMING_SNAKE_CASE`. Human display labels are mapped at the bottom of this doc.

---

## States

| # | Status | Meaning |
|---|---|---|
| 1 | `BACKLOG` | Captured idea. No commitment to specify or build. |
| 2 | `AWAITING_SPECIFICATION` | Picked for specification work. Not yet specified. |
| 3 | `IN_SPECIFICATION` | Being specified. AC, Scenarios, Risks being drafted. |
| 4 | `DONE_SPECIFYING` | Spec complete. Awaiting approver sign-off. |
| 5 | `READY` | Approved. Committed. Waiting for implementation capacity. |
| 6 | `IN_IMPLEMENTATION` | Actively being built. |
| 7 | `DONE_IMPLEMENTING` | Build complete. Awaiting independent validation. |
| 8 | `IN_VALIDATION` | Being validated by a non-builder against AC and Scenarios. |
| 9 | `DONE` | Live in production. Impact observable. |

---

## Issue types

Machine-readable values in `type` frontmatter field. `SCREAMING_SNAKE_CASE`:

| Type | Meaning |
|---|---|
| `STORY` | User-facing delivery. 6-yes applies in full. |
| `TASK` | Operational / non-user-facing work. Reduced schema (see [`ticket-template.md`](ticket-template.md)). |
| `BUG` | Defect on already-released functionality. Not a validation output. |
| `STORY_DEFECT` | Defect discovered during `IN_VALIDATION` of a parent Story. Must map to an existing Scenario (graded by U8, U9). |

---

## Legal transitions

### Forward (the happy path)

```
BACKLOG
  → AWAITING_SPECIFICATION
    → IN_SPECIFICATION
      → DONE_SPECIFYING
        → READY              ← commitment gate (C1, C2, C3, Y1, Y2, Y3, U12)
          → IN_IMPLEMENTATION ← W1 bypass check
            → DONE_IMPLEMENTING ← D4, D5, D6
              → IN_VALIDATION
                → DONE        ← Y4, Y5, U10
```

### Backward (allowed, graded by D10)

Any move from a later state to an earlier state is a **backward transition**. Always legal, always graded. Requires `reason_for_backward_move` populated on the same edit. Common valid backward moves:

- `IN_IMPLEMENTATION → DONE_SPECIFYING` — "scope was wrong, needs re-spec"
- `IN_VALIDATION → IN_IMPLEMENTATION` — "validation found a Story Defect"
- `DONE_IMPLEMENTING → IN_IMPLEMENTATION` — "CI failure, needs a fix"

### Illegal

- **Skipping `DONE_SPECIFYING` or `READY` on the way to `IN_IMPLEMENTATION`.** This is the bypass W1 catches. Enforcement reverts the ticket to `AWAITING_SPECIFICATION` and posts a comment.
- **`DONE_SPECIFYING → IN_IMPLEMENTATION` directly** — must pass through `READY`. The `READY` state is the commitment timestamp used by every downstream cycle-time calculation.
- **`DONE → anything`.** Done tickets are final. Mistakes produce a follow-up ticket (new `id`), not a status change on the original.

---

## The commitment point

`READY → IN_IMPLEMENTATION` is the **commitment point** and is a one-way door (System Rule 2). After entering `IN_IMPLEMENTATION`:

- AC and Scenarios are frozen. Edits fail U7.
- Capacity is allocated. New work cannot enter `IN_SPECIFICATION` or `IN_IMPLEMENTATION` if doing so would exceed WIP limits (System Rule 4; graded by D7).
- Cycle time starts. `READY → DONE_IMPLEMENTING` measured against the 7-day norm (Y6, D8).

The approver recorded in `spec_approver` at `DONE_SPECIFYING → READY` is the human accountable for that commitment (C3, System Rule 1).

---

## Validation discipline

During `IN_VALIDATION`, per System Rule 3:

- Validation confirms agreed behavior. It does not redefine it.
- New ideas return to `BACKLOG` as new tickets, not edits to the one under validation (graded by U7, U8).
- Story Defects may be filed as separate tickets (`type: STORY_DEFECT`) and must map to existing Scenarios (graded by U8, U9).

---

## Transition matrix — gates per edge

Cross-reference: [`gates.md`](gates.md) has full gate definitions. This matrix answers "what fires when?" at a glance.

| From → To | Deterministic gates | Judge gates |
|---|---|---|
| `BACKLOG → AWAITING_SPECIFICATION` | — | — |
| `AWAITING_SPECIFICATION → IN_SPECIFICATION` | — | — |
| `IN_SPECIFICATION → DONE_SPECIFYING` | — | — |
| `DONE_SPECIFYING → READY` | C1, C3, U12 | C2, Y1, Y2, Y3 |
| `READY → IN_IMPLEMENTATION` | W1, D1 (timing anchor), D7 (WIP), D2 (design artifact if non-trivial) | — |
| `IN_IMPLEMENTATION → DONE_IMPLEMENTING` | D4, D5, D6, D7 | — |
| `DONE_IMPLEMENTING → IN_VALIDATION` | — | — |
| `IN_VALIDATION → DONE` | Y4, Y5, U10 | — |
| *any* → *earlier* (backward) | D10 | — |
| edits to AC / Scenarios while `status >= IN_IMPLEMENTATION` | U7 | — |
| new ticket linked to this one while in `IN_VALIDATION` | U8 | U9 (on the new ticket if `type: STORY_DEFECT`) |

Gates evaluated retrospectively by the grader only (never at transition): Y6, D8, D9, D3, U11.

---

## WIP limits and exceptions

WIP limits are set in the implementation's config (for markdown: `product-management/.claude/scripts/config.json`). Default norms:

- **`IN_SPECIFICATION`** — 2 per specifier
- **`IN_IMPLEMENTATION`** — 1 per engineer, 6 system-wide
- **`IN_VALIDATION`** — 3 system-wide

Transitions that would exceed a limit are blocked unless the edit also populates `wip_exception` with a justification (System Rule 4, graded by D7). Exceptions are logged in git history and rolled up monthly.

---

## Display labels

Machine values above are canonical. When rendering for humans — PR comments, rollup reports, Jira bridge — map to these display labels. The mapping is the single place the two conventions meet.

| Machine value | Display label |
|---|---|
| `BACKLOG` | Backlog |
| `AWAITING_SPECIFICATION` | Awaiting Specification |
| `IN_SPECIFICATION` | In Specification |
| `DONE_SPECIFYING` | Done Specifying |
| `READY` | Ready |
| `IN_IMPLEMENTATION` | In Implementation |
| `DONE_IMPLEMENTING` | Done Implementing |
| `IN_VALIDATION` | In Validation |
| `DONE` | Done |
| `STORY` | Story |
| `TASK` | Task |
| `BUG` | Bug |
| `STORY_DEFECT` | Story Defect |

The Jira implementation uses the display-label column as its workflow status names. The markdown implementation uses the machine-value column in frontmatter. Grader output uses machine values; UI layers (PR comments, rollup tables) render display labels.

---

## Implementations

- **Markdown:** status is a YAML frontmatter field with `SCREAMING_SNAKE_CASE` value. Transitions are commits that edit it. Gates run as pre-write hooks on `tickets/*.md`.
- **Jira:** status is workflow state using the display label. Transitions are Jira transitions. Gates run as workflow validators and Automation rules — see [`../rollout/jira-workflow-rules.md`](../rollout/jira-workflow-rules.md). The grader normalizes Jira status names to machine values on read.

Both must accept exactly the forward / backward transitions above and fire exactly the gates in the matrix.
