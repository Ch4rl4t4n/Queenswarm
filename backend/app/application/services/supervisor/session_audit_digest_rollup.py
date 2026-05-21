"""Multi-tenant supervisor operator audit digest rollup for admin command center."""

from __future__ import annotations

import csv
import io
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.session_audit import SUPERVISOR_SESSION_TARGET_TYPE
from app.application.services.supervisor.session_audit_digest_config import (
    classify_tenant_digest_health,
    effective_digest_enabled,
    get_tenant_audit_digest_config,
)
from app.core.config import settings
from app.core.notifications import notify_email, notify_slack
from app.core.redis_client import get_json, redis_delete, set_json
from app.infrastructure.persistence.models.tenant import Tenant, TenantAuditLog

logger = structlog.get_logger(__name__)


def fill_supervisor_audit_rollup_daily_trend(
    *,
    start_day: datetime,
    day_count: int,
    rows: list[tuple[str, int, int]],
) -> list[dict[str, Any]]:
    """Build a contiguous UTC day series with zero-filled gaps."""

    safe_days = max(1, min(int(day_count), 30))
    start = start_day.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    by_date = {
        day: {"date": day, "action_count": actions, "tenants_active": tenants}
        for day, actions, tenants in rows
    }
    series: list[dict[str, Any]] = []
    for offset in range(safe_days):
        day_key = (start + timedelta(days=offset)).date().isoformat()
        series.append(
            by_date.get(
                day_key,
                {"date": day_key, "action_count": 0, "tenants_active": 0},
            ),
        )
    return series


async def build_supervisor_audit_rollup_daily_trend(
    db: AsyncSession,
    *,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Return per-day supervisor operator action counts for sparkline charts."""

    day_count = max(1, min(int(days), 30))
    now = datetime.now(tz=UTC)
    start = (now - timedelta(days=day_count - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    day_bucket = func.date_trunc("day", TenantAuditLog.created_at)

    raw_rows = list(
        (
            await db.execute(
                select(
                    day_bucket.label("day"),
                    func.count().label("action_count"),
                    func.count(func.distinct(TenantAuditLog.tenant_id)).label("tenants_active"),
                )
                .where(
                    TenantAuditLog.target_type == SUPERVISOR_SESSION_TARGET_TYPE,
                    TenantAuditLog.created_at >= start,
                )
                .group_by(day_bucket)
                .order_by(day_bucket),
            )
        ).all(),
    )

    parsed_rows: list[tuple[str, int, int]] = []
    for row in raw_rows:
        day_value = row.day
        if hasattr(day_value, "date"):
            day_key = day_value.date().isoformat()
        else:
            day_key = str(day_value)[:10]
        parsed_rows.append((day_key, int(row.action_count or 0), int(row.tenants_active or 0)))

    return fill_supervisor_audit_rollup_daily_trend(
        start_day=start,
        day_count=day_count,
        rows=parsed_rows,
    )


async def build_supervisor_audit_digest_rollup(
    db: AsyncSession,
    *,
    window_hours: int = 168,
) -> dict[str, Any]:
    """Aggregate supervisor session operator audit activity across active tenants."""

    hours = max(1, min(int(window_hours), 168))
    since = datetime.now(tz=UTC) - timedelta(hours=hours)
    generated_at = datetime.now(tz=UTC)

    tenants = list(
        (await db.scalars(select(Tenant).where(Tenant.status == "active"))).all(),
    )

    action_rows = list(
        (
            await db.execute(
                select(
                    TenantAuditLog.tenant_id,
                    TenantAuditLog.action,
                    func.count().label("action_count"),
                )
                .where(
                    TenantAuditLog.target_type == SUPERVISOR_SESSION_TARGET_TYPE,
                    TenantAuditLog.created_at >= since,
                )
                .group_by(TenantAuditLog.tenant_id, TenantAuditLog.action),
            )
        ).all(),
    )

    session_rows = list(
        (
            await db.execute(
                select(
                    TenantAuditLog.tenant_id,
                    func.count(func.distinct(TenantAuditLog.target_ref)).label("session_count"),
                )
                .where(
                    TenantAuditLog.target_type == SUPERVISOR_SESSION_TARGET_TYPE,
                    TenantAuditLog.created_at >= since,
                )
                .group_by(TenantAuditLog.tenant_id),
            )
        ).all(),
    )

    per_tenant_actions: dict[uuid.UUID, Counter[str]] = defaultdict(Counter)
    global_counts: Counter[str] = Counter()
    for row in action_rows:
        tenant_id = row.tenant_id
        action = str(row.action)
        count = int(row.action_count or 0)
        per_tenant_actions[tenant_id][action] += count
        global_counts[action] += count

    session_counts: dict[uuid.UUID, int] = {
        row.tenant_id: int(row.session_count or 0) for row in session_rows
    }

    tenant_summaries: list[dict[str, Any]] = []
    digest_health_summary: Counter[str] = Counter()
    total_actions = 0
    for tenant in tenants:
        counts = per_tenant_actions.get(tenant.id, Counter())
        action_count = sum(counts.values())
        if action_count <= 0:
            continue
        total_actions += action_count
        digest_cfg = get_tenant_audit_digest_config(tenant)
        digest_enabled = effective_digest_enabled(tenant=tenant)
        digest_health = classify_tenant_digest_health(
            tenant=tenant,
            digest_enabled=digest_enabled,
            now=generated_at,
        )
        digest_health_summary[digest_health] += 1
        tenant_summaries.append(
            {
                "tenant_id": str(tenant.id),
                "tenant_name": tenant.name,
                "tenant_slug": tenant.slug,
                "platform_mode": tenant.platform_mode,
                "action_count": action_count,
                "session_count": session_counts.get(tenant.id, 0),
                "action_counts": dict(counts.most_common()),
                "digest_enabled": digest_enabled,
                "digest_health": digest_health,
                "last_digest_sent_at": digest_cfg.get("last_sent_at"),
            },
        )

    tenant_summaries.sort(key=lambda item: (-int(item["action_count"]), str(item["tenant_name"])))
    daily_trend = await build_supervisor_audit_rollup_daily_trend(db, days=7)

    return {
        "window_hours": hours,
        "generated_at": generated_at.isoformat(),
        "tenants_active": len(tenant_summaries),
        "tenants_total": len(tenants),
        "total_actions": total_actions,
        "global_action_counts": dict(global_counts.most_common()),
        "daily_trend": daily_trend,
        "digest_health_summary": dict(digest_health_summary),
        "tenants": tenant_summaries,
    }


def supervisor_audit_rollup_cache_key(*, window_hours: int) -> str:
    """Build Redis cache key for one rollup window."""

    hours = max(1, min(int(window_hours), 168))
    return f"supervisor:audit_rollup:v1:{hours}"


def supervisor_audit_rollup_cache_windows(*, window_hours: int | None = None) -> list[int]:
    """Return rollup window sizes whose Redis snapshots should be dropped."""

    if window_hours is not None:
        return [max(1, min(int(window_hours), 168))]

    configured = max(1, min(int(settings.supervisor_audit_rollup_window_hours or 168), 168))
    return sorted({configured, 24, 168})


async def invalidate_supervisor_audit_rollup_cache(
    *,
    window_hours: int | None = None,
) -> int:
    """Delete cached rollup snapshot(s) so the next fetch rebuilds from PostgreSQL."""

    if int(settings.supervisor_audit_rollup_cache_ttl_sec or 0) <= 0:
        return 0

    removed = 0
    for hours in supervisor_audit_rollup_cache_windows(window_hours=window_hours):
        removed += await redis_delete(supervisor_audit_rollup_cache_key(window_hours=hours))
    if removed:
        logger.info(
            "supervisor_audit_rollup.cache_invalidated",
            removed=removed,
            window_hours=window_hours,
        )
    return removed


async def fetch_supervisor_audit_digest_rollup(
    db: AsyncSession,
    *,
    window_hours: int = 168,
    bypass_cache: bool = False,
) -> dict[str, Any]:
    """Return rollup payload, optionally served from Redis cache."""

    ttl = int(settings.supervisor_audit_rollup_cache_ttl_sec or 0)
    cache_key = supervisor_audit_rollup_cache_key(window_hours=window_hours)
    if ttl > 0 and not bypass_cache:
        cached = await get_json(cache_key)
        if isinstance(cached, dict) and cached.get("window_hours") is not None:
            payload = dict(cached)
            payload["cached"] = True
            return payload

    payload = await build_supervisor_audit_digest_rollup(db, window_hours=window_hours)
    payload["cached"] = False
    if ttl > 0:
        store = dict(payload)
        store.pop("cached", None)
        await set_json(cache_key, store, ttl=ttl)
    return payload


def summarize_digest_health_alerts(payload: dict[str, Any]) -> dict[str, Any]:
    """Summarize tenant digest delivery issues for operator alerts."""

    summary = dict(payload.get("digest_health_summary") or {})
    stale_count = int(summary.get("stale") or 0)
    never_sent_count = int(summary.get("never_sent") or 0)
    attention_tenants = [
        tenant
        for tenant in payload.get("tenants") or []
        if isinstance(tenant, dict) and tenant.get("digest_health") in {"stale", "never_sent"}
    ]
    return {
        "stale_count": stale_count,
        "never_sent_count": never_sent_count,
        "needs_attention": stale_count > 0 or never_sent_count > 0,
        "attention_tenants": attention_tenants,
    }


def format_digest_health_markdown_section(payload: dict[str, Any]) -> list[str]:
    """Render digest delivery health section for rollup markdown exports."""

    alerts = summarize_digest_health_alerts(payload)
    lines = ["", "## Digest delivery health", ""]
    if not alerts["needs_attention"]:
        lines.append("_All active hives with operator activity have healthy digest delivery._")
        return lines

    lines.append(
        f"- **Stale deliveries:** {alerts['stale_count']} · "
        f"**Never sent:** {alerts['never_sent_count']}",
    )
    lines.append("- Review tenant schedule in **Settings → Audit log**.")
    lines.append("")
    lines.append("### Hives needing attention")
    lines.append("")
    for tenant in alerts["attention_tenants"]:
        if not isinstance(tenant, dict):
            continue
        lines.append(
            f"- **{tenant.get('tenant_name', '?')}** (`{tenant.get('tenant_slug', '?')}`) · "
            f"health `{tenant.get('digest_health', 'unknown')}` · "
            f"last sent `{tenant.get('last_digest_sent_at') or 'never'}`",
        )
    return lines


def format_digest_health_slack_summary(payload: dict[str, Any]) -> str:
    """Return a one-line Slack digest health summary."""

    alerts = summarize_digest_health_alerts(payload)
    if not alerts["needs_attention"]:
        return "Digest delivery: all active hives healthy."
    return (
        f"Digest alerts — stale: {alerts['stale_count']} · "
        f"never sent: {alerts['never_sent_count']}"
    )


def serialize_supervisor_audit_rollup_markdown(payload: dict[str, Any]) -> str:
    """Render cross-tenant rollup as compliance-friendly Markdown."""

    lines = [
        "# Queenswarm Supervisor Audit Rollup",
        "",
        f"- Generated: `{payload.get('generated_at', '')}`",
        f"- Window: last {payload.get('window_hours', 168)} hours",
        f"- Active hives: {payload.get('tenants_active', 0)} / {payload.get('tenants_total', 0)} tenants",
        f"- Total operator actions: {payload.get('total_actions', 0)}",
        "",
        "## Global action counts",
        "",
    ]
    global_counts = dict(payload.get("global_action_counts") or {})
    if global_counts:
        for action, count in global_counts.items():
            lines.append(f"- `{action}`: {count}")
    else:
        lines.append("_No supervisor operator actions in this window._")
    lines.extend(format_digest_health_markdown_section(payload))
    lines.extend(["", "## Per-tenant breakdown", ""])
    tenants = list(payload.get("tenants") or [])
    if not tenants:
        lines.append("_No tenant activity._")
    else:
        for tenant in tenants:
            if not isinstance(tenant, dict):
                continue
            action_bits = ", ".join(
                f"`{action}`={count}" for action, count in dict(tenant.get("action_counts") or {}).items()
            )
            lines.append(
                f"- **{tenant.get('tenant_name', '?')}** (`{tenant.get('tenant_slug', '?')}`) · "
                f"mode `{tenant.get('platform_mode', '?')}` · actions **{tenant.get('action_count', 0)}** · "
                f"sessions **{tenant.get('session_count', 0)}** · digest "
                f"{tenant.get('digest_health', 'disabled')} · {action_bits or '—'}",
            )
    trend = list(payload.get("daily_trend") or [])
    if trend:
        lines.extend(["", "## 7-day trend", ""])
        for point in trend:
            if not isinstance(point, dict):
                continue
            lines.append(
                f"- `{point.get('date', '')}`: {point.get('action_count', 0)} actions · "
                f"{point.get('tenants_active', 0)} active hives",
            )
    return "\n".join(lines) + "\n"


def serialize_supervisor_audit_rollup_csv(payload: dict[str, Any]) -> str:
    """Render cross-tenant rollup as CSV for spreadsheets."""

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "tenant_id",
            "tenant_name",
            "tenant_slug",
            "platform_mode",
            "action_count",
            "session_count",
            "digest_enabled",
            "digest_health",
            "last_digest_sent_at",
            "action_breakdown",
        ],
    )
    for tenant in payload.get("tenants") or []:
        if not isinstance(tenant, dict):
            continue
        breakdown = "; ".join(
            f"{action}={count}" for action, count in dict(tenant.get("action_counts") or {}).items()
        )
        writer.writerow(
            [
                tenant.get("tenant_id", ""),
                tenant.get("tenant_name", ""),
                tenant.get("tenant_slug", ""),
                tenant.get("platform_mode", ""),
                tenant.get("action_count", 0),
                tenant.get("session_count", 0),
                tenant.get("digest_enabled", False),
                tenant.get("digest_health", "disabled"),
                tenant.get("last_digest_sent_at") or "",
                breakdown,
            ],
        )
    return buffer.getvalue()


async def send_supervisor_audit_rollup_operator_email(
    db: AsyncSession,
    *,
    window_hours: int | None = None,
    recipients: list[str] | None = None,
) -> dict[str, Any]:
    """Email platform operators a cross-tenant supervisor audit rollup."""

    hours = window_hours or settings.supervisor_audit_rollup_window_hours
    payload = await fetch_supervisor_audit_digest_rollup(db, window_hours=hours, bypass_cache=True)
    alerts = summarize_digest_health_alerts(payload)
    body = serialize_supervisor_audit_rollup_markdown(payload)
    attachment = body.encode("utf-8")
    targets = list(recipients or [])
    if not targets and settings.notify_email:
        targets = [settings.notify_email.strip()]

    subject = "Supervisor audit weekly rollup · Queenswarm"
    if alerts["needs_attention"]:
        subject = (
            f"Supervisor audit rollup · {alerts['stale_count']} stale / "
            f"{alerts['never_sent_count']} never sent · Queenswarm"
        )

    sent_count = 0
    for recipient in targets:
        ok = await notify_email(
            subject=subject,
            body=body,
            to_email=recipient,
            attachment_bytes=attachment,
            attachment_filename=f"supervisor-audit-rollup-{datetime.now(tz=UTC).date().isoformat()}.md",
        )
        if ok:
            sent_count += 1

    slack_color = "#FF00AA" if alerts["needs_attention"] else "#FFB800"
    slack_sent = await notify_slack(
        f"*Supervisor audit rollup*\n"
        f"Window: {hours}h · Actions: {payload.get('total_actions', 0)} · "
        f"Active hives: {payload.get('tenants_active', 0)}\n"
        f"{format_digest_health_slack_summary(payload)}",
        color=slack_color,
        title="Operator audit rollup",
    )

    if not sent_count and not slack_sent:
        return {"sent": False, "reason": "no_delivery_channels", "total_actions": payload.get("total_actions", 0)}

    logger.info(
        "supervisor_audit_rollup.sent",
        sent_count=sent_count,
        slack_sent=slack_sent,
        total_actions=payload.get("total_actions", 0),
        tenants_active=payload.get("tenants_active", 0),
        digest_stale_count=alerts["stale_count"],
        digest_never_sent_count=alerts["never_sent_count"],
    )
    return {
        "sent": sent_count > 0 or slack_sent,
        "sent_count": sent_count,
        "slack_sent": slack_sent,
        "recipients": targets,
        "total_actions": payload.get("total_actions", 0),
        "tenants_active": payload.get("tenants_active", 0),
        "digest_stale_count": alerts["stale_count"],
        "digest_never_sent_count": alerts["never_sent_count"],
        "digest_needs_attention": alerts["needs_attention"],
    }


async def run_supervisor_audit_rollup_email_tick(db: AsyncSession) -> dict[str, Any]:
    """Scheduled weekly platform operator rollup delivery."""

    if not settings.supervisor_audit_rollup_email_enabled:
        return {"enabled": False, "sent": False}
    result = await send_supervisor_audit_rollup_operator_email(db)
    if result.get("digest_needs_attention"):
        logger.warning(
            "supervisor_audit_rollup.digest_health_alert",
            digest_stale_count=result.get("digest_stale_count", 0),
            digest_never_sent_count=result.get("digest_never_sent_count", 0),
        )
    return {"enabled": True, **result}


async def send_attention_supervisor_audit_digests(
    db: AsyncSession,
    *,
    window_hours: int = 168,
) -> dict[str, Any]:
    """Send digests for rollup tenants flagged stale or never_sent."""

    import uuid as uuid_module

    from app.application.services.supervisor.session_audit_digest import (
        send_supervisor_audit_digest_for_tenant,
    )

    hours = max(1, min(int(window_hours), 168))
    payload = await build_supervisor_audit_digest_rollup(db, window_hours=hours)
    alerts = summarize_digest_health_alerts(payload)
    attention_tenants = list(alerts["attention_tenants"])
    if not attention_tenants:
        return {
            "sent": False,
            "reason": "no_attention_tenants",
            "tenants_attempted": 0,
            "tenants_sent": 0,
            "results": [],
        }

    results: list[dict[str, Any]] = []
    sent = 0
    for tenant_row in attention_tenants:
        if not isinstance(tenant_row, dict):
            continue
        tenant_id = uuid_module.UUID(str(tenant_row["tenant_id"]))
        result = await send_supervisor_audit_digest_for_tenant(
            db,
            tenant_id=tenant_id,
            window_hours=hours,
            mark_scheduled_sent=True,
        )
        results.append(result)
        if result.get("sent"):
            sent += 1

    if sent > 0:
        await invalidate_supervisor_audit_rollup_cache()

    logger.info(
        "supervisor_audit_digest.attention_batch_sent",
        tenants_attempted=len(attention_tenants),
        tenants_sent=sent,
        digest_stale_count=alerts["stale_count"],
        digest_never_sent_count=alerts["never_sent_count"],
    )
    return {
        "sent": sent > 0,
        "reason": None if sent > 0 else "no_delivery_channels",
        "tenants_attempted": len(attention_tenants),
        "tenants_sent": sent,
        "digest_stale_count": alerts["stale_count"],
        "digest_never_sent_count": alerts["never_sent_count"],
        "results": results,
    }


__all__ = [
    "build_supervisor_audit_digest_rollup",
    "build_supervisor_audit_rollup_daily_trend",
    "fetch_supervisor_audit_digest_rollup",
    "fill_supervisor_audit_rollup_daily_trend",
    "format_digest_health_markdown_section",
    "format_digest_health_slack_summary",
    "invalidate_supervisor_audit_rollup_cache",
    "run_supervisor_audit_rollup_email_tick",
    "send_attention_supervisor_audit_digests",
    "send_supervisor_audit_rollup_operator_email",
    "serialize_supervisor_audit_rollup_csv",
    "serialize_supervisor_audit_rollup_markdown",
    "summarize_digest_health_alerts",
    "supervisor_audit_rollup_cache_key",
    "supervisor_audit_rollup_cache_windows",
]
