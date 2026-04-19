"""Custom field name → Jira field ID resolution with a 24-hour disk cache.

Jira field IDs (e.g., ``customfield_10014``) are instance-specific and can
change after Jira admin operations. The grader resolves by name on first use
and caches the mapping so subsequent runs don't pay the API cost.

Cache location (standalone): ``$XDG_CACHE_HOME/nolte-grader/jira/<host>/fields.json``
                             (``~/.cache/nolte-grader/jira/<host>/fields.json`` on macOS/Linux)
The embedded host can pass a custom ``cache_path`` to point at its own storage.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from nolte_grader.core.errors import JiraFieldNotFoundError
from nolte_grader.core.logging import get_logger

if TYPE_CHECKING:
    from nolte_grader.core.protocols import JiraClientProtocol

log = get_logger(__name__)

_CACHE_TTL = timedelta(hours=24)


def _default_cache_path(instance_url: str) -> Path:
    host = urlparse(instance_url).hostname or "unknown"
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "nolte-grader" / "jira" / host / "fields.json"


class FieldDiscovery:
    """Resolves Jira field names to field IDs.

    On first call to ``resolve()``, loads the disk cache if fresh, otherwise
    calls ``/field`` and writes a new cache. Auto-refreshes when a named
    field is not found (guards against new fields added after cache was written).
    """

    def __init__(
        self,
        jira_client: JiraClientProtocol,
        cache_path: Path | None = None,
        *,
        instance_url: str = "",
    ) -> None:
        self._client = jira_client
        self._cache_path = cache_path or _default_cache_path(instance_url)
        self._memory: dict[str, str] | None = None

    def resolve(self, field_name: str) -> str:
        """Return the Jira field ID for ``field_name``.

        Raises:
            JiraFieldNotFoundError: field name not found even after a refresh.
        """
        mapping = self._load()
        if field_name in mapping:
            return mapping[field_name]
        log.info("field not in cache — refreshing", field_name=field_name)
        mapping = self._refresh()
        if field_name not in mapping:
            raise JiraFieldNotFoundError(
                f"Field '{field_name}' not found in this Jira instance. "
                "Check the field name in grader.config.yaml matches the "
                "Jira admin display name exactly (case-sensitive)."
            )
        return mapping[field_name]

    def resolve_many(self, field_names: list[str]) -> dict[str, str]:
        """Resolve multiple field names in a single pass. Returns name → id mapping."""
        return {name: self.resolve(name) for name in field_names}

    def _load(self) -> dict[str, str]:
        if self._memory is not None:
            return self._memory
        if self._cache_path.exists():
            try:
                data: dict[str, Any] = json.loads(self._cache_path.read_text(encoding="utf-8"))
                fetched_at = datetime.fromisoformat(data["fetched_at"])
                if datetime.now(timezone.utc) - fetched_at < _CACHE_TTL:
                    log.debug("field cache hit", path=str(self._cache_path))
                    self._memory = data["fields"]
                    return self._memory
                log.debug("field cache expired — refreshing")
            except (KeyError, ValueError, OSError) as exc:
                log.warning("field cache unreadable — refreshing", error=str(exc))
        return self._refresh()

    def _refresh(self) -> dict[str, str]:
        log.info("fetching field list from Jira")
        fields = self._client.get_fields()
        mapping: dict[str, str] = {f["name"]: f["id"] for f in fields if "name" in f and "id" in f}
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(
            json.dumps(
                {"fetched_at": datetime.now(timezone.utc).isoformat(), "fields": mapping},
                indent=2,
            ),
            encoding="utf-8",
        )
        self._memory = mapping
        log.info("field cache written", field_count=len(mapping), path=str(self._cache_path))
        return mapping
