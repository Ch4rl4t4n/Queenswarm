"""Unit tests for live MCP Ops Studio snapshot composition."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.mcp_ops_studio_snapshot import compose_mcp_ops_studio_snapshot


@pytest.mark.asyncio
async def test_compose_live_snapshot_from_marketplace(monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()

    monkeypatch.setattr(
        "app.application.services.mcp_ops_studio_snapshot.settings",
        SimpleNamespace(mcp_ops_studio_live_snapshot_enabled=True, tool_gap_signal_enabled=True),
    )

    async def fake_catalog(_session, *, dashboard_user_id: uuid.UUID) -> dict[str, object]:
        return {
            "phase3_templates": [
                {
                    "id": "github_rest",
                    "slug": "github_rest",
                    "title": "GitHub REST",
                    "auth_type": "api_key",
                    "tool_count": 4,
                    "installed": False,
                    "featured": True,
                },
            ],
        }

    with (
        patch(
            "app.application.services.mcp_ops_studio_snapshot.marketplace_catalog",
            new=fake_catalog,
        ),
        patch(
            "app.application.services.mcp_ops_studio_snapshot.list_tool_gaps",
            new=AsyncMock(return_value=[]),
        ),
    ):
        snapshot = await compose_mcp_ops_studio_snapshot(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
        )

    assert snapshot.source == "live"
    assert len(snapshot.catalog) == 1
    assert snapshot.catalog[0].provider == "GitHub REST"
    assert len(snapshot.install) == 1
    assert snapshot.install[0].template_id == "github_rest"


@pytest.mark.asyncio
async def test_compose_mock_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.application.services.mcp_ops_studio_snapshot.settings",
        SimpleNamespace(mcp_ops_studio_live_snapshot_enabled=False),
    )
    snapshot = await compose_mcp_ops_studio_snapshot(
        AsyncMock(),
        tenant_id=uuid.uuid4(),
        dashboard_user_id=uuid.uuid4(),
    )
    assert snapshot.source == "read_only_mock"
