"""Unit tests for commerce order sync idempotency."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.application.services.commerce_order_sync import (
    CommerceOrderEvent,
    ingest_commerce_order_event,
    normalize_stripe_event,
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
    """First ingest persists and publishes swarm event."""

    get_json = AsyncMock(return_value=None)
    set_json = AsyncMock()
    publish = AsyncMock()
    monkeypatch.setattr("app.application.services.commerce_order_sync.get_json", get_json)
    monkeypatch.setattr("app.application.services.commerce_order_sync.set_json", set_json)
    monkeypatch.setattr("app.application.services.commerce_order_sync.publish_event", publish)

    event = CommerceOrderEvent(
        provider="stripe",
        event_id="evt_1",
        event_type="checkout.session.completed",
        object_id="cs_1",
    )
    assert await ingest_commerce_order_event(event) is True
    set_json.assert_awaited_once()
    publish.assert_awaited_once()


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
