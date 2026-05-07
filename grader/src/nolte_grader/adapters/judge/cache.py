"""Disk-based result cache for judge calls.

Cache key: sha256(issue_key|dimension_code|input_hash|model|prompt_version)
where input_hash = sha256(canonical JSON of inputs, sorted keys).

Layout: {root}/{first_2_hex}/{full_hash}.json

Any change to issue content, dimension, model, or prompt version produces a
new key — natural invalidation, no TTL needed.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JudgeCache:
    def __init__(self, root: Path) -> None:
        self._root = root
        root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def default_dir() -> Path:
        xdg = os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
        return Path(xdg) / "nolte-grader" / "judge"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(
        self,
        issue_key: str,
        dimension_code: str,
        inputs: dict[str, str | None],
        model: str,
        prompt_version: str,
    ) -> dict[str, Any] | None:
        """Return cached result dict, or None on miss."""
        key = self._derive_key(issue_key, dimension_code, inputs, model, prompt_version)
        path = self._path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def put(
        self,
        issue_key: str,
        dimension_code: str,
        inputs: dict[str, str | None],
        model: str,
        prompt_version: str,
        result: dict[str, Any],
    ) -> None:
        """Write result to cache. Silently swallows write errors."""
        key = self._derive_key(issue_key, dimension_code, inputs, model, prompt_version)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {**result, "_cached_at": datetime.now(timezone.utc).isoformat()}
        try:
            path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _input_hash(inputs: dict[str, str | None]) -> str:
        normalized = {k: (v or "") for k, v in inputs.items()}
        canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _derive_key(
        self,
        issue_key: str,
        dimension_code: str,
        inputs: dict[str, str | None],
        model: str,
        prompt_version: str,
    ) -> str:
        ih = self._input_hash(inputs)
        payload = f"{issue_key}|{dimension_code}|{ih}|{model}|{prompt_version}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def _path(self, key: str) -> Path:
        return self._root / key[:2] / f"{key}.json"
