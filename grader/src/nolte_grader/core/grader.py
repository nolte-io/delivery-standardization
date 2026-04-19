"""Grader — the library's public entry point. Spec §3.2.

Adapters are injected at construction so NolteOS can swap any of them.
Each has a default implementation for standalone use; see
``nolte_grader.adapters`` (wired in later commits).

Embeddability invariants (spec §3.4):
- No module-level state.
- Never reads os.environ, working directory, or config files.
- No print statements — structlog only.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from nolte_grader.core.config import GraderConfig
from nolte_grader.core.logging import get_logger
from nolte_grader.core.models import IssueGrade, RollupReport

if TYPE_CHECKING:
    from nolte_grader.core.protocols import (
        JiraClientProtocol,
        JudgeClientProtocol,
        MetricsSinkProtocol,
        SecretsProviderProtocol,
        StorageProtocol,
    )

log = get_logger(__name__)


class Grader:
    """Core grading engine.

    Instantiate with a ``GraderConfig``. Adapters are optional at
    construction; missing adapters raise ``NotImplementedError`` when
    the corresponding method is called.
    """

    def __init__(
        self,
        config: GraderConfig,
        *,
        jira_client: JiraClientProtocol | None = None,
        judge_client: JudgeClientProtocol | None = None,
        storage: StorageProtocol | None = None,
        secrets: SecretsProviderProtocol | None = None,
        metrics: MetricsSinkProtocol | None = None,
    ) -> None:
        self._config = config
        self._jira_client = jira_client
        self._judge_client = judge_client
        self._storage = storage
        self._secrets = secrets
        self._metrics = metrics

    @property
    def config(self) -> GraderConfig:
        return self._config

    def grade_issue(self, issue_key: str) -> IssueGrade:
        """Grade a single issue.

        Returns an ``IssueGrade`` for any graded outcome (including all-FAIL).
        Raises on unrecoverable adapter failure.

        Wired in: commit 5 (deterministic evaluators) and commit 9 (judge).
        """
        raise NotImplementedError(
            "grade_issue is wired in commits 5 (deterministic) and 9 (judge)."
        )

    def grade_issues(self, keys: list[str]) -> list[IssueGrade]:
        """Grade multiple issues. Default delegates to grade_issue; override for batching."""
        return [self.grade_issue(k) for k in keys]

    def grade_by_window(
        self,
        from_date: date,
        to_date: date,
        project_keys: list[str],
    ) -> list[IssueGrade]:
        """Grade all eligible issues in [from_date, to_date] across project_keys.

        Wired in: commit 2 (Jira adapter).
        """
        raise NotImplementedError(
            "grade_by_window requires the Jira adapter from commit 2."
        )

    def rollup(self, grades: list[IssueGrade]) -> RollupReport:
        """Aggregate per-issue grades into a run-level report.

        Wired in: commit 10 (aggregator + rollup).
        """
        raise NotImplementedError("rollup is wired in commit 10.")
