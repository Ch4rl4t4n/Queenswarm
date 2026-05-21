"""Unit coverage for marketplace/registry service helpers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services import tool_marketplace
from app.infrastructure.connectors.dynamic.models import DynamicConnectorCacheRow


@pytest.mark.asyncio
async def test_tool_registry_snapshot_filters_manager_and_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    """Registry rows respect tool-level manager filters and rank by goal overlap."""

    async def _fake_snapshots(_session: object) -> tuple[DynamicConnectorCacheRow, ...]:
        return (
            DynamicConnectorCacheRow(
                slug="notion",
                display_name="Notion",
                base_url="https://api.notion.com",
                auth_type="oauth2",
                mcp_manifest={
                    "tools": [
                        {
                            "name": "search_pages",
                            "description": "Search workspace pages",
                            "allowed_manager_slugs": ["research_intelligence"],
                        },
                        {"name": "write_page", "description": "Create page", "allowed_manager_slugs": ["execution_operations"]},
                    ],
                },
                allowed_manager_slugs=(),
                is_active=True,
                is_builtin=False,
                builtin_kind=None,
            ),
        )

    monkeypatch.setattr(tool_marketplace.DynamicConnectorHub, "snapshots", _fake_snapshots)
    rows = await tool_marketplace.tool_registry_snapshot(
        session=SimpleNamespace(),
        manager_slug="research_intelligence",
        goal="search knowledge pages",
        limit=10,
    )
    assert len(rows) == 1
    assert rows[0]["tool_name"] == "search_pages"
    assert float(rows[0]["score"]) > 0.0


@pytest.mark.asyncio
async def test_install_marketplace_entry_unsupported_source_returns_stub() -> None:
    """Unknown source is rejected as unsupported without side effects."""

    status, connector = await tool_marketplace.install_marketplace_entry(
        session=SimpleNamespace(),
        dashboard_user_id=uuid.uuid4(),
        source="community_registry",
        entry_id="x",
    )
    assert status == "unsupported_source"
    assert connector is None


def test_venice_mcp_template_has_cost_speed_hints() -> None:
    """Venice preset ships orchestration hints on every tool row."""

    from app.infrastructure.connectors.phase3.catalog import get_phase3_template

    tpl = get_phase3_template("venice_mcp")
    assert tpl.category == "ai"
    assert tpl.suggested_slug == "venice_mcp"
    assert len(tpl.tools) >= 8
    for tool in tpl.tools:
        assert tool.get("cost_tier") in {"low", "medium", "high"}
        assert tool.get("latency_tier") in {"fast", "balanced", "slow"}


@pytest.mark.asyncio
async def test_tool_rows_include_cost_latency_hints() -> None:
    """Manifest tool hints propagate into registry rows."""

    rows = tool_marketplace._tool_rows_from_manifest(
        connector_slug="venice_mcp",
        connector_display_name="Venice",
        manifest={
            "tools": [
                {
                    "name": "chat_completions",
                    "description": "Chat",
                    "cost_tier": "medium",
                    "latency_tier": "balanced",
                },
            ],
        },
        is_active=True,
    )
    assert rows[0]["cost_tier"] == "medium"
    assert rows[0]["latency_tier"] == "balanced"


@pytest.mark.asyncio
async def test_tool_hub_overview_includes_venice_preset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hub overview bundles registry + featured Venice preset."""

    async def _fake_catalog(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "phase3_templates": [
                {
                    "id": "venice_mcp",
                    "title": "Venice AI · MCP Hub",
                    "installed": False,
                    "featured": True,
                },
            ],
            "plugins_builtin": [],
            "plugins_user": [],
        }

    async def _fake_registry(*_args: object, **_kwargs: object) -> list[dict[str, object]]:
        return [{"connector_slug": "venice_mcp", "tool_name": "chat_completions", "score": 0.5}]

    monkeypatch.setattr(tool_marketplace, "marketplace_catalog", _fake_catalog)
    monkeypatch.setattr(tool_marketplace, "tool_registry_snapshot", _fake_registry)

    payload = await tool_marketplace.tool_hub_overview(
        session=SimpleNamespace(),
        dashboard_user_id=uuid.uuid4(),
        goal="chat",
    )
    assert payload["venice_preset"]["id"] == "venice_mcp"
    assert payload["featured_presets"][0]["featured"] is True
    assert payload["registry"][0]["tool_name"] == "chat_completions"
    assert payload["goal"] == "chat"
