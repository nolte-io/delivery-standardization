"""Environment-variable secrets provider for standalone mode.

The core library never reads environment variables. This adapter is the
boundary: the CLI entry point instantiates it and passes it to ``Grader``.
The embedded host provides its own ``SecretsProvider`` instead.
"""
from __future__ import annotations

import os

from nolte_grader.core.errors import ConfigError


class EnvSecretsProvider:
    """Reads ``JIRA_API_TOKEN`` and ``ANTHROPIC_API_KEY`` from the environment.

    Raises ``ConfigError`` immediately if either variable is absent, so the
    error surfaces before any API calls are attempted.
    """

    def jira_token(self) -> str:
        token = os.environ.get("JIRA_API_TOKEN")
        if not token:
            raise ConfigError(
                "JIRA_API_TOKEN environment variable is not set. "
                "Set it before running nolte-grader, or copy .env.example to .env."
            )
        return token

    def anthropic_key(self) -> str:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ConfigError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Set it before running nolte-grader, or copy .env.example to .env."
            )
        return key
