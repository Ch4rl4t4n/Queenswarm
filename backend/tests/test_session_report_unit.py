"""Unit tests for supervisor session operator report builders."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.application.services.supervisor.session_report import (
    build_supervisor_session_report_html,
    build_supervisor_session_report_markdown,
    build_supervisor_session_report_pdf,
)


def test_build_supervisor_session_report_markdown_includes_sections() -> None:
    """Markdown report includes audit, context history, and timeline sections."""

    session_id = uuid.uuid4()
    generated_at = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)
    body = build_supervisor_session_report_markdown(
        session_id=session_id,
        session={
            "goal": "Investigate latency",
            "status": "running",
            "runtime_mode": "durable",
            "sub_agents": [{"role": "researcher", "status": "running", "runtime_mode": "durable"}],
        },
        audit_rows=[{"created_at": generated_at, "action": "supervisor_session_create", "payload": {}}],
        event_rows=[{"occurred_at": generated_at, "event_type": "session_started", "message": "Started"}],
        context_history=[
            {
                "created_at": generated_at,
                "action": "supervisor_session_control",
                "context_diff": {"changed": {"requeued_sub_agents": {"before": 0, "after": 2}}},
            },
        ],
        generated_at=generated_at,
    )
    assert "Operator audit" in body
    assert "Context history" in body
    assert "Session timeline" in body
    assert "supervisor_session_create" in body


def test_build_supervisor_session_report_html_escapes_goal() -> None:
    """HTML report escapes user-controlled session goal text."""

    session_id = uuid.uuid4()
    generated_at = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)
    body = build_supervisor_session_report_html(
        session_id=session_id,
        session={"goal": "<script>alert(1)</script>", "status": "running", "runtime_mode": "durable", "sub_agents": []},
        audit_rows=[],
        event_rows=[],
        context_history=[],
        generated_at=generated_at,
    )
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body


def test_build_supervisor_session_report_pdf_returns_pdf_magic_bytes() -> None:
    """PDF builder returns a valid PDF document header."""

    session_id = uuid.uuid4()
    generated_at = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)
    payload = build_supervisor_session_report_pdf(
        session_id=session_id,
        session={
            "goal": "Latency investigation",
            "status": "running",
            "runtime_mode": "durable",
            "sub_agents": [{"role": "researcher", "status": "running", "runtime_mode": "durable"}],
        },
        audit_rows=[{"created_at": generated_at, "action": "supervisor_session_create", "payload": {}}],
        event_rows=[{"occurred_at": generated_at, "event_type": "session_started", "message": "Started"}],
        context_history=[],
        generated_at=generated_at,
    )
    assert payload.startswith(b"%PDF")
    assert len(payload) > 500
