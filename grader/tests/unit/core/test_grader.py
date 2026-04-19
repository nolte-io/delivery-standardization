"""Tests for core/grader.py — stable public API contract (spec §3.2)."""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from nolte_grader.core.config import GraderConfig
from nolte_grader.core.grader import Grader


@pytest.fixture()
def grader(minimal_config_dict: dict[str, Any]) -> Grader:
    return Grader(GraderConfig.model_validate(minimal_config_dict))


class TestGraderConstruction:
    def test_accepts_config_only(self, minimal_config_dict: dict[str, Any]) -> None:
        cfg = GraderConfig.model_validate(minimal_config_dict)
        g = Grader(cfg)
        assert g.config is cfg

    def test_config_property_returns_same_object(self, grader: Grader) -> None:
        assert grader.config is grader.config

    def test_accepts_all_adapter_injections(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        cfg = GraderConfig.model_validate(minimal_config_dict)
        sentinel = object()
        g = Grader(
            cfg,
            jira_client=sentinel,  # type: ignore[arg-type]
            judge_client=sentinel,  # type: ignore[arg-type]
            storage=sentinel,  # type: ignore[arg-type]
            secrets=sentinel,  # type: ignore[arg-type]
            metrics=sentinel,  # type: ignore[arg-type]
        )
        assert g.config is cfg


class TestPublicAPIContractExists:
    """Every method in the §3.2 contract is present and callable."""

    def test_grade_issue_raises_not_implemented_until_wired(
        self, grader: Grader
    ) -> None:
        with pytest.raises(NotImplementedError):
            grader.grade_issue("TEST-1")

    def test_grade_issues_delegates_to_grade_issue(self, grader: Grader) -> None:
        with pytest.raises(NotImplementedError):
            grader.grade_issues(["TEST-1", "TEST-2"])

    def test_grade_by_window_raises_not_implemented_until_wired(
        self, grader: Grader
    ) -> None:
        with pytest.raises(NotImplementedError):
            grader.grade_by_window(
                from_date=date(2026, 3, 20),
                to_date=date(2026, 4, 19),
                project_keys=["TEST"],
            )

    def test_rollup_raises_on_empty_grades(self, grader: Grader) -> None:
        with pytest.raises(ValueError, match="Cannot aggregate zero grades"):
            grader.rollup([])

    def test_grade_issues_empty_list_returns_empty(self, grader: Grader) -> None:
        result = grader.grade_issues([])
        assert result == []
