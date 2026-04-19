# Evidence Codes

Stable SCREAMING_SNAKE_CASE strings returned by the grader with every dimension verdict. The grader aggregates on these for the rollup. Changes to codes here are breaking and require a prompt version bump.

## Universal codes (any dimension)

| Code | Meaning |
|---|---|
| `MISSING_SECTION` | A required template section is absent from the issue description. |
| `FIELD_EMPTY` | A required custom field is empty. |
| `EVIDENCE_INSUFFICIENT_TO_JUDGE` | Judge returned INSUFFICIENT_EVIDENCE. |
| `TEAM_SIZE_EXCEPTION` | Single-person team; dimension skipped or flagged rather than failed. |

## Y1 — Business objective nameable

| Code | Verdict |
|---|---|
| `BUSINESS_OBJECTIVE_IN_BUSINESS_TERMS` | PASS |
| `OBJECTIVE_IS_TECHNICAL_NOT_BUSINESS` | FAIL |
| `OBJECTIVE_TOO_VAGUE_TO_VERIFY` | FAIL |
| `OBJECTIVE_TEXT_MISSING` | FAIL |
| `EPIC_LINK_MISSING` | FAIL |

## Y2 — Observable business difference describable

| Code | Verdict |
|---|---|
| `IMPACT_HAS_METRIC_THRESHOLD_AND_OBSERVATION` | PASS |
| `IMPACT_MISSING_METRIC` | FAIL |
| `IMPACT_MISSING_THRESHOLD` | FAIL |
| `IMPACT_MISSING_OBSERVATION_POINT` | FAIL |
| `IMPACT_VAGUE_OR_ASPIRATIONAL` | FAIL |
| `IMPACT_SECTION_EMPTY` | FAIL |

## Y3 — AC in plain language, pre-implementation

| Code | Verdict |
|---|---|
| `AC_PRESENT_AND_PRE_COMMIT` | PASS (Y3.a) |
| `AC_PLAIN_AND_NON_ENGINEER_VERIFIABLE` | PASS (Y3.b) |
| `AC_WRITTEN_POST_COMMIT` | FAIL (Y3.a) |
| `AC_TECHNICAL_RESTATEMENT` | FAIL (Y3.b) |
| `AC_AMBIGUOUS_OR_UNVERIFIABLE` | FAIL (Y3.b) |
| `AC_EMPTY_OR_PLACEHOLDER` | FAIL |

## Y4 — Non-builder validates

| Code | Verdict |
|---|---|
| `VALIDATOR_INDEPENDENT` | PASS |
| `VALIDATOR_IS_BUILDER` | FAIL |

## Y5 — Live in production at Done

| Code | Verdict |
|---|---|
| `PRODUCTION_REFERENCE_PRESENT_AT_DONE` | PASS |
| `PRODUCTION_REFERENCE_EMPTY` | FAIL |
| `PRODUCTION_REFERENCE_STAGING_ONLY` | FAIL |
| `PRODUCTION_REFERENCE_POST_DONE` | FAIL |

## Y6 — One cycle (retrospective)

| Code | Verdict |
|---|---|
| `CYCLE_TIME_WITHIN_LIMIT` | PASS |
| `CYCLE_TIME_EXCEEDS_LIMIT` | FAIL |

## U7 — No scope evolution after commitment

| Code | Verdict |
|---|---|
| `NO_POST_COMMIT_AC_EDITS` | PASS |
| `AC_EDITED_POST_COMMIT` | FAIL |
| `SCENARIOS_EDITED_POST_COMMIT` | FAIL |

## U8 — Validation outputs

| Code | Verdict |
|---|---|
| `VALIDATION_OUTPUTS_IN_CONTRACT` | PASS |
| `NEW_STORY_CREATED_DURING_VALIDATION` | FAIL |
| `NEW_TASK_CREATED_DURING_VALIDATION` | FAIL |
| `NEW_BUG_CREATED_DURING_VALIDATION` | FAIL |

## U9 — Story defect classification

| Code | Verdict |
|---|---|
| `DEFECT_MAPS_TO_SCENARIO` | PASS |
| `DEFECT_IS_SCOPE_EVOLUTION` | PASS (flagged in rollup) |
| `DEFECT_DESCRIPTION_INSUFFICIENT` | INSUFFICIENT_EVIDENCE |

## U10 — Impact measurement infrastructure

| Code | Verdict |
|---|---|
| `IMPACT_LINK_PRESENT_AND_RESOLVABLE` | PASS |
| `IMPACT_LINK_MISSING` | FAIL |
| `IMPACT_LINK_BROKEN` | FAIL |

## U11 — Issue-type classification

| Code | Verdict |
|---|---|
| `TYPE_CORRECT` | PASS |
| `TYPE_MISMATCH` | FAIL (recommended_type populated) |

## U12 — Risks surfaced

| Code | Verdict |
|---|---|
| `RISKS_POPULATED` | PASS |
| `RISKS_EMPTY_OR_MISSING` | FAIL |
| `RISKS_PLACEHOLDER` | FAIL |

## C1 — Commitment transition exists

| Code | Verdict |
|---|---|
| `COMMITMENT_TRANSITION_FOUND` | PASS |
| `COMMITMENT_TRANSITION_MISSING` | FAIL |

## C2 — BDD quality at commitment

| Code | Verdict |
|---|---|
| `SCENARIOS_COVER_CORE_RULE` | PASS |
| `SCENARIOS_COVER_ONLY_EDGE_CASES` | FAIL |
| `SCENARIOS_PLACEHOLDER_OR_EMPTY` | FAIL |
| `SCENARIOS_NOT_GIVEN_WHEN_THEN` | FAIL |

## C3 — Gate approver recorded

| Code | Verdict |
|---|---|
| `APPROVER_RECORDED_AND_AUTHORIZED` | PASS |
| `APPROVER_FIELD_EMPTY` | FAIL |
| `APPROVER_NOT_AUTHORIZED` | FAIL |
| `APPROVER_IS_BUILDER` | FAIL |

## D1 — Sub-tasks created after commit

| Code | Verdict |
|---|---|
| `SUBTASKS_CREATED_POST_COMMIT` | PASS |
| `SUBTASKS_CREATED_PRE_COMMIT` | FAIL |
| `SUBTASKS_ABSENT_ON_NON_TRIVIAL` | FAIL |

## D2 — Design artifact

| Code | Verdict |
|---|---|
| `DESIGN_NOT_REQUIRED_WORK_TRIVIAL` | PASS |
| `DESIGN_PRESENT_AS_REQUIRED` | PASS |
| `DESIGN_MISSING_FOR_COMPLEX_WORK` | FAIL |

## D3 — Violations surfaced

| Code | Verdict |
|---|---|
| `NO_DEVIATION_DETECTED` | PASS |
| `DEVIATION_SURFACED_EXPLICITLY` | PASS |
| `DEVIATION_ABSORBED_SILENTLY` | FAIL |

## D4 — Sub-tasks closed at Done Implementing

| Code | Verdict |
|---|---|
| `ALL_SUBTASKS_CLOSED_AT_DONE_IMPL` | PASS |
| `OPEN_SUBTASK_AT_DONE_IMPL` | FAIL |

## D5 — Tests passing with evidence

| Code | Verdict |
|---|---|
| `TEST_SUBTASK_CLOSED_WITH_CI_LINK` | PASS |
| `TEST_SUBTASK_MISSING` | FAIL |
| `TEST_SUBTASK_OPEN` | FAIL |
| `TEST_SUBTASK_MISSING_CI_LINK` | FAIL |

## D6 — Operationally shippable

| Code | Verdict |
|---|---|
| `DEPLOY_REFERENCE_PRESENT` | PASS |
| `DEPLOY_REFERENCE_EMPTY` | FAIL |
| `DEPLOY_REFERENCE_LOCAL_ONLY` | FAIL |

## D7 — WIP respected

| Code | Verdict |
|---|---|
| `WIP_WITHIN_LIMITS` | PASS |
| `WIP_EXCEEDED_PER_ENGINEER` | FAIL |
| `WIP_EXCEEDED_SYSTEM` | FAIL |

## D8 — Cycle time within norm

| Code | Verdict |
|---|---|
| `CYCLE_TIME_WITHIN_NORM` | PASS |
| `CYCLE_TIME_EXCEEDS_NORM` | FAIL |

## D9 — Story defect rate

| Code | Verdict |
|---|---|
| `ZERO_DEFECTS` | PASS |
| `DEFECTS_PRESENT` | FAIL |

## D10 — No backward transitions

| Code | Verdict |
|---|---|
| `FORWARD_ONLY_TRANSITIONS` | PASS |
| `BACKWARD_TRANSITION_DETECTED` | FAIL |

## Adding or changing codes

- Adding new codes: minor version bump, no prompt invalidation.
- Changing existing codes: breaking, requires prompt version bump and a migration note in the rollup historical data.
- Retiring codes: mark `DEPRECATED` for one release cycle before removal.
