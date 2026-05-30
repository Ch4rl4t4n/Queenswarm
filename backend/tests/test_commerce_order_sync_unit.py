"""Unit tests for commerce order sync idempotency."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.commerce_order_sync import (
    CommerceOrderEvent,
    ingest_commerce_order_event,
    list_recent_commerce_order_events,
    normalize_stripe_event,
    persist_commerce_order_event_audit,
)


def test_normalize_stripe_event_when_checkout_completed_then_fields() -> None:
    """Checkout session maps amount, currency, and customer."""

    body = {
        "id": "evt_abc",
        "type": "checkout.session.completed",
        "livemode": False,
        "data": {
            "object": {
                "id": "cs_test",
                "object": "checkout.session",
                "amount_total": 4999,
                "currency": "eur",
                "customer": "cus_123",
                "payment_status": "paid",
            }
        },
    }
    event = normalize_stripe_event(body)
    assert event is not None
    assert event.event_id == "evt_abc"
    assert event.amount_cents == 4999
    assert event.currency == "eur"
    assert event.customer_id == "cus_123"
    assert event.order_status == "paid"


@pytest.mark.asyncio
async def test_ingest_commerce_order_event_when_new_then_publishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """First ingest persists, indexes, and publishes swarm event."""

    get_json = AsyncMock(return_value=None)
    set_json = AsyncMock()
    zset_increment = AsyncMock(return_value=1.0)
    publish = AsyncMock()
    monkeypatch.setattr("app.application.services.commerce_order_sync.get_json", get_json)
    monkeypatch.setattr("app.application.services.commerce_order_sync.set_json", set_json)
    monkeypatch.setattr("app.application.services.commerce_order_sync.zset_increment", zset_increment)
    monkeypatch.setattr("app.application.services.commerce_order_sync.publish_event", publish)

    event = CommerceOrderEvent(
        provider="stripe",
        event_id="evt_1",
        event_type="checkout.session.completed",
        object_id="cs_1",
    )
    assert await ingest_commerce_order_event(event) is True
    set_json.assert_awaited_once()
    zset_increment.assert_awaited_once()
    publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_recent_commerce_order_events_when_indexed_then_ordered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """List hydrates events from index members newest-first."""

    zset_top = AsyncMock(return_value=[("stripe:evt_2", 2.0), ("stripe:evt_1", 1.0)])
    get_json = AsyncMock(
        side_effect=[
            {"provider": "stripe", "event_id": "evt_2", "event_type": "checkout.session.completed"},
            {"provider": "stripe", "event_id": "evt_1", "event_type": "payment_intent.succeeded"},
        ]
    )
    monkeypatch.setattr("app.application.services.commerce_order_sync.zset_top", zset_top)
    monkeypatch.setattr("app.application.services.commerce_order_sync.get_json", get_json)

    events = await list_recent_commerce_order_events(limit=10)
    assert len(events) == 2
    assert events[0].event_id == "evt_2"
    assert events[1].event_id == "evt_1"


@pytest.mark.asyncio
async def test_persist_commerce_order_event_audit_when_new_then_true() -> None:
    """Postgres audit row persists on first insert."""

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()

    event = CommerceOrderEvent(
        provider="stripe",
        event_id="evt_db_1",
        event_type="checkout.session.completed",
    )
    assert await persist_commerce_order_event_audit(session, event) is True
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingest_commerce_order_event_when_duplicate_then_skips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Duplicate event_id returns False without republishing."""

    get_json = AsyncMock(return_value={"event_id": "evt_1"})
    set_json = AsyncMock()
    publish = AsyncMock()
    monkeypatch.setattr("app.application.services.commerce_order_sync.get_json", get_json)
    monkeypatch.setattr("app.application.services.commerce_order_sync.set_json", set_json)
    monkeypatch.setattr("app.application.services.commerce_order_sync.publish_event", publish)

    event = CommerceOrderEvent(
        provider="stripe",
        event_id="evt_1",
        event_type="checkout.session.completed",
    )
    assert await ingest_commerce_order_event(event) is False
    set_json.assert_not_awaited()
    publish.assert_not_awaited()
