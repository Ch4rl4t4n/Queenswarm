"""Commerce order sync — idempotent Stripe/Shopify event persistence for HiveMind + eshop-ops."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field

from app.core.redis_client import CHANNEL_SWARM_EVENTS, get_json, publish_event, set_json

logger = structlog.get_logger(__name__)

COMMERCE_EVENT_KEY_PREFIX = "commerce:order_event:v1"
COMMERCE_EVENT_TTL_SEC = 7 * 24 * 3600
CommerceProvider = Literal["stripe", "shopify"]


class CommerceOrderEvent(BaseModel):
    """Normalized commerce webhook event for eshop-ops swarms and HiveMind ingest."""

    model_config = ConfigDict(extra="ignore")

    provider: CommerceProvider
    event_id: str
    event_type: str
    object_id: str = ""
    amount_cents: int | None = None
    currency: str | None = None
    customer_id: str | None = None
    order_status: str | None = None
    raw_type: str = ""
    ingested_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    payload_summary: dict[str, Any] = Field(default_factory=dict)


def _event_storage_key(provider: CommerceProvider, event_id: str) -> str:
    """Redis key for idempotent commerce event storage."""

    return f"{COMMERCE_EVENT_KEY_PREFIX}:{provider}:{event_id}"


def normalize_stripe_event(body: dict[str, Any]) -> CommerceOrderEvent | None:
    """Map a verified Stripe webhook body into a normalized commerce event."""

    event_type = str(body.get("type") or "")
    event_id = str(body.get("id") or "")
    if not event_id or not event_type:
        return None

    data_obj = body.get("data") if isinstance(body.get("data"), dict) else {}
    inner = data_obj.get("object") if isinstance(data_obj.get("object"), dict) else {}

    amount_cents: int | None = None
    currency: str | None = None
    customer_id: str | None = None
    order_status: str | None = None

    if event_type.startswith("checkout.session"):
        amount_cents = inner.get("amount_total")
        currency = str(inner.get("currency") or "") or None
        customer_id = str(inner.get("customer") or "") or None
        order_status = str(inner.get("payment_status") or "") or None
    elif event_type.startswith("payment_intent"):
        amount_cents = inner.get("amount")
        currency = str(inner.get("currency") or "") or None
        customer_id = str(inner.get("customer") or "") or None
        order_status = str(inner.get("status") or "") or None

    return CommerceOrderEvent(
        provider="stripe",
        event_id=event_id,
        event_type=event_type,
        object_id=str(inner.get("id") or ""),
        amount_cents=int(amount_cents) if isinstance(amount_cents, int) else None,
        currency=currency,
        customer_id=customer_id,
        order_status=order_status,
        raw_type=event_type,
        payload_summary={
            "livemode": body.get("livemode"),
            "object_kind": inner.get("object"),
        },
    )


async def ingest_commerce_order_event(event: CommerceOrderEvent) -> bool:
    """Persist event idempotently and fan out to swarm_events. Returns False if duplicate."""

    key = _event_storage_key(event.provider, event.event_id)
    existing = await get_json(key)
    if existing is not None:
        logger.info(
            "commerce_order_sync_duplicate",
            provider=event.provider,
            event_id=event.event_id,
            event_type=event.event_type,
        )
        return False

    record = event.model_dump()
    await set_json(key, record, ttl=COMMERCE_EVENT_TTL_SEC)

    await publish_event(
        CHANNEL_SWARM_EVENTS,
        {
            "event": "commerce_order_sync",
            "provider": event.provider,
            "event_id": event.event_id,
            "event_type": event.event_type,
            "object_id": event.object_id,
            "amount_cents": event.amount_cents,
            "currency": event.currency,
            "order_status": event.order_status,
            "ingested_at": event.ingested_at,
        },
    )

    logger.info(
        "commerce_order_sync_ingested",
        provider=event.provider,
        event_id=event.event_id,
        event_type=event.event_type,
        object_id=event.object_id,
    )
    return True


__all__ = [
    "CommerceOrderEvent",
    "ingest_commerce_order_event",
    "normalize_stripe_event",
]
