"""Deterministic workflow evaluators — W1.

W1 checks that the issue was routed through the spec workflow (Done Specifying)
before entering implementation. An issue that jumps from any backlog status
directly to In Implementation bypasses the commitment gate entirely.
"""
from __future__ import annotations

from datetime import datetime

from nolte_grader.core.models import DimensionResult, Verdict


def _r(code: str, verdict: Verdict, evidence_code: str, rationale: str) -> DimensionResult:
    return DimensionResult(code=code, verdict=verdict, evidence_code=evidence_code, rationale=rationale)


def eval_w1(
    commit_ts: datetime | None,
    impl_entry_ts: datetime | None,
) -> DimensionResult:
    """W1 — Issue went through Done Specifying before entering In Implementation.

    Args:
        commit_ts: Timestamp of the Done Specifying → In Implementation transition.
            Not None means the full spec workflow was observed.
        impl_entry_ts: Timestamp of first entry into In Implementation from any status.
            None means the issue never reached implementation.
    """
    if impl_entry_ts is None:
        return _r(
            "W1", Verdict.NOT_APPLICABLE, "NEVER_REACHED_IMPLEMENTATION",
            "Issue never entered In Implementation; workflow check not applicable.",
        )
    if commit_ts is not None:
        return _r(
            "W1", Verdict.PASS, "SPEC_STAGES_OBSERVED",
            "Issue transitioned through Done Specifying before In Implementation.",
        )
    return _r(
        "W1", Verdict.FAIL, "SPEC_STAGES_BYPASSED",
        "Issue entered In Implementation without transitioning through Done Specifying. "
        "The spec workflow was bypassed entirely.",
    )
