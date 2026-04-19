"""Nolte Delivery Grader — library-first scoring for delivery hygiene.

Public API per specs/grader-v0.2.md §3.2. Stable contract; breaking
changes require a version bump.
"""
from __future__ import annotations

from nolte_grader.core.config import GraderConfig, config_hash, load_config
from nolte_grader.core.grader import Grader
from nolte_grader.core.models import (
    ApproverStats,
    ClassificationCorrections,
    DimensionFailRate,
    DimensionResult,
    IssueGrade,
    OwnerStats,
    OwnerView,
    RollupReport,
    RollupWindow,
    SystemView,
    Verdict,
)

__all__ = [
    "ApproverStats",
    "ClassificationCorrections",
    "DimensionFailRate",
    "DimensionResult",
    "Grader",
    "GraderConfig",
    "IssueGrade",
    "OwnerStats",
    "OwnerView",
    "RollupReport",
    "RollupWindow",
    "SystemView",
    "Verdict",
    "config_hash",
    "load_config",
]

__version__ = "0.1.0"
