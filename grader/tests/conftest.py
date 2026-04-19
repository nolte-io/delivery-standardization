"""Shared fixtures for all grader tests."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture()
def fixtures_root() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture()
def minimal_config_dict() -> dict[str, Any]:
    """Minimal valid GraderConfig as a raw dict. All required fields present."""
    return {
        "jira": {
            "instance_url": "https://example.atlassian.net",
            "service_account_email": "grader@example.com",
        },
        "projects": {"include": ["TEST"], "exclude": []},
        "authorized_approvers": {
            "default": [{"accountId": "u1", "role": "head_of_engineering"}],
            "per_project": {},
        },
        "dimensions": {
            "enabled": [
                "Y1", "Y2", "Y3", "Y4", "Y5", "Y6",
                "U7", "U8", "U9", "U10", "U11", "U12",
                "C1", "C2", "C3",
                "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
            ],
        },
        "thresholds": {
            "cycle_time_days": 7,
            "wip_limits": {
                "in_specification": 8,
                "ready": 5,
                "in_implementation_per_engineer": 3,
                "in_implementation_system": 15,
                "done_implementing": 5,
                "in_validation": 6,
            },
        },
        "conventions": {
            "template_sections": [
                "## Business Objective",
                "## Observable Impact",
                "## Acceptance Criteria",
                "## Scenarios",
                "## Risks",
            ],
            "test_subtask_title_pattern": r"^Tests — [A-Z]+-\d+$",
        },
        "custom_fields": {
            "design_artifact_link": "Design Artifact Link",
            "production_release_reference": "Production Release Reference",
            "impact_measurement_link": "Impact Measurement Link",
            "spec_approver": "Spec Approver",
        },
        "judge": {
            "model": "claude-sonnet-4-6",
            "temperature": 0,
            "max_tokens": 1000,
            "cache_enabled": True,
            "max_concurrency": 4,
            "model_by_dimension": {},
        },
        "output": {
            "directory": "./runs/{run_id}/",
            "formats": ["json", "csv", "md"],
        },
        "teams": {
            "default": {"size": 5},
            "per_project": {},
        },
    }


@pytest.fixture()
def minimal_config_yaml(tmp_path: Path, minimal_config_dict: dict[str, Any]) -> Path:
    """Minimal valid config written to a temp YAML file."""
    path = tmp_path / "grader.config.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(minimal_config_dict, f)
    return path
