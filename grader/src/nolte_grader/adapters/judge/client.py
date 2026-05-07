"""Anthropic-backed judge client — implements JudgeClientProtocol.

One public method: ``judge(issue_key, dimension_code, inputs) → DimensionResult``.

Features:
- Disk cache keyed by (issue_key, dimension_code, input_hash, model, prompt_version).
- Exponential-backoff retry on rate-limit and 5xx errors (up to 3 attempts).
- Non-JSON or API-failure responses return INSUFFICIENT_EVIDENCE, not a crash.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import anthropic

from nolte_grader.adapters.judge.cache import JudgeCache
from nolte_grader.adapters.judge.prompts import load_prompts
from nolte_grader.core.config import JudgeConfig
from nolte_grader.core.logging import get_logger
from nolte_grader.core.models import DimensionResult, Verdict

log = get_logger(__name__)

_MAX_RETRIES = 3
_BASE_BACKOFF_S = 1.0


class AnthropicJudgeClient:
    """Anthropic Messages API judge client."""

    def __init__(
        self,
        config: JudgeConfig,
        api_key: str,
        prompts_dir: Path,
    ) -> None:
        self._config = config
        self._client = anthropic.Anthropic(api_key=api_key)
        self._prompts = load_prompts(prompts_dir)
        if config.cache_enabled:
            cache_root = Path(config.cache_dir) if config.cache_dir else JudgeCache.default_dir()
            self._cache: JudgeCache | None = JudgeCache(cache_root)
        else:
            self._cache = None
        log.info(
            "judge client ready",
            model=config.model,
            dimensions=sorted(self._prompts),
            cache_enabled=config.cache_enabled,
        )

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def judge(
        self,
        issue_key: str,
        dimension_code: str,
        inputs: dict[str, str | None],
    ) -> DimensionResult:
        """Evaluate one dimension for one issue.

        Returns a fully-populated ``DimensionResult`` with ``model``,
        ``prompt_version``, and ``cached`` set.
        """
        spec = self._prompts.get(dimension_code)
        if spec is None:
            return _error(
                dimension_code, "PROMPT_NOT_FOUND",
                f"No prompt file for {dimension_code}.",
            )

        model = self._config.model_for(dimension_code)

        # Cache hit
        if self._cache is not None:
            cached = self._cache.get(issue_key, dimension_code, inputs, model, spec.version)
            if cached is not None:
                log.debug("judge cache hit", issue_key=issue_key, dim=dimension_code)
                return _parse_result(dimension_code, cached, model, spec.version, cached=True)

        # Render prompt and call API
        rendered_user = spec.render(inputs)
        raw = self._call_with_retry(
            issue_key=issue_key,
            dimension_code=dimension_code,
            system=spec.system_message,
            user=rendered_user,
            model=model,
        )
        if raw is None:
            return _error(
                dimension_code, "JUDGE_API_ERROR",
                "Judge API call failed after retries.",
            )

        # Write to cache
        if self._cache is not None:
            self._cache.put(issue_key, dimension_code, inputs, model, spec.version, raw)

        return _parse_result(dimension_code, raw, model, spec.version, cached=False)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _call_with_retry(
        self,
        issue_key: str,
        dimension_code: str,
        system: str,
        user: str,
        model: str,
    ) -> dict[str, Any] | None:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = self._client.messages.create(
                    model=model,
                    max_tokens=self._config.max_tokens,
                    temperature=self._config.temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                content = response.content[0].text if response.content else ""
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    log.warning(
                        "judge returned non-JSON",
                        issue_key=issue_key,
                        dim=dimension_code,
                        preview=content[:200],
                    )
                    return None

            except anthropic.RateLimitError:
                wait = _BASE_BACKOFF_S * (2 ** (attempt - 1))
                log.warning(
                    "judge rate limited",
                    attempt=attempt,
                    wait_s=wait,
                    issue_key=issue_key,
                    dim=dimension_code,
                )
                time.sleep(wait)

            except anthropic.APIStatusError as exc:
                if exc.status_code in (500, 502, 503, 529):
                    wait = _BASE_BACKOFF_S * (2 ** (attempt - 1))
                    log.warning(
                        "judge API error, retrying",
                        status=exc.status_code,
                        attempt=attempt,
                        wait_s=wait,
                    )
                    time.sleep(wait)
                else:
                    log.error(
                        "judge API error (non-retriable)",
                        status=exc.status_code,
                        issue_key=issue_key,
                        dim=dimension_code,
                    )
                    return None

            except Exception as exc:
                log.error(
                    "judge unexpected error",
                    error=str(exc),
                    issue_key=issue_key,
                    dim=dimension_code,
                )
                return None

        log.error(
            "judge exhausted retries",
            issue_key=issue_key,
            dim=dimension_code,
            attempts=_MAX_RETRIES,
        )
        return None


# ------------------------------------------------------------------
# Parse helpers (module-level, not bound to client)
# ------------------------------------------------------------------


def _parse_result(
    code: str,
    raw: dict[str, Any],
    model: str,
    prompt_version: str,
    *,
    cached: bool,
) -> DimensionResult:
    verdict_str = raw.get("verdict", "INSUFFICIENT_EVIDENCE")
    try:
        verdict = Verdict(verdict_str)
    except ValueError:
        verdict = Verdict.INSUFFICIENT_EVIDENCE

    return DimensionResult(
        code=code,
        verdict=verdict,
        evidence_code=raw.get("evidence_code") or "UNKNOWN",
        rationale=raw.get("rationale") or "",
        quotes=raw.get("quotes") or [],
        recommended_type=raw.get("recommended_type"),
        model=model,
        prompt_version=prompt_version,
        cached=cached,
    )


def _error(code: str, evidence_code: str, rationale: str) -> DimensionResult:
    return DimensionResult(
        code=code,
        verdict=Verdict.INSUFFICIENT_EVIDENCE,
        evidence_code=evidence_code,
        rationale=rationale,
    )
