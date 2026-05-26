"""Phase 9 — external auto-simulate, browser live gate, connector telemetry."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.execution_studio_external import (
    handoff_on_approved_external_proposal,
    infer_connector_slug_from_goal,
    infer_simulate_tool_name,
)
from app.application.services.execution_studio_telemetry import build_activity_telemetry
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion


def test_infer_connector_from_goal_slack() -> None:
    """Goal keywords map to connector slugs."""

    assert infer_connector_slug_from_goal("Post update to slack channel") == "slack_workspace"
    assert infer_simulate_tool_name("slack_workspace")


def test_build_activity_telemetry_by_connector() -> None:
    """Telemetry includes per-connector breakdown."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "execution_studio": {
                "recent_activity": [
                    {
                        "event_type": "tool_execute",
                        "message": "Simulated: notion_workspace/search",
                        "payload": {},
                        "at": "2026-05-21T12:00:00+00:00",
                    },
                    {
                        "event_type": "tool_execute",
                        "message": "Simulated: slack_workspace/post_message",
                        "payload": {"connector_slug": "slack_workspace"},
                        "at": "2026-05-21T12:01:00+00:00",
                    },
                    {
                        "event_type": "tool_execute",
                        "message": "dynamic_invoke_error: cost_tier_blocked notion_workspace",
                        "payload": {"connector_slug": "notion_workspace", "error": "cost_tier_blocked"},
                        "at": "2026-05-21T12:02:00+00:00",
                    },
                ],
            },
        },
    )
    tel = build_activity_telemetry(tenant, limit=40)
    assert tel["by_connector"]["notion_workspace"] == 2
    assert tel["by_connector"]["slack_workspace"] == 1
    assert tel["connector_cost_blocks"]["notion_workspace"] == 1


@pytest.mark.asyncio
async def test_external_proposal_handoff_simulate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Approved external proposal triggers simulate connector call."""

    simulate_calls: list[str] = []

    async def _fake_execute(*_a: object, **kwargs: object) -> dict:
        simulate_calls.append(str(kwargs.get("connector_slug")))
        return {"ok": True, "mode": "simulate", "executed": False}

    monkeypatch.setattr(
        "app.application.services.execution_studio_external.execute_studio_tool",
        _fake_execute,
    )

    async def _noop_activity(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(
        "app.application.services.execution_studio_external.persist_execution_activity",
        _noop_activity,
    )

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    suggestion = AgentSuggestion(
        tenant_id=tenant.id,
        proposal_type="execution_studio_external",
        proposed_by_role="researcher",
        title="External lane",
        description="Retry slack post",
        proposal_payload={"goal_excerpt": "Post update to slack channel"},
        risk_level="low",
        impact_score=0.4,
        status="approved",
        requires_manual_approval=False,
        evaluation_reason="external_simulate_lane_auto_ok",
    )
    suggestion.id = uuid.uuid4()

    class _Session:
        async def flush(self) -> None:
            return None

    out = await handoff_on_approved_external_proposal(
        _Session(),  # type: ignore[arg-type]
        suggestion=suggestion,
        tenant=tenant,  # type: ignore[arg-type]
        reviewer_subject=f"dashboard:{uuid.uuid4()}",
    )
    assert out is not None
    assert out.get("ok") is True
    assert simulate_calls == ["slack_workspace", "slack_workspace"]
    assert suggestion.proposal_payload.get("simulate_executed_at")


@pytest.mark.asyncio
async def test_auto_browser_live_pending_after_simulate(monkeypatch: pytest.MonkeyPatch) -> None:
    """After simulate ok, live step returns approval_required and stores pending state."""

    from app.application.services.supervisor import browser_fallback as mod
    from app.infrastructure.persistence.models.supervisor_session import SupervisorSession, SubAgentSession

    call_modes: list[str] = []

    async def _fake_step(*_a: object, **kwargs: object) -> dict:
        mode = str(kwargs.get("mode") or "simulate")
        call_modes.append(mode)
        if mode == "live":
            return {"ok": False, "error": "approval_required", "mode": "live", "preview": {"start_url": "https://example.com"}}
        return {"ok": True, "mode": "simulate"}

    monkeypatch.setattr(
        "app.application.services.execution_studio_browser.execute_browser_fallback_step",
        _fake_step,
    )

    async def _noop_event(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(mod, "append_event", _noop_event)

    async def _noop_persist(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(
        "app.application.services.execution_studio_activity.persist_execution_activity",
        _noop_persist,
    )

    sup = SupervisorSession(
        goal="Verify https://queenswarm.love after connector fail",
        status="running",
        runtime_mode="inprocess",
        context_summary={},
    )
    sup.id = uuid.uuid4()
    sub = SubAgentSession(
        supervisor_session_id=sup.id,
        role="researcher",
        status="completed",
        runtime_mode="inprocess",
        toolset=[],
        short_memory={},
        spawn_order=0,
    )
    sub.id = uuid.uuid4()

    class _Db:
        async def get(self, *_a: object, **_k: object) -> None:
            return None

    out = await mod.maybe_auto_browser_harness_step(
        _Db(),  # type: ignore[arg-type]
        supervisor_session=sup,
        failed_sub_agent=sub,
        meta_reasoning={"issues": ["tool_failure"]},
        output_text="dynamic_invoke_error: circuit_open",
    )
    assert out is not None
    assert call_modes == ["simulate", "live"]
    live_state = sup.context_summary.get("browser_auto_step_live")
    assert isinstance(live_state, dict)
    assert live_state.get("pending_approval") is True
