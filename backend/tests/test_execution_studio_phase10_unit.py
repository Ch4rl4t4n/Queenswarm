"""Phase 10 — notifications, external live gate, connector chart, supervisor chain."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.execution_studio_notifications import notify_browser_live_pending
from app.application.services.execution_studio_telemetry import build_activity_telemetry
from app.application.services.supervisor.initiative import _build_drafts
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion


def test_connector_chart_series() -> None:
    """Telemetry exposes recharts-friendly connector_chart rows."""

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
                        "message": "cost_tier_blocked",
                        "payload": {"connector_slug": "notion_workspace", "error": "cost_tier_blocked"},
                        "at": "2026-05-21T12:01:00+00:00",
                    },
                ],
            },
        },
    )
    tel = build_activity_telemetry(tenant, limit=40)
    assert len(tel["connector_chart"]) == 1
    assert tel["connector_chart"][0]["slug"] == "notion_workspace"
    assert tel["connector_chart"][0]["runs"] == 2
    assert tel["connector_chart"][0]["blocks"] == 1


@pytest.mark.asyncio
async def test_notify_browser_live_pending_calls_slack(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pending browser live step triggers Slack webhook notification."""

    calls: list[str] = []

    async def _fake_slack(message: str, **_k: object) -> bool:
        calls.append(message)
        return True

    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_slack",
        _fake_slack,
    )
    async def _fake_discord(*_a: object, **_k: object) -> bool:
        return False

    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_discord",
        _fake_discord,
    )
    async def _fake_teams(*_a: object, **_k: object) -> bool:
        return False

    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_teams",
        _fake_teams,
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications._resolve_webhook",
        lambda *_a, **_k: "https://hooks.slack.com/test",
    )

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    out = await notify_browser_live_pending(
        tenant=tenant,  # type: ignore[arg-type]
        supervisor_session_id=uuid.uuid4(),
        goal_excerpt="Verify pricing page",
        start_url="https://queenswarm.love",
    )
    assert out["slack"] is True
    assert len(calls) == 1
    assert "Live harness step requires operator confirmation" in calls[0]


@pytest.mark.asyncio
async def test_external_proposal_live_pending_after_simulate(monkeypatch: pytest.MonkeyPatch) -> None:
    """External simulate ok → live attempt returns approval_required + notifies."""

    modes: list[str] = []
    notify_calls: list[str] = []

    async def _fake_tool(*_a: object, **kwargs: object) -> dict:
        mode = str(kwargs.get("mode") or "simulate")
        modes.append(mode)
        if mode == "live":
            return {"ok": False, "error": "approval_required", "preview": {"connector_slug": "slack_workspace"}}
        return {"ok": True, "mode": "simulate", "executed": False}

    monkeypatch.setattr(
        "app.application.services.execution_studio_external.execute_studio_tool",
        _fake_tool,
    )

    async def _noop_activity(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(
        "app.application.services.execution_studio_external.persist_execution_activity",
        _noop_activity,
    )

    async def _fake_notify(*_a: object, **kwargs: object) -> dict:
        notify_calls.append(str(kwargs.get("connector_slug")))
        return {"slack": True, "discord": False, "teams": False}

    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_external_live_pending",
        _fake_notify,
    )

    from app.application.services.execution_studio_external import execute_external_proposal_simulate

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

    out = await execute_external_proposal_simulate(
        _Session(),  # type: ignore[arg-type]
        tenant=tenant,  # type: ignore[arg-type]
        suggestion=suggestion,
        dashboard_user_id=uuid.uuid4(),
    )
    assert modes == ["simulate", "live"]
    assert out.get("live_pending_approval") is True
    assert suggestion.proposal_payload.get("live_pending_approval") is True
    assert notify_calls == ["slack_workspace"]


@pytest.mark.asyncio
async def test_supervisor_failure_chain_initiative_and_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool failure → browser auto step + external initiative draft in one chain."""

    from app.application.services.supervisor import browser_fallback as browser_mod
    from app.infrastructure.persistence.models.supervisor_session import SupervisorSession, SubAgentSession

    call_modes: list[str] = []

    async def _fake_browser(*_a: object, **kwargs: object) -> dict:
        mode = str(kwargs.get("mode") or "simulate")
        call_modes.append(mode)
        if mode == "live":
            return {"ok": False, "error": "approval_required", "mode": "live", "preview": {"start_url": "https://x.com"}}
        return {"ok": True, "mode": "simulate"}

    monkeypatch.setattr(
        "app.application.services.execution_studio_browser.execute_browser_fallback_step",
        _fake_browser,
    )

    async def _noop_append(*_a: object, **_k: object) -> None:
        return None

    async def _noop_persist(*_a: object, **_k: object) -> None:
        return None

    async def _noop_notify(**_k: object) -> dict[str, bool]:
        return {"slack": True, "discord": False, "teams": False}

    monkeypatch.setattr(browser_mod, "append_event", _noop_append)
    monkeypatch.setattr(
        "app.application.services.execution_studio_activity.persist_execution_activity",
        _noop_persist,
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_browser_live_pending",
        _noop_notify,
    )

    sup = SupervisorSession(
        goal="Post launch update to slack after API failure",
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

    await browser_mod.maybe_auto_browser_harness_step(
        _Db(),  # type: ignore[arg-type]
        supervisor_session=sup,
        failed_sub_agent=sub,
        meta_reasoning={"issues": ["tool_failure"]},
        output_text="dynamic_invoke_error: circuit_open",
    )

    drafts = _build_drafts(
        role="researcher",
        goal=sup.goal,
        selected_skills=["execution-studio"],
        retrieval_sections=["default"],
        meta_reasoning={"issues": ["tool_failure"], "strategy_score": 0.6},
        reflections=[],
    )
    ext = next((d for d in drafts if d.proposal_type == "execution_studio_external"), None)

    assert call_modes == ["simulate", "live"]
    assert sup.context_summary.get("browser_auto_step_live", {}).get("pending_approval") is True
    assert ext is not None
    assert ext.requires_manual_approval is False
