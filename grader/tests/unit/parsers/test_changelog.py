"""Tests for parsers/changelog.py."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pytest

from nolte_grader.core.errors import ChangelogError
from nolte_grader.parsers.changelog import (
    KANBAN_ORDER,
    FieldEdit,
    ParsedChangelog,
    StatusTransition,
    parse_changelog,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

UTC = timezone.utc


def ts(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _history(
    history_id: str,
    created: str,
    actor_id: str = "u1",
    actor_name: str = "Actor",
    items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": history_id,
        "author": {"accountId": actor_id, "displayName": actor_name},
        "created": created,
        "items": items or [],
    }


def _status_item(from_s: str, to_s: str) -> dict[str, Any]:
    return {
        "field": "status",
        "fieldtype": "jira",
        "fromString": from_s,
        "toString": to_s,
    }


def _field_item(name: str, from_val: str | None, to_val: str | None) -> dict[str, Any]:
    return {
        "field": name,
        "fieldtype": "jira",
        "fromString": from_val,
        "toString": to_val,
    }


# ---------------------------------------------------------------------------
# parse_changelog — structural
# ---------------------------------------------------------------------------


class TestParseChangelog:
    def test_empty_histories_returns_empty(self) -> None:
        cl = parse_changelog([])
        assert cl.status_transitions == []
        assert cl.field_edits == []

    def test_extracts_status_transition(self) -> None:
        histories = [
            _history(
                "h1",
                "2026-03-15T10:00:00.000+0000",
                actor_id="u1",
                actor_name="Yanna",
                items=[_status_item("Ready", "In Implementation")],
            )
        ]
        cl = parse_changelog(histories)
        assert len(cl.status_transitions) == 1
        t = cl.status_transitions[0]
        assert t.from_status == "Ready"
        assert t.to_status == "In Implementation"
        assert t.actor_account_id == "u1"
        assert t.history_id == "h1"

    def test_extracts_field_edit(self) -> None:
        histories = [
            _history(
                "h2",
                "2026-03-14T09:00:00.000+0000",
                items=[_field_item("description", "old text", "new text")],
            )
        ]
        cl = parse_changelog(histories)
        assert len(cl.field_edits) == 1
        e = cl.field_edits[0]
        assert e.field_name == "description"
        assert e.from_value == "old text"
        assert e.to_value == "new text"

    def test_multiple_items_in_one_entry(self) -> None:
        histories = [
            _history(
                "h3",
                "2026-03-15T10:00:00.000+0000",
                actor_id="hector",
                items=[
                    _status_item("Done Specifying", "Ready"),
                    _field_item("Spec Approver", None, "hector-id"),
                ],
            )
        ]
        cl = parse_changelog(histories)
        assert len(cl.status_transitions) == 1
        assert len(cl.field_edits) == 1
        assert cl.field_edits[0].history_id == "h3"

    def test_sorted_by_timestamp_ascending(self) -> None:
        histories = [
            _history("h2", "2026-03-16T00:00:00.000+0000", items=[_status_item("Ready", "In Implementation")]),
            _history("h1", "2026-03-14T00:00:00.000+0000", items=[_status_item("Backlog", "In Specification")]),
        ]
        cl = parse_changelog(histories)
        assert cl.status_transitions[0].from_status == "Backlog"
        assert cl.status_transitions[1].from_status == "Ready"

    def test_skips_entry_missing_created(self) -> None:
        histories = [{"id": "h1", "author": {}, "items": [_status_item("Ready", "In Implementation")]}]
        cl = parse_changelog(histories)
        assert cl.status_transitions == []

    def test_skips_status_item_missing_fromstring(self) -> None:
        histories = [
            _history("h1", "2026-03-15T10:00:00.000+0000", items=[{"field": "status", "toString": "Ready"}])
        ]
        cl = parse_changelog(histories)
        assert cl.status_transitions == []

    def test_handles_timezone_offset_without_colon(self) -> None:
        histories = [
            _history("h1", "2026-03-15T10:00:00.000+0500", items=[_status_item("Ready", "In Implementation")])
        ]
        cl = parse_changelog(histories)
        assert len(cl.status_transitions) == 1
        assert cl.status_transitions[0].timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# Commitment and gate timestamps
# ---------------------------------------------------------------------------


class TestCommitmentTimestamp:
    def _cl_with_full_flow(self) -> ParsedChangelog:
        histories = [
            _history("h1", "2026-03-10T08:00:00Z", items=[_status_item("Backlog", "In Specification")]),
            _history("h2", "2026-03-12T09:00:00Z", items=[_status_item("In Specification", "Done Specifying")]),
            _history(
                "h3",
                "2026-03-13T10:00:00Z",
                actor_id="hector",
                items=[
                    _status_item("Done Specifying", "Ready"),
                    _field_item("Spec Approver", None, "hector-id"),
                ],
            ),
            _history("h4", "2026-03-15T10:00:00Z", items=[_status_item("Ready", "In Implementation")]),
            _history("h5", "2026-03-20T14:00:00Z", items=[_status_item("In Implementation", "Done Implementing")]),
            _history("h6", "2026-03-21T09:00:00Z", items=[_status_item("Done Implementing", "In Validation")]),
            _history("h7", "2026-03-22T16:00:00Z", actor_id="yanna", items=[_status_item("In Validation", "Done")]),
        ]
        return parse_changelog(histories)

    def test_commitment_timestamp_found(self) -> None:
        cl = self._cl_with_full_flow()
        commit_ts = cl.commitment_timestamp()
        assert commit_ts == datetime(2026, 3, 15, 10, 0, tzinfo=UTC)

    def test_commitment_timestamp_none_when_no_transition(self) -> None:
        cl = parse_changelog([
            _history("h1", "2026-03-10T00:00:00Z", items=[_status_item("Backlog", "In Specification")])
        ])
        assert cl.commitment_timestamp() is None

    def test_done_specifying_to_ready_timestamp(self) -> None:
        cl = self._cl_with_full_flow()
        ts = cl.done_specifying_to_ready_timestamp()
        assert ts == datetime(2026, 3, 13, 10, 0, tzinfo=UTC)

    def test_done_implementing_timestamp(self) -> None:
        cl = self._cl_with_full_flow()
        ts = cl.done_implementing_timestamp()
        assert ts == datetime(2026, 3, 20, 14, 0, tzinfo=UTC)

    def test_done_timestamp(self) -> None:
        cl = self._cl_with_full_flow()
        ts = cl.done_timestamp()
        assert ts == datetime(2026, 3, 22, 16, 0, tzinfo=UTC)

    def test_actor_who_transitioned_to_done(self) -> None:
        cl = self._cl_with_full_flow()
        actor = cl.actor_who_transitioned_to("Done")
        assert actor == "yanna"


# ---------------------------------------------------------------------------
# Field edit queries
# ---------------------------------------------------------------------------


class TestFieldEditQueries:
    def _cl(self) -> ParsedChangelog:
        histories = [
            _history(
                "h1",
                "2026-03-10T00:00:00Z",
                items=[_field_item("description", None, "initial text")],
            ),
            _history(
                "h2",
                "2026-03-14T00:00:00Z",
                items=[_field_item("description", "initial text", "updated AC text")],
            ),
            _history(
                "h3",
                "2026-03-16T00:00:00Z",
                items=[_field_item("description", "updated AC text", "post-commit edit")],
            ),
        ]
        return parse_changelog(histories)

    def test_field_edits_for_returns_all(self) -> None:
        cl = self._cl()
        edits = cl.field_edits_for("description")
        assert len(edits) == 3

    def test_field_edits_for_returns_empty_for_unknown(self) -> None:
        cl = self._cl()
        assert cl.field_edits_for("nonexistent") == []

    def test_field_edits_after_filters_correctly(self) -> None:
        cl = self._cl()
        commit_ts = datetime(2026, 3, 15, 0, 0, tzinfo=UTC)
        edits = cl.field_edits_after("description", commit_ts)
        assert len(edits) == 1
        assert edits[0].to_value == "post-commit edit"

    def test_field_edits_after_empty_before_first_edit(self) -> None:
        cl = self._cl()
        future_ts = datetime(2030, 1, 1, tzinfo=UTC)
        assert cl.field_edits_after("description", future_ts) == []


# ---------------------------------------------------------------------------
# Spec Approver at ready transition (C3)
# ---------------------------------------------------------------------------


class TestSpecApproverAtReadyTransition:
    def test_returns_approver_from_same_history_entry(self) -> None:
        histories = [
            _history(
                "h3",
                "2026-03-13T10:00:00Z",
                actor_id="hector",
                items=[
                    _status_item("Done Specifying", "Ready"),
                    _field_item("Spec Approver", None, "hector-account-id"),
                ],
            ),
        ]
        cl = parse_changelog(histories)
        approver = cl.spec_approver_at_ready_transition("Spec Approver")
        assert approver == "hector-account-id"

    def test_returns_none_when_no_done_specifying_to_ready(self) -> None:
        histories = [_history("h1", "2026-03-15T10:00:00Z", items=[_status_item("Ready", "In Implementation")])]
        cl = parse_changelog(histories)
        assert cl.spec_approver_at_ready_transition("Spec Approver") is None

    def test_returns_none_when_approver_field_not_in_same_entry(self) -> None:
        histories = [
            _history("h1", "2026-03-13T10:00:00Z", items=[_status_item("Done Specifying", "Ready")]),
            _history("h2", "2026-03-13T11:00:00Z", items=[_field_item("Spec Approver", None, "hector-id")]),
        ]
        cl = parse_changelog(histories)
        assert cl.spec_approver_at_ready_transition("Spec Approver") is None


# ---------------------------------------------------------------------------
# Historical description reconstruction
# ---------------------------------------------------------------------------


class TestDescriptionAt:
    def _cl(self) -> ParsedChangelog:
        histories = [
            _history("h1", "2026-03-10T00:00:00Z", items=[_field_item("description", "original", "v1")]),
            _history("h2", "2026-03-14T00:00:00Z", items=[_field_item("description", "v1", "v2-with-ac")]),
            _history("h3", "2026-03-16T00:00:00Z", items=[_field_item("description", "v2-with-ac", "v3-post-commit")]),
        ]
        return parse_changelog(histories)

    def test_description_at_before_all_edits_returns_from_value_of_first(self) -> None:
        cl = self._cl()
        result = cl.description_at(datetime(2026, 3, 9, tzinfo=UTC))
        assert result == "original"

    def test_description_at_between_edits(self) -> None:
        cl = self._cl()
        result = cl.description_at(datetime(2026, 3, 12, tzinfo=UTC))
        assert result == "v1"

    def test_description_at_exactly_on_edit_timestamp(self) -> None:
        cl = self._cl()
        result = cl.description_at(datetime(2026, 3, 14, tzinfo=UTC))
        assert result == "v2-with-ac"

    def test_description_at_after_all_edits(self) -> None:
        cl = self._cl()
        result = cl.description_at(datetime(2026, 3, 20, tzinfo=UTC))
        assert result == "v3-post-commit"

    def test_description_at_returns_none_when_no_edits(self) -> None:
        cl = parse_changelog([_history("h1", "2026-03-15T00:00:00Z", items=[_status_item("Ready", "In Implementation")])])
        assert cl.description_at(datetime(2026, 3, 15, tzinfo=UTC)) is None


# ---------------------------------------------------------------------------
# Status intervals and D7 days_in_status
# ---------------------------------------------------------------------------


class TestStatusIntervals:
    def _cl(self) -> ParsedChangelog:
        histories = [
            _history("h1", "2026-03-15T10:00:00Z", items=[_status_item("Ready", "In Implementation")]),
            _history("h2", "2026-03-20T14:00:00Z", items=[_status_item("In Implementation", "Done Implementing")]),
        ]
        return parse_changelog(histories)

    def test_status_intervals_returns_tuples(self) -> None:
        cl = self._cl()
        intervals = cl.status_intervals()
        assert intervals[0][0] == "In Implementation"
        assert intervals[0][1] == datetime(2026, 3, 15, 10, 0, tzinfo=UTC)
        assert intervals[0][2] == datetime(2026, 3, 20, 14, 0, tzinfo=UTC)
        assert intervals[1][0] == "Done Implementing"
        assert intervals[1][2] is None

    def test_empty_changelog_gives_empty_intervals(self) -> None:
        cl = parse_changelog([])
        assert cl.status_intervals() == []

    def test_days_in_status_covers_span(self) -> None:
        cl = self._cl()
        days = cl.days_in_status("In Implementation")
        assert date(2026, 3, 15) in days
        assert date(2026, 3, 20) in days
        assert date(2026, 3, 17) in days
        assert date(2026, 3, 21) not in days

    def test_days_in_status_empty_for_status_not_entered(self) -> None:
        cl = self._cl()
        assert cl.days_in_status("In Validation") == []


# ---------------------------------------------------------------------------
# D10 backward transition detection
# ---------------------------------------------------------------------------


class TestBackwardTransitions:
    def test_forward_only_returns_false(self) -> None:
        histories = [
            _history("h1", "2026-03-10T00:00:00Z", items=[_status_item("Backlog", "In Specification")]),
            _history("h2", "2026-03-12T00:00:00Z", items=[_status_item("In Specification", "Done Specifying")]),
            _history("h3", "2026-03-15T00:00:00Z", items=[_status_item("Done Specifying", "Ready")]),
        ]
        cl = parse_changelog(histories)
        assert cl.has_backward_transitions() is False

    def test_backward_transition_detected(self) -> None:
        histories = [
            _history("h1", "2026-03-15T00:00:00Z", items=[_status_item("In Implementation", "Ready")]),
        ]
        cl = parse_changelog(histories)
        assert cl.has_backward_transitions() is True

    def test_backward_transitions_list(self) -> None:
        histories = [
            _history("h1", "2026-03-12T00:00:00Z", items=[_status_item("In Specification", "Done Specifying")]),
            _history("h2", "2026-03-15T00:00:00Z", items=[_status_item("In Implementation", "Ready")]),
        ]
        cl = parse_changelog(histories)
        bw = cl.backward_transitions()
        assert len(bw) == 1
        assert bw[0].from_status == "In Implementation"
        assert bw[0].to_status == "Ready"

    def test_unknown_status_not_counted_as_backward(self) -> None:
        histories = [
            _history("h1", "2026-03-15T00:00:00Z", items=[_status_item("In Implementation", "Cancelled")]),
        ]
        cl = parse_changelog(histories)
        assert cl.has_backward_transitions() is False

    def test_kanban_order_has_eight_stages(self) -> None:
        assert len(KANBAN_ORDER) == 8
        assert KANBAN_ORDER[3] == "Ready"
        assert KANBAN_ORDER[4] == "In Implementation"
