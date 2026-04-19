"""Config loader, validator, and ``config_hash`` — spec §10.

GraderConfig is a Pydantic model so schema violations fail loudly at load
time. Unknown keys are rejected (``extra="forbid"``) so typos surface
immediately rather than silently losing intent.

``config_hash`` canonicalizes the resolved config to JSON with sorted keys
and returns a ``sha256:<hex>`` string. Logged at run start and stamped on
every ``IssueGrade`` record for historical reproducibility.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from nolte_grader.core.errors import ConfigError


class JiraConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instance_url: str
    service_account_email: str


class ProjectsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    include: list[str]
    exclude: list[str] = Field(default_factory=list)


class ApproverEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accountId: str
    role: str


class AuthorizedApprovers(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default: list[ApproverEntry] = Field(default_factory=list)
    per_project: dict[str, list[ApproverEntry]] = Field(default_factory=dict)

    def for_project(self, project_key: str) -> list[ApproverEntry]:
        return [*self.default, *self.per_project.get(project_key, [])]


class DimensionsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: list[str]


class WipLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    in_specification: int
    ready: int
    in_implementation_per_engineer: int
    in_implementation_system: int
    done_implementing: int
    in_validation: int


class Thresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cycle_time_days: int
    wip_limits: WipLimits


class Conventions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template_sections: list[str]
    test_subtask_title_pattern: str


class CustomFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    design_artifact_link: str
    production_release_reference: str
    impact_measurement_link: str
    spec_approver: str


class JudgeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str
    temperature: float = 0.0
    max_tokens: int = 1000
    cache_enabled: bool = True
    cache_dir: str | None = None
    max_concurrency: int = 4
    model_by_dimension: dict[str, str] = Field(default_factory=dict)

    def model_for(self, dimension_code: str) -> str:
        """Resolve effective model for a dimension, honoring per-dimension override."""
        return self.model_by_dimension.get(dimension_code, self.model)


class OutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    directory: str
    formats: list[str]


class TeamConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    size: int


class TeamsConfig(BaseModel):
    """Team size per project — drives Y4 TEAM_SIZE_EXCEPTION (approved 2026-04-19).

    Sub-task assignee counts are unreliable (a solo-executed Story on a
    larger team would wrongly trip the exception). Config is the source
    of truth.
    """

    model_config = ConfigDict(extra="forbid")
    default: TeamConfig
    per_project: dict[str, TeamConfig] = Field(default_factory=dict)

    def size_for(self, project_key: str) -> int:
        override = self.per_project.get(project_key)
        if override is not None:
            return override.size
        return self.default.size


class GraderConfig(BaseModel):
    """Top-level grader config. Passed into ``Grader(config=...)``.

    ``prompts_dir`` lets the embedded host point at its own prompt tree.
    When unset, the runtime resolves prompts relative to the installed
    package's bundled ``/prompts`` directory.
    """

    model_config = ConfigDict(extra="forbid")
    jira: JiraConfig
    projects: ProjectsConfig
    authorized_approvers: AuthorizedApprovers
    dimensions: DimensionsConfig
    thresholds: Thresholds
    conventions: Conventions
    custom_fields: CustomFields
    judge: JudgeConfig
    output: OutputConfig
    teams: TeamsConfig
    prompts_dir: str | None = None


def load_config(path: Path | str) -> GraderConfig:
    """Load and validate a grader config from YAML.

    Raises:
        FileNotFoundError: config file does not exist.
        ConfigError: YAML is not a mapping at the top level.
        pydantic.ValidationError: schema violations (unknown keys, missing
            required fields, wrong types).
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ConfigError(
            f"Config at {path} must be a YAML mapping at the top level; "
            f"got {type(raw).__name__}."
        )
    return GraderConfig.model_validate(raw)


def config_hash(config: GraderConfig) -> str:
    """Canonical sha256 of the resolved config.

    Keys are sorted for determinism; ``None`` values are included so absent
    fields hash distinctly from explicit nulls. The config carries no
    secrets, so nothing needs stripping.
    """
    payload: dict[str, Any] = config.model_dump(mode="json", exclude_none=False)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
