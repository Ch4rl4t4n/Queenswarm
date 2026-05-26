"""Phase 6 — research_then_action, parallel_hint, browser fallback."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.super_tool_router import (
    RouterInvokePlan,
    partition_research_action_slugs,
)


def test_partition_research_action_slugs() -> None:
    """Research slugs split from action routers."""

    research, action = partition_research_action_slugs(("monid_mcp", "composio_router", "apify_store"))
    assert research == ["monid_mcp", "apify_store"]
    assert action == ["composio_router"]


@pytest.mark.asyncio
async def test_parallel_hint_invokes_all(monkeypatch: pytest.MonkeyPatch) -> None:
    """Parallel hint mode gathers results from each connector slug."""

    from app.application.services import super_tool_router as mod

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    seen: list[str] = []

    async def _fake_one(_session: object, *, svc: object, slug: str, **_kwargs: object) -> tuple[str, str, str]:
        seen.append(slug)
        return slug, "invoke", f"payload-{slug}"

    monkeypatch.setattr(mod, "resolve_router_invoke_plan", lambda *_a, **_k: RouterInvokePlan(
        routing_mode="parallel_hint",
        connector_slugs=("monid_mcp", "apify_store"),
    ))
    monkeypatch.setattr(mod, "_invoke_one_slug", _fake_one)

    result = await mod.invoke_mcp_with_router_fallback(
        None,  # type: ignore[arg-type]
        tenant=tenant,  # type: ignore[arg-type]
        manager_slug="research_intelligence",
        connector_slug="monid_mcp",
        tool_name="discover",
        arguments={},
        agent_task_id="test",
    )
    assert "parallel_router_results" in result
    assert seen == ["monid_mcp", "apify_store"]


@pytest.mark.asyncio
async def test_research_then_action_requires_research_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    """Research phase must succeed before action invoke runs."""

    from app.application.services import super_tool_router as mod

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    calls: list[tuple[str, bool]] = []

    async def _fake_one(
        _session: object,
        *,
        svc: object,
        slug: str,
        prefer_research_tool: bool = False,
        **_kwargs: object,
    ) -> tuple[str, str, str]:
        calls.append((slug, prefer_research_tool))
        if prefer_research_tool:
            return slug, "discover", "dynamic_invoke_error: research miss"
        return slug, "invoke", "action-ok"

    monkeypatch.setattr(mod, "resolve_router_invoke_plan", lambda *_a, **_k: RouterInvokePlan(
        routing_mode="research_then_action",
        connector_slugs=("monid_mcp", "composio_router"),
    ))
    monkeypatch.setattr(mod, "_invoke_one_slug", _fake_one)

    result = await mod.invoke_mcp_with_router_fallback(
        None,  # type: ignore[arg-type]
        tenant=tenant,  # type: ignore[arg-type]
        manager_slug="research_intelligence",
        connector_slug="composio_router",
        tool_name="post_message",
        arguments={},
        agent_task_id="test",
    )
    assert "research phase produced no verified data" in result
    assert any(prefer for _slug, prefer in calls)


def test_healing_tool_failure_detection() -> None:
    """Browser fallback trigger detects dynamic invoke errors in output."""

    from app.application.services.supervisor.browser_fallback import _healing_has_tool_failure

    assert _healing_has_tool_failure({"issues": ["tool_failure"]}, "ok")
    assert _healing_has_tool_failure({}, "dynamic_invoke_error: circuit_open")
