"""Tenant team management routes (RBAC, invites, membership management)."""

from __future__ import annotations

import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select

from app.application.services.rbac import (
    ROLE_OWNER,
    VALID_TENANT_ROLES,
    has_permission,
    normalize_tenant_role,
    permissions_for_role,
)
from app.application.services.tenancy import write_tenant_audit_log
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.infrastructure.persistence.models.tenant import (
    DashboardUserTenantMembership,
    Tenant,
    TenantAuditLog,
    TenantInvite,
)
from app.presentation.api.error_payloads import forbidden_error, unprocessable_error
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role
from app.presentation.api.middleware.rate_limit import peer_ip_for_rate_limit

router = APIRouter(prefix="/settings/team", tags=["Settings Team"])


class TeamMemberView(BaseModel):
    id: str
    user_id: str
    email: str
    role: str
    joined_at: str
    can_manage: bool


class TeamInviteView(BaseModel):
    id: str
    email: str
    role: str
    status: str
    invite_token: str
    created_at: str


class TeamOverviewResponse(BaseModel):
    tenant_id: str
    tenant_role: str
    permissions: list[str]
    members: list[TeamMemberView]
    invites: list[TeamInviteView]


class TenantAuditLogView(BaseModel):
    id: str
    action: str
    target_type: str
    target_ref: str
    actor_user_id: str | None
    payload: dict[str, Any]
    created_at: str


class InviteMemberBody(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    email: EmailStr
    role: str = Field(default="member", min_length=4, max_length=32)


class UpdateMemberRoleBody(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    role: str = Field(..., min_length=4, max_length=32)


def _require_team_manage(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "")
    if not has_permission(role=role, permission="team:manage"):
        raise forbidden_error(
            code="team_management_permission_required",
            message="Team management permission required.",
        )


def _require_team_view(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "")
    if not has_permission(role=role, permission="team:view"):
        raise forbidden_error(
            code="team_visibility_permission_required",
            message="Team visibility permission required.",
        )


@router.get("/audit-logs", response_model=list[TenantAuditLogView], summary="List tenant-sensitive audit entries")
async def get_tenant_audit_logs(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> list[TenantAuditLogView]:
    """Return latest tenant audit rows for owner/admin team management workflows."""

    _require_team_manage(principal)
    tenant_id = principal["tenant_id"]
    rows = list(
        (
            await db.scalars(
                select(TenantAuditLog)
                .where(TenantAuditLog.tenant_id == tenant_id)
                .order_by(TenantAuditLog.created_at.desc())
                .limit(200),
            )
        ).all(),
    )
    return [
        TenantAuditLogView(
            id=str(row.id),
            action=row.action,
            target_type=row.target_type,
            target_ref=row.target_ref,
            actor_user_id=str(row.actor_user_id) if row.actor_user_id else None,
            payload=dict(row.payload or {}),
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]


class AuditDigestSendResponse(BaseModel):
    """Result envelope for manual supervisor audit digest send."""

    sent: bool
    reason: str | None = None
    recipients: list[str] = Field(default_factory=list)
    sent_count: int = 0
    action_count: int = 0
    slack_sent: bool = False
    discord_sent: bool = False
    teams_sent: bool = False


class AuditDigestWebhookTestResponse(BaseModel):
    """Result of pinging configured digest webhook channels."""

    slack: bool = False
    discord: bool = False
    teams: bool = False
    detail: str | None = None


class AuditDigestConfigView(BaseModel):
    """Effective and override values for tenant supervisor audit digest scheduling."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    enabled_override: bool | None = None
    window_hours: int
    window_hours_override: int | None = None
    schedule_hour_utc: int
    schedule_hour_override: int | None = None
    extra_recipients: list[str] = Field(default_factory=list)
    slack_webhook_configured: bool = False
    slack_webhook_preview: str | None = None
    discord_webhook_configured: bool = False
    discord_webhook_preview: str | None = None
    teams_webhook_configured: bool = False
    teams_webhook_preview: str | None = None
    last_sent_at: str | None = None
    global_enabled: bool
    global_window_hours: int
    global_schedule_hour_utc: int


class AuditDigestConfigPatch(BaseModel):
    """Partial update for tenant supervisor audit digest settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    window_hours: int | None = Field(default=None, ge=1, le=168)
    schedule_hour_utc: int | None = Field(default=None, ge=0, le=23)
    extra_recipients: list[str] | None = None
    slack_webhook_url: str | None = None
    clear_slack_webhook: bool = False
    discord_webhook_url: str | None = None
    clear_discord_webhook: bool = False
    teams_webhook_url: str | None = None
    clear_teams_webhook: bool = False


class SessionPlaybookConfigView(BaseModel):
    """Tenant automation for saving supervisor session playbooks on approve."""

    model_config = ConfigDict(extra="forbid")

    auto_save_on_approve: bool
    auto_save_on_approve_override: bool | None = None
    mark_verified_on_auto_save: bool
    mark_verified_on_auto_save_override: bool | None = None
    recipes_enabled: bool


class SessionPlaybookConfigPatch(BaseModel):
    """Partial update for tenant session playbook automation."""

    model_config = ConfigDict(extra="forbid")

    auto_save_on_approve: bool | None = None
    mark_verified_on_auto_save: bool | None = None


@router.get(
    "/session-playbook/config",
    response_model=SessionPlaybookConfigView,
    summary="Get tenant supervisor session playbook automation settings",
)
async def get_session_playbook_config(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> SessionPlaybookConfigView:
    """Return whether approved sessions auto-save into Recipe Library."""

    _require_team_manage(principal)
    from app.application.services.supervisor.session_playbook_config import serialize_session_playbook_config_view

    tenant_id = principal["tenant_id"]
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return SessionPlaybookConfigView(**serialize_session_playbook_config_view(tenant))


@router.patch(
    "/session-playbook/config",
    response_model=SessionPlaybookConfigView,
    summary="Update tenant supervisor session playbook automation settings",
)
async def patch_session_playbook_config(
    body: SessionPlaybookConfigPatch,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> SessionPlaybookConfigView:
    """Persist tenant-level auto-save playbook settings (owner/admin only)."""

    _require_team_manage(principal)
    from app.application.services.supervisor.session_playbook_config import (
        merge_tenant_session_playbook_patch,
        serialize_session_playbook_config_view,
    )

    tenant_id = principal["tenant_id"]
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    tenant.operator_settings = merge_tenant_session_playbook_patch(
        tenant,
        auto_save_on_approve=body.auto_save_on_approve,
        mark_verified_on_auto_save=body.mark_verified_on_auto_save,
    )
    await db.commit()
    await db.refresh(tenant)
    return SessionPlaybookConfigView(**serialize_session_playbook_config_view(tenant))


@router.get(
    "/audit-digest/config",
    response_model=AuditDigestConfigView,
    summary="Get tenant supervisor audit digest schedule and recipients",
)
async def get_supervisor_audit_digest_config(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AuditDigestConfigView:
    """Return effective digest config for the active tenant."""

    _require_team_manage(principal)
    from app.application.services.supervisor.session_audit_digest_config import serialize_audit_digest_config_view

    tenant_id = principal["tenant_id"]
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return AuditDigestConfigView(**serialize_audit_digest_config_view(tenant))


@router.patch(
    "/audit-digest/config",
    response_model=AuditDigestConfigView,
    summary="Update tenant supervisor audit digest schedule and recipients",
)
async def patch_supervisor_audit_digest_config(
    body: AuditDigestConfigPatch,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AuditDigestConfigView:
    """Persist tenant-level digest overrides (owner/admin only)."""

    _require_team_manage(principal)
    from app.application.services.supervisor.session_audit_digest_config import (
        merge_tenant_audit_digest_patch,
        serialize_audit_digest_config_view,
    )
    from app.presentation.api.routers.dashboard_session import discord_webhook_url_ok, teams_webhook_url_ok

    tenant_id = principal["tenant_id"]
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if body.discord_webhook_url and not discord_webhook_url_ok(body.discord_webhook_url.strip()):
        raise unprocessable_error(
            code="discord_webhook_invalid",
            message="Discord webhook must be an https URL under discord.com (or discordapp.com) /api/webhooks/",
        )
    if body.teams_webhook_url and not teams_webhook_url_ok(body.teams_webhook_url.strip()):
        raise unprocessable_error(
            code="teams_webhook_invalid",
            message="Teams webhook must be an https Office 365 or Power Automate incoming webhook URL.",
        )

    tenant.operator_settings = merge_tenant_audit_digest_patch(
        tenant,
        enabled=body.enabled,
        window_hours=body.window_hours,
        schedule_hour_utc=body.schedule_hour_utc,
        extra_recipients=body.extra_recipients,
        slack_webhook_url=body.slack_webhook_url,
        clear_slack_webhook=body.clear_slack_webhook,
        discord_webhook_url=body.discord_webhook_url,
        clear_discord_webhook=body.clear_discord_webhook,
        teams_webhook_url=body.teams_webhook_url,
        clear_teams_webhook=body.clear_teams_webhook,
    )
    await db.commit()
    await db.refresh(tenant)
    return AuditDigestConfigView(**serialize_audit_digest_config_view(tenant))


@router.post(
    "/audit-digest/test-webhooks",
    response_model=AuditDigestWebhookTestResponse,
    summary="Ping configured supervisor digest Slack, Discord, and Teams webhooks",
)
async def test_supervisor_audit_digest_webhooks(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AuditDigestWebhookTestResponse:
    """Send one test message to each configured tenant digest webhook channel."""

    _require_team_manage(principal)
    from app.application.services.supervisor.session_audit_digest_config import get_tenant_audit_digest_config
    from app.core.notifications import notify_discord, notify_slack, notify_teams

    tenant_id = principal["tenant_id"]
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    cfg = get_tenant_audit_digest_config(tenant)
    message = "Queenswarm supervisor digest webhook test — channel is reachable."
    slack_ok = await notify_slack(
        message,
        color="#00FFFF",
        title="Digest webhook test",
        webhook_url=cfg.get("slack_webhook_url"),
    )
    discord_ok = await notify_discord(message, webhook_url=cfg.get("discord_webhook_url"))
    teams_ok = await notify_teams(
        message,
        title="Digest webhook test",
        webhook_url=cfg.get("teams_webhook_url"),
    )
    if not slack_ok and not discord_ok and not teams_ok:
        return AuditDigestWebhookTestResponse(detail="no_webhooks_accepted")
    return AuditDigestWebhookTestResponse(slack=slack_ok, discord=discord_ok, teams=teams_ok)


@router.post(
    "/audit-digest/send",
    response_model=AuditDigestSendResponse,
    summary="Send supervisor session operator audit digest via email, Slack, Discord, and Teams",
)
async def send_supervisor_audit_digest_now(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AuditDigestSendResponse:
    """Trigger one digest delivery for the active tenant (owner/admin only)."""

    _require_team_manage(principal)
    from app.application.services.supervisor.session_audit_digest import send_supervisor_audit_digest_for_tenant

    tenant_id = principal["tenant_id"]
    result = await send_supervisor_audit_digest_for_tenant(
        db,
        tenant_id=tenant_id,
        mark_scheduled_sent=True,
    )
    if result.get("sent"):
        from app.application.services.supervisor.session_audit_digest_rollup import (
            invalidate_supervisor_audit_rollup_cache,
        )

        await invalidate_supervisor_audit_rollup_cache()
    return AuditDigestSendResponse(
        sent=bool(result.get("sent")),
        reason=result.get("reason"),
        recipients=list(result.get("recipients") or []),
        sent_count=int(result.get("sent_count") or 0),
        action_count=int(result.get("action_count") or 0),
        slack_sent=bool(result.get("slack_sent")),
        discord_sent=bool(result.get("discord_sent")),
        teams_sent=bool(result.get("teams_sent")),
    )


@router.get("", response_model=TeamOverviewResponse, summary="List tenant members and invites")
async def get_team_overview(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> TeamOverviewResponse:
    """Return team roster and pending invites for active tenant."""

    tenant_id = principal["tenant_id"]
    _require_team_view(principal)
    role = str(principal.get("tenant_role") or "guest")
    memberships = list(
        (
            await db.scalars(
                select(DashboardUserTenantMembership).where(
                    DashboardUserTenantMembership.tenant_id == tenant_id,
                ),
            )
        ).all(),
    )
    members: list[TeamMemberView] = []
    for membership in memberships:
        user = await db.get(DashboardUser, membership.dashboard_user_id)
        if user is None:
            continue
        members.append(
            TeamMemberView(
                id=str(membership.id),
                user_id=str(user.id),
                email=user.email,
                role=str(membership.role),
                joined_at=membership.joined_at.isoformat(),
                can_manage=has_permission(role=role, permission="team:manage"),
            ),
        )
    invites = list(
        (
            await db.scalars(
                select(TenantInvite).where(
                    TenantInvite.tenant_id == tenant_id,
                    TenantInvite.status == "pending",
                ),
            )
        ).all(),
    )
    invite_rows = [
        TeamInviteView(
            id=str(inv.id),
            email=inv.email,
            role=inv.role,
            status=inv.status,
            invite_token=inv.invite_token,
            created_at=inv.created_at.isoformat(),
        )
        for inv in invites
    ]
    return TeamOverviewResponse(
        tenant_id=str(tenant_id),
        tenant_role=role,
        permissions=sorted(permissions_for_role(role)),
        members=members,
        invites=invite_rows,
    )


@router.post("/invites", response_model=TeamInviteView, status_code=status.HTTP_201_CREATED, summary="Invite member")
async def invite_team_member(
    body: InviteMemberBody,
    db: DbSession,
    request: Request,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> TeamInviteView:
    """Create pending email invite for active tenant."""

    _require_team_manage(principal)
    tenant_id = principal["tenant_id"]
    role = normalize_tenant_role(body.role)
    if role not in VALID_TENANT_ROLES:
        raise unprocessable_error(code="tenant_role_invalid", message="Invalid role.")
    invite = TenantInvite(
        tenant_id=tenant_id,
        email=body.email.strip().lower(),
        role=role,
        invited_by_user_id=principal["user"].id,
        invite_token=secrets.token_urlsafe(24),
        status="pending",
    )
    db.add(invite)
    await db.flush()
    await write_tenant_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal["user"].id,
        action="invite_created",
        target_type="invite",
        target_ref=str(invite.id),
        payload={"email": invite.email, "role": role},
        client_ip=peer_ip_for_rate_limit(request),
    )
    await db.commit()
    return TeamInviteView(
        id=str(invite.id),
        email=invite.email,
        role=invite.role,
        status=invite.status,
        invite_token=invite.invite_token,
        created_at=invite.created_at.isoformat(),
    )


@router.patch("/members/{membership_id}", response_model=TeamMemberView, summary="Update member role")
async def update_team_member_role(
    membership_id: uuid.UUID,
    body: UpdateMemberRoleBody,
    db: DbSession,
    request: Request,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> TeamMemberView:
    """Change role for an existing tenant member."""

    _require_team_manage(principal)
    tenant_id = principal["tenant_id"]
    membership = await db.get(DashboardUserTenantMembership, membership_id)
    if membership is None or membership.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found.")
    new_role = normalize_tenant_role(body.role)
    membership.role = new_role
    await write_tenant_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal["user"].id,
        action="member_role_updated",
        target_type="membership",
        target_ref=str(membership.id),
        payload={"new_role": new_role},
        client_ip=peer_ip_for_rate_limit(request),
    )
    await db.commit()
    user = await db.get(DashboardUser, membership.dashboard_user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member user missing.")
    return TeamMemberView(
        id=str(membership.id),
        user_id=str(user.id),
        email=user.email,
        role=membership.role,
        joined_at=membership.joined_at.isoformat(),
        can_manage=True,
    )


@router.delete(
    "/members/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Remove member",
)
async def remove_team_member(
    membership_id: uuid.UUID,
    db: DbSession,
    request: Request,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> Response:
    """Remove a member from tenant."""

    _require_team_manage(principal)
    tenant_id = principal["tenant_id"]
    membership = await db.get(DashboardUserTenantMembership, membership_id)
    if membership is None or membership.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found.")
    if membership.role == ROLE_OWNER and str(membership.dashboard_user_id) == str(principal["user"].id):
        raise unprocessable_error(code="owner_self_removal_forbidden", message="Owner cannot remove self.")
    await db.delete(membership)
    await write_tenant_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal["user"].id,
        action="member_removed",
        target_type="membership",
        target_ref=str(membership_id),
        payload={},
        client_ip=peer_ip_for_rate_limit(request),
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

