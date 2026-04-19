# The 6-Yes — Readiness Test

The 6-yes is the gate into Nolte's delivery system. Before any item is committed as a delivery, it must answer yes to all six. If any answer is no, the work is not ready.

Canonical public reference: [nolte.io/delivery](https://nolte.io/delivery). When this file disagrees with the public reference, the public reference wins and this file is updated.

## The six

1. **Y1 — Business objective nameable.** Can I name the business objective this delivery serves, in business terms (revenue, retention, activation, risk reduction, cost savings, time savings, compliance)?

2. **Y2 — Observable business difference describable.** Can I describe what is observably different in the business after this ships? A metric, a threshold, and either a measurement location or an observability mechanism.

3. **Y3 — Acceptance criteria in plain language, before implementation.** Are the AC written in plain language, verifiable by a non-engineer, and defined before implementation begins?

4. **Y4 — Non-builder can validate.** Can someone other than the builder validate it against those criteria?

5. **Y5 — Live in production when it counts as Done.** Will this be live in production when called done? Staging does not count. Demos do not count.

6. **Y6 — Completable in one cycle.** Can this be completed within a single week of active work? Consistent sizing is what makes throughput data meaningful.

## Why these six

Each question rules something in and rules something out. Two out of six is not enough. Five out of six is not enough. The test is binary because predictability is binary.

## How the grader uses the 6-yes

The grader evaluates every Story against these six and reports per-dimension pass/fail. The six-yes pass rate is the headline metric for the upstream lane.

Retrospective mapping:
- Y6 is checked by actual cycle time (`Ready` → `Done Implementing` ≤ 7 calendar days). The forward-looking prediction at commit is captured separately by the Spec Approver gate (C3 in the rubric).
- Y5 is checked by the presence of a Production Release Reference at the Done transition.
- Y1, Y2, Y3 require both a deterministic field/section check and a judgment pass on quality.
- Y4 is checked by comparing validator identity against builder identity in Jira history.

## Rollout phase

The 6-yes is enforced as a hard gate from day one of the grader running. Baseline scores will be low. That is the point.
