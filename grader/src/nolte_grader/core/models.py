"""Output schemas — specs/grader-v0.2.md §9. Stable contract.

NOT_APPLICABLE is the fourth verdict state (approved 2026-04-19). Dimensions
that genuinely do not apply to an issue (e.g., downstream dimensions for a
Story that never entered In Implementation) are excluded from fail-rate
denominators. INSUFFICIENT_EVIDENCE is a judge-side outcome that rolls up
as fail with a distinct flag.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


RecommendedType = Literal["Story", "Task", "Bug", "Sub-task"]


class DimensionResult(BaseModel):
    """One dimension's verdict for one issue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    verdict: Verdict
    evidence_code: str
    rationale: str
    quotes: list[str] = Field(default_factory=list)
    recommended_type: RecommendedType | None = None
    model: str | None = None
    prompt_version: str | None = None
    cached: bool = False


class IssueGrade(BaseModel):
    """Per-issue grade record — §9.1."""

    model_config = ConfigDict(extra="forbid")

    issue_key: str
    issue_type: str
    project_key: str
    epic_key: str | None = None
    title: str
    run_timestamp: datetime
    commitment_timestamp: datetime | None = None
    done_timestamp: datetime | None = None
    cycle_time_days: float | None = None
    upstream_owner: str | None = None
    downstream_owner: str | None = None
    validator: str | None = None
    spec_approver: str | None = None
    dimensions: dict[str, DimensionResult]
    six_yes_overall: Verdict
    upstream_overall: Verdict
    downstream_overall: Verdict
    story_overall: Verdict
    flags: list[str] = Field(default_factory=list)
    config_hash: str


class DimensionFailRate(BaseModel):
    """Per-dimension aggregation for the rollup. NA is excluded from the denominator."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    graded: int
    passes: int
    fails: int
    insufficient_evidence: int
    not_applicable: int
    fail_rate: float


class RollupWindow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    from_date: date
    to_date: date


class ClassificationCorrections(BaseModel):
    """U11 aggregation — misclassification counts and corrected Task:Story ratio."""

    model_config = ConfigDict(extra="forbid")

    corrections: dict[str, int] = Field(default_factory=dict)
    corrected_task_story_ratio: str | None = None


class OwnerStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stories: int
    top_fails: list[str] = Field(default_factory=list)


class ApproverStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: int
    downstream_pass_rate_of_approved: float


class SystemView(BaseModel):
    """System-level rollup — §9.2."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    window: RollupWindow
    story_count: int
    issue_count_all_types: int
    six_yes_pass_rate: float
    dimension_fail_rates: dict[str, DimensionFailRate]
    top_failing_dimensions: list[str]
    classification_corrections: ClassificationCorrections
    repeat_offenders_by_epic: list[str] = Field(default_factory=list)


class OwnerView(BaseModel):
    """Owner-grouped rollup — §9.2.

    The §9.2 example mixes owner-name keys with a special "by_engineer" key
    under "downstream". Represented here as separate typed dicts to avoid
    key-collision ambiguity; a future JSON formatter can emit the flat shape
    for human-readable outputs.
    """

    model_config = ConfigDict(extra="forbid")

    upstream: dict[str, OwnerStats] = Field(default_factory=dict)
    downstream_by_owner: dict[str, OwnerStats] = Field(default_factory=dict)
    downstream_by_engineer: dict[str, OwnerStats] = Field(default_factory=dict)
    approvers: dict[str, ApproverStats] = Field(default_factory=dict)


class RollupReport(BaseModel):
    """Top-level rollup container — system view plus owner view plus run metadata."""

    model_config = ConfigDict(extra="forbid")

    system: SystemView
    owner: OwnerView
    config_hash: str
