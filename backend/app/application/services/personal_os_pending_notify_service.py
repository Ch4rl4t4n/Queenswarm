"""POS-L — Zero-UI Telegram pings when Personal OS compound/email drafts need approval."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.operator_telegram_gateway import notify_zero_ui_ping
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

WEEKLY_COMPOUND_SETTINGS_KEY = "weekly_compound_gardener"
EMAIL_DRAFT_SETTINGS_KEY = "email_draft_outer_loop"
COCKPIT_APPROVALS_HREF = "/cockpit#approvals"


def _bucket(operator_settings: dict[str, Any] | None, key: str) -> dict[str, Any]:
    root = dict(operator_settings or {})
    raw = root.get(key)
    return dict(raw) if isinstance(raw, dict) else {}


async def _persist_notify_marker(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    settings_key: str,
    marker_key: str,
    marker_value: str,
) -> None:
    """Record dedupe marker in tenant operator_settings."""

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return

    root = dict(tenant.operator_settings or {})
    bucket = _bucket(root, settings_key)
    bucket[marker_key] = marker_value
    root[settings_key] = bucket
    tenant.operator_settings = root
    await session.flush()


async def notify_weekly_compound_draft_pending(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID | None,
    week_key: str,
    draft_title: str,
) -> dict[str, bool]:
    """Telegram ping when weekly compound draft awaits Cockpit approval (once per week)."""

    if not settings.operator_zero_ui_notify_enabled or dashboard_user_id is None:
        return {"telegram": False}

    tenant = await session.get(Tenant, tenant_id)
    bucket = _bucket(tenant.operator_settings if tenant else None, WEEKLY_COMPOUND_SETTINGS_KEY)
    if bucket.get("last_telegram_notify_week") == week_key:
        return {"telegram": False}

    result = await notify_zero_ui_ping(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        priority="simulate",
        title="Weekly compound draft ready",
        detail=f"{draft_title[:180]} — approve in Cockpit before Hive Mind apply.",
        href=COCKPIT_APPROVALS_HREF,
    )
    if result.get("telegram"):
        await _persist_notify_marker(
            session,
            tenant_id=tenant_id,
            settings_key=WEEKLY_COMPOUND_SETTINGS_KEY,
            marker_key="last_telegram_notify_week",
            marker_value=week_key,
        )
        _logger.info(
            "personal_os_pending_notify.compound_sent",
            agent_id="personal_os_pending_notify",
            swarm_id=str(tenant_id),
            task_id=week_key,
        )
    return result


async def notify_email_drafts_pending(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    created_count: int,
) -> dict[str, bool]:
    """Telegram ping when simulate-only email reply drafts land in Approval Inbox (once per UTC day)."""

    if (
        not settings.operator_zero_ui_notify_enabled
        or not settings.email_draft_outer_loop_enabled
        or created_count <= 0
    ):
        return {"telegram": False}

    day_key = datetime.now(tz=UTC).date().isoformat()
    tenant = await session.get(Tenant, tenant_id)
    bucket = _bucket(tenant.operator_settings if tenant else None, EMAIL_DRAFT_SETTINGS_KEY)
    if bucket.get("last_telegram_notify_day") == day_key:
        return {"telegram": False}

    noun = "draft" if created_count == 1 else "drafts"
    result = await notify_zero_ui_ping(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        priority="simulate",
        title="Email reply drafts ready",
        detail=f"{created_count} simulate-only {noun} in Approval Inbox — review before send.",
        href=COCKPIT_APPROVALS_HREF,
    )
    if result.get("telegram"):
        await _persist_notify_marker(
            session,
            tenant_id=tenant_id,
            settings_key=EMAIL_DRAFT_SETTINGS_KEY,
            marker_key="last_telegram_notify_day",
            marker_value=day_key,
        )
        _logger.info(
            "personal_os_pending_notify.email_sent",
            agent_id="personal_os_pending_notify",
            swarm_id=str(tenant_id),
            task_id=day_key,
            created_count=created_count,
        )
    return result


__all__ = [
    "COCKPIT_APPROVALS_HREF",
    "notify_email_drafts_pending",
    "notify_weekly_compound_draft_pending",
]
