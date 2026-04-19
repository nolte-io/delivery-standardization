# Y3.b — Acceptance criteria in plain language

**Version:** 0.1
**Type:** Judge (J) — Y3.a is deterministic and handled separately
**Lane:** Upstream
**Owner:** Yanna

## Purpose

Confirm AC is a contract readable by a business stakeholder, not a technical restatement.

Note: Y3.a (AC written before commitment) is a deterministic changelog check and is not part of this prompt.

## Inputs

- `{{story_key}}`
- `{{acceptance_criteria_text}}` — text of the Story's `## Acceptance Criteria` section

## Evidence codes

| Code | Verdict |
|---|---|
| `AC_PLAIN_AND_NON_ENGINEER_VERIFIABLE` | PASS |
| `AC_TECHNICAL_RESTATEMENT` | FAIL |
| `AC_AMBIGUOUS_OR_UNVERIFIABLE` | FAIL |
| `AC_EMPTY_OR_PLACEHOLDER` | FAIL |

## User prompt

```
Dimension: Y3.b — AC plain language, non-engineer verifiable.

Passing AC describes observable behavior in plain business language. A non-engineer stakeholder reading it can, without additional context, determine whether the delivered work satisfies the criterion.

Failing AC: is a technical restatement (implementation steps, code-level detail, framework references); is ambiguous (uses "etc.," "and so on," open-ended lists); or is vague to the point of being unverifiable.

Note: the Y3.a timestamp check (AC written before commitment) is performed deterministically elsewhere. You are evaluating only language quality, not timing.

Story: {{story_key}}
Acceptance Criteria text:
---
{{acceptance_criteria_text}}
---

Grade Y3.b. Return JSON only.
```
