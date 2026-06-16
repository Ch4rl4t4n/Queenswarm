"""API unit tests for RA5 broker order queue routes."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_user_with_tenant_role


@pytest.fixture
def restore_overrides() -> None:
    yield
    app.dependency_overrides.clear()


def _owner_principal() -> dict[str, object]:
    return {
        "user": type("U", (), {"id": uuid.uuid4()})(),
        "tenant_id": uuid.uuid4(),
        "tenant_role": "owner",
        "permissions": ["*"],
        "sub": "auth0|test",
    }


@pytest.mark.asyncio
async def test_trading_cockpit_order_queue_get(restore_overrides: None) -> None:
    from app.application.services.broker_order_queue_service import BrokerOrderQueueSnapshotOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    snapshot = BrokerOrderQueueSnapshotOut(enabled=True, pending_count=1)

    with patch(
        "app.presentation.api.routers.trading_cockpit.build_broker_order_queue_snapshot",
        AsyncMock(return_value=snapshot),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/trading-cockpit/order-queue",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["pending_count"] == 1


@pytest.mark.asyncio
async def test_trading_cockpit_order_queue_review_post(restore_overrides: None) -> None:
    from app.application.services.broker_order_queue_service import BrokerOrderReviewOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    from datetime import UTC, datetime

    result = BrokerOrderReviewOut(
        id="abc",
        status="rejected",
        reviewed_at=datetime.now(tz=UTC),
    )

    with patch(
        "app.presentation.api.routers.trading_cockpit.review_broker_order",
        AsyncMock(return_value=result),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/trading-cockpit/order-queue/abc/review",
                headers={"Authorization": "Bearer x"},
                json={"decision": "reject"},
            )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    mock_db.commit.assert_awaited_once()
