"""Super Tool Router runtime invoke fallback."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.super_tool_router import (
    RouterInvokePlan,
    pick_fallback_tool_name,
    resolve_router_invoke_plan,
)


def test_resolve_router_invoke_plan_merges_lane() -> None:
    """Active routers for a lane produce invoke plan with routing mode."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "super_tool_routers": {
                "items": [
                    {
                        "id": str(uuid.uuid4()),
                        "name": "Deep Research",
                        "slug": "deep_research",
                        "description": "",
                        "is_active": True,
                        "routing_mode": "priority",
                        "manager_slugs": ["research_intelligence"],
                        "connector_slugs": ["monid_mcp", "apify_store"],
                        "fallback_builtin_search": True,
                    },
                ],
            },
        },
    )
    plan = resolve_router_invoke_plan(tenant, manager_slug="research_intelligence")  # type: ignore[arg-type]
    assert plan is not None
    assert plan.routing_mode == "priority"
    assert plan.connector_slugs == ("monid_mcp", "apify_store")


def test_pick_fallback_tool_name_prefers_discover() -> None:
    """Fallback picks discover/search-like tools when preferred missing."""

    manifest = {
        "tools": [
            {"name": "discover", "method": "POST"},
            {"name": "runs_get", "method": "GET"},
        ],
    }
    assert pick_fallback_tool_name(preferred="chat_completions", manifest=manifest) == "discover"


@pytest.mark.asyncio
async def test_invoke_mcp_with_router_fallback_tries_second(monkeypatch: pytest.MonkeyPatch) -> None:
    """Priority routing falls back to next connector slug on dynamic_invoke_error."""

    from app.application.services import super_tool_router as mod

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    calls: list[str] = []

    async def _fake_invoke(_session: object, *, connector_slug: str, **_kwargs: object) -> str:
        calls.append(connector_slug)
        if connector_slug == "monid_mcp":
            return "dynamic_invoke_error: circuit_open"
        return "ok_payload_from_apify"

    monkeypatch.setattr(mod, "resolve_router_invoke_plan", lambda *_a, **_k: RouterInvokePlan(
        routing_mode="priority",
        connector_slugs=("monid_mcp", "apify_store"),
    ))

    class _Row:
        mcp_manifest = {"tools": [{"name": "invoke", "method": "POST", "path": "/"}]}

    class _Svc:
        async def fetch_by_slug(self, *_a: object, **_k: object) -> _Row:
            return _Row()

    monkeypatch.setattr(
        "app.infrastructure.connectors.dynamic.service.DynamicConnectorService",
        lambda: _Svc(),
    )
    monkeypatch.setattr(
        "app.infrastructure.connectors.dynamic.service.invoke_dynamic_tool",
        _fake_invoke,
    )

    result = await mod.invoke_mcp_with_router_fallback(
        None,  # type: ignore[arg-type]
        tenant=tenant,  # type: ignore[arg-type]
        manager_slug="research_intelligence",
        connector_slug="monid_mcp",
        tool_name="discover",
        arguments={},
        agent_task_id="test",
    )
    assert "router_fallback_ok" in result
    assert calls == ["monid_mcp", "apify_store"]
