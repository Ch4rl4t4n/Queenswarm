"""Phase 8 — telemetry, external auto-approve, auto browser step."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.execution_studio_telemetry import build_activity_telemetry
from app.application.services.supervisor.initiative import _build_drafts


def test_build_activity_telemetry_counts() -> None:
    """Telemetry aggregates event types and cost blocks."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "execution_studio": {
                "recent_activity": [
                    {
                        "event_type": "tool_execute",
                        "message": "Executed: notion/search",
                        "payload": {},
                        "at": "2026-05-21T12:00:00+00:00",
                    },
                    {
                        "event_type": "tool_execute",
                        "message": "dynamic_invoke_error: cost_tier_blocked (high > max medium)",
                        "payload": {},
                        "at": "2026-05-21T12:01:00+00:00",
                    },
                    {
                        "event_type": "browser_step",
                        "message": "Browser simulate",
                        "payload": {},
                        "at": "2026-05-21T12:02:00+00:00",
                    },
                ],
            },
        },
    )
    tel = build_activity_telemetry(tenant, limit=40)
    assert tel["tool_executes"] == 2
    assert tel["browser_steps"] == 1
    assert tel["cost_tier_blocks"] == 1


def test_external_proposal_auto_approve_eligible() -> None:
    """External domain + tool_failure yields low-risk auto-approve eligible draft."""

    drafts = _build_drafts(
        role="researcher",
        goal="Post update to slack channel for launch",
        selected_skills=["execution-studio"],
        retrieval_sections=["default"],
        meta_reasoning={"issues": ["tool_failure"], "strategy_score": 0.65},
        reflections=[],
    )
    ext = next((d for d in drafts if d.proposal_type == "execution_studio_external"), None)
    assert ext is not None
    assert ext.risk_level == "low"
    assert ext.requires_manual_approval is False
    assert ext.proposal_payload.get("auto_approved_eligible") is True


@pytest.mark.asyncio
async def test_auto_browser_harness_step_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auto browser step runs simulate mode once per session."""

    from app.application.services.supervisor import browser_fallback as mod
    from app.infrastructure.persistence.models.supervisor_session import SupervisorSession, SubAgentSession

    calls = 0

    async def _fake_step(*_a: object, **kwargs: object) -> dict:
        nonlocal calls
        calls += 1
        mode = str(kwargs.get("mode") or "simulate")
        if mode == "live":
            return {"ok": False, "error": "approval_required", "mode": "live"}
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
    assert calls == 2
    assert sup.context_summary.get("browser_auto_step_at")
    assert sup.context_summary.get("browser_auto_step_live", {}).get("pending_approval") is True

    out2 = await mod.maybe_auto_browser_harness_step(
        _Db(),  # type: ignore[arg-type]
        supervisor_session=sup,
        failed_sub_agent=sub,
        meta_reasoning={"issues": ["tool_failure"]},
        output_text="dynamic_invoke_error: circuit_open",
    )
    assert out2 is None
    assert calls == 2
