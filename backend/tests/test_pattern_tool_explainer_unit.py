"""Unit tests for AL4 pattern + tool explainer service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.pattern_tool_explainer_service import (
    compose_pattern_tool_explainer,
    derive_pattern_tool_explainer,
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
    goal: str = "Research competitors and publish launch pack",
    sub_agents: list[SimpleNamespace] | None = None,
    agentic_patterns: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        task_id=uuid.uuid4(),
        goal=goal,
        context_summary={
            "raw_goal": goal,
            "agentic_patterns": agentic_patterns
            or {
                "primary": ["planning", "multi_agent", "tool_use", "reflection"],
                "secondary": ["rag", "guardrails", "human_in_the_loop"],
                "rationale": ["baseline: planning + multi-agent + RAG + guardrails"],
            },
        },
        sub_agents=sub_agents or [],
    )


def test_derive_pattern_tool_explainer_phase_and_sub_chips() -> None:
    researcher_id = uuid.uuid4()
    publisher_id = uuid.uuid4()
    session = _session(
        sub_agents=[
            SimpleNamespace(
                id=researcher_id,
                role="researcher",
                status="completed",
                toolset=["web_search"],
                short_memory={"discovered_tools": ["web_search"]},
            ),
            SimpleNamespace(
                id=publisher_id,
                role="publisher",
                status="needs_input",
                toolset=["post_message"],
                short_memory={},
            ),
        ],
    )
    events = [
        _event(
            "tool_execute",
            message="Simulated: slack/post_message",
            payload={"tool_name": "post_message", "connector_slug": "slack"},
            sub_id=publisher_id,
        ),
        _event(
            "dynamic_tools_discovered",
            payload={"tools": ["web_search"]},
            sub_id=researcher_id,
        ),
    ]
    registry = [
        {
            "tool_name": "post_message",
            "connector_display_name": "Slack Post",
            "description": "Send channel message",
        },
        {"tool_name": "web_search", "connector_display_name": "Web Search"},
    ]

    panel = derive_pattern_tool_explainer(session=session, events=events, registry_rows=registry)

    assert panel.visible is True
    assert len(panel.chips) >= 6
    phase_ids = {chip.phase_id for chip in panel.chips if chip.phase_id}
    assert phase_ids == {"goal", "plan", "tool", "verify"}
    tool_phase = next(chip for chip in panel.chips if chip.phase_id == "tool")
    assert tool_phase.tool_name == "post_message"
    assert tool_phase.tool_label == "Slack Post"
    assert "Tool:" in tool_phase.explainer
    sub_roles = {chip.sub_agent_role for chip in panel.chips if chip.sub_agent_role}
    assert "researcher" in sub_roles
    assert "publisher" in sub_roles
    assert panel.pattern_rationale


def test_derive_pattern_tool_explainer_router_fallback_without_context_patterns() -> None:
    session = _session(
        goal="Build and deploy landing page with browser automation",
        agentic_patterns=None,
        sub_agents=[
            SimpleNamespace(
                id=uuid.uuid4(),
                role="browser",
                status="running",
                toolset=["browser_navigate"],
                short_memory={},
            ),
        ],
    )
    session.context_summary = {"raw_goal": session.goal}

    panel = derive_pattern_tool_explainer(session=session, events=[], registry_rows=[])

    assert panel.visible is True
    browser_chip = next(
        chip for chip in panel.chips if chip.sub_agent_role == "browser"
    )
    assert browser_chip.pattern_id == "tool_use"
    assert browser_chip.tool_name == "browser_navigate"


def test_derive_pattern_tool_explainer_empty_session_not_visible() -> None:
    session = _session(sub_agents=[], agentic_patterns={"primary": [], "secondary": [], "rationale": []})
    session.context_summary = {"raw_goal": "", "agentic_patterns": {"primary": [], "secondary": []}}

    panel = derive_pattern_tool_explainer(session=session, events=[], registry_rows=[])

    assert panel.visible is False
    assert panel.chips == []


@pytest.mark.asyncio
async def test_compose_pattern_tool_explainer_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "pattern_tool_explainer_enabled", False)
    session_row = _session()
    db = AsyncMock()

    result = await compose_pattern_tool_explainer(db, supervisor_session=session_row)

    assert result.enabled is False
    assert result.visible is False


@pytest.mark.asyncio
async def test_compose_pattern_tool_explainer_loads_events_and_registry() -> None:
    sub_id = uuid.uuid4()
    session_row = _session(
        sub_agents=[
            SimpleNamespace(
                id=sub_id,
                role="publisher",
                status="needs_input",
                toolset=["post_message"],
                short_memory={},
            ),
        ],
    )
    db = AsyncMock()
    fake_events = [
        _event(
            "tool_execute",
            payload={"tool_name": "post_message", "connector_slug": "slack"},
            sub_id=sub_id,
        ),
    ]
    fake_registry = [{"tool_name": "post_message", "connector_display_name": "Slack Post"}]

    with (
        patch(
            "app.application.services.supervisor.session_service.list_session_events",
            AsyncMock(return_value=fake_events),
        ),
        patch(
            "app.application.services.tool_marketplace.tool_registry_snapshot",
            AsyncMock(return_value=fake_registry),
        ),
    ):
        result = await compose_pattern_tool_explainer(db, supervisor_session=session_row)

    assert result.enabled is True
    assert result.visible is True
    assert any(chip.tool_name == "post_message" for chip in result.chips)
