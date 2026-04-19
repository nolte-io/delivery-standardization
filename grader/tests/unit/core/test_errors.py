"""Tests for core/errors.py — exception hierarchy contracts."""
from __future__ import annotations

import pytest

from nolte_grader.core.errors import (
    ChangelogError,
    ConfigError,
    EvaluatorError,
    GraderError,
    JiraAdapterError,
    JiraAuthError,
    JiraFieldNotFoundError,
    JiraRateLimitError,
    JudgeAdapterError,
    JudgeResponseError,
    ParserError,
    PromptLoadError,
)


ALL_ERRORS = [
    ConfigError,
    JiraAdapterError,
    JiraAuthError,
    JiraRateLimitError,
    JiraFieldNotFoundError,
    JudgeAdapterError,
    JudgeResponseError,
    PromptLoadError,
    ChangelogError,
    ParserError,
    EvaluatorError,
]


def test_all_errors_inherit_from_grader_error() -> None:
    for cls in ALL_ERRORS:
        assert issubclass(cls, GraderError), f"{cls.__name__} must inherit GraderError"


def test_jira_errors_inherit_from_jira_adapter_error() -> None:
    for cls in (JiraAuthError, JiraRateLimitError, JiraFieldNotFoundError):
        assert issubclass(cls, JiraAdapterError)


def test_judge_response_inherits_from_judge_adapter_error() -> None:
    assert issubclass(JudgeResponseError, JudgeAdapterError)


def test_can_catch_specific_error_as_grader_error() -> None:
    with pytest.raises(GraderError):
        raise ConfigError("bad config")


def test_can_catch_jira_auth_as_jira_adapter_error() -> None:
    with pytest.raises(JiraAdapterError):
        raise JiraAuthError("401 Unauthorized")


def test_errors_carry_message() -> None:
    msg = "field 'Design Artifact Link' not found"
    err = JiraFieldNotFoundError(msg)
    assert str(err) == msg
