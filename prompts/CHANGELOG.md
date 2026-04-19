# Prompt Changelog

Prompt versions are part of the grader's judge cache key. Every change here invalidates cached judgments for the affected dimensions.

Format: every entry lists the prompt codes affected. The grader logs prompt versions per run for reproducibility.

## [0.1] — Initial prompt set

### Added
- `shared-contract.md` — contract injected into every judge call.
- `Y1.md`, `Y2.md`, `Y3b.md` — upstream 6-yes judge prompts.
- `U9.md` — Story defect classification.
- `U11.md` — issue-type classification; applies to Stories, Tasks, Bugs, and standalone Sub-tasks.
- `C2.md` — BDD quality at commitment.
- `D2.md` — design artifact necessity and presence.
- `D3.md` — violations surfaced.

### Notes
- No few-shot examples in v0.1. Calibration runs on real Nolte data will inform whether examples are warranted.
- D3 is the noisiest dimension by design. Expect to iterate after the first real run.
