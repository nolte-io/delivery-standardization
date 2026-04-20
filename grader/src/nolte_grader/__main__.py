"""CLI entry point — run as: python -m nolte_grader

Usage:
  python -m nolte_grader backfill [--dry-run] [--from YYYY-MM-DD] [--to YYYY-MM-DD]

Backfill mode: grades all Done Stories across configured projects for the
given date window (defaults to last 30 days), writes grades.json + grades.csv
+ rollup.md to ./runs/{run_id}/.

--dry-run: auth probe + config validation + field discovery only. No fetch.

.env loading lives here and ONLY here — core library never reads os.environ
(spec §3.4 embeddability rules). EnvSecretsProvider still reads from
os.environ; this module is the boundary that populates it.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# .env loading — MUST happen before any nolte_grader imports
# ---------------------------------------------------------------------------

def _load_dotenv(path: Path) -> None:
    """Parse KEY=VALUE lines from path and set into os.environ.

    Rules:
    - Blank lines and lines starting with # are skipped.
    - Splits on first = only.
    - Strips surrounding single or double quotes from values.
    - Never overwrites a variable already present in os.environ.
    - Token values are never printed or logged.
    """
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, rest = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = rest.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key not in os.environ:
            os.environ[key] = value


_DOTENV = Path.cwd() / ".env"
if _DOTENV.exists():
    _load_dotenv(_DOTENV)
    print(f"[grader] loaded {_DOTENV}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Imports — after .env is populated
# ---------------------------------------------------------------------------

import yaml  # noqa: E402

from nolte_grader.adapters.jira import FieldDiscovery, JiraHttpClient  # noqa: E402
from nolte_grader.adapters.secrets.env import EnvSecretsProvider  # noqa: E402
from nolte_grader.core.aggregator import aggregate  # noqa: E402
from nolte_grader.core.config import GraderConfig  # noqa: E402
from nolte_grader.core.errors import JiraFieldNotFoundError  # noqa: E402
from nolte_grader.core.grader import Grader  # noqa: E402
from nolte_grader.core.models import IssueGrade, RollupWindow  # noqa: E402
from nolte_grader.formatters.excel import write_workbook  # noqa: E402
from nolte_grader.formatters.markdown import format_rollup  # noqa: E402


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="nolte_grader")
    sub = parser.add_subparsers(dest="command")

    bf = sub.add_parser("backfill", help="Grade all Done stories in a date window.")
    bf.add_argument("--dry-run", action="store_true",
                    help="Auth probe + field discovery only. No fetch or grading.")
    bf.add_argument("--from", dest="from_date", metavar="YYYY-MM-DD",
                    help="Window start (inclusive). Default: today-30d.")
    bf.add_argument("--to", dest="to_date", metavar="YYYY-MM-DD",
                    help="Window end (inclusive). Default: today.")

    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.command != "backfill":
        print("Usage: python -m nolte_grader backfill [--dry-run] [--from DATE] [--to DATE]",
              file=sys.stderr)
        sys.exit(1)

    # --- config ------------------------------------------------------------
    config_path = _resolve_config_path()
    print(f"[grader] config: {config_path}", file=sys.stderr)
    with config_path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    # --- secrets -----------------------------------------------------------
    secrets = EnvSecretsProvider()
    token = secrets.jira_token()  # raises ConfigError immediately if absent

    instance_url: str = raw["jira"]["instance_url"]
    email: str = raw["jira"]["service_account_email"]

    with JiraHttpClient(instance_url, email, token) as client:

        # --- auth probe ----------------------------------------------------
        print(f"[grader] probing {instance_url} ...", file=sys.stderr)
        me = client.whoami()
        print(
            f"[grader] auth OK — {me.get('displayName', '?')} "
            f"<{me.get('emailAddress', '?')}>",
            file=sys.stderr,
        )

        # --- field resolution (name → ID for fields-dict access) -----------
        print("[grader] resolving custom field IDs ...", file=sys.stderr)
        discovery = FieldDiscovery(client, instance_url=instance_url)
        cf_names: dict[str, str] = raw.get("custom_fields", {})
        cf_resolved = dict(cf_names)

        # These three are accessed via issue["fields"][field_id] → must be IDs.
        # spec_approver is matched by display name in changelog items → keep as name.
        for key in ("design_artifact_link", "production_release_reference", "impact_measurement_link"):
            if cf_names.get(key):
                try:
                    field_id = discovery.resolve(cf_names[key])
                    cf_resolved[key] = field_id
                    print(f"[grader]   '{cf_names[key]}' → {field_id}", file=sys.stderr)
                except JiraFieldNotFoundError:
                    print(
                        f"[grader]   WARNING: '{cf_names[key]}' not found in this instance — "
                        f"skipping (judge-only field, not accessed by deterministic pipeline)",
                        file=sys.stderr,
                    )

        raw["custom_fields"] = cf_resolved
        config = GraderConfig.model_validate(raw)
        print("[grader] config valid.", file=sys.stderr)

        # --- date window ---------------------------------------------------
        today = datetime.now(timezone.utc).date()
        from_date: date = (
            date.fromisoformat(args.from_date) if args.from_date
            else today - timedelta(days=30)
        )
        to_date: date = (
            date.fromisoformat(args.to_date) if args.to_date
            else today
        )
        print(f"[grader] window: {from_date} → {to_date}", file=sys.stderr)

        # --- JQL -----------------------------------------------------------
        include = config.projects.include
        exclude = set(config.projects.exclude)
        projects = [k for k in include if k not in exclude]
        proj_clause = ", ".join(projects)
        jql = (
            f'project in ({proj_clause}) AND issuetype in (Story, Task, Bug) AND status = Done '
            f'AND resolutiondate >= "{from_date}" AND resolutiondate <= "{to_date}"'
        )
        print(f"[grader] JQL: {jql}", file=sys.stderr)

        if args.dry_run:
            print("[grader] --dry-run complete. Auth OK, config valid, fields resolved.",
                  file=sys.stderr)
            print("DRY-RUN PASSED")
            return

        # --- fetch and grade -----------------------------------------------
        run_id = uuid.uuid4().hex[:8]
        run_start = datetime.now(timezone.utc)
        grader = Grader(config)
        grades: list[IssueGrade] = []
        errors: list[dict[str, str]] = []
        issue_count = 0

        for search_result in client.search_issues(jql, ["*all"]):
            issue_key: str = search_result.get("key", "?")
            issue_count += 1
            print(f"[grader]   [{issue_count}] grading {issue_key} ...",
                  end="\r", file=sys.stderr)

            try:
                # Re-fetch if changelog was truncated in search result
                cl = search_result.get("changelog", {})
                if cl.get("total", 0) > len(cl.get("histories", [])):
                    issue = client.get_issue(issue_key)
                else:
                    issue = search_result

                # Fetch subtasks with their own changelogs
                subtask_refs = (issue.get("fields") or {}).get("subtasks") or []
                subtasks: list[dict[str, Any]] = []
                for ref in subtask_refs:
                    st_key = ref.get("key", "")
                    if st_key:
                        subtasks.append(client.get_issue(st_key))

                grade = grader.grade_issue_from_data(issue, subtasks)
                grades.append(grade)

            except Exception as exc:
                errors.append({"issue_key": issue_key, "error": str(exc)})
                print(f"\n[grader]   ERROR {issue_key}: {exc}", file=sys.stderr)

        elapsed = (datetime.now(timezone.utc) - run_start).total_seconds()
        print(
            f"\n[grader] graded {len(grades)} issues, {len(errors)} errors "
            f"in {elapsed:.1f}s",
            file=sys.stderr,
        )

        if not grades:
            print("[grader] No issues graded. Exiting.", file=sys.stderr)
            sys.exit(0)

        # --- aggregate -----------------------------------------------------
        window = RollupWindow(from_date=from_date, to_date=to_date)
        report = aggregate(
            grades,
            run_id=run_id,
            window=window,
            cycle_time_threshold_days=config.thresholds.cycle_time_days,
        )

        # --- write outputs -------------------------------------------------
        run_dir = Path(config.output.directory.format(run_id=run_id))
        run_dir.mkdir(parents=True, exist_ok=True)

        json_path = run_dir / "grades.json"
        with json_path.open("w", encoding="utf-8") as jf:
            for g in grades:
                jf.write(g.model_dump_json() + "\n")

        csv_path = run_dir / "grades.csv"
        _write_csv(csv_path, grades)

        md_path = run_dir / "rollup.md"
        md = format_rollup(report)
        md_path.write_text(md, encoding="utf-8")

        xlsx_path = run_dir / "grades.xlsx"
        write_workbook(report, grades, instance_url, xlsx_path)

        if errors:
            err_path = run_dir / "errors.json"
            err_path.write_text(json.dumps(errors, indent=2), encoding="utf-8")
            print(f"[grader] errors written to {err_path}", file=sys.stderr)

        # --- final report --------------------------------------------------
        top = ", ".join(report.system.top_failing_dimensions) or "none"
        print("", file=sys.stderr)
        print(f"run_id:            {run_id}", file=sys.stderr)
        print(f"duration:          {elapsed:.1f}s", file=sys.stderr)
        print(f"issues_graded:     {len(grades)}", file=sys.stderr)
        print(f"errors:            {len(errors)}", file=sys.stderr)
        print(f"six_yes_pass_rate: {report.system.six_yes_pass_rate:.0%}", file=sys.stderr)
        print(f"top_failing:       {top}", file=sys.stderr)
        print(f"run_dir:           {run_dir.resolve()}", file=sys.stderr)
        print(f"rollup_md:         {md_path.resolve()}", file=sys.stderr)
        print(f"grades_xlsx:       {xlsx_path.resolve()}", file=sys.stderr)

        sys.stdout.write("\n" + "=" * 70 + "\n")
        sys.stdout.write(f"rollup.md — run {run_id}\n")
        sys.stdout.write("=" * 70 + "\n")
        sys.stdout.write(md)
        sys.stdout.write("=" * 70 + "\n")
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_config_path() -> Path:
    candidates = [
        Path.cwd() / "config" / "grader.config.local.yaml",
        Path.cwd() / "config" / "grader.config.yaml",
        Path.cwd() / "grader.config.local.yaml",
        Path.cwd() / "grader.config.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "No grader config found. Expected one of:\n"
        + "\n".join(f"  {p}" for p in candidates)
    )


def _write_csv(path: Path, grades: list[IssueGrade]) -> None:
    if not grades:
        return
    rows: list[dict[str, Any]] = []
    for g in grades:
        row: dict[str, Any] = {
            "issue_key": g.issue_key,
            "project_key": g.project_key,
            "issue_type": g.issue_type,
            "epic_key": g.epic_key or "",
            "title": g.title,
            "commitment_timestamp": (
                g.commitment_timestamp.isoformat() if g.commitment_timestamp else ""
            ),
            "done_timestamp": g.done_timestamp.isoformat() if g.done_timestamp else "",
            "cycle_time_days": "" if g.cycle_time_days is None else g.cycle_time_days,
            "six_yes_overall": g.six_yes_overall,
            "upstream_overall": g.upstream_overall,
            "downstream_overall": g.downstream_overall,
            "story_overall": g.story_overall,
            "spec_approver": g.spec_approver or "",
        }
        for code, result in sorted(g.dimensions.items()):
            row[f"dim_{code}"] = result.verdict
            row[f"ev_{code}"] = result.evidence_code
        rows.append(row)

    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
