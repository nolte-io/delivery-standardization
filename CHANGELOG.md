# Changelog

All notable changes to the delivery standardization system. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — Initial scaffold

### Added
- Standards: 6-yes (aligned with nolte.io/delivery), rubric (25 dimensions), system rules, evidence codes.
- Prompts: shared contract + 8 judge prompts (Y1, Y2, Y3b, U9, U11, C2, D2, D3).
- Spec: grader design v0.2 (library-first architecture, NolteOS-embeddable).
- Rollout: team prep todos, Jira template, field checklist.
- Grader: scaffold and example config. Implementation deferred to Claude Code.

### Notes
- This commit establishes structure. No production code yet.
- First grader run will score against the baseline as the team rolls out template and field changes from `rollout/`.
