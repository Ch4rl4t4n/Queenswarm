"""Unit tests for operator-friendly work digest."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.application.services.operator_work_digest import (
    build_operator_work_digest_email_text,
    build_operator_work_digest_markdown,
    build_operator_work_digest_telegram_text,
    human_session_goal,
    session_status_bucket,
    short_session_id,
)


def test_short_session_id_uses_tail() -> None:
    sid = uuid.UUID("54523f80-a366-4e48-acb8-7fb10a70a6fe")
    assert short_session_id(sid) == "S-A6FE"


def test_human_session_goal_prefers_raw_goal() -> None:
    row = SimpleNamespace(
        goal="=== MISSION ===\nGeneric solo mission",
        context_summary={"raw_goal": "Najman — fáze 0 tržní analýza"},
    )
    assert "Najman" in human_session_goal(row)  # type: ignore[arg-type]
    assert "MISSION" not in human_session_goal(row)  # type: ignore[arg-type]


def test_build_operator_work_digest_markdown_lists_done_sessions() -> None:
    session_id = uuid.uuid4()
    row = SimpleNamespace(
        id=session_id,
        status="completed",
        goal="fallback",
        context_summary={"raw_goal": "Najman marketing digest"},
        completed_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        task_id=None,
        sub_agents=[
            SimpleNamespace(role="researcher", last_output="SWOT complete for Najman e-shop."),
        ],
    )
    body = build_operator_work_digest_markdown(
        tenant_name="Hive Queen",
        window_hours=24,
        sessions=[row],  # type: ignore[list-item]
        routine_lane={},
        generated_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
    )
    assert "Daily work digest" in body
    assert "Done" in body
    assert "Najman marketing digest" in body
    assert short_session_id(session_id) in body
    assert "SWOT complete" in body
    assert "supervisor_session_delete" not in body


def test_session_status_bucket_when_auto_approve_and_already_approved_then_running() -> None:
    row = SimpleNamespace(
        status="needs_input",
        goal="Forager digest",
        context_summary={"approval_state": "approve"},
    )
    assert session_status_bucket(row, auto_approve_enabled=True) == "running"  # type: ignore[arg-type]


def test_session_status_bucket_when_auto_approve_and_pending_then_running() -> None:
    row = SimpleNamespace(
        status="needs_input",
        goal="Four lane digest",
        context_summary={},
    )
    assert session_status_bucket(row, auto_approve_enabled=True) == "running"  # type: ignore[arg-type]


def test_session_status_bucket_when_manual_mode_and_needs_input_then_needs_you() -> None:
    row = SimpleNamespace(
        status="needs_input",
        goal="Four lane digest",
        context_summary={},
    )
    assert session_status_bucket(row, auto_approve_enabled=False) == "needs_you"  # type: ignore[arg-type]


def test_build_operator_work_digest_email_text_has_no_markdown_bold() -> None:
    session_id = uuid.uuid4()
    row = SimpleNamespace(
        id=session_id,
        status="completed",
        goal="fallback",
        context_summary={"raw_goal": "Najman marketing digest"},
        completed_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        task_id=None,
        sub_agents=[
            SimpleNamespace(role="researcher", last_output="SWOT complete for Najman e-shop."),
        ],
    )
    body = build_operator_work_digest_email_text(
        tenant_name="Hive Queen",
        window_hours=24,
        sessions=[row],  # type: ignore[list-item]
        routine_lane={},
        generated_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        auto_approve_enabled=True,
    )
    assert "**" not in body
    assert "Task:" in body
    assert "auto-approve enabled" in body


def test_build_operator_work_digest_telegram_prioritizes_needs_input() -> None:
    done = SimpleNamespace(
        id=uuid.uuid4(),
        status="completed",
        goal="done goal",
        context_summary={},
        completed_at=None,
        updated_at=datetime.now(tz=UTC),
        task_id=None,
        sub_agents=[],
    )
    needs = SimpleNamespace(
        id=uuid.uuid4(),
        status="needs_input",
        goal="needs goal",
        context_summary={},
        completed_at=None,
        updated_at=datetime.now(tz=UTC),
        task_id=None,
        sub_agents=[],
    )
    text = build_operator_work_digest_telegram_text(
        tenant_name="Hive Queen",
        window_hours=24,
        sessions=[done, needs],  # type: ignore[list-item]
        routine_lane={},
        auto_approve_enabled=False,
    )
    assert "Requires manual approval" in text
    assert "Done" in text
    assert "**" not in text
