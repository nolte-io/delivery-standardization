# Nolte Delivery Grader — Design Spec

**Version:** 0.2 (pre-implementation)
**Owner:** Jeffrey Nolte
**Implementer:** Claude Code
**Status:** Ready for build

Changes from v0.1: Library-first architecture for NolteOS embedding. Model configurability explicit. U11 expanded to all issue types. Y6 simplified to deterministic retrospective check. C3 added for gate approver.

---

## 1. Purpose

An objective, repeatable scoring system for Nolte's delivery pipeline. Grades every Story against the published 6-yes (nolte.io/delivery) and Nolte's internal delivery rules. Exposes where the system leaks, upstream and downstream. Runs on command, on demand, and — in Phase 2 — in realtime at gate transitions.

The grader does not replace judgment at gates. It provides evidence. Gate decisions remain with Yanna (upstream) and Hector (downstream).

---

## 2. Scope

### In scope
- Stories and their lifecycle across the seven kanban stages.
- Sub-tasks as evidence for Story completeness.
- Story Defects as validation outputs.
- Bugs, Tasks, and standalone Sub-tasks for classification integrity (U11).
- Epics only as containers for business objective linkage.

### Out of scope
- Measuring actual business impact post-Done (monthly review, not per-Story grading).
- Replacing Yanna's or Hector's gate decisions.
- Grading work created before the template and field changes land.
- Grading Stories in projects not listed in the grader config.

---

## 3. Architecture — library-first, embeddable

The grader is designed to run standalone **and** to embed inside NolteOS. This shapes the architecture.

### 3.1 Three layers
- **Core library** — evaluation engine. Pure functions where possible. No I/O assumptions. Stateless per issue grade. This is what NolteOS embeds.
- **Adapters** — Jira client, storage backend, output formatters, judge client. Pluggable via interfaces so NolteOS can swap them.
- **Entry points** — CLI, webhook service, and (future) NolteOS module. Thin wrappers over the core library.

### 3.2 Public API contract
The core library exposes, at minimum:

```
Grader(config: GraderConfig)
  .grade_issue(issue_key: str) -> IssueGrade
  .grade_issues(keys: list[str]) -> list[IssueGrade]
  .grade_by_window(from_date: date, to_date: date, project_keys: list[str]) -> list[IssueGrade]
  .rollup(grades: list[IssueGrade]) -> RollupReport
```

`IssueGrade` and `RollupReport` are the output schemas defined in §9. They are stable contracts — changes require a version bump.

### 3.3 Pluggable adapters
- **Storage backend** — local filesystem (default for standalone), pluggable for NolteOS to use its own storage.
- **Output formatters** — JSON, CSV, Markdown built in; interface defined so custom formatters can be added.
- **Judge client** — Anthropic API default; interface defined so NolteOS could route through its own LLM layer if needed.
- **Metrics/telemetry** — stdout default; hookable for observability when embedded.

### 3.4 Non-negotiables for embeddability
- No globals. No module-level state.
- No reliance on working directory.
- All configuration passed in, never read from ambient environment inside the core library.
- Logging via standard logger; no print statements in the core.

---

## 4. Modes

One codebase, three modes. Each mode calls the same core library.

| Mode | Trigger | Phase | Use |
|---|---|---|---|
| Backfill | CLI with date range | 1 | Monthly rollups, historical runs, baseline establishment |
| On-demand | CLI with issue key(s) | 1 | Spot-check, Epic audit, pre-gate review |
| Realtime | Jira webhook on status transition | 2 | Grade at gate moment; flag before approval |

Phase 2 requires Phase 1 judge prompts to be validated against real data. Do not build realtime until Phase 1 has produced at least one 30-day rollup that Yanna and Hector have reviewed and accepted.

---

## 5. Inputs

### 5.1 Jira Cloud API

- **Instance:** Atlassian Cloud (specific instance URL provided in config).
- **Auth:** Service account email + API token (Basic auth header). Token stored in environment variable `JIRA_API_TOKEN` (standalone mode) or injected via adapter (embedded mode).
- **API version:** REST API v3.
- **Rate limits:** Respect Atlassian's published limits. Implement exponential backoff.

### 5.2 Required endpoints

| Endpoint | Purpose |
|---|---|
| `GET /rest/api/3/search` | JQL-driven issue list for a run |
| `GET /rest/api/3/issue/{key}?expand=changelog,renderedFields` | Full issue including history and rendered body |
| `GET /rest/api/3/issue/{key}/changelog` | Paginated changelog when expand is truncated |
| `GET /rest/api/3/project` | Project list for config validation |
| `GET /rest/api/3/field` | Discover custom field IDs by name on first run |
| `POST /rest/api/3/webhook` | Phase 2 realtime registration |

### 5.3 Field mappings

The grader discovers custom field IDs by name on first run and caches them. Mapping is by field name, not hard-coded ID, so the grader survives Jira admin changes.

| Logical field | Source |
|---|---|
| Issue type | Standard `issuetype.name` |
| Status | Standard `status.name` |
| Epic link | Standard parent / Epic Link |
| Assignee | Standard `assignee.accountId` |
| Created / Resolved | Standard timestamps |
| Description body | `renderedFields.description` (HTML) and `fields.description` (ADF) |
| Business Objective | Parsed from Epic description, `## Business Objective` section |
| Observable Impact | Parsed from Story description, `## Observable Impact` section |
| Acceptance Criteria | Parsed from Story description, `## Acceptance Criteria` section |
| Scenarios | Parsed from Story description, `## Scenarios` section |
| Risks | Parsed from Story description, `## Risks` section |
| Design Artifact Link | Custom field by name |
| Production Release Reference | Custom field by name |
| Impact Measurement Link | Custom field by name |
| Spec Approver | Custom field by name (user picker) — required at Done Specifying → Ready transition |
| Sub-tasks | Standard `subtasks[]` |
| Story Defects | Linked issues of type `Story defect` |
| Changelog | Standard `changelog.histories[]` |

Issues with missing template sections fail the relevant dimension with evidence code `MISSING_SECTION`. Not an error — a graded failure.

### 5.4 Run filters

Grader accepts:
- `--projects` list of Jira project keys (defaults to config file value)
- `--from` and `--to` ISO dates (for backfill)
- `--keys` list of issue keys (for on-demand)
- `--include-canceled` flag (default false)
- `--include-open` flag (default false — by default grade only issues that have reached Done)
- `--model` override (see §8)

---

## 6. Commitment point

**Commitment point = status transition `Ready` → `In Implementation`.**
Timestamp pulled from changelog. This timestamp drives Y3, Y6, U7, C2, D1, D7, D8.

If a Story never entered `In Implementation`, it cannot be graded for downstream dimensions. Upstream dimensions still grade.

The **Spec Approver** (C3) is recorded at the prior transition: `Done Specifying` → `Ready`. The approver signoff is the pre-commit reference snapshot used by U7.

---

## 7. Evaluation dimensions

Each dimension has:
- **Code** (Y/U/C/D + number)
- **Lane** (upstream / downstream / system)
- **Owner** (who the score informs)
- **Gate** (when the evidence should exist)
- **Evidence type** — D (deterministic), J (Claude judge), A (audit-only)
- **Pass / fail criteria**
- **Data source**

### 7.1 Upstream 6-yes (matches nolte.io/delivery)

**Y1 — Business objective nameable**
- Lane: Upstream · Owner: Yanna · Gate: Done Specifying · Type: **D + J**
- Pass: Story has Epic Link; Epic description contains non-empty `## Business Objective` section; judge confirms objective is stated in business terms (revenue, activation, retention, risk reduction, cost, time savings), not technical terms.
- Fail: No Epic link; Epic missing section; judge classifies as technical objective.
- Source: Story `parent` field → Epic description parse → judge call.

**Y2 — Observable business difference describable**
- Lane: Upstream · Owner: Yanna · Gate: Done Specifying · Type: **D + J**
- Pass: Story has non-empty `## Observable Impact` section; judge confirms it contains a metric, a threshold, and either a measurement location or an observability mechanism.
- Fail: Section missing or present but vague.
- Source: Story description parse → judge call.

**Y3 — AC in plain language, pre-implementation**
- Lane: Upstream · Owner: Yanna · Gate: Done Specifying · Type: **D + J**
- Y3.a (D): `## Acceptance Criteria` section populated before commitment timestamp. Determined by changelog analysis on description edits.
- Y3.b (J): Judge confirms AC is plain language, verifiable by a non-engineer, not post-hoc technical restatement.
- Pass: Both.
- Fail: Either.
- Source: Description changelog + judge call.

**Y4 — Non-builder can validate**
- Lane: Upstream · Owner: Yanna · Gate: In Validation · Type: **D**
- Pass: Account that executed the `In Validation` → `Done` transition is not the same account that held any In Implementation sub-task on the Story.
- Fail: Validator is also the builder. Small-team exception: if team size is 1, flag as `TEAM_SIZE_EXCEPTION` rather than fail.
- Source: Changelog + sub-task assignees.

**Y5 — Live in production when called Done**
- Lane: Upstream · Owner: Yanna · Gate: Done · Type: **D**
- Pass: Production Release Reference field populated at moment of Done transition.
- Fail: Empty, staging-only URL, or populated after Done.
- Source: Custom field + changelog.

**Y6 — Completable in one cycle (retrospective)**
- Lane: Upstream · Owner: Yanna · Gate: Retrospective · Type: **D**
- Pass: Actual cycle time from `Ready` → `Done Implementing` ≤ config threshold (default 7 calendar days).
- Fail: Exceeds threshold.
- Source: Changelog.
- Note: The forward-looking "can this fit one cycle?" confirmation at commit is captured by C3 (approver recorded). Y6 checks whether the prediction held.

### 7.2 Upstream rubric (beyond 6-yes)

**U7 — No scope evolution after commitment**
- Lane: Upstream · Owner: Yanna · Gate: In Implementation onward · Type: **D**
- Pass: No edits to `## Acceptance Criteria` or `## Scenarios` sections after commitment timestamp.
- Fail: Any post-commitment edit. Whitespace-only edits ignored.
- Source: Description changelog diff.

**U8 — Validation outputs are Acceptance or Story Defect only**
- Lane: Upstream · Owner: Yanna · Gate: In Validation · Type: **D**
- Pass: Only Story Defect issues or the Story's own acceptance transition are created during In Validation.
- Fail: New Stories, Tasks, or Bugs created under this Story while in Validation.
- Source: Linked issue creation timestamps + Story status timeline.

**U9 — Story defects classified**
- Lane: Upstream · Owner: Yanna · Gate: Validation · Type: **D + J**
- Pass: Each Story Defect has a classification (functional, design, UX, regulatory, performance). Judge determines if the defect maps to an original AC scenario or is a scope-evolution defect.
- Fail: Unclassified defects. Scope-evolution defects do not fail U9 — they are reported separately in the rollup.
- Rollup reports: defects-against-scenario count vs. scope-evolution defect count. Scope-evolution dominance is a spec-quality signal.
- Source: Story Defect field + judge.

**U10 — Impact measurement infrastructure present at Done**
- Lane: Upstream · Owner: Yanna · Gate: Done · Type: **D**
- Pass: Impact Measurement Link field populated at Done with a resolvable URL.
- Fail: Empty or link-broken.
- Source: Custom field + HTTP HEAD check (non-blocking; timeout 5s).

**U11 — Correct issue-type classification (all types)**
- Lane: System · Owner: Yanna + Hector · Gate: At creation · Type: **J**
- Grades every issue in the run window, not only Stories. Applies to Stories, Tasks, Bugs, and standalone Sub-tasks.
- Pass: Judge reads title, description, AC if present, and classifies work type. Classification matches the Jira Issue Type.
- Fail: Mismatch. Judge returns the recommended correct type and rationale.
- Rollup: reports misclassification count per type pair (e.g., "Task → should be Story: N") and the resulting Task:Story ratio correction.
- Source: Full issue text → judge.

**U12 — Risks surfaced**
- Lane: Upstream · Owner: Yanna · Gate: Done Specifying · Type: **D**
- Pass: `## Risks` section populated, even if contents are "None identified."
- Fail: Section missing, blank, or placeholder text.
- Source: Description parse.

### 7.3 Commitment point checks

**C1 — Commitment transition exists**
- Lane: System · Type: **D**
- Pass: Story has a `Ready` → `In Implementation` transition in changelog.
- Fail: No such transition (Story that skipped stages or was moved directly).
- Source: Changelog.

**C2 — BDD quality at commitment**
- Lane: Upstream · Owner: Yanna · Gate: Commitment · Type: **J**
- Pass: Judge confirms that at commitment time, `## Scenarios` contains at least one Given/When/Then covering the highest-value rule(s) in the AC.
- Fail: Scenarios missing, placeholder, or cover only trivial edge cases while leaving the core rule uncovered.
- Source: Description at commitment timestamp (historical version via changelog) → judge.

**C3 — Gate approver recorded**
- Lane: System · Owner: Hector (commitment gate) · Gate: Done Specifying → Ready · Type: **D**
- Pass: Spec Approver field populated at the transition to Ready. Approver is in the authorized approvers list for the project (config §10). Approver is not the Story builder (checked against sub-task assignees and reporter).
- Fail: Field empty, approver not authorized, or approver is also builder.
- Authorized approver roles (configurable per engagement): Head of Engineering (Hector) and delegates; Nolte POC when Nolte is the trusted Product Owner; client POC when ownership sits with the client.
- Source: Custom field + config + changelog.

### 7.4 Downstream dimensions

**D1 — Sub-tasks created after Story review**
- Lane: Downstream · Owner: Hector · Gate: In Implementation start · Type: **D**
- Pass: Sub-task creation timestamps ≥ commitment timestamp.
- Fail: Sub-tasks created before commitment (planning artifact) or Story has no sub-tasks (unless judge classifies as trivial Story).
- Source: Sub-task creation times vs. commitment timestamp.

**D2 — Design artifact for non-trivial work**
- Lane: Downstream · Owner: Hector · Gate: In Implementation · Type: **J + D**
- Judge determines if Story complexity warrants a design artifact (architecture, frontend, UI, etc.).
- Pass: Simple Story OR Design Artifact Link populated for complex Story.
- Fail: Complex Story with no design artifact.
- Source: Story content → judge → field check.

**D3 — Violations surfaced, not absorbed**
- Lane: Downstream · Owner: Hector · Gate: In Implementation · Type: **J**
- Pass: If implementation hit deviation from agreed scenarios, a comment or sub-task exists raising it. Judge reads comments and commits history text.
- Fail: Judge detects post-hoc language suggesting silent deviation without a surfaced flag.
- Source: Comments + sub-task descriptions → judge.

**D4 — All sub-tasks closed at Done Implementing**
- Lane: Downstream · Owner: Hector · Gate: Done Implementing · Type: **D**
- Pass: All sub-tasks at status `Done` before Story transitions to `Done Implementing`.
- Fail: Any open sub-task at transition time.
- Source: Sub-task status snapshot via changelog.

**D5 — Tests passing with evidence**
- Lane: Downstream · Owner: Hector · Gate: Done Implementing · Type: **D**
- Pass: Story has a sub-task titled `Tests — [Story key]` or matching convention; sub-task is closed; sub-task description contains a CI run link.
- Fail: No test sub-task, test sub-task open, or no CI link present.
- Source: Sub-tasks + description parse.
- Phase 2 upgrade: CI webhook writes status to a dedicated field.

**D6 — Operationally shippable**
- Lane: Downstream · Owner: Hector · Gate: Done Implementing · Type: **D**
- Pass: Production Release Reference field populated with a deploy URL, release tag, or merged PR link at Done Implementing (same field as Y5 — two uses).
- Fail: Empty or local-only reference.
- Source: Custom field.

**D7 — WIP respected**
- Lane: System · Owner: Hector · Gate: In Implementation · Type: **D**
- Pass: For each day the Story was in `In Implementation`, total concurrent Stories in `In Implementation` ≤ WIP limit in config. Applied per assignee and system-wide.
- Fail: Any day over limit without a logged exception comment from Head of Product.
- Source: Changelog reconstruction of daily WIP state.

**D8 — Cycle time within norm**
- Lane: System · Owner: Hector · Type: **D**
- Pass: `Ready` → `Done Implementing` elapsed time ≤ config threshold (default 7 calendar days).
- Fail: Exceeds threshold without a logged blocker comment.
- Source: Changelog.

**D9 — Story Defect rate**
- Lane: Downstream · Owner: Hector · Gate: Validation · Type: **D**
- Per-Story: 0 defects = pass. 1+ defects = fail for that Story. Scope-evolution defects (per U9) are excluded from this count.
- Source: Linked Story Defects + U9 classification.

**D10 — No backward transitions**
- Lane: System · Owner: Hector + Yanna · Type: **D**
- Pass: Changelog contains only forward transitions per the kanban order.
- Fail: Any backward transition.
- Source: Changelog.

---

## 8. Claude-judge contract

Judge dimensions are marked **J** above. Each is a single API call per issue per dimension.

### 8.1 Model — configurable
- **Config default:** set in `grader.config.yaml` under `judge.model`.
- **CLI override:** `--model` flag at invocation time.
- **Per-dimension override (optional):** config can specify `judge.model_by_dimension: {U11: "claude-opus-4-7"}` to upgrade specific dimensions where accuracy matters more than cost.
- **Recommended default:** Claude Sonnet 4.6 for bulk grading. Claude Opus 4.7 for targeted re-grades when Sonnet disagrees with human review.
- **Temperature:** 0 (configurable).
- **Max tokens:** 1000 output (configurable).

### 8.2 Input shape
Each judge call receives:
- The dimension code and Nolte's definition of pass/fail (injected from this spec).
- The issue identifier.
- Only the text relevant to the dimension (title + relevant body section + any linked content). Do not pass the full issue to every judge call — that's noise.
- Any auxiliary context required (e.g., for Y1, the Epic objective text; for U11, the full description and AC).

### 8.3 Output shape — strict JSON
```json
{
  "verdict": "PASS" | "FAIL" | "INSUFFICIENT_EVIDENCE",
  "evidence_code": "string",
  "rationale": "one sentence, ≤30 words, concrete",
  "quotes": ["at most 2 short quotes from the source supporting the verdict"],
  "recommended_type": "Story" | "Task" | "Bug" | "Sub-task" | null
}
```

`recommended_type` is populated only for U11 calls; null for all other dimensions.

### 8.4 Guardrails
- On ambiguous cases: return `INSUFFICIENT_EVIDENCE`, which rolls up as fail with a distinct flag.
- No hedging in rationale ("it depends", "somewhat", "partially").
- Judge prompts are written in Nolte voice: declarative, concrete, every word load-bearing. Prompts live in a separate file (`judge_prompts.md`) and are versioned.
- Judge prompts are artifacts of the Nolte × Claude project. Changes require explicit review before re-run.

### 8.5 Retries and idempotency
- Retry on transient API errors (max 3, exponential backoff).
- Cache judge responses keyed by `(issue_key, dimension_code, input_hash, model)` so re-runs on unchanged issues are free.
- Model change invalidates cache for that entry.

---

## 9. Output schema

### 9.1 Per-issue record (JSON)

```json
{
  "issue_key": "BBIT-495",
  "issue_type": "Story",
  "project_key": "BBIT",
  "epic_key": "BBIT-100",
  "title": "...",
  "run_timestamp": "2026-04-19T20:30:00Z",
  "commitment_timestamp": "2026-03-15T10:00:00Z",
  "done_timestamp": "2026-03-22T14:00:00Z",
  "cycle_time_days": 7.2,
  "upstream_owner": "Yanna Lopes",
  "downstream_owner": "Dulce Hernandez Cruz",
  "validator": "Yanna Lopes",
  "spec_approver": "Hector Sanchez",
  "dimensions": {
    "Y1": {"verdict": "PASS", "evidence_code": "EPIC_OBJECTIVE_PRESENT", "rationale": "..."},
    "Y2": {"verdict": "FAIL", "evidence_code": "MISSING_SECTION", "rationale": "..."},
    "U11": {"verdict": "FAIL", "evidence_code": "TYPE_MISMATCH", "rationale": "...", "recommended_type": "Story"}
  },
  "six_yes_overall": "FAIL",
  "upstream_overall": "FAIL",
  "downstream_overall": "PASS",
  "story_overall": "FAIL",
  "flags": ["TEAM_SIZE_EXCEPTION"],
  "config_hash": "sha256:..."
}
```

### 9.2 Rollup (per run, two views)

**System view** — fail rate per dimension across all graded issues.
```json
{
  "run_id": "2026-04-19T2030",
  "window": {"from": "2026-03-20", "to": "2026-04-19"},
  "story_count": 87,
  "issue_count_all_types": 134,
  "six_yes_pass_rate": 0.23,
  "dimension_fail_rates": {"Y1": 0.12, "Y2": 0.73},
  "top_failing_dimensions": ["Y2", "U11", "D5"],
  "classification_corrections": {
    "Task_to_Story": 18,
    "Story_to_Bug": 3,
    "corrected_task_story_ratio": "0.9:1"
  },
  "repeat_offenders_by_epic": []
}
```

**Owner view** — fail rate per dimension grouped by owner role.
```json
{
  "upstream": {
    "Yanna Lopes": {"stories": 87, "top_fails": ["Y2", "U12", "C2"]}
  },
  "downstream": {
    "Hector Sanchez": {"stories": 87, "top_fails": ["D5", "D2"]},
    "by_engineer": {
      "Dulce Hernandez Cruz": {"stories": 14, "top_fails": ["D5", "D1"]}
    }
  },
  "approvers": {
    "Hector Sanchez": {"approved": 62, "downstream_pass_rate_of_approved": 0.71}
  }
}
```

### 9.3 Human-readable outputs
Per run, the grader emits:
- `rollup.md` — one-page summary in Nolte voice. System view first, owner view second, three specific recommendations last.
- `stories.csv` — one row per issue, columns = dimensions. For spreadsheet analysis.
- `stories.json` — full per-issue records (§9.1).

---

## 10. Config file

`grader.config.yaml`:

```yaml
jira:
  instance_url: "https://nolte.atlassian.net"
  service_account_email: "grader@nolte.io"
  # token via env: JIRA_API_TOKEN (standalone) or injected adapter (embedded)

projects:
  include: ["BBIT", "NOLTE"]
  exclude: []

authorized_approvers:
  default:
    - accountId: "hector-id"
      role: "head_of_engineering"
    - accountId: "yanna-id"
      role: "head_of_product_delegate"
  per_project:
    BBIT:
      - accountId: "client-poc-id"
        role: "client_poc"

dimensions:
  enabled: ["Y1","Y2","Y3","Y4","Y5","Y6","U7","U8","U9","U10","U11","U12","C1","C2","C3","D1","D2","D3","D4","D5","D6","D7","D8","D9","D10"]

thresholds:
  cycle_time_days: 7
  wip_limits:
    in_specification: 8
    ready: 5
    in_implementation_per_engineer: 3
    in_implementation_system: 15
    done_implementing: 5
    in_validation: 6

conventions:
  template_sections:
    - "## Business Objective"
    - "## Observable Impact"
    - "## Acceptance Criteria"
    - "## Scenarios"
    - "## Risks"
  test_subtask_title_pattern: "^Tests — [A-Z]+-\\d+$"

judge:
  model: "claude-sonnet-4-6"
  temperature: 0
  max_tokens: 1000
  cache_enabled: true
  model_by_dimension: {}

output:
  directory: "./runs/{run_id}/"
  formats: ["json", "csv", "md"]
```

Config is version-controlled. Changes require a commit. Grader logs the config hash with every run so historical results are reproducible. When embedded in NolteOS, config can be passed programmatically instead of read from disk — the core library accepts either.

---

## 11. Non-goals

The grader does not:
- Measure actual business impact (monthly review, not per-Story).
- Grade work in projects absent from config.
- Auto-promote work across gates.
- Replace Yanna's or Hector's judgment.
- Fix Jira hygiene — it grades against it.
- Flatter the results. Failures stay loud.

---

## 12. Implementation sequencing

### Phase 1 (first build)
1. Core library scaffold with `Grader` class and stable API contract.
2. Jira client adapter with auth, pagination, rate limiting, custom-field discovery.
3. Changelog parser (status transitions, field edits, timestamps).
4. Description section parser (extract template sections, handle ADF and HTML).
5. Deterministic evaluators for all D-typed dimensions.
6. Judge runner: one call per J-typed dimension, JSON-strict parsing, cache, model-configurable.
7. Rollup generator (system view, owner view, markdown summary).
8. CLI entry point — thin wrapper around core library.
9. Config loader and validator.
10. Tests: unit tests on parsers and evaluators; integration test against a sanitized fixture of Jira data.

### Phase 2 (after Phase 1 produces an accepted 30-day rollup)
11. Webhook receiver for Jira status transitions — thin wrapper around core library.
12. Realtime single-issue grading with low-latency output.
13. Optional: CI integration for D5 test evidence.
14. Optional: dedicated Jira field for approver-confirmed one-cycle fit (further hardens Y6 and C3).

### Phase 3 (NolteOS embedding)
15. NolteOS adapter package — wraps core library, maps its storage and telemetry to NolteOS.
16. Single-issue grade endpoint in NolteOS API.
17. Dashboard integration.

### What success looks like at end of Phase 1
- A single command grades last 30 days across configured projects.
- Produces `rollup.md`, `stories.csv`, `stories.json` in a dated run folder.
- Yanna reads `rollup.md` and can name three system-level problems without reading the CSV.
- Hector reads `rollup.md` and can name three engineer-specific coaching conversations.
- Jeffrey reads `rollup.md` and can name whether the system is getting more predictable.

If those three things don't happen, the grader failed its own 6-yes.

---

## 13. Open items for Claude Code

Intentionally left for the implementer to propose:
- Language choice (Python or TypeScript — both viable; Python likely faster for judge orchestration, TypeScript better if NolteOS is TS-based).
- Testing framework.
- Package layout consistent with library-first architecture.
- Deployment target for Phase 2 webhook receiver.
- Secret management approach beyond `JIRA_API_TOKEN` env var.
- NolteOS adapter package shape (Phase 3 — likely deferred).

Claude Code proposes, Jeffrey approves. The spec above does not prescribe these.
