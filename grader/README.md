# Grader

Python package. Scores every issue in Jira against Nolte's delivery standards.

## Status

**Not yet implemented.** This directory is the target for Claude Code. Build against [`specs/grader-v0.2.md`](../specs/grader-v0.2.md).

## Start here

When building, Claude Code reads (in order):

1. [`specs/grader-v0.2.md`](../specs/grader-v0.2.md) — architecture, dimensions, contracts, modes, config.
2. [`standards/six-yes.md`](../standards/six-yes.md) and [`standards/rubric.md`](../standards/rubric.md) — what gets graded.
3. [`standards/evidence-codes.md`](../standards/evidence-codes.md) — stable strings the grader returns.
4. [`prompts/`](../prompts/) — judge prompts loaded at runtime. Start with `shared-contract.md`.
5. [`rollout/grader-team-todos.md`](../rollout/grader-team-todos.md) — what the team is doing in parallel to prepare Jira.

## Non-negotiables

- Library-first architecture. CLI and webhook are thin wrappers. See `specs/grader-v0.2.md` §3.
- No print statements in core. Standard logger.
- No module-level state. Config passed in.
- Judge responses cached by `(issue_key, dimension_code, input_hash, model, prompt_version)`.
- Config hash logged with every run.

## Propose before implementing

- Language: Python (confirmed).
- Testing framework.
- Package layout.
- Secret management beyond `JIRA_API_TOKEN` env var.
- Jira client library choice (e.g., `atlassian-python-api`, custom, other).

Submit proposals as a discussion or PR comment before writing code.

## Config

See `config/grader.config.example.yaml`. Copy to `config/grader.config.yaml` (git-ignored) and fill in real values locally.

## Running (once implemented)

```
# Backfill over last 30 days
nolte-grader backfill --from 2026-03-20 --to 2026-04-19

# Spot-check specific issues
nolte-grader grade --keys BBIT-495,BBIT-496

# Override model for a single run
nolte-grader backfill --from 2026-03-20 --to 2026-04-19 --model claude-opus-4-7
```
