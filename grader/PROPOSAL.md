# Nolte Delivery Grader — Implementation Proposal

**For review against:** `/specs/grader-v0.2.md` (v0.2, Phase 1).
**Author:** Claude Code.
**Status:** Approved 2026-04-19. Implementation in progress at commit 1.

### Approved decisions (2026-04-19)

All 15 open items resolved. Key decisions locked in:
- Python ≥3.12 via uv. Sync + `ThreadPoolExecutor`, concurrency 4.
- `run_id` format: `YYYYMMDDTHHMMSSZ` (UTC, filesystem-safe).
- `config_hash`: sha256 of canonical JSON (sorted keys, secrets stripped).
- U10 timeout → `IMPACT_LINK_UNREACHABLE` (flag on PASS); 4xx/5xx → `IMPACT_LINK_BROKEN` (FAIL).
- D7 WIP exception anchor phrase: `"WIP exception:"` in authorized-approver comment.
- Spec Approver (C3): read from changelog snapshot at transition, not current field value.
- Changelog pagination: expand first, fallback to `/changelog` paginated endpoint.
- ADF → plaintext with `## heading` re-emit; tables flattened. Revisit if judge quality bites.
- Prompt version: parsed from `**Version:** X.Y` line in each prompt file.
- `prompts_dir` configurable; embedded host can pass its own path.
- `NOT_APPLICABLE` is the fourth verdict state; excluded from fail-rate denominators.
- Rate limit: tenacity, exponential backoff, honor `Retry-After`, max 5 retries.
- Package: `nolte-grader` / `nolte_grader` / `nolte-grader` CLI entry point.
- Team size: config-driven (`teams.size_for(project)`). `TEAM_SIZE_EXCEPTION` fires when `size == 1`.

Standards PR (separate — not bundled): add `NOT_APPLICABLE`, `IMPACT_LINK_UNREACHABLE`, `IMPACT_LINK_BROKEN`
to `evidence-codes.md`; add WIP exception phrase to `system-rules.md` under Rule 4.
Wait for that PR to merge before commit 8 (judge adapter).

---

## 1. Package layout

Library-first. Core is pure and embeddable. Adapters sit behind Protocols. CLI is a thin wrapper.

```
grader/
├── pyproject.toml
├── README.md
├── PROPOSAL.md                       # this file
├── config/
│   └── grader.config.example.yaml
├── src/
│   └── nolte_grader/
│       ├── __init__.py               # public API re-exports
│       ├── core/
│       │   ├── grader.py             # Grader class — §3.2 contract
│       │   ├── models.py             # IssueGrade, RollupReport, DimensionResult (pydantic)
│       │   ├── config.py             # GraderConfig, loader, validator, config_hash()
│       │   ├── pipeline.py           # per-issue: fetch → parse → evaluate → judge → aggregate
│       │   ├── aggregator.py         # overall verdicts from per-dimension verdicts
│       │   ├── rollup.py             # system view + owner view
│       │   ├── errors.py             # typed exceptions
│       │   └── logging.py            # get_logger(name) factory; no globals
│       ├── dimensions/
│       │   ├── base.py               # Evaluator Protocol + DimensionContext dataclass
│       │   ├── registry.py           # code → evaluator mapping
│       │   ├── deterministic/        # Y3a, Y4, Y5, Y6, U7, U8, U10, U12, C1, C3, D1, D4–D10
│       │   └── judge/                # Y1, Y2, Y3b, C2, D2, D3, U9, U11 (D2 is composite D+J)
│       ├── parsers/
│       │   ├── adf.py                # Atlassian Doc Format → plaintext+heading structure
│       │   ├── description.py        # extract ## template sections
│       │   ├── changelog.py          # status transitions, field edits, timestamps
│       │   ├── subtasks.py
│       │   ├── links.py
│       │   └── wip.py                # daily concurrency reconstruction for D7
│       ├── adapters/
│       │   ├── jira/
│       │   │   ├── protocol.py       # JiraClient Protocol
│       │   │   ├── http_client.py    # httpx-backed default impl
│       │   │   └── field_discovery.py
│       │   ├── judge/
│       │   │   ├── protocol.py       # JudgeClient Protocol
│       │   │   ├── anthropic_client.py
│       │   │   ├── prompt_loader.py  # reads /prompts, extracts version
│       │   │   └── cache.py          # JudgeCache Protocol + FilesystemCache
│       │   ├── storage/              # StorageBackend Protocol + filesystem default
│       │   ├── telemetry/            # MetricsSink Protocol + stdout default
│       │   └── secrets/              # SecretsProvider Protocol + EnvProvider default
│       ├── formatters/
│       │   ├── json_formatter.py
│       │   ├── csv_formatter.py
│       │   └── markdown_formatter.py # rollup.md in Nolte voice
│       └── cli/
│           ├── __main__.py           # entry point
│           └── commands.py           # backfill, grade, rollup — thin argparse
└── tests/
    ├── unit/                         # parsers, evaluators, adapters, aggregator
    ├── integration/
    │   ├── fixtures/jira/            # sanitized issue + changelog snapshots
    │   └── test_end_to_end.py
    └── conftest.py
```

Honors §3.1 (three layers), §3.2 (public API), §3.3 (pluggable via Protocols), §3.4 (no globals, no working dir, no print, logger only, config passed in). CLI/webhook never reach past `nolte_grader` public exports.

---

## 2. Jira client library choice — custom `httpx` client

**Choice: custom client behind a `JiraClient` Protocol. (Approved 2026-04-19.)**

Jira's v3 REST surface for this spec is ~6 endpoints with predictable pagination, and spec §5 demands precise control over rate-limit backoff, changelog pagination fallback, custom-field discovery, and Phase 2 webhook registration. `atlassian-python-api` bundles Confluence/Bitbucket and lags on v3 specifics; `python-jira` wraps responses in heavy object models that fight the Protocol-based embed shape and make changelog snapshotting awkward. A focused httpx client keeps dependencies minimal, makes mocking with `respx` trivial, and lets NolteOS swap the whole adapter without reimplementing a library's surface area.

---

## 3. Testing framework

- **pytest** — unit and integration.
- **respx** — httpx request mocking for the Jira adapter.
- **syrupy** — snapshot tests for `rollup.md` and serialized `IssueGrade`.
- **hypothesis** — property tests for the ADF walker and changelog diffing (edit-detection edge cases).
- **pytest-cov** — coverage gating in CI.

No live network in any test. Integration tests use sanitized Jira JSON fixtures under `tests/integration/fixtures/`.

---

## 4. Dependencies (pinned)

Python `>=3.12`.

**Runtime:**
```
httpx==0.28.1
anthropic==0.42.0
pydantic==2.10.4
PyYAML==6.0.2
python-dateutil==2.9.0.post0
tenacity==9.0.0
click==8.1.8
structlog==24.4.0
```

**Dev:**
```
pytest==8.3.4
pytest-cov==6.0.0
respx==0.22.0
syrupy==4.8.0
hypothesis==6.123.2
mypy==1.14.1
ruff==0.8.4
```

`python-dotenv` is intentionally excluded. `.env` loading happens in the CLI entry point only, via `os.environ` + a local one-shot parser, so the core library remains free of env concerns.

---

## 5. Secret management

The core library **never** touches `os.environ`. It receives a `SecretsProvider`:

```python
class SecretsProvider(Protocol):
    def jira_token(self) -> str: ...
    def anthropic_key(self) -> str: ...
```

**Standalone mode** — `EnvSecretsProvider` reads `JIRA_API_TOKEN` and `ANTHROPIC_API_KEY` from the environment. The CLI's `__main__` optionally loads `.env` from the working directory before instantiating the provider, then hands it to the `Grader`. This is the only place env vars are touched.

**Embedded mode (NolteOS)** — NolteOS implements its own `SecretsProvider` (vault, KMS, injected config) and passes it to `Grader(config, secrets=...)`. No env read, no file read, no side effects in core.

Secrets never appear in `IssueGrade`, `RollupReport`, logs, or on-disk cache entries.

---

## 6. Caching implementation

**Location:**
- Standalone: `$XDG_CACHE_HOME/nolte-grader/judge/` (`~/.cache/nolte-grader/judge/` on macOS/Linux). Override via `judge.cache_dir` in config.
- Embedded: NolteOS injects a `JudgeCache` implementation; filesystem default is not used.

**Key (per shared-contract.md):**
```
sha256(issue_key | dimension_code | input_hash | model | prompt_version)
```
- `input_hash` — sha256 of canonical JSON of the rendered prompt variables (sorted keys, no whitespace).
- `prompt_version` — parsed from the `**Version:** X.Y` line in each prompt file at load time.
- `model` — effective model after `judge.model_by_dimension` override resolution.

**Storage format:** one JSON file per entry at `cache/<first-2-hex>/<full-hash>.json`:
```json
{
  "verdict": "PASS",
  "evidence_code": "BUSINESS_OBJECTIVE_IN_BUSINESS_TERMS",
  "rationale": "...",
  "quotes": ["..."],
  "recommended_type": null,
  "model": "claude-sonnet-4-6",
  "prompt_version": "0.1",
  "cached_at": "2026-04-19T20:30:00Z",
  "usage": {"input_tokens": 842, "output_tokens": 118}
}
```

**Invalidation:** natural — any change to issue content, dimension code, model, or prompt version produces a new key; stale entries are simply never hit. Explicit TTL is not set. `judge.cache_enabled: false` bypasses read and write. A future `nolte-grader cache prune --older-than` can reclaim space; not in Phase 1 scope.

Field-discovery cache is separate: `cache/jira/<instance-host>/fields.json`, 24-hour TTL, auto-refreshed when a referenced field name is not found.

---

## 7. Build order (maps to spec §12.1 Phase 1 items 1–10)

Sequencing prioritizes stable contracts first so every subsequent layer compiles against frozen types.

| Step | Deliverable | Spec item |
|---|---|---|
| 1 | `core/models.py`, `core/config.py` (loader + `config_hash()`), Protocols for all adapters, `logging.py`, exceptions | 1, 9 |
| 2 | `adapters/jira/http_client.py` + `field_discovery.py`, auth, pagination, `tenacity` backoff on 429/5xx honoring `Retry-After`, respx-mocked unit tests | 2 |
| 3 | `parsers/changelog.py` — status transitions, field-edit history, historical description snapshots for C2 and U7 | 3 |
| 4 | `parsers/adf.py` + `parsers/description.py` — ADF walker; extract `## Business Objective`, `## Observable Impact`, `## Acceptance Criteria`, `## Scenarios`, `## Risks`; handle rendered HTML fallback | 4 |
| 5 | `dimensions/deterministic/*` — all D-type dimensions (Y3a, Y4, Y5, Y6, U7, U8, U10, U12, C1, C3, D1, D4–D10) + unit tests | 5 |
| 6 | `adapters/judge/` — prompt loader with version extraction, filesystem cache, Anthropic client with retry, concurrency limiter; `dimensions/judge/*` evaluators; composite D+J for Y1/Y2/Y3/U9/D2 | 6 |
| 7 | `core/aggregator.py` + `core/rollup.py` — overall verdicts and system/owner views | 7 |
| 8 | `formatters/*` — JSON, CSV, Markdown (`rollup.md` in Nolte voice) | 8 (output side) |
| 9 | `cli/__main__.py` + `cli/commands.py` — `backfill`, `grade`, `--model` override, `.env` load, run-id stamping (CLI library: **click**) | 8 |
| 10 | Integration fixtures + `test_end_to_end.py` across all layers; snapshot tests on rollup markdown | 10 |

First milestone for human review: after step 5, a run against fixtures can produce partial `IssueGrade` records with deterministic dimensions only. Catches schema/field-discovery problems before burning API credits on step 6.

---

## 8. Questions and assumptions

Items the spec leaves ambiguous. Flagging so you can confirm or override before I start.

1. **Python ≥3.12.** Confirm — enables `Protocol` ergonomics and `StrEnum`.
2. **Sync, not async.** Per-issue work is naturally serial; parallelism for judge fan-out via `concurrent.futures.ThreadPoolExecutor(max_workers=judge.max_concurrency)`, default 4. Async raises complexity for marginal gain. Flag if you want async.
3. **`run_id` format** — `YYYYMMDDTHHMMSSZ` (UTC). Spec shows `"2026-04-19T2030"` — I'll normalize to a filesystem-safe sortable form. Confirm.
4. **`config_hash`** — sha256 over canonicalized JSON of the resolved config (merged defaults + file + CLI overrides), keys sorted, secrets stripped. Logged at run start and embedded in every `IssueGrade`.
5. **U10 HTTP HEAD timeout behavior** — spec says non-blocking with 5s timeout. On timeout/transient error I plan to emit `IMPACT_LINK_UNREACHABLE` as a *flag* on PASS rather than fail outright, reserving `IMPACT_LINK_BROKEN` for resolved 4xx/5xx. Confirm — this adds a new evidence code and would need entry in `evidence-codes.md`.
6. **D7 daily WIP boundary** — UTC midnight. Exception rule (§7.4 D7) requires scanning comments for "logged exception from Head of Product." Propose a regex-anchored check: a comment by an authorized approver (`authorized_approvers`) containing `WIP exception:` within the Story's In Implementation window. Confirm the exact anchor phrase.
7. **Spec Approver value source for C3** — field is a user picker. Read from the changelog snapshot at the `Done Specifying → Ready` transition, not the current value (which may have drifted). Confirm.
8. **Changelog pagination** — default request uses `?expand=changelog`. When `issue.changelog.total > len(issue.changelog.histories)`, fall back to `/rest/api/3/issue/{key}/changelog` with `startAt`/`maxResults=100`. Confirm.
9. **ADF → text strategy** — walk node tree; paragraphs emit with `\n\n`; headings re-emit as `## <text>` so `description.py` can find template sections uniformly across ADF input and rendered-HTML fallback. Tables and panels are flattened to plaintext with delimiters. Confirm, or specify a richer target (we lose table structure otherwise).
10. **Prompt version source of truth** — parse `**Version:** X.Y` from each prompt file's header. Bumping the line bumps the cache key. `CHANGELOG.md` is descriptive, not load-bearing.
11. **Embeddability — static prompts path** — core library accepts `prompts_dir: Path` via config (defaults to `../prompts` relative to the installed package). NolteOS can pass its own path. Prompt text never baked into Python source.
12. **`include_open` grading** — spec §5.4 defaults to Done-only. Open Stories skip downstream dimensions and any check that depends on the commitment timestamp, marking them as `NOT_APPLICABLE` rather than FAIL. Confirm this semantics and whether `NOT_APPLICABLE` needs an entry in `evidence-codes.md`.
13. **Rate limit policy** — tenacity with exponential backoff (0.5s → 30s), max 5 retries, honors `Retry-After` header. Non-retriable on 4xx except 408/425/429. Confirm.
14. **Package name** — PyPI distribution name `nolte-grader`, import name `nolte_grader`, CLI entry point `nolte-grader` (per `grader/README.md`). Confirm.
15. **Team-size detection for Y4 `TEAM_SIZE_EXCEPTION`** — spec says "if team size is 1." Propose: count distinct assignees across sub-tasks for the Story; if ≤1, flag exception. Alternative is project-level team size from config — cleaner but requires config entry. Confirm which.

---

## Non-negotiables I am honoring

- No globals, no module-level state in `nolte_grader.core`.
- No `print`; `structlog`-wrapped logger via `core.logging.get_logger`.
- Config object passed in everywhere; core never reads `os.environ`, `Path.cwd()`, or ambient config.
- Config hash stamped on every run and every `IssueGrade` record.
- Judge cache key exactly `(issue_key, dimension_code, input_hash, model, prompt_version)`.
- `/standards` and `/prompts` are read-only from the grader. No writes, no edits.
- No code outside `/grader/`.

Ready to implement on your approval. Flagging open items 1–15 especially — small decisions now prevent rework later.
