"""Unit tests for Track P RA5 broker HITL order queue."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.broker_order_queue_service import (
    BrokerOrderProposeIn,
    BrokerOrderReviewIn,
    build_broker_order_queue_snapshot,
    compose_broker_order_inbox_items,
    propose_broker_order,
    queue_live_trade_from_agent,
    review_broker_order,
)


@pytest.mark.asyncio
async def test_propose_broker_order_persists_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()
    tenant = MagicMock(operator_settings={})
    session.get = AsyncMock(return_value=tenant)

    monkeypatch.setattr(
        "app.application.services.broker_order_queue_service.settings",
        MagicMock(broker_order_queue_enabled=True),
    )

    with patch(
        "app.application.services.broker_order_queue_service._record_broker_order_audit",
        AsyncMock(),
    ):
        item = await propose_broker_order(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            body=BrokerOrderProposeIn(
                venue="polymarket",
                title="Buy YES token-1",
                notional_usd=25.0,
                payload={"notional_usd": 25, "symbol": "token-1"},
                project_settings={"connector_slug": "polymarket_clob", "venue": "polymarket"},
            ),
        )

    assert item.status == "pending"
    assert item.venue == "polymarket"
    bucket = tenant.operator_settings["broker_order_queue"]
    assert bucket["orders"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_build_broker_order_queue_snapshot_counts_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    tenant = MagicMock(
        operator_settings={
            "broker_order_queue": {
                "orders": [
                    {
                        "id": "a",
                        "status": "pending",
                        "venue": "polymarket",
                        "title": "Order A",
                        "detail": "",
                        "notional_usd": 10,
                        "payload": {},
                        "project_settings": {},
                        "created_at": "2026-06-16T12:00:00+00:00",
                    },
                ],
            },
        },
    )
    session.get = AsyncMock(return_value=tenant)

    monkeypatch.setattr(
        "app.application.services.broker_order_queue_service.settings",
        MagicMock(broker_order_queue_enabled=True),
    )

    snapshot = await build_broker_order_queue_snapshot(session, tenant_id=tenant_id)
    assert snapshot.pending_count == 1
    assert snapshot.items[0].title == "Order A"


@pytest.mark.asyncio
async def test_review_broker_order_reject(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()
    tenant = MagicMock(
        operator_settings={
            "broker_order_queue": {
                "orders": [
                    {
                        "id": "order-1",
                        "status": "pending",
                        "venue": "polymarket",
                        "title": "Reject me",
                        "detail": "",
                        "notional_usd": 5,
                        "payload": {},
                        "project_settings": {},
                        "created_at": "2026-06-16T12:00:00+00:00",
                    },
                ],
            },
        },
    )
    session.get = AsyncMock(return_value=tenant)

    monkeypatch.setattr(
        "app.application.services.broker_order_queue_service.settings",
        MagicMock(broker_order_queue_enabled=True),
    )

    with patch(
        "app.application.services.broker_order_queue_service._record_broker_order_audit",
        AsyncMock(),
    ):
        result = await review_broker_order(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            order_id="order-1",
            body=BrokerOrderReviewIn(decision="reject", note="too risky"),
        )

    assert result.status == "rejected"
    assert tenant.operator_settings["broker_order_queue"]["orders"][0]["status"] == "rejected"


@pytest.mark.asyncio
async def test_review_broker_order_approve_executes(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()
    tenant = MagicMock(
        operator_settings={
            "broker_order_queue": {
                "orders": [
                    {
                        "id": "order-2",
                        "status": "pending",
                        "venue": "polymarket",
                        "title": "Execute me",
                        "detail": "",
                        "notional_usd": 15,
                        "payload": {"notional_usd": 15},
                        "project_settings": {"connector_slug": "polymarket_clob", "venue": "polymarket"},
                        "created_at": "2026-06-16T12:00:00+00:00",
                    },
                ],
            },
        },
    )
    session.get = AsyncMock(return_value=tenant)

    monkeypatch.setattr(
        "app.application.services.broker_order_queue_service.settings",
        MagicMock(broker_order_queue_enabled=True),
    )

    async def _exec(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"status": "executed", "verified": True}

    with (
        patch(
            "app.application.services.broker_order_queue_service._execute_approved_broker_order",
            _exec,
        ),
        patch(
            "app.application.services.broker_order_queue_service._record_broker_order_audit",
            AsyncMock(),
        ),
    ):
        result = await review_broker_order(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            order_id="order-2",
            body=BrokerOrderReviewIn(decision="approve"),
        )

    assert result.status == "executed"


@pytest.mark.asyncio
async def test_build_snapshot_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.broker_order_queue_service.settings",
        MagicMock(broker_order_queue_enabled=False),
    )
    snapshot = await build_broker_order_queue_snapshot(AsyncMock(), tenant_id=uuid.uuid4())
    assert snapshot.enabled is False


@pytest.mark.asyncio
async def test_propose_raises_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.broker_order_queue_service.settings",
        MagicMock(broker_order_queue_enabled=False),
    )
    with pytest.raises(ValueError, match="disabled"):
        await propose_broker_order(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            body=BrokerOrderProposeIn(title="x", venue="polymarket"),
        )


@pytest.mark.asyncio
async def test_queue_live_trade_from_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()
    tenant = MagicMock(operator_settings={})
    session.get = AsyncMock(return_value=tenant)

    monkeypatch.setattr(
        "app.application.services.broker_order_queue_service.settings",
        MagicMock(broker_order_queue_enabled=True),
    )

    with patch(
        "app.application.services.broker_order_queue_service._record_broker_order_audit",
        AsyncMock(),
    ):
        out = await queue_live_trade_from_agent(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            payload={"market_ticker": "KX", "count": 2, "yes_price": 50},
            project_settings={"venue": "polymarket", "connector_slug": "polymarket_clob"},
            proposed_by="agent:test",
        )

    assert out["status"] == "queued"
    assert out["order_id"]


@pytest.mark.asyncio
async def test_compose_broker_order_inbox_items_pending_only(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    tenant = MagicMock(
        operator_settings={
            "broker_order_queue": {
                "orders": [
                    {
                        "id": "p1",
                        "status": "pending",
                        "venue": "polymarket",
                        "title": "Pending",
                        "detail": "",
                        "notional_usd": 1,
                        "payload": {},
                        "project_settings": {},
                        "created_at": "2026-06-16T12:00:00+00:00",
                    },
                    {
                        "id": "e1",
                        "status": "executed",
                        "venue": "polymarket",
                        "title": "Done",
                        "detail": "",
                        "notional_usd": 1,
                        "payload": {},
                        "project_settings": {},
                        "created_at": "2026-06-16T12:00:00+00:00",
                    },
                ],
            },
        },
    )
    session.get = AsyncMock(return_value=tenant)
    monkeypatch.setattr(
        "app.application.services.broker_order_queue_service.settings",
        MagicMock(broker_order_queue_enabled=True),
    )
    rows = await compose_broker_order_inbox_items(session, tenant_id=tenant_id)
    assert len(rows) == 1
    assert rows[0]["id"] == "p1"


@pytest.mark.asyncio
async def test_review_broker_order_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    tenant = MagicMock(operator_settings={"broker_order_queue": {"orders": []}})
    session.get = AsyncMock(return_value=tenant)
    monkeypatch.setattr(
        "app.application.services.broker_order_queue_service.settings",
        MagicMock(broker_order_queue_enabled=True),
    )
    with pytest.raises(LookupError):
        await review_broker_order(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=uuid.uuid4(),
            order_id="missing",
            body=BrokerOrderReviewIn(decision="reject"),
        )
