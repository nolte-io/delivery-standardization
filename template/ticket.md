---
# Always required — see standards/ticket-template.md
id: PROJ-000                       # Project-prefixed identifier (prefix matches `project`)
project: PROJ                      # Project code, e.g. BBIT, SCPG
type: STORY                        # STORY | TASK | BUG | STORY_DEFECT
status: BACKLOG                    # See standards/workflow.md for the nine statuses
title: One-line summary of the delivery
assignee: unassigned               # The builder. Validator (Y4) must be different.
created_at: 2026-01-01             # ISO-8601

# Parent / structure
epic: null                         # Required for STORY (Y1)
subtasks: []                       # Populated as sub-task tickets are created
story_defects: []                  # Links to STORY_DEFECT tickets filed against this one

# Required at specific transitions — leave null until the transition
spec_approver: null                # C3 — required at DONE_SPECIFYING → READY
approved_at: null                  # C3 — required at DONE_SPECIFYING → READY
design_artifact_link: null         # D2 — required at IN_IMPLEMENTATION entry if non-trivial
production_release_reference: null # D6, Y5 — required at DONE_IMPLEMENTING and DONE
impact_measurement_link: null      # U10 — required at DONE
validator: null                    # Y4 — required at DONE; must not equal `assignee`

# Exceptional transitions only
reason_for_backward_move: null     # D10 — free text, required on any backward status move
wip_exception: null                # D7 — free text, required when transition exceeds WIP limit

# Appended by automation — do not edit by hand
merged_prs: []
ci_runs: []
---

## Business Objective

<!-- Graded by Y1. Link to Epic. Outcome in business terms: revenue, retention,
     activation, risk reduction, cost savings, time savings, compliance. Name the mechanism.
     "None identified" is NOT valid here. -->

_Example: Reduce P50 claim intake time from 8min to <3min to handle 30% more claim volume without adding headcount._

## Observable Impact

<!-- Graded by Y2. One sentence. The metric, the threshold, and either the measurement
     location or the observability mechanism.
     "None identified" allowed only for non-user-facing operational TASK tickets. -->

_Example: P50 claim intake time drops from 8min to <3min in Datadog dashboard X, observed within 2 weeks of release._

## Acceptance Criteria

<!-- Graded by Y3. Plain language. Verifiable by a non-engineer. Written BEFORE implementation.
     Editing this section after commitment (DONE_SPECIFYING → READY) fails U7. -->

- When ..., then ...
- When ..., then ...

## Scenarios

<!-- Graded by C2. BDD Given/When/Then covering the highest-value rules — not every rule.
     Written before commitment. -->

Given ...
When ...
Then ...
And ...

## Risks

<!-- Graded by U12. Regulatory, technical, dependency, data.
     "None identified" is allowed and must be explicit. Blank is not. -->

- ...
