"""Trust Autopilot — Zero-UI priority pings for verify-first operator outcomes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.operator_telegram_gateway import ZeroUiPriority, notify_zero_ui_ping
from app.application.services.publish_queue_notify import _resolve_tenant_for_user
from app.core.config import settings
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

logger = structlog.get_logger(__name__)


def _publish_queue_href(*, deliverable_id: uuid.UUID) -> str:
    return f"/integrations?tab=studio#publish-queue&pack={deliverable_id}"


def _social_publish_href(*, deliverable_id: uuid.UUID) -> str:
    return f"/integrations?tab=studio#social-publish&pack={deliverable_id}"


def _structured(row: TaskFinalDeliverable) -> dict[str, Any]:
    return dict(row.structured_json) if isinstance(row.structured_json, dict) else {}


def _trust_ping_already_sent(row: TaskFinalDeliverable, *, key: str) -> bool:
    pings = _structured(row).get("trust_autopilot_pings")
    return isinstance(pings, dict) and key in pings


async def _mark_trust_ping_sent(
    db: AsyncSession,
    *,
    row: TaskFinalDeliverable,
    key: str,
) -> None:
    structured = _structured(row)
    pings = dict(structured.get("trust_autopilot_pings") or {})
    pings[key] = datetime.now(tz=UTC).isoformat()
    structured["trust_autopilot_pings"] = pings
    row.structured_json = structured
    await db.flush()


async def _send_trust_ping(
    db: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    priority: ZeroUiPriority,
    title: str,
    detail: str,
    href: str | None,
) -> dict[str, bool]:
    """Route Trust Autopilot ping through Zero-UI gateway."""

    if not settings.operator_zero_ui_notify_enabled:
        return {"telegram": False}

    tenant = await _resolve_tenant_for_user(db, dashboard_user_id=dashboard_user_id)
    if tenant is None:
        return {"telegram": False}

    result = await notify_zero_ui_ping(
        db,
        tenant_id=tenant.id,
        dashboard_user_id=dashboard_user_id,
        priority=priority,
        title=title,
        detail=detail,
        href=href,
    )
    logger.info(
        "trust_autopilot.ping",
        agent_id="trust_autopilot",
        task_id=str(dashboard_user_id),
        priority=priority,
        sent=bool(result.get("telegram")),
    )
    return result


async def notify_publish_pack_simulate_ready(
    db: AsyncSession,
    *,
    row: TaskFinalDeliverable,
    dashboard_user_id: uuid.UUID,
) -> dict[str, bool]:
    """🟡 Ping when verified publish pack enters operator queue."""

    if not settings.publish_queue_enabled:
        return {"telegram": False}
    if _trust_ping_already_sent(row, key="simulate_ready"):
        return {"telegram": False}

    structured = _structured(row)
    channel = str(structured.get("channel") or "instagram")
    body_preview = str(structured.get("body") or row.markdown_body or "")[:160]
    detail = f"{row.title}\nKanál: {channel}\n{body_preview}"

    result = await _send_trust_ping(
        db,
        dashboard_user_id=dashboard_user_id,
        priority="simulate",
        title="Publish pack — schváľ v queue",
        detail=detail,
        href=_publish_queue_href(deliverable_id=row.id),
    )
    if result.get("telegram"):
        await _mark_trust_ping_sent(db, row=row, key="simulate_ready")
    return result


async def notify_publish_queue_approved(
    db: AsyncSession,
    *,
    row: TaskFinalDeliverable,
    dashboard_user_id: uuid.UUID,
) -> dict[str, bool]:
    """🟢 Ping after operator approves publish pack (simulate-first)."""

    if not settings.publish_queue_telegram_notify_enabled:
        return {"telegram": False}

    structured = _structured(row)
    channel = str(structured.get("channel") or "instagram")
    return await _send_trust_ping(
        db,
        dashboard_user_id=dashboard_user_id,
        priority="info",
        title="Publish pack schválený",
        detail=f"{row.title} · {channel} — ďalší krok Social publish (Simulate).",
        href=_social_publish_href(deliverable_id=row.id),
    )


async def notify_social_simulate_ready_for_live(
    db: AsyncSession,
    *,
    row: TaskFinalDeliverable,
    dashboard_user_id: uuid.UUID,
    channel: str,
) -> dict[str, bool]:
    """🟡 Ping after successful social simulate — live needs explicit confirm."""

    if _trust_ping_already_sent(row, key="social_simulate_ready"):
        return {"telegram": False}

    result = await _send_trust_ping(
        db,
        dashboard_user_id=dashboard_user_id,
        priority="simulate",
        title="Simulate OK — live vyžaduje potvrdenie",
        detail=f"{row.title} · {channel}",
        href=_social_publish_href(deliverable_id=row.id),
    )
    if result.get("telegram"):
        await _mark_trust_ping_sent(db, row=row, key="social_simulate_ready")
    return result


async def notify_live_publish_gate(
    db: AsyncSession,
    *,
    row: TaskFinalDeliverable,
    dashboard_user_id: uuid.UUID,
    channel: str,
    reason: str,
) -> dict[str, bool]:
    """🔴 Ping when live publish blocked until operator confirms."""

    reason_labels = {
        "trusted_auto_global_off": "Zapni trusted auto alebo potvrď Live v UI.",
        "trusted_auto_tenant_off": "Trusted auto vypnuté — potvrď Live manuálne.",
        "channel_manual_mode": "Kanál je v manual mode — potvrď Live.",
        "pack_not_simulated": "Najprv spusti Simulate na tomto packu.",
        "insufficient_channel_simulates": "Potrebné viac úspešných simulácií pred auto-live.",
    }
    detail = reason_labels.get(reason, "Live publish vyžaduje explicitné potvrdenie operátora.")

    return await _send_trust_ping(
        db,
        dashboard_user_id=dashboard_user_id,
        priority="critical",
        title=f"Live gate · {channel}",
        detail=f"{row.title}\n{detail}",
        href=_social_publish_href(deliverable_id=row.id),
    )


__all__ = [
    "notify_live_publish_gate",
    "notify_publish_pack_simulate_ready",
    "notify_publish_queue_approved",
    "notify_social_simulate_ready_for_live",
]
