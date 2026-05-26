"""Publish Queue operator notifications — Phase E Telegram brief + approve link."""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio_notifications import _resolve_telegram_credentials
from app.application.services.publish_queue import PublishQueueDecision
from app.core.config import settings
from app.core.notifications import notify_telegram
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable
from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership, Tenant

logger = structlog.get_logger(__name__)


async def _resolve_tenant_for_user(
    db: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
) -> Tenant | None:
    """Pick active tenant for operator notifications."""

    membership = await db.scalar(
        select(DashboardUserTenantMembership)
        .where(DashboardUserTenantMembership.dashboard_user_id == dashboard_user_id)
        .order_by(DashboardUserTenantMembership.created_at.asc())
        .limit(1),
    )
    if membership is None:
        return None
    return await db.get(Tenant, membership.tenant_id)


def _studio_links(*, deliverable_id: uuid.UUID) -> str:
    domain = str(settings.domain or "queenswarm.love").strip().rstrip("/")
    base = f"https://{domain}" if not domain.startswith("http") else domain.rstrip("/")
    return (
        f"{base}/integrations?tab=studio#publish-queue\n"
        f"{base}/integrations?tab=studio#social-publish\n"
        f"{base}/outputs?ready_to_publish=true&id={deliverable_id}"
    )


async def notify_publish_queue_review(
    db: AsyncSession,
    *,
    row: TaskFinalDeliverable,
    dashboard_user_id: uuid.UUID,
    decision: PublishQueueDecision,
) -> dict[str, bool]:
    """Best-effort Zero-UI ping when operator approves a publish pack."""

    if decision != "approve":
        return {"telegram": False}

    from app.application.services.trust_autopilot_notify import notify_publish_queue_approved

    return await notify_publish_queue_approved(
        db,
        row=row,
        dashboard_user_id=dashboard_user_id,
    )


async def notify_social_publish_auto_live(
    db: AsyncSession,
    *,
    row: TaskFinalDeliverable,
    dashboard_user_id: uuid.UUID,
    channel: str,
) -> dict[str, bool]:
    """Best-effort Telegram ping when trusted auto-live succeeds."""

    if not settings.social_publish_telegram_notify_on_auto_live_enabled:
        return {"telegram": False}

    tenant = await _resolve_tenant_for_user(db, dashboard_user_id=dashboard_user_id)
    token, chat_id = _resolve_telegram_credentials(tenant)
    if not token or not chat_id:
        return {"telegram": False}

    structured = dict(row.structured_json or {})
    body_preview = str(structured.get("body") or row.markdown_body or "")[:180]
    message = (
        f"🚀 Auto-live publish (trusted auto)\n"
        f"*{row.title}*\n"
        f"Kanál: {channel}\n"
        f"{body_preview}\n\n"
        f"Audit + Social publish:\n"
        f"{_studio_links(deliverable_id=row.id)}"
    )

    ok = await notify_telegram(message, bot_token=token, chat_id=chat_id)
    logger.info(
        "social_publish.telegram_auto_live",
        agent_id="social_publish",
        task_id=str(row.id),
        sent=ok,
        channel=channel,
    )
    return {"telegram": ok}


__all__ = ["notify_publish_queue_review", "notify_social_publish_auto_live"]
