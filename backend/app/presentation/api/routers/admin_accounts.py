"""Admin CMS API — dashboard accounts, tiers, and tenant profiles."""

from __future__ import annotations

import os
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.admin_accounts import (
    bulk_update_admin_accounts,
    create_admin_account,
    ensure_commercial_demo_account,
    ensure_commercial_demo_preview_membership,
    get_commercial_demo_status,
    list_admin_account_audit_logs,
    list_admin_accounts,
    mint_bootstrap_password,
    reset_admin_account_password,
    serialize_admin_account_audit_csv,
    serialize_admin_account_audit_json,
    update_admin_account,
    update_admin_tenant,
)
from app.core.logging import get_logger
from app.presentation.api.deps import DashboardAdmin, DashboardSession, DbSession
from app.presentation.api.error_payloads import unprocessable_error
from app.presentation.api.routers.dashboard_session import _current_dashboard_user

logger = get_logger(__name__)
router = APIRouter(prefix="/operator/accounts", tags=["Admin Accounts"])


class AdminAccountMembershipView(BaseModel):
    """Tenant membership row for CMS table."""

    tenant_id: str
    tenant_slug: str
    tenant_name: str
    platform_mode: str
    role: str
    tier: str
    subscription_status: str


class AdminAccountRowView(BaseModel):
    """One dashboard operator with tenant context."""

    user_id: str
    email: str
    display_name: str | None = None
    is_admin: bool
    is_active: bool
    totp_enabled: bool
    totp_required: bool
    active_tenant_id: str | None = None
    created_at: str | None = None
    memberships: list[AdminAccountMembershipView] = Field(default_factory=list)


class AdminAccountListResponse(BaseModel):
    """Paginated CMS account list."""

    total: int
    limit: int
    offset: int
    items: list[AdminAccountRowView] = Field(default_factory=list)


class AdminAccountCreateBody(BaseModel):
    """Provision a new dashboard user from CMS."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=256)
    display_name: str | None = Field(default=None, max_length=160)
    is_admin: bool = False
    enable_totp: bool = False
    platform_mode: str | None = Field(default=None, pattern="^(internal|commercial)$")
    tier: str | None = Field(default=None, pattern="^(free|pro|enterprise)$")


class AdminAccountPatchBody(BaseModel):
    """Patch user flags."""

    model_config = ConfigDict(extra="ignore")

    display_name: str | None = Field(default=None, max_length=160)
    is_admin: bool | None = None
    is_active: bool | None = None


class AdminAccountPasswordResetBody(BaseModel):
    """Force password reset."""

    password: str = Field(..., min_length=8, max_length=256)
    disable_totp: bool = True


class AdminTenantPatchBody(BaseModel):
    """Patch tenant platform mode and billing tier."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    tenant_name: str | None = Field(default=None, max_length=256)
    platform_mode: str | None = Field(default=None, pattern="^(internal|commercial)$")
    tier: str | None = Field(default=None, pattern="^(free|pro|enterprise)$")
    subscription_status: str | None = Field(default=None, pattern="^(active|past_due|canceled|trialing)$")


class AdminAccountAuditLogView(BaseModel):
    """One tenant audit row for CMS drawer."""

    id: str
    tenant_id: str
    action: str
    target_type: str
    target_ref: str
    actor_user_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class AdminAccountBulkPatchBody(BaseModel):
    """Bulk CMS patch for selected dashboard users."""

    model_config = ConfigDict(extra="ignore")

    user_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=50)
    is_active: bool | None = None
    platform_mode: str | None = Field(default=None, pattern="^(internal|commercial)$")
    tier: str | None = Field(default=None, pattern="^(free|pro|enterprise)$")


class CommercialDemoBootstrapBody(BaseModel):
    """Optional overrides when ensuring the commercial demo workspace."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=256)
    display_name: str | None = Field(default=None, max_length=160)
    tier: str | None = Field(default="pro", pattern="^(free|pro|enterprise)$")


class CommercialDemoBootstrapResponse(BaseModel):
    """Commercial demo credentials returned once after bootstrap."""

    email: str
    user_id: str
    tenant_id: str
    tenant_slug: str
    tenant_name: str
    platform_mode: str
    tier: str
    password: str


class CommercialDemoStatusView(BaseModel):
    """Commercial demo workspace readiness (no secrets)."""

    ready: bool
    email: str
    user_id: str | None = None
    tenant_id: str | None = None
    tenant_slug: str
    tenant_name: str | None = None
    platform_mode: str | None = None
    tier: str | None = None
    profile_key: str | None = None
    is_active: bool | None = None
    preview_access: bool = False
    last_bootstrapped_at: str | None = None


class CommercialDemoPreviewGrantResponse(BaseModel):
    """Result of granting the caller preview membership."""

    tenant_id: str
    tenant_slug: str
    preview_access: bool
    granted: bool


@router.get("", summary="List dashboard accounts for admin CMS")
async def list_accounts(
    _: DashboardAdmin,
    db: DbSession,
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminAccountListResponse:
    """Return paginated operators with tenant memberships."""

    rows, total = await list_admin_accounts(db, query=q, limit=limit, offset=offset)
    return AdminAccountListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[AdminAccountRowView.model_validate(row) for row in rows],
    )


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create dashboard account")
async def create_account(
    body: AdminAccountCreateBody,
    sess: DashboardSession,
    _: DashboardAdmin,
    db: DbSession,
) -> AdminAccountRowView:
    """Provision operator + personal tenant."""

    actor = await _current_dashboard_user(sess, db)
    try:
        user = await create_admin_account(
            db,
            email=str(body.email),
            password=body.password,
            display_name=body.display_name,
            is_admin=body.is_admin,
            enable_totp=body.enable_totp,
            platform_mode=body.platform_mode,
            tier=body.tier,
            actor_user_id=actor.id,
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from exc

    rows, _ = await list_admin_accounts(db, query=user.email, limit=1, offset=0)
    if not rows:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Account created but reload failed.")
    return AdminAccountRowView.model_validate(rows[0])


@router.post("/bulk", summary="Bulk update selected dashboard accounts")
async def bulk_patch_accounts(
    body: AdminAccountBulkPatchBody,
    sess: DashboardSession,
    _: DashboardAdmin,
    db: DbSession,
) -> dict[str, int]:
    """Activate/deactivate users or align primary tenant mode/tier for many accounts."""

    if body.is_active is None and body.platform_mode is None and body.tier is None:
        raise unprocessable_error(code="admin_accounts_patch_empty", message="No patch fields provided.")

    actor = await _current_dashboard_user(sess, db)
    try:
        result = await bulk_update_admin_accounts(
            db,
            user_ids=body.user_ids,
            is_active=body.is_active,
            platform_mode=body.platform_mode,
            tier=body.tier,
            actor_user_id=actor.id,
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise unprocessable_error(code="admin_accounts_bulk_invalid", message=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from exc

    logger.info(
        "admin_accounts.bulk_patch",
        agent_id=str(actor.id),
        swarm_id="",
        task_id="",
        updated_users=result["updated_users"],
        updated_tenants=result["updated_tenants"],
    )
    return result


@router.get(
    "/commercial-demo/status",
    summary="Commercial demo workspace readiness",
    response_model=CommercialDemoStatusView,
)
async def commercial_demo_status(
    sess: DashboardSession,
    _: DashboardAdmin,
    db: DbSession,
) -> CommercialDemoStatusView:
    """Return demo tenant/user status without exposing credentials."""

    actor = await _current_dashboard_user(sess, db)
    payload = await get_commercial_demo_status(db, admin_user_id=actor.id)
    return CommercialDemoStatusView.model_validate(payload)


@router.post(
    "/commercial-demo/grant-preview-access",
    summary="Grant caller viewer access to commercial demo tenant",
    response_model=CommercialDemoPreviewGrantResponse,
)
async def grant_commercial_demo_preview_access(
    sess: DashboardSession,
    _: DashboardAdmin,
    db: DbSession,
) -> CommercialDemoPreviewGrantResponse:
    """Allow an internal admin to switch into the demo tenant via sidebar."""

    actor = await _current_dashboard_user(sess, db)
    status_payload = await get_commercial_demo_status(db, admin_user_id=actor.id)
    if not status_payload.get("ready"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commercial demo workspace is not bootstrapped yet.",
        )

    tenant_id = uuid.UUID(str(status_payload["tenant_id"]))
    try:
        granted = await ensure_commercial_demo_preview_membership(
            db,
            admin_user_id=actor.id,
            tenant_id=tenant_id,
        )
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from exc

    logger.info(
        "admin_accounts.commercial_demo_preview_granted",
        agent_id=str(actor.id),
        swarm_id="",
        task_id="",
        tenant_id=str(tenant_id),
        granted=granted,
    )
    return CommercialDemoPreviewGrantResponse(
        tenant_id=str(tenant_id),
        tenant_slug=str(status_payload["tenant_slug"]),
        preview_access=True,
        granted=granted,
    )


@router.post(
    "/bootstrap-commercial-demo",
    summary="Ensure commercial demo tenant + user exist",
    response_model=CommercialDemoBootstrapResponse,
)
async def bootstrap_commercial_demo_account(
    body: CommercialDemoBootstrapBody,
    sess: DashboardSession,
    _: DashboardAdmin,
    db: DbSession,
) -> CommercialDemoBootstrapResponse:
    """Idempotently create or refresh demo@queenswarm.love commercial workspace."""

    actor = await _current_dashboard_user(sess, db)
    try:
        password = mint_bootstrap_password(
            env_password=(body.password or os.environ.get("QS_BOOTSTRAP_PASSWORD", "")).strip(),
        )
    except ValueError as exc:
        raise unprocessable_error(code="commercial_demo_password_invalid", message=str(exc)) from exc

    demo_kwargs: dict[str, Any] = {
        "password": password,
        "tier": body.tier or "pro",
        "actor_user_id": actor.id,
    }
    if body.email is not None:
        demo_kwargs["email"] = str(body.email)
    if body.display_name is not None:
        demo_kwargs["display_name"] = body.display_name

    try:
        payload = await ensure_commercial_demo_account(db, **demo_kwargs)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise unprocessable_error(code="commercial_demo_bootstrap_invalid", message=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from exc

    logger.info(
        "admin_accounts.commercial_demo_bootstrapped",
        agent_id=str(actor.id),
        swarm_id="",
        task_id="",
        tenant_id=payload["tenant_id"],
        user_id=payload["user_id"],
    )
    return CommercialDemoBootstrapResponse.model_validate(payload)


@router.patch("/{user_id}", summary="Update dashboard account flags")
async def patch_account(
    user_id: uuid.UUID,
    body: AdminAccountPatchBody,
    sess: DashboardSession,
    _: DashboardAdmin,
    db: DbSession,
) -> AdminAccountRowView:
    """Activate/deactivate, grant admin, rename."""

    actor = await _current_dashboard_user(sess, db)
    try:
        user = await update_admin_account(
            db,
            user_id=user_id,
            display_name=body.display_name,
            is_admin=body.is_admin,
            is_active=body.is_active,
            actor_user_id=actor.id,
        )
        await db.commit()
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from exc

    rows, _ = await list_admin_accounts(db, query=user.email, limit=1, offset=0)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account missing after update.")
    return AdminAccountRowView.model_validate(rows[0])


@router.post("/{user_id}/reset-password", summary="Force password reset for account")
async def reset_account_password(
    user_id: uuid.UUID,
    body: AdminAccountPasswordResetBody,
    sess: DashboardSession,
    _: DashboardAdmin,
    db: DbSession,
) -> dict[str, str]:
    """Set a new password and optionally strip TOTP requirement."""

    actor = await _current_dashboard_user(sess, db)
    try:
        user = await reset_admin_account_password(
            db,
            user_id=user_id,
            password=body.password,
            disable_totp=body.disable_totp,
            actor_user_id=actor.id,
        )
        await db.commit()
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from exc

    logger.info(
        "admin_accounts.password_reset",
        agent_id=str(actor.id),
        swarm_id="",
        task_id="",
        target_user_id=str(user.id),
    )
    return {"status": "ok", "email": user.email}


@router.patch("/tenants/{tenant_id}", summary="Update tenant platform mode and subscription tier")
async def patch_tenant(
    tenant_id: uuid.UUID,
    body: AdminTenantPatchBody,
    sess: DashboardSession,
    _: DashboardAdmin,
    db: DbSession,
) -> dict[str, Any]:
    """Change commercial/internal mode or billing tier for one tenant."""

    actor = await _current_dashboard_user(sess, db)
    try:
        payload = await update_admin_tenant(
            db,
            tenant_id=tenant_id,
            platform_mode=body.platform_mode,
            tenant_name=body.tenant_name,
            tier=body.tier,
            subscription_status=body.subscription_status,
            actor_user_id=actor.id,
        )
        await db.commit()
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise unprocessable_error(code="admin_tenant_patch_invalid", message=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Persist failure.") from exc

    return payload


@router.get("/{user_id}/audit-logs", summary="Audit trail for one dashboard account")
async def get_account_audit_logs(
    user_id: uuid.UUID,
    _: DashboardAdmin,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AdminAccountAuditLogView]:
    """Return tenant audit rows where the user is actor, target, or tenant member."""

    try:
        rows = await list_admin_account_audit_logs(db, user_id=user_id, limit=limit)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [AdminAccountAuditLogView.model_validate(row) for row in rows]


@router.get("/{user_id}/audit-logs/export", summary="Export audit trail as CSV or JSON file")
async def export_account_audit_logs(
    user_id: uuid.UUID,
    _: DashboardAdmin,
    db: DbSession,
    export_format: Literal["json", "csv"] = Query(default="json", alias="format"),
    limit: int = Query(default=200, ge=1, le=500),
) -> Response:
    """Download audit rows for compliance review."""

    try:
        rows = await list_admin_account_audit_logs(db, user_id=user_id, limit=limit)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if export_format == "csv":
        content = serialize_admin_account_audit_csv(rows)
        media_type = "text/csv; charset=utf-8"
        filename = f"account-audit-{user_id}.csv"
    else:
        content = serialize_admin_account_audit_json(rows)
        media_type = "application/json; charset=utf-8"
        filename = f"account-audit-{user_id}.json"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
