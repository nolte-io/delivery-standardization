# Nolte Delivery Standardization

This repo is the system that standardizes Nolte's delivery process around the delivery model published at [nolte.io/delivery](https://nolte.io/delivery).

## Contents

- **[`standards/`](standards/)** — The 6-yes, the rubric, the system rules, and a page per dimension. Authoritative.
  - [`six-yes.md`](standards/six-yes.md) — The six readiness questions
  - [`rubric.md`](standards/rubric.md) — Full 25-dimension table
  - [`system-rules.md`](standards/system-rules.md) — 12 non-negotiable operating rules
  - [`evidence-codes.md`](standards/evidence-codes.md) — Stable evidence-code catalog
  - [`dimensions/`](standards/dimensions/) — One page per dimension, with current rollup status
- **[`prompts/`](prompts/)** — Judge prompts used by the grader. Versioned.
- **[`specs/`](specs/)** — Design specs for implementations.
- **[`grader/`](grader/)** — The delivery grader. Python. Phase 1 in progress.
- **[`rollout/`](rollout/)** — Operational docs for the delivery team.
  - [`how-we-manage-delivery-quality.md`](rollout/how-we-manage-delivery-quality.md) — Team operating model
  - [`thursday-agenda.md`](rollout/thursday-agenda.md) — Current triage meeting format
  - [`grader-team-todos.md`](rollout/grader-team-todos.md) — Week-one rollout tasks
  - [`jira-template.md`](rollout/jira-template.md) — Story template
  - [`jira-fields-checklist.md`](rollout/jira-fields-checklist.md) — Custom field creation guide

## Where to start

- **New to this?** Read [`standards/six-yes.md`](standards/six-yes.md), then skim [`standards/dimensions/README.md`](standards/dimensions/README.md).
- **Triaging a dimension?** Open its page in [`standards/dimensions/`](standards/dimensions/) and follow the "Open issues" link.
- **Running the grader?** Read [`grader/README.md`](grader/README.md).
- **Understanding the operating model?** Read [`rollout/how-we-manage-delivery-quality.md`](rollout/how-we-manage-delivery-quality.md).

## Rules

- When any file disagrees with `/standards`, `/standards` wins.
- Changes to `/standards` and `/prompts` require review from the repo owner.
- Standards changes come with a companion update to [nolte.io/delivery](https://nolte.io/delivery) in the same PR cycle.
- Judge prompt versions are logged with every grader run. Prompt changes invalidate cached judgments.
- Secrets never enter the repo. Use `.env` locally.

## Ownership

- **Standards & prompts** — Jeffrey approves. Owners propose via PR.
- **Upstream dimensions (Y, U)** — Yanna.
- **Downstream dimensions (D)** — Hector.
- **System dimensions (C, U11, D10)** — Joint.
- **Grader implementation** — engineering, reviewed with Jeffrey.

## What this is not

- A generic agile playbook.
- A coaching resource.
- Documentation for sale.

The delivery model at [nolte.io/delivery](https://nolte.io/delivery) is the canonical public reference. This repo operationalizes it.

## License

MIT.
