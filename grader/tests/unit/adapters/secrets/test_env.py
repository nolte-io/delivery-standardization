"""Tests for adapters/secrets/env.py — EnvSecretsProvider."""
from __future__ import annotations

import pytest

from nolte_grader.adapters.secrets.env import EnvSecretsProvider
from nolte_grader.core.errors import ConfigError


class TestEnvSecretsProvider:
    def test_jira_token_reads_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_API_TOKEN", "my-secret-token")
        provider = EnvSecretsProvider()
        assert provider.jira_token() == "my-secret-token"

    def test_anthropic_key_reads_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        provider = EnvSecretsProvider()
        assert provider.anthropic_key() == "sk-ant-test"

    def test_jira_token_raises_when_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
        provider = EnvSecretsProvider()
        with pytest.raises(ConfigError, match="JIRA_API_TOKEN"):
            provider.jira_token()

    def test_anthropic_key_raises_when_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        provider = EnvSecretsProvider()
        with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
            provider.anthropic_key()

    def test_jira_token_raises_on_empty_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_API_TOKEN", "")
        provider = EnvSecretsProvider()
        with pytest.raises(ConfigError):
            provider.jira_token()

    def test_satisfies_secrets_provider_protocol(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("JIRA_API_TOKEN", "tok")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        from nolte_grader.core.protocols import SecretsProviderProtocol
        provider = EnvSecretsProvider()
        assert isinstance(provider, SecretsProviderProtocol)
