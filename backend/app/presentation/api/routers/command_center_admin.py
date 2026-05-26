"""Admin command center — host load, dependencies, LLM/API wiring."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from starlette.responses import Response

from app.application.services.command_center import build_command_center_snapshot
from app.core.logging import get_logger
from app.presentation.api.deps import DashboardAdmin, DbSession

logger = get_logger(__name__)
router = APIRouter(prefix="/operator/command-center", tags=["Command Center"])


class NotifyTestResponse(BaseModel):
    """Smoke-test result for Slack/email from command center."""

    message: str
    results: dict[str, bool] = Field(default_factory=dict)


class AuditDigestRollupTenantView(BaseModel):
    """Per-tenant supervisor audit activity in the rollup window."""

    tenant_id: str
    tenant_name: str
    tenant_slug: str
    platform_mode: str
    action_count: int
    session_count: int
    action_counts: dict[str, int] = Field(default_factory=dict)
    digest_enabled: bool
    digest_health: Literal["healthy", "stale", "never_sent", "disabled"] = "disabled"
    last_digest_sent_at: str | None = None


class AuditDigestRollupDayView(BaseModel):
    """One UTC day in the supervisor audit rollup trend series."""

    date: str
    action_count: int
    tenants_active: int


class AuditDigestRollupView(BaseModel):
    """Cross-tenant weekly supervisor operator audit summary."""

    window_hours: int
    generated_at: str
    tenants_active: int
    tenants_total: int
    total_actions: int
    global_action_counts: dict[str, int] = Field(default_factory=dict)
    daily_trend: list[AuditDigestRollupDayView] = Field(default_factory=list)
    digest_health_summary: dict[str, int] = Field(default_factory=dict)
    tenants: list[AuditDigestRollupTenantView] = Field(default_factory=list)
    cached: bool = False


class AuditDigestRollupSendResponse(BaseModel):
    """Result envelope for manual platform rollup email send."""

    sent: bool
    reason: str | None = None
    sent_count: int = 0
    slack_sent: bool = False
    recipients: list[str] = Field(default_factory=list)
    total_actions: int = 0
    tenants_active: int = 0
    digest_stale_count: int = 0
    digest_never_sent_count: int = 0
    digest_needs_attention: bool = False


class TenantAuditDigestSendResponse(BaseModel):
    """Result envelope for cross-tenant manual supervisor digest send."""

    tenant_id: str
    sent: bool
    reason: str | None = None
    sent_count: int = 0
    slack_sent: bool = False
    discord_sent: bool = False
    teams_sent: bool = False
    action_count: int = 0
    recipients: list[str] = Field(default_factory=list)


class TenantAuditDigestBatchSendResponse(BaseModel):
    """Result envelope for batch stale/never-sent digest recovery."""

    sent: bool
    reason: str | None = None
    tenants_attempted: int = 0
    tenants_sent: int = 0
    digest_stale_count: int = 0
    digest_never_sent_count: int = 0


@router.get("", summary="Admin command center snapshot")
async def get_command_center_snapshot(_: DashboardAdmin) -> dict[str, Any]:
    """Return host metrics, dependency health, and integration status for admin settings."""

    return await build_command_center_snapshot()


@router.get(
    "/audit-digest-rollup",
    response_model=AuditDigestRollupView,
    summary="Multi-tenant supervisor audit digest weekly rollup",
)
async def get_audit_digest_rollup(
    _: DashboardAdmin,
    db: DbSession,
    window_hours: int = Query(default=168, ge=1, le=168),
) -> AuditDigestRollupView:
    """Return operator session audit activity aggregated across all active tenants."""

    from app.application.services.supervisor.session_audit_digest_rollup import (
        fetch_supervisor_audit_digest_rollup,
    )

    payload = await fetch_supervisor_audit_digest_rollup(db, window_hours=window_hours)
    return AuditDigestRollupView(**payload)


@router.get(
    "/audit-digest-rollup/export",
    summary="Export cross-tenant supervisor audit rollup (CSV or Markdown)",
)
async def export_audit_digest_rollup(
    _: DashboardAdmin,
    db: DbSession,
    export_format: Literal["csv", "markdown"] = Query(default="markdown", alias="format"),
    window_hours: int = Query(default=168, ge=1, le=168),
) -> Response:
    """Download compliance rollup export for platform operators."""

    from app.application.services.supervisor.session_audit_digest_rollup import (
        fetch_supervisor_audit_digest_rollup,
        serialize_supervisor_audit_rollup_csv,
        serialize_supervisor_audit_rollup_markdown,
    )

    payload = await fetch_supervisor_audit_digest_rollup(db, window_hours=window_hours)
    stamp = datetime.now(tz=UTC).date().isoformat()
    if export_format == "csv":
        content = serialize_supervisor_audit_rollup_csv(payload)
        media_type = "text/csv; charset=utf-8"
        filename = f"supervisor-audit-rollup-{stamp}.csv"
    else:
        content = serialize_supervisor_audit_rollup_markdown(payload)
        media_type = "text/markdown; charset=utf-8"
        filename = f"supervisor-audit-rollup-{stamp}.md"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/audit-digest-rollup/send",
    response_model=AuditDigestRollupSendResponse,
    summary="Email platform supervisor audit rollup to NOTIFY_EMAIL",
)
async def send_audit_digest_rollup_now(
    _: DashboardAdmin,
    db: DbSession,
    window_hours: int = Query(default=168, ge=1, le=168),
) -> AuditDigestRollupSendResponse:
    """Trigger one cross-tenant rollup email + Slack summary for platform operators."""

    from app.application.services.supervisor.session_audit_digest_rollup import (
        send_supervisor_audit_rollup_operator_email,
    )

    result = await send_supervisor_audit_rollup_operator_email(db, window_hours=window_hours)
    return AuditDigestRollupSendResponse(
        sent=bool(result.get("sent")),
        reason=result.get("reason"),
        sent_count=int(result.get("sent_count") or 0),
        slack_sent=bool(result.get("slack_sent")),
        recipients=list(result.get("recipients") or []),
        total_actions=int(result.get("total_actions") or 0),
        tenants_active=int(result.get("tenants_active") or 0),
        digest_stale_count=int(result.get("digest_stale_count") or 0),
        digest_never_sent_count=int(result.get("digest_never_sent_count") or 0),
        digest_needs_attention=bool(result.get("digest_needs_attention")),
    )


@router.post(
    "/audit-digest-rollup/tenants/{tenant_id}/send-digest",
    response_model=TenantAuditDigestSendResponse,
    summary="Send supervisor audit digest for one tenant (platform operator)",
)
async def send_tenant_audit_digest_from_command_center(
    tenant_id: UUID,
    _: DashboardAdmin,
    db: DbSession,
    window_hours: int = Query(default=168, ge=1, le=168),
) -> TenantAuditDigestSendResponse:
    """Trigger one tenant digest from command center for stale/never-sent recovery."""

    from app.application.services.supervisor.session_audit_digest import send_supervisor_audit_digest_for_tenant
    from app.application.services.supervisor.session_audit_digest_rollup import (
        invalidate_supervisor_audit_rollup_cache,
    )
    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await db.get(Tenant, tenant_id)
    if tenant is None or tenant.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")

    result = await send_supervisor_audit_digest_for_tenant(
        db,
        tenant_id=tenant_id,
        window_hours=window_hours,
        mark_scheduled_sent=True,
    )
    if result.get("sent"):
        await invalidate_supervisor_audit_rollup_cache()

    return TenantAuditDigestSendResponse(
        tenant_id=str(tenant_id),
        sent=bool(result.get("sent")),
        reason=result.get("reason"),
        sent_count=int(result.get("sent_count") or 0),
        slack_sent=bool(result.get("slack_sent")),
        discord_sent=bool(result.get("discord_sent")),
        teams_sent=bool(result.get("teams_sent")),
        action_count=int(result.get("action_count") or 0),
        recipients=list(result.get("recipients") or []),
    )


@router.post(
    "/audit-digest-rollup/send-attention-digests",
    response_model=TenantAuditDigestBatchSendResponse,
    summary="Send digests for all stale/never-sent tenants in rollup",
)
async def send_attention_audit_digests_from_command_center(
    _: DashboardAdmin,
    db: DbSession,
    window_hours: int = Query(default=168, ge=1, le=168),
) -> TenantAuditDigestBatchSendResponse:
    """Batch-send tenant digests flagged stale or never_sent in the current rollup."""

    from app.application.services.supervisor.session_audit_digest_rollup import (
        send_attention_supervisor_audit_digests,
    )

    result = await send_attention_supervisor_audit_digests(db, window_hours=window_hours)
    return TenantAuditDigestBatchSendResponse(
        sent=bool(result.get("sent")),
        reason=result.get("reason"),
        tenants_attempted=int(result.get("tenants_attempted") or 0),
        tenants_sent=int(result.get("tenants_sent") or 0),
        digest_stale_count=int(result.get("digest_stale_count") or 0),
        digest_never_sent_count=int(result.get("digest_never_sent_count") or 0),
    )


@router.post("/notify-test", summary="Smoke-test Slack + email wiring")
async def command_center_notify_test(_: DashboardAdmin, db: DbSession) -> NotifyTestResponse:
    """Trigger optional Slack/email notifications using deployment settings."""

    from app.application.services.supervisor.session_audit_digest_rollup import (
        fetch_supervisor_audit_digest_rollup,
        format_digest_health_slack_summary,
    )
    from app.core.notifications import notify_email, notify_slack

    digest_note = ""
    try:
        rollup = await fetch_supervisor_audit_digest_rollup(db, window_hours=168)
        digest_note = f" {format_digest_health_slack_summary(rollup)}"
    except Exception as exc:  # noqa: BLE001 — probe must not block notify smoke test
        logger.warning("command_center.notify_test.digest_probe_failed", error=str(exc))

    results: dict[str, bool] = {
        "slack": await notify_slack(
            f"🐝 Command center test — Queenswarm notifications OK.\n{digest_note.strip()}",
            color="#00FF88",
            title="Command Center",
        ),
        "email": await notify_email(
            subject="Queenswarm Command Center Test",
            body=(
                "🐝 Command center test — notification channel probe from admin settings."
                f"{digest_note}"
            ),
        ),
    }
    sent = [channel for channel, ok in results.items() if ok]
    skipped = [channel for channel, ok in results.items() if not ok]
    summary = (
        f"Delivered: {', '.join(sent) or 'none'}. "
        f"Skipped: {', '.join(skipped) or 'none'}."
        f"{digest_note}"
    )
    logger.info("command_center.notify_test", slack=results["slack"], email=results["email"])
    return NotifyTestResponse(message=summary, results=results)


@router.get(
    "/codebase-atlas",
    summary="Codebase Atlas — LOC, dev hours estimate, FE/BE architecture map",
)
async def get_codebase_atlas(_: DashboardAdmin) -> dict[str, Any]:
    """Return lines-of-code breakdown, git effort estimate, and architecture layers."""

    from app.application.services.codebase_atlas import build_codebase_atlas_cached

    return await build_codebase_atlas_cached()


__all__ = ["router"]
