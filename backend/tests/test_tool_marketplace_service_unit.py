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
