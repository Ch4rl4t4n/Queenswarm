"""Unit tests for AL2 tool outcome panel service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.tool_outcome_panel_service import (
    compose_tool_outcome_panel,
    derive_tool_outcome_panel,
)


def _event(
    event_type: str,
    *,
    message: str = "",
    payload: dict | None = None,
    sub_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        event_type=event_type,
        message=message,
        payload=payload or {},
        sub_agent_session_id=sub_id,
        occurred_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )


def _session(
    *,
    status: str = "needs_input",
    approval_required: bool = False,
    approval_reason: str | None = None,
    sub_agents: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        task_id=None,
        context_summary={
            "approval_required": approval_required,
            "approval_reason": approval_reason,
            "loop_last_rubric_score": 0.72,
            "loop_min_score": 0.8,
        },
        sub_agents=sub_agents or [],
    )


def test_derive_tool_outcome_panel_from_tool_execute_event() -> None:
    sub_id = uuid.uuid4()
    session = _session(
        sub_agents=[SimpleNamespace(id=sub_id, role="publisher", status="needs_input", toolset=[], short_memory={})],
    )
    events = [
        _event(
            "tool_execute",
            message="Simulated: stripe/create_checkout",
            payload={
                "mode": "simulate",
                "executed": False,
                "connector_slug": "stripe",
                "tool_name": "create_checkout",
                "risk_tier": "financial",
                "arguments": {"amount": 9900, "currency": "usd"},
            },
            sub_id=sub_id,
        ),
    ]

    panel = derive_tool_outcome_panel(session=session, events=events)

    assert panel.visible is True
    assert len(panel.tools) == 1
    assert panel.tools[0].tool_name == "create_checkout"
    assert panel.tools[0].connector_slug == "stripe"
    assert panel.tools[0].mode == "simulate"
    assert "amount=9900" in panel.tools[0].args_summary
    assert panel.critic is not None
    assert panel.critic.passed is False


def test_derive_tool_outcome_panel_approval_requested() -> None:
    session = _session(approval_required=True, approval_reason="Critical action keyword detected: billing")
    events = [
        _event(
            "approval_requested",
            message="publisher requires approval before critical action.",
            payload={"reason": "Critical action keyword detected: billing"},
        ),
    ]

    panel = derive_tool_outcome_panel(session=session, events=events)

    assert panel.pending_approval is True
    assert panel.approval_reason == "Critical action keyword detected: billing"
    assert "billing" in panel.operator_action.lower()
    assert panel.tools[0].tool_name == "operator checkpoint"


def test_derive_tool_outcome_panel_includes_sub_agent_toolset() -> None:
    session = _session(
        sub_agents=[
            SimpleNamespace(
                id=uuid.uuid4(),
                role="researcher",
                status="needs_input",
                toolset=["web_search", "summarize"],
                short_memory={"last_summary": "Found 3 competitor pages."},
                last_output="Found 3 competitor pages.",
            ),
        ],
    )

    panel = derive_tool_outcome_panel(session=session, events=[])

    assert panel.visible is True
    names = {row.tool_name for row in panel.tools}
    assert "web_search" in names
    assert "summarize" in names


def test_derive_tool_outcome_panel_running_not_visible_without_tools() -> None:
    session = _session(status="running")
    session.context_summary = {}

    panel = derive_tool_outcome_panel(session=session, events=[])

    assert panel.visible is False


@pytest.mark.asyncio
async def test_compose_tool_outcome_panel_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "tool_outcome_panel_enabled", False)
    session_row = _session()
    db = AsyncMock()

    result = await compose_tool_outcome_panel(db, supervisor_session=session_row)

    assert result.enabled is False
    assert result.visible is False


@pytest.mark.asyncio
async def test_compose_tool_outcome_panel_loads_events() -> None:
    session_row = _session()
    db = AsyncMock()
    fake_events = [
        _event(
            "tool_execute",
            message="Simulated: slack/post_message",
            payload={"mode": "simulate", "connector_slug": "slack", "tool_name": "post_message", "executed": False},
        ),
    ]

    with patch(
        "app.application.services.supervisor.session_service.list_session_events",
        AsyncMock(return_value=fake_events),
    ):
        result = await compose_tool_outcome_panel(db, supervisor_session=session_row)

    assert result.enabled is True
    assert len(result.tools) >= 1
    assert result.tools[0].tool_name == "post_message"
