# Nolte Delivery Standardization

This repo is the system that standardizes Nolte's delivery process around the delivery model published at [nolte.io/delivery](https://nolte.io/delivery).

## Contents

- **`standards/`** — The 6-yes, the rubric, the system rules. Authoritative.
- **`prompts/`** — Judge prompts used by the delivery grader. Versioned.
- **`specs/`** — Design specs for implementations.
- **`grader/`** — The delivery grader. Python. Scores every issue against the standards.
- **`rollout/`** — Operational docs for the delivery team (Jira template, field checklists, rollout todos).

## Rules

- When any file disagrees with `/standards`, `/standards` wins.
- Changes to `/standards` and `/prompts` require review from the repo owner.
- Standards changes come with a companion update to [nolte.io/delivery](https://nolte.io/delivery) in the same PR cycle. Drift between repo and public model is tracked as an issue, not ignored.
- Judge prompt versions are logged with every grader run. Prompt changes invalidate cached judgments for that dimension.
- Secrets never enter the repo. Use `.env` locally. Config examples use placeholder values; real config is git-ignored.

## What this is not

- A generic agile playbook.
- A coaching resource.
- Documentation for sale.

## Roadmap

Current focus: the delivery grader (Phase 1, spec v0.2).

Future scope (tracked separately, not yet implemented):
- Kanban steering prompts per stage.
- Role-specific guidance.
- Rollout playbook.

The delivery model at [nolte.io/delivery](https://nolte.io/delivery) is the canonical public reference. This repo operationalizes it.

## License

MIT.
