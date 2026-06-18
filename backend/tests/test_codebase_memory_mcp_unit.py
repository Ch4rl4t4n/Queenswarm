"""Unit tests for POS-I5 codebase-memory MCP connector."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.codebase_memory_mcp_service import (
    CODEBASE_MEMORY_MCP_SLUG,
    compose_codebase_memory_mcp_readiness,
    ensure_codebase_memory_connector,
    invoke_codebase_memory_tool,
)


@pytest.mark.asyncio
async def test_invoke_search_hive_mind_returns_json_hits() -> None:
    with patch(
        "app.application.services.codebase_memory_mcp_service.settings",
    ) as mock_settings:
        mock_settings.codebase_memory_mcp_enabled = True
        mock_settings.hive_mind_max_query_hits_vector = 8
        with patch(
            "app.application.services.codebase_memory_mcp_service.semantic_search",
            AsyncMock(
                return_value=[
                    {"id": "hit-1", "document": "Tech SCV digest", "metadata": {}, "distance": 0.12},
                ],
            ),
        ):
            raw = await invoke_codebase_memory_tool(
                tool_name="search_hive_mind",
                arguments={"q": "tech scv upgrade", "limit": 3},
            )

    payload = json.loads(raw)
    assert payload["count"] == 1
    assert payload["query"] == "tech scv upgrade"


@pytest.mark.asyncio
async def test_invoke_tech_health_snapshot_returns_report() -> None:
    with patch(
        "app.application.services.codebase_memory_mcp_service.settings",
    ) as mock_settings:
        mock_settings.codebase_memory_mcp_enabled = True
        with patch(
            "app.application.services.codebase_memory_mcp_service.build_tech_health_report",
            return_value={"health_score": 0.9, "signals": []},
        ):
            raw = await invoke_codebase_memory_tool(
                tool_name="tech_health_snapshot",
                arguments={},
            )

    payload = json.loads(raw)
    assert payload["health_score"] == 0.9


@pytest.mark.asyncio
async def test_invoke_disabled_returns_error() -> None:
    with patch(
        "app.application.services.codebase_memory_mcp_service.settings",
    ) as mock_settings:
        mock_settings.codebase_memory_mcp_enabled = False
        result = await invoke_codebase_memory_tool(
            tool_name="search_hive_mind",
            arguments={"q": "hello"},
        )
    assert "disabled" in result


@pytest.mark.asyncio
async def test_ensure_connector_skips_when_disabled() -> None:
    session = AsyncMock()
    with patch(
        "app.application.services.codebase_memory_mcp_service.settings",
    ) as mock_settings:
        mock_settings.codebase_memory_mcp_enabled = False
        ok = await ensure_codebase_memory_connector(session)
    assert ok is False


@pytest.mark.asyncio
async def test_readiness_reports_installed_connector() -> None:
    session = AsyncMock()
    row = MagicMock()
    row.is_active = True
    svc = MagicMock()
    svc.fetch_by_slug = AsyncMock(return_value=row)
    with patch(
        "app.application.services.codebase_memory_mcp_service.settings",
    ) as mock_settings:
        mock_settings.codebase_memory_mcp_enabled = True
        with patch(
            "app.application.services.codebase_memory_mcp_service.DynamicConnectorService",
            return_value=svc,
        ):
            payload = await compose_codebase_memory_mcp_readiness(session)

    assert payload["connector_slug"] == CODEBASE_MEMORY_MCP_SLUG
    assert payload["ready"] is True
    assert "search_hive_mind" in payload["tools"]


@pytest.mark.asyncio
async def test_dynamic_invoke_routes_codebase_memory_builtin() -> None:
    from app.infrastructure.connectors.dynamic.models import DynamicConnectorCacheRow
    from app.infrastructure.connectors.dynamic.service import invoke_dynamic_tool

    row = MagicMock()
    row.slug = CODEBASE_MEMORY_MCP_SLUG
    row.is_active = True
    row.builtin_kind = "codebase_memory"
    row.dashboard_user_id = None
    row.mcp_manifest = {
        "tools": [{"name": "tech_health_snapshot", "path": "/tech-health", "method": "GET"}],
    }
    row.auth_type = "none"
    row.allowed_manager_slugs = ["execution_operations"]

    svc = MagicMock()
    svc.fetch_by_slug = AsyncMock(return_value=row)
    svc._secrets_dict = MagicMock(return_value={})

    snap = DynamicConnectorCacheRow(
        slug=CODEBASE_MEMORY_MCP_SLUG,
        display_name="Codebase Memory MCP",
        base_url="internal://codebase-memory",
        auth_type="none",
        mcp_manifest=row.mcp_manifest,
        allowed_manager_slugs=("execution_operations",),
        is_active=True,
        is_builtin=True,
        builtin_kind="codebase_memory",
    )

    with patch("app.infrastructure.connectors.dynamic.service.get_settings") as mock_settings:
        mock_settings.return_value.codebase_memory_mcp_enabled = True
        with patch(
            "app.infrastructure.connectors.dynamic.service.DynamicConnectorService",
            return_value=svc,
        ):
            with patch(
                "app.infrastructure.connectors.dynamic.service.CostGovernor",
            ) as gov_cls:
                gov_cls.return_value.assert_can_spend = AsyncMock()
                with patch(
                    "app.infrastructure.connectors.dynamic.service.DynamicConnectorHub.throttle_ok",
                    AsyncMock(return_value=True),
                ):
                    with patch(
                        "app.infrastructure.connectors.dynamic.service.DynamicConnectorHub.breaker_is_open",
                        AsyncMock(return_value=False),
                    ):
                        with patch(
                            "app.infrastructure.connectors.dynamic.service.DynamicConnectorHub.snapshots",
                            AsyncMock(return_value=(snap,)),
                        ):
                            with patch(
                                "app.application.services.codebase_memory_mcp_service.invoke_codebase_memory_tool",
                                AsyncMock(return_value='{"health_score":0.8}'),
                            ):
                                result = await invoke_dynamic_tool(
                                    AsyncMock(),
                                    connector_slug=CODEBASE_MEMORY_MCP_SLUG,
                                    tool_name="tech_health_snapshot",
                                    arguments={},
                                    manager_slug="execution_operations",
                                )

    assert "health_score" in result
