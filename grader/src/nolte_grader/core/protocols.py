"""Adapter Protocols. Core depends on these contracts; concrete adapters
are injected by the host.
"""
from __future__ import annotations

from typing import Any, Iterator, Protocol, runtime_checkable


@runtime_checkable
class JiraClientProtocol(Protocol):
    """Contract the grader expects from any Jira client implementation.

    All methods return raw Jira API v3 response shapes as dicts.
    Parsing into domain objects is the responsibility of the parsers layer.
    """

    def get_issue(self, key: str) -> dict[str, Any]:
        """Fetch a single issue with changelog and renderedFields expanded.

        Handles changelog truncation internally: when the expanded changelog
        is incomplete, falls back to the paginated /changelog endpoint.
        """
        ...

    def get_full_changelog(self, key: str) -> list[dict[str, Any]]:
        """Return all changelog history entries for an issue, handling pagination.

        Each entry is a Jira changelog history object
        ``{"id": ..., "author": {...}, "created": "...", "items": [...]}``.
        """
        ...

    def search_issues(self, jql: str, fields: list[str]) -> Iterator[dict[str, Any]]:
        """Yield all issues matching a JQL query, handling pagination transparently.

        Each yielded item is a Jira issue object ``{"key": ..., "fields": {...}}``.
        """
        ...

    def get_fields(self) -> list[dict[str, Any]]:
        """Return all field descriptors.

        Each item: ``{"id": "customfield_10014", "name": "Epic Link", ...}``.
        """
        ...

    def get_projects(self) -> list[dict[str, Any]]:
        """Return all accessible project descriptors.

        Each item: ``{"key": "PROJ", "name": "...", ...}``.
        """
        ...


@runtime_checkable
class JudgeClientProtocol(Protocol):
    """Contract the grader expects from any LLM judge.

    Concrete surface is wired in commit 8 (adapters/judge/).
    """


@runtime_checkable
class StorageProtocol(Protocol):
    """Contract for per-run output storage. Filesystem default in commit 11."""


@runtime_checkable
class SecretsProviderProtocol(Protocol):
    """Contract for credentials.

    Standalone mode uses :class:`EnvSecretsProvider` (wired in commit 2
    alongside the Jira client). Embedded hosts pass a custom provider.
    """

    def jira_token(self) -> str: ...

    def anthropic_key(self) -> str: ...


@runtime_checkable
class MetricsSinkProtocol(Protocol):
    """Contract for emitting metrics/telemetry. Hookable for observability."""

    def emit(self, name: str, value: float, tags: dict[str, str] | None = None) -> None: ...


# Re-exported ``Any`` keeps mypy strict-mode happy when signatures take a
# Protocol that has no declared methods yet.
__all__ = [
    "Any",
    "JiraClientProtocol",
    "JudgeClientProtocol",
    "MetricsSinkProtocol",
    "SecretsProviderProtocol",
    "StorageProtocol",
]
