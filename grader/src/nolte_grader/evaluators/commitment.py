"""Deterministic commitment-point evaluators — C1, C3.

C2 (BDD quality) is judge-only; it lives in the judge runner.
"""
from __future__ import annotations

from nolte_grader.core.models import DimensionResult, Verdict


def _r(
    code: str,
    verdict: Verdict,
    evidence_code: str,
    rationale: str,
) -> DimensionResult:
    return DimensionResult(
        code=code,
        verdict=verdict,
        evidence_code=evidence_code,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# C1 — Commitment transition exists
# ---------------------------------------------------------------------------


def eval_c1(commit_ts: object) -> DimensionResult:
    """C1 — Ready → In Implementation transition present in changelog."""
    if commit_ts is not None:
        return _r("C1", Verdict.PASS, "COMMITMENT_TRANSITION_FOUND",
                  "Ready → In Implementation transition found in changelog.")
    return _r("C1", Verdict.FAIL, "COMMITMENT_TRANSITION_MISSING",
              "No Ready → In Implementation transition in changelog.")


# ---------------------------------------------------------------------------
# C3 — Gate approver recorded and authorized
# ---------------------------------------------------------------------------


def eval_c3(
    spec_approver_id: str | None,
    authorized_account_ids: set[str],
    builder_account_ids: set[str],
) -> DimensionResult:
    """C3 — Spec Approver field populated at Done Specifying → Ready with an authorized, non-builder account.

    Args:
        spec_approver_id: Value from the Spec Approver field edit in the same
            changelog history entry as the Done Specifying → Ready transition.
            None or empty string → FAIL APPROVER_FIELD_EMPTY.
        authorized_account_ids: Resolved from AuthorizedApprovers.for_project()
            for the Story's project. Must contain the approver's accountId.
        builder_account_ids: accountIds assigned to any sub-task during
            In Implementation.  Approver must not be in this set.
    """
    if not spec_approver_id:
        return _r("C3", Verdict.FAIL, "APPROVER_FIELD_EMPTY",
                  "Spec Approver field empty at Done Specifying → Ready transition.")
    if spec_approver_id not in authorized_account_ids:
        return _r("C3", Verdict.FAIL, "APPROVER_NOT_AUTHORIZED",
                  "Spec Approver account not in authorized approvers list for this project.")
    if spec_approver_id in builder_account_ids:
        return _r("C3", Verdict.FAIL, "APPROVER_IS_BUILDER",
                  "Spec Approver is also a Story builder.")
    return _r("C3", Verdict.PASS, "APPROVER_RECORDED_AND_AUTHORIZED",
              "Spec Approver recorded, authorized, and independent from builders.")
