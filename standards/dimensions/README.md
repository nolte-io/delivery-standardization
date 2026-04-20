# Dimensions — Index

Every dimension the grader evaluates has its own page here. One page per dimension. Each page is the authoritative reference for what that rule does, what evidence it reads, and where the current team discussion lives.

When a dimension changes, it changes here first. The judge prompts and evaluator code reference these pages, not the other way around.

## How to use this index

- **Looking for the summary table across all 25?** See [`../rubric.md`](../rubric.md).
- **Looking for details on a specific rule?** Click its page below.
- **Looking for the current team discussion or refinement?** Follow the "Open issues" link on each dimension page.
- **Looking for the original 6-yes?** See [`../six-yes.md`](../six-yes.md).

## Current rollup status (as of 19 Apr 2026)

Run window: 20 Mar – 19 Apr 2026, 59 Stories graded. Six-yes pass rate: 0% (0/59).

Dimensions below are ordered by fail rate in the most recent rollup — the ones most urgent to discuss appear first.

## Upstream 6-yes

| Dim | Name | Fail rate | Owner | Page |
|---|---|---|---|---|
| Y5 | Live in production at Done | 100% | Yanna | [`Y5.md`](Y5.md) |
| Y3 | AC in plain language, pre-implementation | 100% | Yanna | [`Y3.md`](Y3.md) |
| Y6 | Completable in one cycle (retrospective) | 14% | Yanna | [`Y6.md`](Y6.md) |
| Y4 | Non-builder can validate | 2% | Yanna | [`Y4.md`](Y4.md) |
| Y1 | Business objective nameable | — judge pending | Yanna | [`Y1.md`](Y1.md) |
| Y2 | Observable business difference describable | — judge pending | Yanna | [`Y2.md`](Y2.md) |

## Upstream rubric

| Dim | Name | Fail rate | Owner | Page |
|---|---|---|---|---|
| U10 | Impact measurement infrastructure at Done | 100% | Yanna | [`U10.md`](U10.md) |
| U12 | Risks surfaced | 100% | Yanna | [`U12.md`](U12.md) |
| U7 | No scope evolution after commitment | 0% | Yanna | [`U7.md`](U7.md) |
| U8 | Validation outputs are Acceptance or Story Defect only | 0% | Yanna | [`U8.md`](U8.md) |
| U9 | Story defects classified | — judge pending | Yanna | [`U9.md`](U9.md) |
| U11 | Correct issue-type classification | — judge pending | Joint | [`U11.md`](U11.md) |

## Commitment point

| Dim | Name | Fail rate | Owner | Page |
|---|---|---|---|---|
| C3 | Gate approver recorded | 100% | Joint | [`C3.md`](C3.md) |
| C1 | Commitment transition exists | 2% | System | [`C1.md`](C1.md) |
| C2 | BDD quality at commitment | — judge pending | Yanna | [`C2.md`](C2.md) |

## Downstream

| Dim | Name | Fail rate | Owner | Page |
|---|---|---|---|---|
| D5 | Tests passing with evidence | 100% | Hector | [`D5.md`](D5.md) |
| D6 | Operationally shippable | 100% | Hector | [`D6.md`](D6.md) |
| D1 | Sub-tasks created after commit | 98% | Hector | [`D1.md`](D1.md) |
| D10 | No backward transitions | 32% | Joint | [`D10.md`](D10.md) |
| D8 | Cycle time within norm | 14% | Hector | [`D8.md`](D8.md) |
| D4 | All sub-tasks closed at Done Implementing | 7% | Hector | [`D4.md`](D4.md) |
| D7 | WIP respected | 0% | Hector | [`D7.md`](D7.md) |
| D9 | Story defect rate | 0% | Hector | [`D9.md`](D9.md) |
| D2 | Design artifact for non-trivial work | — judge pending | Hector | [`D2.md`](D2.md) |
| D3 | Violations surfaced, not absorbed | — judge pending | Hector | [`D3.md`](D3.md) |

## Ownership

- **Yanna** — upstream lane (Y, U). Owns template, field, and specification quality.
- **Hector** — downstream lane (D). Owns engineering execution discipline.
- **Joint** — system dimensions (C, U11). Both own, both are accountable.

## How to propose a change to a dimension

Open a GitHub issue labeled `dim:<code>`. Use the issue template. Pre-filled templates for the current triage are linked on each dimension page.

Decisions on any standards change require approval from Jeffrey. Discussion happens on the issue. Standards file updates happen via PR that references the issue.
