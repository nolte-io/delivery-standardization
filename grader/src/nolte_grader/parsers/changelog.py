"""Changelog parser — spec §5.3, §6, §12.1/3.

Converts raw Jira changelog histories into structured domain objects that
evaluators can query without re-parsing JSON.

Responsibilities:
- Status transitions (for C1, Y4, Y5, Y6, U7, C2, C3, D4, D7, D8, D10).
- Field edits (for Y3a pre-commit AC, U7 post-commit AC/Scenarios, C3 approver).
- Historical description reconstruction (for C2 BDD at commitment).
- Status interval reconstruction (for D7 daily WIP state).

Out of scope: section extraction from description text — that is parsers/description.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from dateutil import parser as dateutil_parser

from nolte_grader.core.errors import ChangelogError
from nolte_grader.core.logging import get_logger

log = get_logger(__name__)

# Canonical kanban stage order — used by D10 backward-transition detection.
# Statuses outside this list (e.g., "Cancelled") are ignored for ordering.
# Nolte workflow: Backlog/In Backlog → Awaiting Specification → In Specification
#   → Done Specifying → In Implementation → Done Implementing → In Validation → Done
# Note: there is no "Ready" status in the Nolte Jira; commitment is Done Specifying → In Implementation.
KANBAN_ORDER: list[str] = [
    "Backlog",
    "In Backlog",
    "Awaiting Specification",
    "In Specification",
    "Done Specifying",
    "In Implementation",
    "Done Implementing",
    "In Validation",
    "Done",
]

_KANBAN_RANK: dict[str, int] = {s: i for i, s in enumerate(KANBAN_ORDER)}


def _parse_ts(value: str) -> datetime:
    """Parse a Jira ISO timestamp into a timezone-aware UTC datetime."""
    try:
        dt = dateutil_parser.parse(value)
    except (ValueError, OverflowError) as exc:
        raise ChangelogError(f"Cannot parse timestamp {value!r}: {exc}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True, order=True)
class StatusTransition:
    """One status transition extracted from a changelog history entry."""

    timestamp: datetime
    from_status: str
    to_status: str
    actor_account_id: str
    actor_display_name: str
    history_id: str


@dataclass(frozen=True)
class FieldEdit:
    """One field-value change extracted from a changelog history entry."""

    timestamp: datetime
    field_name: str
    from_value: str | None
    to_value: str | None
    actor_account_id: str
    history_id: str

    def _sort_key(self) -> tuple[datetime, str, str, str]:
        return (self.timestamp, self.field_name, self.from_value or "", self.to_value or "")


@dataclass
class ParsedChangelog:
    """Structured view of a Jira issue's full changelog.

    All lists are sorted by timestamp ascending. Callers should treat
    this as a read-only view — evaluators query it, they don't mutate it.
    """

    status_transitions: list[StatusTransition]
    field_edits: list[FieldEdit]

    # ------------------------------------------------------------------
    # Commitment and gate timestamps
    # ------------------------------------------------------------------

    def commitment_timestamp(self) -> datetime | None:
        """Time of the first ``Done Specifying → In Implementation`` transition.

        Per spec §6, this is the commitment point. The Nolte workflow has no
        "Ready" status — commitment fires on Done Specifying → In Implementation.
        Returns None if the Story never entered In Implementation from Done Specifying.
        """
        for t in self.status_transitions:
            if t.from_status == "Done Specifying" and t.to_status == "In Implementation":
                return t.timestamp
        return None

    def done_specifying_to_ready_timestamp(self) -> datetime | None:
        """Time of the commitment gate (Done Specifying → In Implementation).

        Kept for API compatibility; aliases commitment_timestamp().
        """
        return self.commitment_timestamp()

    def done_implementing_timestamp(self) -> datetime | None:
        """Time of the first transition into ``Done Implementing``."""
        return self._first_entry_into("Done Implementing")

    def done_timestamp(self) -> datetime | None:
        """Time of the first transition into ``Done``."""
        return self._first_entry_into("Done")

    def _first_entry_into(self, status: str) -> datetime | None:
        for t in self.status_transitions:
            if t.to_status == status:
                return t.timestamp
        return None

    # ------------------------------------------------------------------
    # Transition queries
    # ------------------------------------------------------------------

    def transitions_to(self, status: str) -> list[StatusTransition]:
        return [t for t in self.status_transitions if t.to_status == status]

    def transitions_from(self, status: str) -> list[StatusTransition]:
        return [t for t in self.status_transitions if t.from_status == status]

    def transitions_from_to(self, from_status: str, to_status: str) -> list[StatusTransition]:
        return [
            t for t in self.status_transitions
            if t.from_status == from_status and t.to_status == to_status
        ]

    def actor_who_transitioned_to(self, status: str) -> str | None:
        """Return the ``accountId`` of the actor who first transitioned into ``status``."""
        transitions = self.transitions_to(status)
        return transitions[0].actor_account_id if transitions else None

    # ------------------------------------------------------------------
    # Field edit queries
    # ------------------------------------------------------------------

    def field_edits_for(self, field_name: str) -> list[FieldEdit]:
        """All edits to ``field_name``, sorted by timestamp ascending."""
        return [e for e in self.field_edits if e.field_name == field_name]

    def field_edits_after(self, field_name: str, timestamp: datetime) -> list[FieldEdit]:
        """Edits to ``field_name`` that occurred strictly after ``timestamp``."""
        return [
            e for e in self.field_edits
            if e.field_name == field_name and e.timestamp > timestamp
        ]

    def field_edits_in_same_entry(self, history_id: str, field_name: str) -> list[FieldEdit]:
        """Field edits for ``field_name`` that share a history entry with ``history_id``.

        Used by C3: find the Spec Approver field edit that happened in the same
        Jira history event as the Done Specifying → Ready status transition.
        """
        return [
            e for e in self.field_edits
            if e.history_id == history_id and e.field_name == field_name
        ]

    def spec_approver_at_ready_transition(self, spec_approver_field_name: str) -> str | None:
        """Return the Spec Approver field value set at the commitment gate.

        Looks in the same changelog entry as the Done Specifying → In Implementation
        transition (the Nolte commitment gate). Returns ``to_value`` if found.
        """
        gate = self.transitions_from_to("Done Specifying", "In Implementation")
        if not gate:
            return None
        history_id = gate[0].history_id
        edits = self.field_edits_in_same_entry(history_id, spec_approver_field_name)
        return edits[0].to_value if edits else None

    # ------------------------------------------------------------------
    # Historical description reconstruction
    # ------------------------------------------------------------------

    def description_at(self, timestamp: datetime) -> str | None:
        """Best-effort description text at ``timestamp``.

        Returns the ``toString`` of the last description edit at or before
        ``timestamp``. If all edits are after ``timestamp``, returns the
        ``fromString`` of the earliest edit (the pre-edit state).
        Returns None when no description edits exist in the changelog at all
        — the caller should fall back to the current ``fields.description``.

        Note: Jira Cloud changelog stores description edits as text
        representations of ADF, not raw ADF. These are sufficient for section
        detection (finding ## headings) but may differ from the full ADF
        structure available in current ``fields.description``.
        """
        edits = self.field_edits_for("description")
        if not edits:
            return None
        before = [e for e in edits if e.timestamp <= timestamp]
        if not before:
            return edits[0].from_value
        return before[-1].to_value

    # ------------------------------------------------------------------
    # Status interval reconstruction
    # ------------------------------------------------------------------

    def status_intervals(self) -> list[tuple[str, datetime, datetime | None]]:
        """Return ``(status, entered_at, left_at)`` intervals in chronological order.

        The last interval has ``left_at=None`` (still active, or no further transition).
        Intervals where the status is unknown at the start (before the first recorded
        transition) are not included — the first known interval starts at the first
        transition's target status.
        """
        if not self.status_transitions:
            return []
        intervals: list[tuple[str, datetime, datetime | None]] = []
        for i, t in enumerate(self.status_transitions):
            entered_at = t.timestamp
            left_at = self.status_transitions[i + 1].timestamp if i + 1 < len(self.status_transitions) else None
            intervals.append((t.to_status, entered_at, left_at))
        return intervals

    def days_in_status(self, status: str) -> list[date]:
        """Return all UTC calendar days the issue was in ``status``.

        A day is included if the issue was in ``status`` at any point during
        that day (i.e., entry timestamp ≤ end-of-day AND either no exit or
        exit after start-of-day). Used by D7 for daily WIP reconstruction.
        """
        days: set[date] = set()
        for interval_status, entered_at, left_at in self.status_intervals():
            if interval_status != status:
                continue
            current = entered_at.date()
            end = left_at.date() if left_at else datetime.now(timezone.utc).date()
            while current <= end:
                days.add(current)
                current = _next_day(current)
        return sorted(days)

    # ------------------------------------------------------------------
    # D10 backward transition detection
    # ------------------------------------------------------------------

    def has_backward_transitions(
        self,
        ordered_statuses: list[str] | None = None,
    ) -> bool:
        """True if any transition moves backward in the kanban order.

        Statuses not present in ``ordered_statuses`` (or ``KANBAN_ORDER``)
        are ignored rather than failing — handles custom/cancelled statuses.
        """
        rank = {s: i for i, s in enumerate(ordered_statuses or KANBAN_ORDER)}
        for t in self.status_transitions:
            from_rank = rank.get(t.from_status)
            to_rank = rank.get(t.to_status)
            if from_rank is not None and to_rank is not None and to_rank < from_rank:
                return True
        return False

    def backward_transitions(
        self,
        ordered_statuses: list[str] | None = None,
    ) -> list[StatusTransition]:
        """Return all backward transitions (for reporting in the rollup)."""
        rank = {s: i for i, s in enumerate(ordered_statuses or KANBAN_ORDER)}
        return [
            t for t in self.status_transitions
            if (r_from := rank.get(t.from_status)) is not None
            and (r_to := rank.get(t.to_status)) is not None
            and r_to < r_from
        ]


def _next_day(d: date) -> date:
    from datetime import timedelta
    return d + timedelta(days=1)


def parse_changelog(histories: list[dict[str, Any]]) -> ParsedChangelog:
    """Parse raw Jira changelog histories into a ``ParsedChangelog``.

    ``histories`` is the list from ``issue["changelog"]["histories"]`` or
    the ``values`` list from the paginated ``/changelog`` endpoint.

    Raises ``ChangelogError`` on unrecoverable structural problems (missing
    required keys). Logs warnings for unexpected-but-tolerable shapes.
    """
    transitions: list[StatusTransition] = []
    edits: list[FieldEdit] = []

    for entry in histories:
        history_id = str(entry.get("id", ""))
        created_raw = entry.get("created")
        if not created_raw:
            log.warning("changelog entry missing 'created' field", history_id=history_id)
            continue
        try:
            timestamp = _parse_ts(created_raw)
        except ChangelogError as exc:
            log.warning("skipping changelog entry with unparseable timestamp", error=str(exc))
            continue

        author = entry.get("author") or {}
        actor_id = author.get("accountId", "")
        actor_name = author.get("displayName", "")

        for item in entry.get("items", []):
            field_name: str = item.get("field", "")
            from_string: str | None = item.get("fromString")
            to_string: str | None = item.get("toString")

            if field_name == "status":
                if not from_string or not to_string:
                    log.warning(
                        "status item missing fromString/toString",
                        history_id=history_id,
                    )
                    continue
                transitions.append(
                    StatusTransition(
                        timestamp=timestamp,
                        from_status=from_string,
                        to_status=to_string,
                        actor_account_id=actor_id,
                        actor_display_name=actor_name,
                        history_id=history_id,
                    )
                )
            else:
                edits.append(
                    FieldEdit(
                        timestamp=timestamp,
                        field_name=field_name,
                        from_value=from_string,
                        to_value=to_string,
                        actor_account_id=actor_id,
                        history_id=history_id,
                    )
                )

    transitions.sort()
    edits.sort(key=lambda e: e._sort_key())
    return ParsedChangelog(status_transitions=transitions, field_edits=edits)
