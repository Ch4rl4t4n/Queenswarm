"""Weekly Execution Studio telemetry rollup for operator Slack/email digests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio_notifications import (
    notify_execution_studio_email,
    notify_execution_studio_pending_approval,
)
from app.application.services.execution_studio_telemetry import build_activity_telemetry
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

logger = get_logger(__name__)


def format_weekly_rollup_message(*, tenant_name: str, telemetry: dict[str, Any]) -> str:
    """Build operator-facing weekly Execution Studio summary text (Slack markdown)."""

    top_connectors = sorted(
        (telemetry.get("connector_chart") or []),
        key=lambda row: int(row.get("runs") or 0),
        reverse=True,
    )[:5]
    connector_lines = ", ".join(
        f"{row.get('slug')} ({row.get('runs')} runs, {row.get('blocks')} blocked)"
        for row in top_connectors
    ) or "none"

    return (
        f"Weekly Execution Studio rollup for *{tenant_name}*\n"
        f"Tool runs: {telemetry.get('tool_executes', 0)} · "
        f"Browser steps: {telemetry.get('browser_steps', 0)} · "
        f"Proposals: {telemetry.get('proposals_created', 0)} · "
        f"Cost blocks: {telemetry.get('cost_tier_blocks', 0)}\n"
        f"Top connectors: {connector_lines}\n"
        f"Window: last {telemetry.get('window_limit', 40)} activity events"
    )


def format_weekly_rollup_email_body(*, tenant_name: str, telemetry: dict[str, Any]) -> str:
    """Plain-text weekly rollup for SMTP delivery."""

    slack_text = format_weekly_rollup_message(tenant_name=tenant_name, telemetry=telemetry)
    return slack_text.replace("*", "")


async def send_weekly_execution_studio_rollup(
    session: AsyncSession,
    *,
    tenant: Tenant,
) -> dict[str, Any]:
    """Send weekly telemetry digest to configured operator webhooks."""

    if not settings.execution_studio_enabled or not settings.execution_studio_weekly_rollup_enabled:
        return {"ok": False, "skipped": True, "reason": "disabled"}

    preview = build_weekly_execution_studio_rollup_preview(tenant=tenant)
    message = str(preview["message"])
    email_body = str(preview["email_body"])
    telemetry = preview["telemetry"]
    channels = await notify_execution_studio_pending_approval(
        tenant=tenant,
        title="Execution Studio weekly rollup",
        message=message,
        color="#FFB800",
    )
    channels["email"] = await notify_execution_studio_email(
        tenant=tenant,
        title=f"Execution Studio weekly rollup · {tenant.name}",
        body=email_body,
    )

    root = dict(tenant.operator_settings or {})
    studio = dict(root.get("execution_studio") or {}) if isinstance(root.get("execution_studio"), dict) else {}
    studio["last_weekly_rollup_at"] = datetime.now(tz=UTC).isoformat()
    root["execution_studio"] = studio
    tenant.operator_settings = root
    await session.flush()

    sent = any(channels.values())
    logger.info(
        "execution_studio.weekly_rollup_sent",
        agent_id="reporter_bee",
        swarm_id=str(tenant.id),
        task_id="weekly_rollup",
        channels=channels,
    )
    return {"ok": sent, "tenant_id": str(tenant.id), "channels": channels, "telemetry": telemetry}


def build_weekly_execution_studio_rollup_preview(*, tenant: Tenant) -> dict[str, Any]:
    """Build weekly rollup message bodies without sending notifications."""

    telemetry = build_activity_telemetry(tenant, limit=40)
    message = format_weekly_rollup_message(tenant_name=tenant.name, telemetry=telemetry)
    email_body = format_weekly_rollup_email_body(tenant_name=tenant.name, telemetry=telemetry)
    bucket = dict(tenant.operator_settings or {}).get("execution_studio") or {}
    last_sent_at = bucket.get("last_weekly_rollup_at") if isinstance(bucket, dict) else None
    return {
        "message": message,
        "email_body": email_body,
        "telemetry": telemetry,
        "last_sent_at": last_sent_at if isinstance(last_sent_at, str) else None,
    }


async def run_weekly_execution_studio_rollup_tick(session: AsyncSession) -> dict[str, Any]:
    """Iterate tenants and send weekly Execution Studio rollups."""

    stmt = select(Tenant).where(Tenant.status == "active")
    tenants = list((await session.scalars(stmt)).all())
    results: list[dict[str, Any]] = []
    for tenant in tenants:
        try:
            outcome = await send_weekly_execution_studio_rollup(session, tenant=tenant)
            results.append(outcome)
        except Exception as exc:
            logger.warning(
                "execution_studio.weekly_rollup_failed",
                agent_id="reporter_bee",
                swarm_id=str(tenant.id),
                task_id="weekly_rollup",
                error=str(exc)[:200],
            )
            results.append({"ok": False, "tenant_id": str(tenant.id), "error": str(exc)[:200]})
    await session.commit()
    return {"tenants": len(tenants), "results": results}


__all__ = [
    "build_weekly_execution_studio_rollup_preview",
    "format_weekly_rollup_email_body",
    "format_weekly_rollup_message",
    "run_weekly_execution_studio_rollup_tick",
    "send_weekly_execution_studio_rollup",
]
