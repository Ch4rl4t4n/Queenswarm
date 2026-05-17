"""Tenant team management routes (RBAC, invites, membership management)."""

from __future__ import annotations

import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
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
    TenantAuditLog,
    TenantInvite,
)
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Team management permission required.")


def _require_team_view(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "")
    if not has_permission(role=role, permission="team:view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Team visibility permission required.")


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
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> TeamInviteView:
    """Create pending email invite for active tenant."""

    _require_team_manage(principal)
    tenant_id = principal["tenant_id"]
    role = normalize_tenant_role(body.role)
    if role not in VALID_TENANT_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role.")
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
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> Response:
    """Remove a member from tenant."""

    _require_team_manage(principal)
    tenant_id = principal["tenant_id"]
    membership = await db.get(DashboardUserTenantMembership, membership_id)
    if membership is None or membership.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found.")
    if membership.role == ROLE_OWNER and str(membership.dashboard_user_id) == str(principal["user"].id):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Owner cannot remove self.")
    await db.delete(membership)
    await write_tenant_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal["user"].id,
        action="member_removed",
        target_type="membership",
        target_ref=str(membership_id),
        payload={},
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

