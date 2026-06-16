"""Registry integration tests for RA5 broker HITL queue."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.external.registry import route_external_invocation


@pytest.mark.asyncio
async def test_route_external_invocation_queues_trade_when_hitl_required(monkeypatch: pytest.MonkeyPatch) -> None:
    project = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        owner_dashboard_user_id=uuid.uuid4(),
        slug="trader",
        project_kind="trading",
        settings={"trading_mode": "real", "venue": "polymarket", "connector_slug": "polymarket_clob"},
    )
    api_key = MagicMock(permissions=["mcp:call", "trading:live"])

    settings = SimpleNamespace(broker_order_queue_enabled=True)

    async def _queue(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "status": "queued",
            "order_id": "queued-1",
            "reason": "broker_hitl_required",
        }

    with patch(
        "app.application.services.broker_order_queue_service.queue_live_trade_from_agent",
        _queue,
    ):
        result = await route_external_invocation(
            AsyncMock(),
            project=project,
            api_key=api_key,
            action="execute_trade",
            payload={"symbol": "token-1", "quantity": 1},
            channel="mcp",
            settings=settings,
        )

    assert result.result.get("status") == "queued"
    assert result.result.get("order_id") == "queued-1"
