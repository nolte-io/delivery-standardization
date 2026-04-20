# How We Manage Delivery Quality

**Effective:** 20 April 2026
**Owner:** Jeffrey (approves system-level standards changes)
**Operational owners:** Yanna (upstream), Hector (downstream)

---

## What changed

Until now, delivery quality discussion at Nolte has been driven by Jeffrey spotting problems, raising them, and asking the team to fix them. That pattern has two failure modes:

1. It requires Jeffrey to be close enough to every engagement to spot the issues. He isn't, and shouldn't be.
2. It frames the team as reactive — fixing what the founder noticed — instead of accountable for the instrument that names the problems.

The grader replaces Jeffrey's role in spotting problems with an objective, repeatable measurement.

## What the grader does

Every 30 days, the grader reads every Story in the delivery system and scores it against the 6-yes published at [nolte.io/delivery](https://nolte.io/delivery) and the 25-dimension rubric in [`/standards/rubric.md`](../standards/rubric.md). The output is:

- A per-Story verdict on every dimension, with evidence.
- A rollup report showing which dimensions are failing across the portfolio.
- A per-owner breakdown showing who owns the failing work.

The grader does not soften. It does not average. It does not hide.

## Who owns what

**Yanna (upstream lane)** — owns Y1–Y6, U7–U12, C2. These dimensions cover specification quality, business objective clarity, AC discipline, risk surfacing, and post-commitment scope control. When an upstream dimension fails, the fix is specification process, template, or Jira field infrastructure.

**Hector (downstream lane)** — owns D1–D10. These cover sub-task hygiene, design artifact discipline, test evidence, operational shippability, WIP respect, cycle time, defect reporting, and workflow integrity. When a downstream dimension fails, the fix is engineering execution discipline or CI/workflow tooling.

**Joint (system)** — C1, C3, U11, D10. Workflow gates, classification integrity, and transition discipline sit between lanes. Both are accountable.

**Jeffrey** — approves changes to `/standards/` and `/prompts/`. Does not own individual dimension triage. Does not approve individual Story decisions. Steps in when the team cannot agree and escalation is needed.

## How we work when a dimension fails

1. The grader runs. A dimension fails at X%.
2. The owner of that dimension (Yanna, Hector, or both) opens or updates the corresponding GitHub issue in the repo under [`nolte-io/delivery-standardization/issues`](https://github.com/nolte-io/delivery-standardization/issues).
3. The issue is classified: **infrastructure** (a field, template, or tool doesn't exist yet) or **discipline** (the infrastructure exists but the behavior isn't there).
4. The owner proposes a response and assigns a date.
5. For dimension definition changes — loosening, tightening, redefining — the owner proposes the change as a PR against the relevant dimension page in `/standards/dimensions/`. Jeffrey approves or rejects.

Decisions happen in writing on the issue or PR. Slack and synchronous conversation are for clarification, not decisions. If a decision was only made in Slack, it did not happen.

## What the monthly rhythm looks like

**Week 1 after rollup:** triage. Every dimension that failed has an owner-assigned issue with a proposed response. Jeffrey reviews triage decisions async.

**Week 2:** infrastructure work. Fields get created, templates get updated, workflows get hardened. Completed work closes issues.

**Week 3:** discipline work. Owner runs team-level coaching against the specific failure patterns. Measures behavior change qualitatively.

**Week 4:** next run. Numbers move or they don't. If they don't, the problem isn't the grader — it's that the rules aren't being enforced. Jeffrey steps in.

## What changes about Jeffrey's role

- No more spotting problems and raising them in Slack.
- No more per-Story quality conversations unless a decision escalates.
- Approves changes to standards, not decisions on individual Stories.
- Sees the monthly rollup first, reviews triage decisions second, approves standards changes third.
- Time recovered goes to growth work — content, promotion, building.

## What we do not do

- **We do not soften the grader to make numbers look better.** The standards are public at nolte.io/delivery. Weakening them internally creates brand drift. If a dimension is consistently failing and the team believes the rule is wrong, the response is a PR against the dimension page, reviewed by Jeffrey, not a silent change.
- **We do not weight dimensions into an aggregate score.** Every pass/fail stays visible. Weighted scores hide failures, and hidden failures compound.
- **We do not let "Jeffrey will figure it out" become a response.** The grader made the problems visible. The team owns the response.

## The standard this enforces

> A delivery is a discrete, validated unit of work that produces a measurable change in a business objective — shipped, tested, and observable in production.

That standard is public. The grader enforces it. Yanna and Hector operationalize it. Jeffrey protects it.

Everything else is execution.
