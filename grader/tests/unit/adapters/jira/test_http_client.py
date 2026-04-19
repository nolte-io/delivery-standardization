"""Tests for adapters/jira/http_client.py — all network calls mocked via respx."""
from __future__ import annotations

import httpx
import pytest
import respx

from nolte_grader.adapters.jira.http_client import JiraHttpClient
from nolte_grader.core.errors import JiraAuthError

BASE = "https://example.atlassian.net"


def _client() -> JiraHttpClient:
    return JiraHttpClient(BASE, "user@example.com", "token123")


# ---------------------------------------------------------------------------
# get_issue
# ---------------------------------------------------------------------------


class TestGetIssue:
    @respx.mock
    def test_returns_issue_dict(self) -> None:
        respx.get(f"{BASE}/rest/api/3/issue/TEST-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "key": "TEST-1",
                    "fields": {"summary": "Example"},
                    "changelog": {"total": 1, "histories": [{"id": "1"}]},
                    "renderedFields": {},
                },
            )
        )
        with _client() as c:
            issue = c.get_issue("TEST-1")
        assert issue["key"] == "TEST-1"

    @respx.mock
    def test_expand_param_sent(self) -> None:
        route = respx.get(f"{BASE}/rest/api/3/issue/TEST-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "key": "TEST-1",
                    "fields": {},
                    "changelog": {"total": 0, "histories": []},
                    "renderedFields": {},
                },
            )
        )
        with _client() as c:
            c.get_issue("TEST-1")
        assert "expand" in route.calls.last.request.url.params

    @respx.mock
    def test_fetches_full_changelog_on_truncation(self) -> None:
        respx.get(f"{BASE}/rest/api/3/issue/TEST-2").mock(
            return_value=httpx.Response(
                200,
                json={
                    "key": "TEST-2",
                    "fields": {},
                    "changelog": {
                        "total": 3,
                        "histories": [{"id": "1"}],
                    },
                    "renderedFields": {},
                },
            )
        )
        respx.get(f"{BASE}/rest/api/3/issue/TEST-2/changelog").mock(
            return_value=httpx.Response(
                200,
                json={
                    "values": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
                    "total": 3,
                },
            )
        )
        with _client() as c:
            issue = c.get_issue("TEST-2")
        assert len(issue["changelog"]["histories"]) == 3

    @respx.mock
    def test_raises_jira_auth_error_on_401(self) -> None:
        respx.get(f"{BASE}/rest/api/3/issue/TEST-1").mock(
            return_value=httpx.Response(401, json={"errorMessages": ["Unauthorized"]})
        )
        with pytest.raises(JiraAuthError):
            with _client() as c:
                c.get_issue("TEST-1")


# ---------------------------------------------------------------------------
# get_full_changelog
# ---------------------------------------------------------------------------


class TestGetFullChangelog:
    @respx.mock
    def test_single_page(self) -> None:
        respx.get(f"{BASE}/rest/api/3/issue/TEST-1/changelog").mock(
            return_value=httpx.Response(
                200,
                json={"values": [{"id": "1"}, {"id": "2"}], "total": 2},
            )
        )
        with _client() as c:
            histories = c.get_full_changelog("TEST-1")
        assert len(histories) == 2

    @respx.mock
    def test_paginates_to_completion(self) -> None:
        call_count = 0

        def side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            params = dict(request.url.params)
            start = int(params.get("startAt", 0))
            call_count += 1
            if start == 0:
                return httpx.Response(
                    200,
                    json={"values": [{"id": str(i)} for i in range(100)], "total": 150},
                )
            return httpx.Response(
                200,
                json={"values": [{"id": str(i)} for i in range(100, 150)], "total": 150},
            )

        respx.get(f"{BASE}/rest/api/3/issue/TEST-1/changelog").mock(side_effect=side_effect)
        with _client() as c:
            histories = c.get_full_changelog("TEST-1")
        assert len(histories) == 150
        assert call_count == 2


# ---------------------------------------------------------------------------
# search_issues
# ---------------------------------------------------------------------------


class TestSearchIssues:
    @respx.mock
    def test_yields_all_issues_single_page(self) -> None:
        respx.get(f"{BASE}/rest/api/3/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "issues": [{"key": "TEST-1"}, {"key": "TEST-2"}],
                    "total": 2,
                    "startAt": 0,
                },
            )
        )
        with _client() as c:
            results = list(c.search_issues("project = TEST", ["summary", "status"]))
        assert [r["key"] for r in results] == ["TEST-1", "TEST-2"]

    @respx.mock
    def test_paginates_across_multiple_pages(self) -> None:
        def side_effect(request: httpx.Request) -> httpx.Response:
            start = int(dict(request.url.params).get("startAt", 0))
            if start == 0:
                return httpx.Response(
                    200,
                    json={
                        "issues": [{"key": f"TEST-{i}"} for i in range(100)],
                        "total": 120,
                        "startAt": 0,
                    },
                )
            return httpx.Response(
                200,
                json={
                    "issues": [{"key": f"TEST-{i}"} for i in range(100, 120)],
                    "total": 120,
                    "startAt": 100,
                },
            )

        respx.get(f"{BASE}/rest/api/3/search").mock(side_effect=side_effect)
        with _client() as c:
            results = list(c.search_issues("project = TEST", ["summary"]))
        assert len(results) == 120

    @respx.mock
    def test_empty_result_set(self) -> None:
        respx.get(f"{BASE}/rest/api/3/search").mock(
            return_value=httpx.Response(
                200,
                json={"issues": [], "total": 0, "startAt": 0},
            )
        )
        with _client() as c:
            results = list(c.search_issues("project = EMPTY", ["summary"]))
        assert results == []


# ---------------------------------------------------------------------------
# get_fields / get_projects
# ---------------------------------------------------------------------------


class TestGetFields:
    @respx.mock
    def test_returns_list(self) -> None:
        respx.get(f"{BASE}/rest/api/3/field").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"id": "summary", "name": "Summary"},
                    {"id": "customfield_10014", "name": "Epic Link"},
                ],
            )
        )
        with _client() as c:
            fields = c.get_fields()
        assert len(fields) == 2
        assert fields[1]["name"] == "Epic Link"


class TestGetProjects:
    @respx.mock
    def test_returns_list(self) -> None:
        respx.get(f"{BASE}/rest/api/3/project").mock(
            return_value=httpx.Response(
                200,
                json=[{"key": "TEST", "name": "Test Project"}],
            )
        )
        with _client() as c:
            projects = c.get_projects()
        assert projects[0]["key"] == "TEST"


# ---------------------------------------------------------------------------
# Context manager and retry
# ---------------------------------------------------------------------------


class TestClientLifecycle:
    @respx.mock
    def test_context_manager_closes_client(self) -> None:
        respx.get(f"{BASE}/rest/api/3/field").mock(
            return_value=httpx.Response(200, json=[])
        )
        with JiraHttpClient(BASE, "u", "t") as c:
            c.get_fields()
        assert c._client.is_closed

    @respx.mock
    def test_retries_on_500(self) -> None:
        attempt = 0

        def side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                return httpx.Response(500, json={"error": "Server Error"})
            return httpx.Response(200, json=[])

        respx.get(f"{BASE}/rest/api/3/field").mock(side_effect=side_effect)
        with _client() as c:
            result = c.get_fields()
        assert attempt == 3
        assert result == []

    @respx.mock
    def test_raises_after_max_retries(self) -> None:
        respx.get(f"{BASE}/rest/api/3/field").mock(
            return_value=httpx.Response(500, json={"error": "persistent"})
        )
        with pytest.raises(httpx.HTTPStatusError):
            with _client() as c:
                c.get_fields()
