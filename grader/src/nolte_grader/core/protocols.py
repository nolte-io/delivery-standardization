"""Adapter Protocols. Core depends on these contracts; concrete adapters
are injected by the host. Method signatures are minimal in commit 1 and
flesh out as subsequent commits wire each adapter.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class JiraClientProtocol(Protocol):
    """Contract the grader expects from any Jira client.

    Concrete surface is wired in commit 2 (adapters/jira/http_client.py).
    """


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
