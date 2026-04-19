"""Tests for adapters/jira/field_discovery.py."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from nolte_grader.adapters.jira.field_discovery import FieldDiscovery
from nolte_grader.core.errors import JiraFieldNotFoundError

_FIELDS = [
    {"id": "summary", "name": "Summary"},
    {"id": "customfield_10014", "name": "Epic Link"},
    {"id": "customfield_10016", "name": "Design Artifact Link"},
]


def _mock_client(fields: list[dict[str, Any]] | None = None) -> MagicMock:
    client = MagicMock()
    client.get_fields.return_value = fields if fields is not None else _FIELDS
    return client


def _cache_path(tmp_path: Path) -> Path:
    return tmp_path / "fields.json"


class TestFieldDiscoveryResolve:
    def test_resolves_known_field(self, tmp_path: Path) -> None:
        client = _mock_client()
        fd = FieldDiscovery(client, cache_path=_cache_path(tmp_path))
        assert fd.resolve("Epic Link") == "customfield_10014"

    def test_resolves_standard_field(self, tmp_path: Path) -> None:
        client = _mock_client()
        fd = FieldDiscovery(client, cache_path=_cache_path(tmp_path))
        assert fd.resolve("Summary") == "summary"

    def test_raises_on_unknown_field(self, tmp_path: Path) -> None:
        client = _mock_client()
        fd = FieldDiscovery(client, cache_path=_cache_path(tmp_path))
        with pytest.raises(JiraFieldNotFoundError, match="NonExistent"):
            fd.resolve("NonExistent")

    def test_resolve_many_returns_mapping(self, tmp_path: Path) -> None:
        client = _mock_client()
        fd = FieldDiscovery(client, cache_path=_cache_path(tmp_path))
        result = fd.resolve_many(["Epic Link", "Summary"])
        assert result == {"Epic Link": "customfield_10014", "Summary": "summary"}


class TestFieldDiscoveryCache:
    def test_writes_cache_on_first_call(self, tmp_path: Path) -> None:
        client = _mock_client()
        path = _cache_path(tmp_path)
        fd = FieldDiscovery(client, cache_path=path)
        fd.resolve("Summary")
        assert path.exists()
        data = json.loads(path.read_text())
        assert "fetched_at" in data
        assert data["fields"]["Summary"] == "summary"

    def test_uses_disk_cache_without_api_call(self, tmp_path: Path) -> None:
        client = _mock_client()
        path = _cache_path(tmp_path)
        path.write_text(
            json.dumps({
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "fields": {"Cached Field": "customfield_99999"},
            }),
            encoding="utf-8",
        )
        fd = FieldDiscovery(client, cache_path=path)
        result = fd.resolve("Cached Field")
        assert result == "customfield_99999"
        client.get_fields.assert_not_called()

    def test_refreshes_expired_cache(self, tmp_path: Path) -> None:
        client = _mock_client()
        path = _cache_path(tmp_path)
        expired_time = datetime.now(timezone.utc) - timedelta(hours=25)
        path.write_text(
            json.dumps({
                "fetched_at": expired_time.isoformat(),
                "fields": {"Old Field": "customfield_00001"},
            }),
            encoding="utf-8",
        )
        fd = FieldDiscovery(client, cache_path=path)
        fd.resolve("Summary")
        client.get_fields.assert_called_once()

    def test_refreshes_on_field_not_in_cache(self, tmp_path: Path) -> None:
        client = _mock_client()
        path = _cache_path(tmp_path)
        path.write_text(
            json.dumps({
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "fields": {"Other Field": "customfield_11111"},
            }),
            encoding="utf-8",
        )
        fd = FieldDiscovery(client, cache_path=path)
        result = fd.resolve("Epic Link")
        assert result == "customfield_10014"
        client.get_fields.assert_called_once()

    def test_in_memory_cache_avoids_repeated_disk_reads(self, tmp_path: Path) -> None:
        client = _mock_client()
        path = _cache_path(tmp_path)
        fd = FieldDiscovery(client, cache_path=path)
        fd.resolve("Summary")
        fd.resolve("Epic Link")
        # Only one network call despite two resolves
        client.get_fields.assert_called_once()

    def test_handles_corrupt_cache_gracefully(self, tmp_path: Path) -> None:
        client = _mock_client()
        path = _cache_path(tmp_path)
        path.write_text("NOT VALID JSON", encoding="utf-8")
        fd = FieldDiscovery(client, cache_path=path)
        result = fd.resolve("Summary")
        assert result == "summary"
        client.get_fields.assert_called_once()
