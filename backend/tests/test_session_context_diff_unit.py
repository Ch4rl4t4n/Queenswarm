"""Unit tests for supervisor session context_summary diff helpers."""

from __future__ import annotations

from app.application.services.supervisor.session_context_diff import compute_context_summary_diff


def test_compute_context_summary_diff_when_keys_change_then_returns_changed() -> None:
    """Diff helper reports changed top-level keys."""

    diff = compute_context_summary_diff(
        {"approval_state": "pending", "requeued_sub_agents": 0},
        {"approval_state": "approve", "requeued_sub_agents": 2},
    )
    assert diff["changed"]["approval_state"]["before"] == "pending"
    assert diff["changed"]["approval_state"]["after"] == "approve"
    assert diff["changed"]["requeued_sub_agents"]["after"] == 2


def test_compute_context_summary_diff_when_no_changes_then_empty() -> None:
    """Identical snapshots produce an empty diff."""

    snapshot = {"approval_state": "approve", "last_resume_at": "2026-05-19T12:00:00Z"}
    assert compute_context_summary_diff(snapshot, dict(snapshot)) == {}


def test_compute_context_summary_diff_when_nested_dict_changes_then_returns_nested() -> None:
    """Nested autonomy_state dict diffs are captured under nested."""

    diff = compute_context_summary_diff(
        {"autonomy_state": {"level": 1, "mode": "assist"}},
        {"autonomy_state": {"level": 2, "mode": "assist"}},
    )
    assert diff["nested"]["autonomy_state"]["changed"]["level"]["before"] == 1
    assert diff["nested"]["autonomy_state"]["changed"]["level"]["after"] == 2


def test_compute_context_summary_diff_when_journal_appends_then_returns_added_items() -> None:
    """List append mutations surface as nested added_items."""

    diff = compute_context_summary_diff(
        {"reflection_journal": [{"step": 1}]},
        {"reflection_journal": [{"step": 1}, {"step": 2, "note": "retry"}]},
    )
    assert diff["nested"]["reflection_journal"]["after_len"] == 2
    assert diff["nested"]["reflection_journal"]["added_items"][0]["step"] == 2
