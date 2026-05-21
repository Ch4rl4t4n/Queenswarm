"""Scheduled supervisor session operator audit digest for enterprise operators."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.session_audit_digest_config import (
    effective_digest_window_hours,
    get_tenant_audit_digest_config,
    is_tenant_digest_due,
    mark_tenant_digest_sent,
)
from app.application.services.rbac import ROLE_ADMIN, ROLE_OWNER
from app.application.services.supervisor.session_audit import SUPERVISOR_SESSION_TARGET_TYPE
from app.core.config import settings
from app.core.notifications import notify_discord, notify_email, notify_slack, notify_teams
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership, Tenant, TenantAuditLog

logger = structlog.get_logger(__name__)

SUPERVISOR_AUDIT_ACTIONS = (
    "supervisor_session_create",
    "supervisor_session_control",
    "supervisor_session_review",
    "supervisor_session_interact",
    "supervisor_sub_agent_retry",
    "supervisor_session_save_playbook",
)


async def list_supervisor_audit_rows_since(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    since: datetime,
    limit: int = 500,
) -> list[TenantAuditLog]:
    """Return supervisor session audit rows for one tenant inside a time window."""

    safe_limit = max(1, min(int(limit), 2000))
    return list(
        (
            await db.scalars(
                select(TenantAuditLog)
                .where(
                    TenantAuditLog.tenant_id == tenant_id,
                    TenantAuditLog.target_type == SUPERVISOR_SESSION_TARGET_TYPE,
                    TenantAuditLog.created_at >= since,
                )
                .order_by(TenantAuditLog.created_at.desc())
                .limit(safe_limit),
            )
        ).all(),
    )


async def list_tenant_audit_digest_recipients(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> list[str]:
    """Resolve owner/admin email recipients opted into supervisor audit digests."""

    rows = list(
        (
            await db.scalars(
                select(DashboardUser)
                .join(
                    DashboardUserTenantMembership,
                    DashboardUserTenantMembership.dashboard_user_id == DashboardUser.id,
                )
                .where(
                    DashboardUserTenantMembership.tenant_id == tenant_id,
                    DashboardUserTenantMembership.role.in_((ROLE_OWNER, ROLE_ADMIN)),
                    DashboardUser.is_active.is_(True),
                ),
            )
        ).all(),
    )
    recipients: list[str] = []
    for user in rows:
        prefs = dict(user.notification_prefs or {})
        if prefs.get("supervisor_audit_digest") is False:
            continue
        delivery = prefs.get("delivery_channels")
        if isinstance(delivery, dict):
            email_bucket = delivery.get("email")
            if isinstance(email_bucket, dict) and email_bucket.get("enabled") is False:
                continue
            address = email_bucket.get("address") if isinstance(email_bucket, dict) else None
            if isinstance(address, str) and address.strip():
                recipients.append(address.strip())
                continue
        if user.email:
            recipients.append(user.email.strip())
    tenant = await db.get(Tenant, tenant_id)
    if tenant is not None:
        extra = get_tenant_audit_digest_config(tenant).get("extra_recipients") or []
        recipients.extend(str(email) for email in extra if isinstance(email, str))
    return sorted(set(recipients))


def build_supervisor_audit_digest_markdown(
    *,
    tenant_name: str,
    window_hours: int,
    rows: list[TenantAuditLog],
    generated_at: datetime,
) -> str:
    """Render a concise digest body for email delivery."""

    counts = Counter(row.action for row in rows)
    session_ids = sorted({row.target_ref for row in rows if row.target_ref})
    lines = [
        f"# Supervisor audit digest — {tenant_name}",
        "",
        f"Generated: {generated_at.isoformat()}",
        f"Window: last {window_hours} hours",
        f"Total operator actions: {len(rows)}",
        "",
        "## Action counts",
        "",
    ]
    if counts:
        for action, count in counts.most_common():
            lines.append(f"- `{action}`: {count}")
    else:
        lines.append("_No supervisor operator actions in this window._")
    lines.extend(["", "## Sessions touched", ""])
    if session_ids:
        for session_ref in session_ids[:20]:
            lines.append(f"- `{session_ref}`")
        if len(session_ids) > 20:
            lines.append(f"- … and {len(session_ids) - 20} more")
    else:
        lines.append("_None_")
    lines.extend(["", "## Recent actions", ""])
    for row in rows[:25]:
        payload_preview = dict(row.payload or {})
        lines.append(
            f"- `{row.created_at.isoformat() if row.created_at else ''}` · `{row.action}` · "
            f"session `{row.target_ref}` · `{payload_preview}`",
        )
    return "\n".join(lines) + "\n"


def build_supervisor_audit_digest_slack_text(
    *,
    tenant_name: str,
    window_hours: int,
    rows: list[TenantAuditLog],
    generated_at: datetime,
) -> str:
    """Render a compact Slack-friendly digest summary."""

    counts = Counter(row.action for row in rows)
    session_ids = sorted({row.target_ref for row in rows if row.target_ref})
    action_lines = "\n".join(f"• `{action}`: {count}" for action, count in counts.most_common(8))
    session_preview = ", ".join(f"`{sid[-8:]}`" for sid in session_ids[:8])
    if len(session_ids) > 8:
        session_preview = f"{session_preview}, +{len(session_ids) - 8} more"
    recent = []
    for row in rows[:5]:
        recent.append(
            f"• `{row.action}` session `{row.target_ref[-8:] if row.target_ref else '?'}`",
        )
    return (
        f"*Supervisor audit digest · {tenant_name}*\n"
        f"Window: last {window_hours}h · Total actions: {len(rows)}\n"
        f"Generated: {generated_at.isoformat()}\n\n"
        f"*Action counts*\n{action_lines or '• _none_'}\n\n"
        f"*Sessions touched*\n{session_preview or '_none_'}\n\n"
        f"*Recent*\n{chr(10).join(recent) if recent else '• _none_'}"
    )


async def send_supervisor_audit_digest_slack(
    *,
    tenant_name: str,
    window_hours: int,
    rows: list[TenantAuditLog],
    generated_at: datetime,
    webhook_url: str | None = None,
) -> bool:
    """Post one digest summary to Slack when enabled and webhook is configured."""

    if not settings.supervisor_audit_digest_slack_enabled:
        return False
    message = build_supervisor_audit_digest_slack_text(
        tenant_name=tenant_name,
        window_hours=window_hours,
        rows=rows,
        generated_at=generated_at,
    )
    return await notify_slack(
        message,
        color="#00FFFF",
        title=f"Supervisor audit · {tenant_name}",
        webhook_url=webhook_url,
    )


async def send_supervisor_audit_digest_discord(
    *,
    tenant_name: str,
    window_hours: int,
    rows: list[TenantAuditLog],
    generated_at: datetime,
    webhook_url: str | None = None,
) -> bool:
    """Post one digest summary to Discord when enabled and webhook is configured."""

    if not settings.supervisor_audit_digest_discord_enabled:
        return False
    message = build_supervisor_audit_digest_slack_text(
        tenant_name=tenant_name,
        window_hours=window_hours,
        rows=rows,
        generated_at=generated_at,
    )
    return await notify_discord(message, webhook_url=webhook_url)


async def send_supervisor_audit_digest_teams(
    *,
    tenant_name: str,
    window_hours: int,
    rows: list[TenantAuditLog],
    generated_at: datetime,
    webhook_url: str | None = None,
) -> bool:
    """Post one digest summary to Microsoft Teams when enabled and webhook is configured."""

    if not settings.supervisor_audit_digest_teams_enabled:
        return False
    message = build_supervisor_audit_digest_slack_text(
        tenant_name=tenant_name,
        window_hours=window_hours,
        rows=rows,
        generated_at=generated_at,
    )
    return await notify_teams(
        message,
        title=f"Supervisor audit · {tenant_name}",
        theme_color="00FFFF",
        webhook_url=webhook_url,
    )


async def send_supervisor_audit_digest_for_tenant(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    window_hours: int | None = None,
    mark_scheduled_sent: bool = False,
) -> dict[str, Any]:
    """Build and deliver one tenant supervisor audit digest via email and chat webhooks."""

    tenant = await db.get(Tenant, tenant_id)
    if tenant is None or tenant.status != "active":
        return {"tenant_id": str(tenant_id), "sent": False, "reason": "tenant_inactive"}

    hours = window_hours or effective_digest_window_hours(tenant)
    since = datetime.now(tz=UTC) - timedelta(hours=hours)

    rows = await list_supervisor_audit_rows_since(db, tenant_id=tenant_id, since=since)
    if not rows:
        return {"tenant_id": str(tenant_id), "sent": False, "reason": "no_activity"}

    recipients = await list_tenant_audit_digest_recipients(db, tenant_id=tenant_id)
    generated_at = datetime.now(tz=UTC)
    body = build_supervisor_audit_digest_markdown(
        tenant_name=tenant.name,
        window_hours=hours,
        rows=rows,
        generated_at=generated_at,
    )
    attachment = body.encode("utf-8")

    sent_count = 0
    if recipients:
        for recipient in recipients:
            ok = await notify_email(
                subject=f"Supervisor audit digest · {tenant.name}",
                body=body,
                to_email=recipient,
                attachment_bytes=attachment,
                attachment_filename=f"supervisor-audit-digest-{generated_at.date().isoformat()}.md",
            )
            if ok:
                sent_count += 1

    slack_webhook = get_tenant_audit_digest_config(tenant).get("slack_webhook_url")
    slack_sent = await send_supervisor_audit_digest_slack(
        tenant_name=tenant.name,
        window_hours=hours,
        rows=rows,
        generated_at=generated_at,
        webhook_url=slack_webhook,
    )

    discord_webhook = get_tenant_audit_digest_config(tenant).get("discord_webhook_url")
    discord_sent = await send_supervisor_audit_digest_discord(
        tenant_name=tenant.name,
        window_hours=hours,
        rows=rows,
        generated_at=generated_at,
        webhook_url=discord_webhook,
    )

    teams_webhook = get_tenant_audit_digest_config(tenant).get("teams_webhook_url")
    teams_sent = await send_supervisor_audit_digest_teams(
        tenant_name=tenant.name,
        window_hours=hours,
        rows=rows,
        generated_at=generated_at,
        webhook_url=teams_webhook,
    )

    if not recipients and not slack_sent and not discord_sent and not teams_sent:
        return {"tenant_id": str(tenant_id), "sent": False, "reason": "no_delivery_channels"}

    if mark_scheduled_sent and (sent_count > 0 or slack_sent or discord_sent or teams_sent):
        await mark_tenant_digest_sent(db, tenant=tenant, sent_at=generated_at)

    logger.info(
        "supervisor_audit_digest.sent",
        tenant_id=str(tenant_id),
        recipients=len(recipients),
        sent_count=sent_count,
        slack_sent=slack_sent,
        discord_sent=discord_sent,
        teams_sent=teams_sent,
        action_count=len(rows),
    )
    return {
        "tenant_id": str(tenant_id),
        "sent": sent_count > 0 or slack_sent or discord_sent or teams_sent,
        "recipients": recipients,
        "sent_count": sent_count,
        "slack_sent": slack_sent,
        "discord_sent": discord_sent,
        "teams_sent": teams_sent,
        "action_count": len(rows),
    }


async def run_supervisor_audit_digest_tick(db: AsyncSession) -> dict[str, Any]:
    """Send digests for active tenants due at the current UTC hour."""

    if not settings.supervisor_audit_digest_enabled:
        return {"enabled": False, "tenants_processed": 0, "tenants_sent": 0}

    now = datetime.now(tz=UTC)
    tenants = list(
        (await db.scalars(select(Tenant).where(Tenant.status == "active"))).all(),
    )
    processed = 0
    sent = 0
    skipped = 0
    results: list[dict[str, Any]] = []
    for tenant in tenants:
        if not is_tenant_digest_due(tenant=tenant, now=now):
            skipped += 1
            continue
        processed += 1
        result = await send_supervisor_audit_digest_for_tenant(
            db,
            tenant_id=tenant.id,
            mark_scheduled_sent=True,
        )
        results.append(result)
        if result.get("sent"):
            sent += 1
    if sent > 0:
        from app.application.services.supervisor.session_audit_digest_rollup import (
            fetch_supervisor_audit_digest_rollup,
            format_digest_health_slack_summary,
            invalidate_supervisor_audit_rollup_cache,
        )

        await invalidate_supervisor_audit_rollup_cache()
        try:
            rollup = await fetch_supervisor_audit_digest_rollup(db, window_hours=168)
            logger.info(
                "supervisor_audit_digest.tick_health",
                tenants_sent=sent,
                digest_health=format_digest_health_slack_summary(rollup),
            )
        except Exception as exc:  # noqa: BLE001 — health probe must not fail tick
            logger.warning("supervisor_audit_digest.tick_health_probe_failed", error=str(exc))
    return {
        "enabled": True,
        "tenants_processed": processed,
        "tenants_skipped": skipped,
        "tenants_sent": sent,
        "results": results,
    }


async def purge_expired_tenant_audit_logs(db: AsyncSession) -> dict[str, int]:
    """Delete tenant audit rows older than configured retention."""

    if not settings.tenant_audit_retention_enabled:
        return {"deleted": 0, "enabled": False}

    cutoff = datetime.now(tz=UTC) - timedelta(days=settings.tenant_audit_retention_days)
    result = await db.execute(delete(TenantAuditLog).where(TenantAuditLog.created_at < cutoff))
    deleted = int(result.rowcount or 0)
    if deleted:
        from app.application.services.supervisor.session_audit_digest_rollup import (
            invalidate_supervisor_audit_rollup_cache,
        )

        await invalidate_supervisor_audit_rollup_cache()
        logger.info(
            "tenant_audit_retention.purged",
            deleted=deleted,
            cutoff=cutoff.isoformat(),
            retention_days=settings.tenant_audit_retention_days,
        )
    return {"deleted": deleted, "enabled": True, "cutoff": cutoff.isoformat()}


__all__ = [
    "build_supervisor_audit_digest_markdown",
    "build_supervisor_audit_digest_slack_text",
    "list_supervisor_audit_rows_since",
    "list_tenant_audit_digest_recipients",
    "purge_expired_tenant_audit_logs",
    "run_supervisor_audit_digest_tick",
    "send_supervisor_audit_digest_discord",
    "send_supervisor_audit_digest_for_tenant",
    "send_supervisor_audit_digest_slack",
    "send_supervisor_audit_digest_teams",
]
