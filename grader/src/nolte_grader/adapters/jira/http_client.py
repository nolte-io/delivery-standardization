"""Jira REST API v3 HTTP client — spec §5.1, §5.2.

Auth: HTTP Basic (email + API token).
Rate limiting: tenacity with exponential backoff; respects ``Retry-After`` header on 429.
Pagination: handled internally — callers receive complete data, not pages.
"""
from __future__ import annotations

import time
from collections.abc import Generator
from typing import Any

import httpx
from tenacity import RetryCallState, retry, retry_if_exception, stop_after_attempt

from nolte_grader.core.errors import JiraAuthError
from nolte_grader.core.logging import get_logger

log = get_logger(__name__)

_SEARCH_PAGE_SIZE = 100
_CHANGELOG_PAGE_SIZE = 100


def _is_retriable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (408, 425, 429, 500, 502, 503, 504)
    return isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError))


def _wait_with_retry_after(
    multiplier: float = 0.5,
    max_wait: float = 30.0,
) -> "type[_RetryAfterWait]":
    return _RetryAfterWait(multiplier=multiplier, max_wait=max_wait)


class _RetryAfterWait:
    """Tenacity-compatible wait callable.

    Honors the ``Retry-After`` response header on 429; falls back to
    exponential backoff otherwise.
    """

    def __init__(self, multiplier: float = 0.5, max_wait: float = 30.0) -> None:
        self._multiplier = multiplier
        self._max_wait = max_wait

    def __call__(self, retry_state: RetryCallState) -> float:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if (
            isinstance(exc, httpx.HTTPStatusError)
            and exc.response.status_code == 429
        ):
            retry_after = exc.response.headers.get("Retry-After")
            if retry_after is not None:
                try:
                    return min(float(retry_after), self._max_wait)
                except ValueError:
                    pass
        attempt = retry_state.attempt_number
        return min(self._multiplier * (2 ** (attempt - 1)), self._max_wait)


class JiraHttpClient:
    """Jira Cloud REST API v3 client.

    Constructed with credentials directly (not a ``SecretsProvider``) so the
    adapter is secrets-agnostic — the CLI or embedded host resolves secrets and
    passes them in.

    Use as a context manager to ensure the underlying ``httpx.Client`` is closed:

        with JiraHttpClient(url, email, token) as client:
            issue = client.get_issue("BBIT-42")
    """

    def __init__(
        self,
        base_url: str,
        email: str,
        token: str,
        *,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            auth=httpx.BasicAuth(email, token),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        _wait = _RetryAfterWait(multiplier=0.5, max_wait=30.0)
        self._retry = retry(
            retry=retry_if_exception(_is_retriable),
            stop=stop_after_attempt(5),
            wait=_wait,
            reraise=True,
        )

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}/rest/api/3{path}"

        @self._retry
        def _do() -> Any:
            resp = self._client.get(url, params=params)
            if resp.status_code == 401:
                raise JiraAuthError(
                    f"Jira authentication failed (401). Check service account "
                    f"email and JIRA_API_TOKEN. URL: {url}"
                )
            resp.raise_for_status()
            return resp.json()

        return _do()

    # ------------------------------------------------------------------
    # Public interface — matches JiraClientProtocol
    # ------------------------------------------------------------------

    def get_issue(self, key: str) -> dict[str, Any]:
        """Fetch issue with changelog and renderedFields expanded.

        When the embedded changelog is truncated (total > delivered), replaces
        the ``changelog.histories`` list with the complete paginated set.
        """
        issue: dict[str, Any] = self._get(
            f"/issue/{key}",
            params={"expand": "changelog,renderedFields"},
        )
        changelog = issue.get("changelog", {})
        total = changelog.get("total", 0)
        delivered = len(changelog.get("histories", []))
        if total > delivered:
            log.debug(
                "changelog truncated — fetching full via paginated endpoint",
                issue_key=key,
                total=total,
                delivered=delivered,
            )
            issue["changelog"]["histories"] = self.get_full_changelog(key)
        return issue

    def get_full_changelog(self, key: str) -> list[dict[str, Any]]:
        """Return all changelog history entries for an issue, handling pagination."""
        histories: list[dict[str, Any]] = []
        start_at = 0
        while True:
            page: dict[str, Any] = self._get(
                f"/issue/{key}/changelog",
                params={"startAt": start_at, "maxResults": _CHANGELOG_PAGE_SIZE},
            )
            values: list[dict[str, Any]] = page.get("values", [])
            histories.extend(values)
            total = page.get("total", 0)
            start_at += len(values)
            if start_at >= total or not values:
                break
        return histories

    def search_issues(self, jql: str, fields: list[str]) -> Generator[dict[str, Any], None, None]:
        """Yield all issues matching a JQL query, paging transparently."""
        start_at = 0
        while True:
            result: dict[str, Any] = self._get(
                "/search",
                params={
                    "jql": jql,
                    "fields": ",".join(fields),
                    "startAt": start_at,
                    "maxResults": _SEARCH_PAGE_SIZE,
                    "expand": "changelog,renderedFields",
                },
            )
            issues: list[dict[str, Any]] = result.get("issues", [])
            for issue in issues:
                yield issue
            total = result.get("total", 0)
            start_at += len(issues)
            if start_at >= total or not issues:
                break

    def get_fields(self) -> list[dict[str, Any]]:
        """Return all Jira field descriptors (standard + custom)."""
        result = self._get("/field")
        return result if isinstance(result, list) else []

    def get_projects(self) -> list[dict[str, Any]]:
        """Return all accessible project descriptors."""
        result = self._get("/project")
        return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> JiraHttpClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
