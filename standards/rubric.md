# Rubric — All Graded Dimensions

The rubric is the full set of dimensions the grader evaluates. It extends the 6-yes with additional upstream, commitment, and downstream checks. Every dimension is binary: PASS or FAIL.

Reference: [specs/grader-v0.2.md](../specs/grader-v0.2.md) for full evaluation logic, data sources, and judge prompts.

## Codes

- **Y1–Y6** — The 6-yes. See `six-yes.md`.
- **U7–U12** — Upstream rubric beyond the 6-yes.
- **C1–C3** — Commitment point checks.
- **D1–D10** — Downstream dimensions.

## Upstream 6-yes (Y1–Y6)

| Code | Name | Owner | Type |
|---|---|---|---|
| Y1 | Business objective nameable | Yanna | D + J |
| Y2 | Observable business difference describable | Yanna | D + J |
| Y3 | AC in plain language, pre-implementation | Yanna | D + J |
| Y4 | Non-builder can validate | Yanna | D |
| Y5 | Live in production when called Done | Yanna | D |
| Y6 | Completable in one cycle (retrospective cycle time) | Yanna | D |

## Upstream rubric (U7–U12)

| Code | Name | Owner | Type |
|---|---|---|---|
| U7 | No scope evolution after commitment | Yanna | D |
| U8 | Validation outputs are Acceptance or Story Defect only | Yanna | D |
| U9 | Story defects classified (in-scope vs. scope-evolution) | Yanna | D + J |
| U10 | Impact measurement infrastructure present at Done | Yanna | D |
| U11 | Correct issue-type classification (all types) | Yanna + Hector | J |
| U12 | Risks surfaced | Yanna | D |

## Commitment point (C1–C3)

| Code | Name | Owner | Type |
|---|---|---|---|
| C1 | Commitment transition exists | System | D |
| C2 | BDD quality at commitment | Yanna | J |
| C3 | Gate approver recorded | Hector (commitment gate) | D |

## Downstream (D1–D10)

| Code | Name | Owner | Type |
|---|---|---|---|
| D1 | Sub-tasks created after Story review | Hector | D |
| D2 | Design artifact for non-trivial work | Hector | D + J |
| D3 | Violations surfaced, not absorbed | Hector | J |
| D4 | All sub-tasks closed at Done Implementing | Hector | D |
| D5 | Tests passing with evidence | Hector | D |
| D6 | Operationally shippable | Hector | D |
| D7 | WIP respected | Hector (system) | D |
| D8 | Cycle time within norm | Hector (system) | D |
| D9 | Story defect rate | Hector | D |
| D10 | No backward transitions | Hector + Yanna | D |

## Evidence types

- **D** — Deterministic. Pulled from Jira fields, changelog, or issue links.
- **J** — Claude judge. Requires reading text and making a judgment. See `prompts/`.
- **D + J** — Both. Deterministic check first (is the section populated?), judge second (is it good?).

## Pass policy

- Per issue, each enabled dimension returns PASS, FAIL, or INSUFFICIENT_EVIDENCE.
- INSUFFICIENT_EVIDENCE rolls up as fail with a distinct flag.
- Weighted scores are not used. Any FAIL on any enabled dimension fails that dimension for the issue.
- The six-yes overall verdict is PASS only if all of Y1–Y6 pass.
- The upstream overall verdict is PASS only if all enabled Y and U dimensions pass.
- The downstream overall verdict is PASS only if all enabled D dimensions pass.
- The story overall verdict is PASS only if upstream and downstream both pass.

## Rollup signals beyond pass/fail

- **U9** additionally classifies Story Defects as in-scope vs. scope-evolution. Scope-evolution dominance is a spec-quality signal reported separately.
- **U11** additionally outputs a `recommended_type` when the Jira type is wrong. Rollup shows misclassification counts per type pair (e.g., Task → Story) and the corrected Task:Story ratio.
