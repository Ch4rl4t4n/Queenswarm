"""Commerce order sync — idempotent Stripe/Shopify event persistence for HiveMind + eshop-ops."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import (
    CHANNEL_SWARM_EVENTS,
    get_json,
    publish_event,
    set_json,
    zset_increment,
    zset_top,
)

logger = structlog.get_logger(__name__)

COMMERCE_EVENT_KEY_PREFIX = "commerce:order_event:v1"
COMMERCE_EVENT_INDEX_KEY = "commerce:order_event:index:v1"
COMMERCE_EVENT_TTL_SEC = 7 * 24 * 3600
COMMERCE_EVENT_INDEX_TTL_SEC = 8 * 24 * 3600
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


def _index_member(provider: CommerceProvider, event_id: str) -> str:
    """Sorted-set member for recent-event index."""

    return f"{provider}:{event_id}"


def _parse_index_member(member: str) -> tuple[CommerceProvider, str] | None:
    """Split index member into provider and event_id."""

    if ":" not in member:
        return None
    provider_raw, event_id = member.split(":", 1)
    if provider_raw not in {"stripe", "shopify"} or not event_id.strip():
        return None
    return provider_raw, event_id


def _row_to_event(row: Any) -> CommerceOrderEvent:
    """Map ORM row to pydantic event."""

    ingested = row.ingested_at
    ingested_iso = ingested.isoformat() if isinstance(ingested, datetime) else str(ingested)
    return CommerceOrderEvent(
        provider=row.provider,
        event_id=row.event_id,
        event_type=row.event_type,
        object_id=row.object_id or "",
        amount_cents=row.amount_cents,
        currency=row.currency,
        customer_id=row.customer_id,
        order_status=row.order_status,
        raw_type=row.event_type,
        ingested_at=ingested_iso,
        payload_summary=dict(row.payload_summary or {}),
    )


async def persist_commerce_order_event_audit(
    session: AsyncSession,
    event: CommerceOrderEvent,
    *,
    tenant_id: uuid.UUID | None = None,
    firm_id: str | None = None,
) -> bool:
    """Persist event to Postgres for long-term audit. Returns False on duplicate."""

    from app.infrastructure.persistence.models.commerce_order_event import CommerceOrderEventORM

    try:
        ingested_dt = datetime.fromisoformat(event.ingested_at.replace("Z", "+00:00"))
    except ValueError:
        ingested_dt = datetime.now(tz=UTC)

    row = CommerceOrderEventORM(
        tenant_id=tenant_id,
        firm_id=firm_id,
        provider=event.provider,
        event_id=event.event_id,
        event_type=event.event_type,
        object_id=event.object_id,
        amount_cents=event.amount_cents,
        currency=event.currency,
        customer_id=event.customer_id,
        order_status=event.order_status,
        ingested_at=ingested_dt,
        payload_summary=dict(event.payload_summary or {}),
    )
    session.add(row)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        logger.info(
            "commerce_order_audit_duplicate",
            provider=event.provider,
            event_id=event.event_id,
        )
        return False
    except SQLAlchemyError as exc:
        await session.rollback()
        logger.warning(
            "commerce_order_audit_persist_failed",
            provider=event.provider,
            event_id=event.event_id,
            error=str(exc),
        )
        return False
    return True


async def list_commerce_order_events_from_db(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None = None,
    firm_id: str | None = None,
    limit: int = 50,
) -> list[CommerceOrderEvent]:
    """List recent commerce events from Postgres audit table."""

    from app.infrastructure.persistence.models.commerce_order_event import CommerceOrderEventORM

    capped = max(1, min(limit, 200))
    stmt = select(CommerceOrderEventORM).order_by(desc(CommerceOrderEventORM.ingested_at)).limit(capped)
    if tenant_id is not None:
        stmt = stmt.where(
            or_(
                CommerceOrderEventORM.tenant_id == tenant_id,
                CommerceOrderEventORM.tenant_id.is_(None),
            ),
        )
    if firm_id:
        stmt = stmt.where(CommerceOrderEventORM.firm_id == firm_id.strip())

    try:
        rows = list((await session.scalars(stmt)).all())
    except SQLAlchemyError as exc:
        logger.warning("commerce_order_audit_list_failed", error=str(exc))
        return []
    return [_row_to_event(row) for row in rows]


async def list_recent_commerce_order_events(
    *,
    limit: int = 50,
    session: AsyncSession | None = None,
    tenant_id: uuid.UUID | None = None,
    firm_id: str | None = None,
) -> list[CommerceOrderEvent]:
    """Return recent events — Postgres when session provided, else Redis index."""

    if session is not None:
        db_events = await list_commerce_order_events_from_db(
            session,
            tenant_id=tenant_id,
            firm_id=firm_id,
            limit=limit,
        )
        if db_events:
            return db_events

    capped = max(1, min(limit, 200))
    rows = await zset_top(COMMERCE_EVENT_INDEX_KEY, limit=capped)
    events: list[CommerceOrderEvent] = []
    for member, _score in rows:
        parsed = _parse_index_member(member)
        if parsed is None:
            continue
        provider, event_id = parsed
        raw = await get_json(_event_storage_key(provider, event_id))
        if raw is None:
            continue
        try:
            events.append(CommerceOrderEvent.model_validate(raw))
        except ValueError:
            logger.warning(
                "commerce_order_sync_list_invalid_record",
                provider=provider,
                event_id=event_id,
            )
    return events


async def ingest_commerce_order_event(
    event: CommerceOrderEvent,
    *,
    session: AsyncSession | None = None,
    tenant_id: uuid.UUID | None = None,
    firm_id: str | None = None,
) -> bool:
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
    await zset_increment(
        COMMERCE_EVENT_INDEX_KEY,
        _index_member(event.provider, event.event_id),
        float(datetime.now(UTC).timestamp()),
        ttl_sec=COMMERCE_EVENT_INDEX_TTL_SEC,
    )

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

    if session is not None:
        await persist_commerce_order_event_audit(
            session,
            event,
            tenant_id=tenant_id,
            firm_id=firm_id,
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
    "list_commerce_order_events_from_db",
    "list_recent_commerce_order_events",
    "normalize_stripe_event",
    "persist_commerce_order_event_audit",
]
