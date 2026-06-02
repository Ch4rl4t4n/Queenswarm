"""Execution Studio HTTP surface — connections overview, policy, governed execution."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.execution_studio import (
    connection_setup_guide,
    execute_studio_tool,
    execution_studio_overview,
    merge_studio_notifications_patch,
    merge_studio_policy_patch,
    set_codebase_routine_enabled,
    studio_notifications,
    submit_codebase_pr_draft,
    trigger_codebase_maintainer_run,
)
from app.application.services.execution_studio_push import (
    clear_push_subscription,
    get_vapid_public_key,
    mark_user_push_enabled,
    upsert_push_subscription,
    web_push_configured,
)
from app.application.services.execution_studio_browser import execute_browser_fallback_step
from app.application.services.execution_studio_handoff import (
    create_codebase_execution_proposal,
    list_pending_codebase_proposals,
)
from app.application.services.execution_studio_manual import build_execution_studio_manual
from app.application.services.execution_studio_telemetry_rollup import (
    build_weekly_execution_studio_rollup_preview,
)
from app.application.services.execution_studio_notifications import (
    _resolve_email_recipients,
    _resolve_webhook,
    _telegram_fingerprint,
    ping_studio_digest_email,
    ping_studio_notification_webhooks,
    record_notification_test_status,
    send_studio_weekly_rollup_preview,
)
from app.core.config import get_settings
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DashboardSession, DbSession, require_tenant_permission
from app.core.jwt_tokens import parse_dashboard_user_subject

router = APIRouter(prefix="/execution-studio", tags=["Execution Studio"])


def _subject_uuid(sess: dict[str, Any]) -> uuid.UUID:
    raw = sess.get("sub")
    if not isinstance(raw, str) or not raw.strip():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing dashboard credential.")
    parsed = parse_dashboard_user_subject(raw.strip())
    if parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed subject.")
    return parsed


async def _tenant_from_session(sess: DashboardSession, db: DbSession) -> Tenant:
    raw_tid = sess.get("tenant_id")
    if raw_tid is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    try:
        tenant_id = raw_tid if isinstance(raw_tid, uuid.UUID) else uuid.UUID(str(raw_tid))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid tenant context.") from exc
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    return tenant


def _assert_enabled() -> None:
    if not get_settings().execution_studio_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution Studio disabled.")


class StudioPolicyPatch(BaseModel):
    """Partial tenant execution policy."""

    model_config = ConfigDict(extra="ignore")
    default_mode: Literal["draft", "simulate", "live"] | None = None
    live_requires_approval: bool | None = None
    simulate_allows_read_calls: bool | None = None
    codebase_default_mode: Literal["draft", "simulate", "live"] | None = None
    live_codebase_requires_approval: bool | None = None
    codebase_auto_approve_enabled: bool | None = None


class StudioNotificationsPatch(BaseModel):
    """Partial Execution Studio notification settings."""

    model_config = ConfigDict(extra="ignore")
    email_recipients: list[str] | None = None
    slack_webhook_url: str | None = None
    discord_webhook_url: str | None = None
    teams_webhook_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


class StudioPushSubscribeBody(BaseModel):
    """Browser PushManager subscription payload."""

    model_config = ConfigDict(extra="ignore")
    subscription: dict[str, Any] = Field(default_factory=dict)


class StudioWebhookTestBody(BaseModel):
    """Optional channel filter for webhook connectivity test."""

    model_config = ConfigDict(extra="ignore")
    channels: list[Literal["slack", "discord", "teams", "telegram"]] | None = None


class StudioRollupPreviewSendBody(BaseModel):
    """Optional channel filter for weekly digest preview delivery."""

    model_config = ConfigDict(extra="ignore")
    channel_group: Literal["webhooks", "email", "all"] | None = None
    channels: list[Literal["slack", "discord", "teams", "telegram", "email"]] | None = None


class StudioExecuteBody(BaseModel):
    """Governed tool invocation from Execution Studio."""

    model_config = ConfigDict(extra="ignore")
    connector_slug: str = Field(..., min_length=2, max_length=160)
    tool_name: str = Field(..., min_length=1, max_length=160)
    arguments: dict[str, Any] = Field(default_factory=dict)
    mode: Literal["draft", "simulate", "live"] | None = None
    manager_slug: str | None = Field(default=None, max_length=64)
    operator_confirmed: bool = False


class StudioBrowserStepBody(BaseModel):
    """Governed browser harness fallback step."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    goal: str = Field(..., min_length=3, max_length=4000)
    start_url: str | None = Field(default=None, max_length=2048)
    mode: Literal["draft", "simulate", "live"] | None = None
    operator_confirmed: bool = False


class StudioCodebaseRoutineBody(BaseModel):
    """Enable or pause Queen Maintainer weekly routine."""

    model_config = ConfigDict(extra="ignore")
    enabled: bool


class StudioCodebasePrDraftBody(BaseModel):
    """Governed PR draft for internal codebase lane."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    title: str = Field(..., min_length=3, max_length=256)
    body: str = Field(..., min_length=10, max_length=65_000)
    slug: str = Field(..., min_length=2, max_length=48)
    changed_paths: list[str] = Field(default_factory=list)
    mode: Literal["draft", "simulate", "live"] | None = None
    operator_confirmed: bool = False


class StudioCodebaseProposalBody(BaseModel):
    """Operator or agent-submitted codebase execution proposal."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    title: str = Field(..., min_length=3, max_length=260)
    description: str = Field(..., min_length=10, max_length=3500)
    goal_excerpt: str = Field(..., min_length=10, max_length=4000)
    suggested_paths: list[str] = Field(default_factory=list)
    proposed_by_role: str = Field(default="operator", max_length=64)


class StudioProposalReviewBody(BaseModel):
    """Approve or reject a codebase execution proposal from Execution Studio."""

    model_config = ConfigDict(extra="ignore")
    decision: Literal["approve", "reject"]


class StudioBulkProposalReviewBody(BaseModel):
    """Bulk approve/reject pending codebase execution proposals."""

    model_config = ConfigDict(extra="ignore")
    decision: Literal["approve", "reject"]
    limit: int = Field(default=50, ge=1, le=100)


@router.get("/overview", summary="Execution Studio connections and policy snapshot")
async def studio_overview(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:read")),
) -> dict[str, Any]:
    """Return connection readiness, packs, and operator policy."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    user_id = _subject_uuid(sess)
    return await execution_studio_overview(db, dashboard_user_id=user_id, tenant=tenant)


@router.delete("/activity", summary="Clear Execution Studio recent activity feed")
async def studio_clear_activity(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Remove all recent activity rows from the tenant operator feed."""

    _assert_enabled()
    from app.application.services.execution_studio_activity import clear_execution_activity

    tenant = await _tenant_from_session(sess, db)
    cleared = clear_execution_activity(tenant)
    await db.commit()
    return {"cleared": cleared, "recent_activity": []}


@router.get("/pending-approvals", summary="Pending Execution Studio operator confirmations")
async def studio_pending_approvals(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:read")),
) -> dict[str, Any]:
    """Lightweight badge payload for mobile notification bell."""

    _assert_enabled()
    from app.application.services.execution_studio_pending import build_pending_approvals_snapshot

    tenant = await _tenant_from_session(sess, db)
    return await build_pending_approvals_snapshot(db, tenant=tenant)


@router.patch("/policy", summary="Update Execution Studio tenant policy")
async def studio_policy_patch(
    body: StudioPolicyPatch,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Persist draft/simulate/live defaults for governed execution."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    tenant.operator_settings = merge_studio_policy_patch(
        tenant.operator_settings,
        body.model_dump(exclude_none=True),
    )
    await db.commit()
    await db.refresh(tenant)
    from app.application.services.execution_studio import studio_policy

    return {"policy": studio_policy(tenant)}


@router.patch("/notifications", summary="Update Execution Studio notification settings")
async def studio_notifications_patch(
    body: StudioNotificationsPatch,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Persist digest email recipients for weekly rollup and operator alerts."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    tenant.operator_settings = merge_studio_notifications_patch(
        tenant.operator_settings,
        body.model_dump(exclude_none=True),
    )
    await db.commit()
    await db.refresh(tenant)
    return {"notifications": studio_notifications(tenant)}


@router.post("/notifications/test-webhooks", summary="Ping Execution Studio notification webhooks")
async def studio_notifications_test_webhooks(
    body: StudioWebhookTestBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Send one test message to configured Slack, Discord, Teams, and/or Telegram channels."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    selected = body.channels or ["slack", "discord", "teams", "telegram"]
    results = await ping_studio_notification_webhooks(tenant=tenant, channels=selected)
    for channel in ("slack", "discord", "teams", "telegram"):
        if channel not in selected:
            continue
        value = (
            _telegram_fingerprint(tenant)
            if channel == "telegram"
            else (_resolve_webhook(tenant, channel=channel) or "")
        )
        record_notification_test_status(
            tenant,
            channel=channel,
            value=value,
            status="ok" if bool(results.get(channel)) else "fail",
        )
    await db.commit()
    return results


@router.post("/notifications/test-email", summary="Send Execution Studio digest test email")
async def studio_notifications_test_email(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Send one test digest email to configured operator recipients."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    results = await ping_studio_digest_email(tenant=tenant)
    email_value = ", ".join(_resolve_email_recipients(tenant))
    record_notification_test_status(
        tenant,
        channel="email",
        value=email_value,
        status="ok" if bool(results.get("sent")) else "fail",
    )
    await db.commit()
    return results


@router.get("/notifications/weekly-rollup-preview", summary="Preview weekly Execution Studio digest")
async def studio_notifications_weekly_rollup_preview(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:read")),
) -> dict[str, Any]:
    """Return formatted weekly rollup text without sending notifications."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    return build_weekly_execution_studio_rollup_preview(tenant=tenant)


@router.post("/notifications/send-weekly-rollup-preview", summary="Send weekly rollup preview to operators")
async def studio_notifications_send_weekly_rollup_preview(
    body: StudioRollupPreviewSendBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Deliver the formatted weekly rollup preview to configured webhooks and/or email."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    return await send_studio_weekly_rollup_preview(
        tenant=tenant,
        channel_group=body.channel_group,
        channels=body.channels,
        session=db,
    )


@router.get("/push/vapid-public-key", summary="VAPID public key for Execution Studio Web Push")
async def studio_push_vapid_public_key(
    _: DashboardSession,
    __: bool = Depends(require_tenant_permission("connectors:read")),
) -> dict[str, Any]:
    """Return server VAPID key when Web Push is configured."""

    _assert_enabled()
    configured = web_push_configured()
    return {"configured": configured, "public_key": get_vapid_public_key() if configured else None}


@router.post("/push/subscribe", summary="Subscribe browser to Execution Studio pending push")
async def studio_push_subscribe(
    body: StudioPushSubscribeBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Persist PushManager subscription for pending approval alerts."""

    _assert_enabled()
    if not web_push_configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="web_push_not_configured")
    tenant = await _tenant_from_session(sess, db)
    user_id = _subject_uuid(sess)
    user = await db.get(DashboardUser, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard user not found.")
    if not isinstance(body.subscription, dict) or not body.subscription.get("endpoint"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid push subscription.")

    tenant.operator_settings = upsert_push_subscription(
        tenant.operator_settings,
        user_id=user_id,
        subscription=body.subscription,
    )
    await mark_user_push_enabled(db, user=user, enabled=True)
    await db.commit()
    return {"ok": True, "enabled": True}


@router.delete("/push/subscribe", summary="Unsubscribe browser from Execution Studio push")
async def studio_push_unsubscribe(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Remove stored push subscription for the current dashboard user."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    user_id = _subject_uuid(sess)
    user = await db.get(DashboardUser, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard user not found.")

    tenant.operator_settings = clear_push_subscription(tenant.operator_settings, user_id=user_id)
    await mark_user_push_enabled(db, user=user, enabled=False)
    await db.commit()
    return {"ok": True, "enabled": False}


@router.get("/guides/{slug}", summary="Per-connection setup guide")
async def studio_connection_guide(
    slug: str,
    _: DashboardSession,
    __: bool = Depends(require_tenant_permission("connectors:read")),
) -> dict[str, Any]:
    """Return in-app manual steps for a connector slug."""

    _assert_enabled()
    from app.infrastructure.connectors.phase3.catalog import iter_phase3_templates

    cleaned = slug.strip().lower()
    template_id: str | None = None
    for template in iter_phase3_templates():
        if template.slug == cleaned:
            template_id = template.template_id
            break
    return connection_setup_guide(template_id=template_id, slug=cleaned)


@router.post("/execute", summary="Governed tool execution (draft / simulate / live)")
async def studio_execute(
    body: StudioExecuteBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Execute or preview a manifest tool under Execution Studio policy."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    user_id = _subject_uuid(sess)
    result = await execute_studio_tool(
        db,
        dashboard_user_id=user_id,
        tenant=tenant,
        connector_slug=body.connector_slug,
        tool_name=body.tool_name,
        arguments=body.arguments,
        mode=body.mode,
        manager_slug=body.manager_slug,
        operator_confirmed=body.operator_confirmed,
    )
    await db.commit()
    return result


@router.post("/browser/step", summary="Governed browser harness fallback step")
async def studio_browser_step(
    body: StudioBrowserStepBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Run draft/simulate/live browser harness when connectors are unavailable."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    user_id = _subject_uuid(sess)
    result = await execute_browser_fallback_step(
        db,
        tenant=tenant,
        dashboard_user_id=user_id,
        goal=body.goal,
        start_url=body.start_url,
        mode=body.mode,
        operator_confirmed=body.operator_confirmed,
    )
    await db.commit()
    return result


@router.patch("/codebase/routine", summary="Enable or pause Queen Maintainer routine")
async def studio_codebase_routine(
    body: StudioCodebaseRoutineBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Toggle weekly Queen Maintainer supervisor routine."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    subject = f"dashboard:{_subject_uuid(sess)}"
    result = await set_codebase_routine_enabled(
        db,
        tenant=tenant,
        created_by_subject=subject,
        enabled=body.enabled,
    )
    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(result.get("error") or "maintainer_unavailable"),
        )
    await db.commit()
    return result


@router.post("/codebase/maintainer-run", summary="Trigger Queen Maintainer supervisor session")
async def studio_codebase_maintainer_run(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Run SCV (Queen Maintainer) swarm now — PR-only, LLM-assisted, denylist enforced."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    subject = f"dashboard:{_subject_uuid(sess)}"
    result = await trigger_codebase_maintainer_run(
        db,
        tenant=tenant,
        created_by_subject=subject,
    )
    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(result.get("error") or "maintainer_unavailable"),
        )
    await db.commit()
    return result


@router.post("/codebase/pr-draft", summary="Governed codebase PR draft (PR-only)")
async def studio_codebase_pr_draft(
    body: StudioCodebasePrDraftBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Validate denylist and create or preview a GitHub PR for codebase changes."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    result = await submit_codebase_pr_draft(
        db,
        tenant=tenant,
        title=body.title,
        body=body.body,
        slug=body.slug,
        changed_paths=body.changed_paths,
        mode=body.mode,
        operator_confirmed=body.operator_confirmed,
    )
    await db.commit()
    return result


@router.get("/manual", summary="Execution Studio operator + agent manual (full)")
async def studio_manual_full(
    __: bool = Depends(require_tenant_permission("connectors:read")),
) -> dict[str, Any]:
    """Return full manual — consumed by UI and agent skills."""

    _assert_enabled()
    return build_execution_studio_manual()


@router.get("/manual/{section_id}", summary="Single manual section")
async def studio_manual_section(
    section_id: str,
    __: bool = Depends(require_tenant_permission("connectors:read")),
) -> dict[str, Any]:
    """Return one manual section by id."""

    _assert_enabled()
    return build_execution_studio_manual(section_id=section_id)


@router.get("/proposals", summary="Pending codebase execution proposals")
async def studio_pending_proposals(
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:read")),
) -> dict[str, Any]:
    """List pending research → codebase handoff proposals."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    rows = await list_pending_codebase_proposals(db, tenant_id=tenant.id, limit=24)
    return {
        "items": [
            {
                "id": str(row.id),
                "title": row.title,
                "description": row.description,
                "proposed_by_role": row.proposed_by_role,
                "risk_level": row.risk_level,
                "proposal_payload": dict(row.proposal_payload or {}),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
    }


@router.post("/proposals", summary="Create codebase execution proposal")
async def studio_create_proposal(
    body: StudioCodebaseProposalBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Submit a codebase change proposal for operator approval."""

    _assert_enabled()
    tenant = await _tenant_from_session(sess, db)
    row = await create_codebase_execution_proposal(
        db,
        tenant_id=tenant.id,
        supervisor_session_id=None,
        sub_agent_session_id=None,
        proposed_by_role=body.proposed_by_role,
        title=body.title,
        description=body.description,
        goal_excerpt=body.goal_excerpt,
        suggested_paths=body.suggested_paths,
        source="execution_studio",
    )
    await db.commit()
    return {"id": str(row.id), "status": row.status, "proposal_type": row.proposal_type}


@router.post("/proposals/{proposal_id}/review", summary="Approve proposal and trigger Maintainer handoff")
async def studio_review_proposal(
    proposal_id: uuid.UUID,
    body: StudioProposalReviewBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Approve or reject codebase proposal; approve queues Queen Maintainer."""

    _assert_enabled()
    from app.application.services.execution_studio_handoff import CODEBASE_PROPOSAL_TYPE
    from app.application.services.supervisor.initiative import review_agent_suggestion_with_handoff
    from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion

    tenant = await _tenant_from_session(sess, db)
    row = await db.get(AgentSuggestion, proposal_id)
    if row is None or row.tenant_id != tenant.id or row.proposal_type != CODEBASE_PROPOSAL_TYPE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found.")

    reviewed, handoff = await review_agent_suggestion_with_handoff(
        db,
        suggestion=row,
        decision="approved" if body.decision == "approve" else "rejected",
        reviewer_subject=f"dashboard:{_subject_uuid(sess)}",
        supervisor_session=None,
        tenant=tenant,
    )
    await db.commit()
    return {
        "id": str(reviewed.id),
        "status": reviewed.status,
        "handoff": handoff,
    }


@router.post("/proposals/bulk-review", summary="Bulk approve/reject codebase execution proposals")
async def studio_bulk_review_proposals(
    body: StudioBulkProposalReviewBody,
    sess: DashboardSession,
    db: DbSession,
    _: bool = Depends(require_tenant_permission("connectors:edit")),
) -> dict[str, Any]:
    """Bulk governance for SCV codebase lane — rejects duplicate auto-initiative spam."""

    _assert_enabled()
    from app.application.services.execution_studio_handoff import CODEBASE_PROPOSAL_TYPE
    from app.application.services.supervisor.initiative import bulk_review_agent_suggestions

    tenant = await _tenant_from_session(sess, db)
    pending = await list_pending_codebase_proposals(db, tenant_id=tenant.id, limit=body.limit)
    if not pending:
        return {"processed": 0, "skipped": 0, "errors": []}

    suggestion_ids = [row.id for row in pending]
    result = await bulk_review_agent_suggestions(
        db,
        tenant_id=tenant.id,
        decision="approved" if body.decision == "approve" else "rejected",
        reviewer_subject=f"dashboard:{_subject_uuid(sess)}",
        suggestion_ids=suggestion_ids,
        include_high_risk=True,
        limit=body.limit,
    )
    await db.commit()
    return {
        **result,
        "proposal_type": CODEBASE_PROPOSAL_TYPE,
    }
