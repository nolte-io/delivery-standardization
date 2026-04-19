"""Typed exception hierarchy. All grader errors inherit from ``GraderError``
so callers can catch broadly or specifically as needed.
"""
from __future__ import annotations


class GraderError(Exception):
    """Base class for all grader errors."""


class ConfigError(GraderError):
    """Config file is missing, malformed, or fails schema validation."""


class JiraAdapterError(GraderError):
    """Base for Jira adapter errors."""


class JiraAuthError(JiraAdapterError):
    """Jira authentication failed. Check service account email and token."""


class JiraRateLimitError(JiraAdapterError):
    """Jira rate limit exceeded and retry budget was exhausted."""


class JiraFieldNotFoundError(JiraAdapterError):
    """A custom field name did not resolve to a Jira field ID."""


class JudgeAdapterError(GraderError):
    """Base for judge (LLM) adapter errors."""


class JudgeResponseError(JudgeAdapterError):
    """Judge returned a response that does not match the expected schema."""


class PromptLoadError(GraderError):
    """A judge prompt file could not be loaded or parsed."""


class ChangelogError(GraderError):
    """Changelog data is malformed or incomplete."""


class ParserError(GraderError):
    """Description or ADF parser could not extract expected structure."""


class EvaluatorError(GraderError):
    """A dimension evaluator failed beyond a normal FAIL verdict."""
