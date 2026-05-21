"""Admin CMS helpers for dashboard accounts, tenants, and subscriptions."""

from __future__ import annotations

import csv
import io
import json
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.billing import TIER_ENTERPRISE, TIER_FREE, TIER_PRO, ensure_tenant_subscription
from app.application.services.dashboard_crypto import hash_dashboard_password, mint_totp_secret
from app.application.services.platform_features import normalize_platform_mode, profile_key_for
from app.application.services.tenancy import ensure_default_tenant_for_user, write_tenant_audit_log
from app.infrastructure.persistence.models.billing import TenantSubscription
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership, Tenant, TenantAuditLog

VALID_TIERS = {TIER_FREE, TIER_PRO, TIER_ENTERPRISE}
VALID_PLATFORM_MODES = {"internal", "commercial"}
VALID_SUBSCRIPTION_STATUSES = {"active", "past_due", "canceled", "trialing"}

COMMERCIAL_DEMO_TENANT_SLUG = "commercial-demo"
COMMERCIAL_DEMO_TENANT_NAME = "Commercial Demo Workspace"
COMMERCIAL_DEMO_EMAIL = "demo@queenswarm.love"
COMMERCIAL_DEMO_DISPLAY = "Commercial Demo User"

VALID_TIERS = {TIER_FREE, TIER_PRO, TIER_ENTERPRISE}
VALID_PLATFORM_MODES = {"internal", "commercial"}
VALID_SUBSCRIPTION_STATUSES = {"active", "past_due", "canceled", "trialing"}


async def list_admin_accounts(
    db: AsyncSession,
    *,
    query: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """List dashboard users with tenant memberships and subscription tiers."""

    safe_limit = max(1, min(int(limit), 200))
    safe_offset = max(0, int(offset))
    base = select(DashboardUser)
    count_stmt = select(func.count()).select_from(DashboardUser)
    if query and query.strip():
        needle = f"%{query.strip().lower()}%"
        filt = or_(
            func.lower(DashboardUser.email).like(needle),
            func.lower(func.coalesce(DashboardUser.display_name, "")).like(needle),
        )
        base = base.where(filt)
        count_stmt = count_stmt.where(filt)
    total = int(await db.scalar(count_stmt) or 0)
    users = list(
        (
            await db.scalars(
                base.order_by(DashboardUser.created_at.desc()).limit(safe_limit).offset(safe_offset),
            )
        ).all(),
    )
    if not users:
        return [], total

    user_ids = [user.id for user in users]
    memberships = list(
        (
            await db.scalars(
                select(DashboardUserTenantMembership).where(
                    DashboardUserTenantMembership.dashboard_user_id.in_(user_ids),
                ),
            )
        ).all(),
    )
    tenant_ids = {membership.tenant_id for membership in memberships}
    tenants: dict[uuid.UUID, Tenant] = {}
    subscriptions: dict[uuid.UUID, TenantSubscription] = {}
    if tenant_ids:
        tenant_rows = list((await db.scalars(select(Tenant).where(Tenant.id.in_(tenant_ids)))).all())
        tenants = {row.id: row for row in tenant_rows}
        sub_rows = list(
            (await db.scalars(select(TenantSubscription).where(TenantSubscription.tenant_id.in_(tenant_ids)))).all(),
        )
        subscriptions = {row.tenant_id: row for row in sub_rows}

    grouped: dict[uuid.UUID, list[dict[str, Any]]] = {uid: [] for uid in user_ids}
    for membership in memberships:
        tenant = tenants.get(membership.tenant_id)
        if tenant is None:
            continue
        subscription = subscriptions.get(membership.tenant_id)
        grouped[membership.dashboard_user_id].append(
            {
                "tenant_id": str(tenant.id),
                "tenant_slug": tenant.slug,
                "tenant_name": tenant.name,
                "platform_mode": normalize_platform_mode(getattr(tenant, "platform_mode", "internal")),
                "role": membership.role,
                "tier": str(subscription.tier) if subscription is not None else TIER_FREE,
                "subscription_status": str(subscription.status) if subscription is not None else "active",
            },
        )

    rows: list[dict[str, Any]] = []
    for user in users:
        rows.append(
            {
                "user_id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "is_admin": bool(user.is_admin),
                "is_active": bool(user.is_active),
                "totp_enabled": bool(user.totp_secret is not None and user.totp_verified_at is not None),
                "totp_required": bool(user.totp_required),
                "active_tenant_id": str(user.active_tenant_id) if user.active_tenant_id else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "memberships": grouped.get(user.id, []),
            },
        )
    return rows, total


async def create_admin_account(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str | None,
    is_admin: bool,
    enable_totp: bool,
    platform_mode: str | None,
    tier: str | None,
    actor_user_id: uuid.UUID | None,
) -> DashboardUser:
    """Provision a dashboard user and bootstrap tenant subscription."""

    email_key = email.strip().lower()
    existing = await db.scalar(select(DashboardUser.id).where(DashboardUser.email == email_key))
    if existing is not None:
        msg = "Email already enrolled."
        raise ValueError(msg)

    totp_secret = mint_totp_secret() if enable_totp else None
    user = DashboardUser(
        email=email_key,
        password_hash=hash_dashboard_password(password),
        display_name=display_name,
        totp_secret=totp_secret,
        totp_verified_at=None,
        totp_required=bool(enable_totp and totp_secret),
        is_admin=is_admin,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    tenant = await ensure_default_tenant_for_user(db, user=user)
    if platform_mode:
        tenant.platform_mode = normalize_platform_mode(platform_mode)
    if tier and tier.strip().lower() in VALID_TIERS:
        subscription = await ensure_tenant_subscription(db, tenant_id=tenant.id)
        subscription.tier = tier.strip().lower()
    await write_tenant_audit_log(
        db,
        tenant_id=tenant.id,
        actor_user_id=actor_user_id,
        action="admin_account_created",
        target_type="dashboard_user",
        target_ref=str(user.id),
        payload={"email": user.email, "is_admin": is_admin},
    )
    await db.flush()
    return user


async def update_admin_account(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    display_name: str | None = None,
    is_admin: bool | None = None,
    is_active: bool | None = None,
    actor_user_id: uuid.UUID | None,
) -> DashboardUser:
    """Patch dashboard user flags."""

    user = await db.get(DashboardUser, user_id)
    if user is None:
        msg = "Dashboard user missing."
        raise LookupError(msg)
    if display_name is not None:
        user.display_name = display_name.strip()[:160] or None
    if is_admin is not None:
        user.is_admin = bool(is_admin)
    if is_active is not None:
        user.is_active = bool(is_active)
    if user.active_tenant_id is not None:
        await write_tenant_audit_log(
            db,
            tenant_id=user.active_tenant_id,
            actor_user_id=actor_user_id,
            action="admin_account_updated",
            target_type="dashboard_user",
            target_ref=str(user.id),
            payload={
                "display_name": user.display_name,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
            },
        )
    await db.flush()
    return user


async def reset_admin_account_password(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    password: str,
    disable_totp: bool,
    actor_user_id: uuid.UUID | None,
) -> DashboardUser:
    """Force-reset operator password (CMS)."""

    user = await db.get(DashboardUser, user_id)
    if user is None:
        msg = "Dashboard user missing."
        raise LookupError(msg)
    user.password_hash = hash_dashboard_password(password)
    if disable_totp:
        user.totp_secret = None
        user.totp_verified_at = None
        user.totp_required = False
    if user.active_tenant_id is not None:
        await write_tenant_audit_log(
            db,
            tenant_id=user.active_tenant_id,
            actor_user_id=actor_user_id,
            action="admin_password_reset",
            target_type="dashboard_user",
            target_ref=str(user.id),
            payload={"disable_totp": disable_totp},
        )
    await db.flush()
    return user


async def update_admin_tenant(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    platform_mode: str | None = None,
    tenant_name: str | None = None,
    tier: str | None = None,
    subscription_status: str | None = None,
    actor_user_id: uuid.UUID | None,
) -> dict[str, Any]:
    """Patch tenant platform mode and subscription envelope."""

    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        msg = "Tenant missing."
        raise LookupError(msg)
    if tenant_name is not None:
        tenant.name = tenant_name.strip()[:256] or tenant.name
    if platform_mode is not None:
        mode = platform_mode.strip().lower()
        if mode not in VALID_PLATFORM_MODES:
            msg = f"Invalid platform_mode: {platform_mode}"
            raise ValueError(msg)
        tenant.platform_mode = mode
    subscription = await ensure_tenant_subscription(db, tenant_id=tenant.id)
    if tier is not None:
        tier_key = tier.strip().lower()
        if tier_key not in VALID_TIERS:
            msg = f"Invalid tier: {tier}"
            raise ValueError(msg)
        subscription.tier = tier_key
    if subscription_status is not None:
        status_key = subscription_status.strip().lower()
        if status_key not in VALID_SUBSCRIPTION_STATUSES:
            msg = f"Invalid subscription status: {subscription_status}"
            raise ValueError(msg)
        subscription.status = status_key
    await write_tenant_audit_log(
        db,
        tenant_id=tenant.id,
        actor_user_id=actor_user_id,
        action="admin_tenant_updated",
        target_type="tenant",
        target_ref=str(tenant.id),
        payload={
            "platform_mode": tenant.platform_mode,
            "tier": subscription.tier,
            "status": subscription.status,
            "tenant_name": tenant.name,
        },
    )
    await db.flush()
    return {
        "tenant_id": str(tenant.id),
        "tenant_slug": tenant.slug,
        "tenant_name": tenant.name,
        "platform_mode": normalize_platform_mode(getattr(tenant, "platform_mode", "internal")),
        "tier": str(subscription.tier),
        "subscription_status": str(subscription.status),
    }


async def list_admin_account_audit_logs(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return audit rows tied to one dashboard user (actor, target, or tenant membership)."""

    user = await db.get(DashboardUser, user_id)
    if user is None:
        msg = "Dashboard user missing."
        raise LookupError(msg)

    safe_limit = max(1, min(int(limit), 200))
    memberships = list(
        (
            await db.scalars(
                select(DashboardUserTenantMembership.tenant_id).where(
                    DashboardUserTenantMembership.dashboard_user_id == user_id,
                ),
            )
        ).all(),
    )
    tenant_ids = list(memberships)
    filters = [
        and_(
            TenantAuditLog.target_type == "dashboard_user",
            TenantAuditLog.target_ref == str(user_id),
        ),
        TenantAuditLog.actor_user_id == user_id,
    ]
    if tenant_ids:
        filters.append(TenantAuditLog.tenant_id.in_(tenant_ids))

    rows = list(
        (
            await db.scalars(
                select(TenantAuditLog)
                .where(or_(*filters))
                .order_by(TenantAuditLog.created_at.desc())
                .limit(safe_limit),
            )
        ).all(),
    )
    return [
        {
            "id": str(row.id),
            "tenant_id": str(row.tenant_id),
            "action": row.action,
            "target_type": row.target_type,
            "target_ref": row.target_ref,
            "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
            "payload": dict(row.payload or {}),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def serialize_admin_account_audit_csv(rows: list[dict[str, Any]]) -> str:
    """Render audit rows as CSV with JSON-encoded payload column."""

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "id",
            "tenant_id",
            "action",
            "target_type",
            "target_ref",
            "actor_user_id",
            "created_at",
            "payload",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "id": row.get("id", ""),
                "tenant_id": row.get("tenant_id", ""),
                "action": row.get("action", ""),
                "target_type": row.get("target_type", ""),
                "target_ref": row.get("target_ref", ""),
                "actor_user_id": row.get("actor_user_id") or "",
                "created_at": row.get("created_at") or "",
                "payload": json.dumps(row.get("payload") or {}, ensure_ascii=False),
            },
        )
    return buffer.getvalue()


def serialize_admin_account_audit_json(rows: list[dict[str, Any]]) -> str:
    """Render audit rows as pretty-printed JSON."""

    return json.dumps(rows, ensure_ascii=False, indent=2)


async def bulk_update_admin_accounts(
    db: AsyncSession,
    *,
    user_ids: list[uuid.UUID],
    is_active: bool | None = None,
    platform_mode: str | None = None,
    tier: str | None = None,
    actor_user_id: uuid.UUID | None,
) -> dict[str, int]:
    """Apply the same patch to multiple dashboard users and their primary tenants."""

    unique_ids = list(dict.fromkeys(user_ids))
    updated_users = 0
    updated_tenants = 0

    for user_id in unique_ids:
        user = await db.get(DashboardUser, user_id)
        if user is None:
            continue
        if is_active is not None:
            user.is_active = bool(is_active)
            updated_users += 1
            if user.active_tenant_id is not None:
                await write_tenant_audit_log(
                    db,
                    tenant_id=user.active_tenant_id,
                    actor_user_id=actor_user_id,
                    action="admin_account_bulk_updated",
                    target_type="dashboard_user",
                    target_ref=str(user.id),
                    payload={"is_active": user.is_active},
                )

        if platform_mode is None and tier is None:
            continue

        tenant_id = user.active_tenant_id
        if tenant_id is None:
            membership = await db.scalar(
                select(DashboardUserTenantMembership).where(
                    DashboardUserTenantMembership.dashboard_user_id == user.id,
                ),
            )
            tenant_id = membership.tenant_id if membership is not None else None
        if tenant_id is None:
            continue

        await update_admin_tenant(
            db,
            tenant_id=tenant_id,
            platform_mode=platform_mode,
            tier=tier,
            actor_user_id=actor_user_id,
        )
        updated_tenants += 1

    await db.flush()
    return {"updated_users": updated_users, "updated_tenants": updated_tenants}


async def ensure_commercial_demo_preview_membership(
    db: AsyncSession,
    *,
    admin_user_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> bool:
    """Grant an internal admin viewer access to the commercial demo tenant for sidebar preview."""

    admin = await db.get(DashboardUser, admin_user_id)
    if admin is None or not admin.is_admin:
        return False

    membership = await db.scalar(
        select(DashboardUserTenantMembership).where(
            DashboardUserTenantMembership.dashboard_user_id == admin_user_id,
            DashboardUserTenantMembership.tenant_id == tenant_id,
        ),
    )
    if membership is None:
        db.add(
            DashboardUserTenantMembership(
                dashboard_user_id=admin_user_id,
                tenant_id=tenant_id,
                role="viewer",
                joined_at=datetime.now(tz=UTC),
            ),
        )
        await db.flush()
        return True
    return False


async def get_commercial_demo_status(
    db: AsyncSession,
    *,
    admin_user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Return commercial demo readiness without exposing credentials."""

    tenant = await db.scalar(select(Tenant).where(Tenant.slug == COMMERCIAL_DEMO_TENANT_SLUG))
    user = await db.scalar(select(DashboardUser).where(DashboardUser.email == COMMERCIAL_DEMO_EMAIL))
    if tenant is None or user is None:
        return {
            "ready": False,
            "email": COMMERCIAL_DEMO_EMAIL,
            "tenant_slug": COMMERCIAL_DEMO_TENANT_SLUG,
            "preview_access": False,
        }

    subscription = await ensure_tenant_subscription(db, tenant_id=tenant.id)
    tier = str(subscription.tier)
    platform_mode = normalize_platform_mode(getattr(tenant, "platform_mode", "commercial"))

    last_bootstrapped_at = await db.scalar(
        select(TenantAuditLog.created_at)
        .where(
            TenantAuditLog.tenant_id == tenant.id,
            TenantAuditLog.action == "commercial_demo_bootstrapped",
        )
        .order_by(TenantAuditLog.created_at.desc())
        .limit(1),
    )

    preview_access = False
    if admin_user_id is not None:
        preview_access = (
            await db.scalar(
                select(DashboardUserTenantMembership.id).where(
                    DashboardUserTenantMembership.dashboard_user_id == admin_user_id,
                    DashboardUserTenantMembership.tenant_id == tenant.id,
                ),
            )
        ) is not None

    return {
        "ready": True,
        "email": user.email,
        "user_id": str(user.id),
        "tenant_id": str(tenant.id),
        "tenant_slug": tenant.slug,
        "tenant_name": tenant.name,
        "platform_mode": platform_mode,
        "tier": tier,
        "profile_key": profile_key_for(platform_mode, tier),
        "is_active": bool(user.is_active),
        "preview_access": preview_access,
        "last_bootstrapped_at": last_bootstrapped_at.isoformat() if last_bootstrapped_at else None,
    }


async def ensure_commercial_demo_account(
    db: AsyncSession,
    *,
    email: str = COMMERCIAL_DEMO_EMAIL,
    password: str,
    display_name: str = COMMERCIAL_DEMO_DISPLAY,
    tenant_slug: str = COMMERCIAL_DEMO_TENANT_SLUG,
    tenant_name: str = COMMERCIAL_DEMO_TENANT_NAME,
    tier: str = TIER_PRO,
    actor_user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Create or refresh the commercial demo tenant + non-admin user (idempotent)."""

    email_clean = email.strip().lower()
    tier_key = tier.strip().lower()
    if tier_key not in VALID_TIERS:
        msg = f"Invalid tier: {tier}"
        raise ValueError(msg)

    hashed = hash_dashboard_password(password)
    tenant = await db.scalar(select(Tenant).where(Tenant.slug == tenant_slug))
    if tenant is None:
        tenant = Tenant(
            slug=tenant_slug,
            name=tenant_name,
            status="active",
            platform_mode="commercial",
        )
        db.add(tenant)
        await db.flush()
    else:
        tenant.platform_mode = "commercial"
        tenant.name = tenant_name
        tenant.status = "active"

    user = await db.scalar(select(DashboardUser).where(DashboardUser.email == email_clean))
    if user is None:
        user = DashboardUser(
            email=email_clean,
            password_hash=hashed,
            display_name=display_name,
            totp_secret=None,
            totp_verified_at=None,
            totp_required=False,
            is_admin=False,
            is_active=True,
        )
        db.add(user)
        await db.flush()
    else:
        user.password_hash = hashed
        user.display_name = display_name
        user.is_admin = False
        user.is_active = True
        user.totp_required = False

    membership = await db.scalar(
        select(DashboardUserTenantMembership).where(
            DashboardUserTenantMembership.dashboard_user_id == user.id,
            DashboardUserTenantMembership.tenant_id == tenant.id,
        ),
    )
    if membership is None:
        db.add(
            DashboardUserTenantMembership(
                dashboard_user_id=user.id,
                tenant_id=tenant.id,
                role="owner",
                joined_at=datetime.now(tz=UTC),
            ),
        )
    else:
        membership.role = "owner"

    user.active_tenant_id = tenant.id
    subscription = await ensure_tenant_subscription(db, tenant_id=tenant.id)
    subscription.tier = tier_key
    subscription.status = "active"

    await write_tenant_audit_log(
        db,
        tenant_id=tenant.id,
        actor_user_id=actor_user_id,
        action="commercial_demo_bootstrapped",
        target_type="dashboard_user",
        target_ref=str(user.id),
        payload={"email": user.email, "tier": tier_key, "tenant_slug": tenant.slug},
    )
    if actor_user_id is not None:
        await ensure_commercial_demo_preview_membership(
            db,
            admin_user_id=actor_user_id,
            tenant_id=tenant.id,
        )
    await db.flush()
    return {
        "email": user.email,
        "user_id": str(user.id),
        "tenant_id": str(tenant.id),
        "tenant_slug": tenant.slug,
        "tenant_name": tenant.name,
        "platform_mode": "commercial",
        "tier": tier_key,
        "password": password,
    }


def mint_bootstrap_password(*, env_password: str | None = None) -> str:
    """Resolve bootstrap password from env or generate a one-time secret."""

    cleaned = (env_password or "").strip()
    if cleaned:
        if len(cleaned) < 8:
            msg = "Bootstrap password too short (min 8)."
            raise ValueError(msg)
        return cleaned
    return secrets.token_urlsafe(16)


__all__ = [
    "COMMERCIAL_DEMO_EMAIL",
    "COMMERCIAL_DEMO_TENANT_SLUG",
    "VALID_PLATFORM_MODES",
    "VALID_TIERS",
    "bulk_update_admin_accounts",
    "create_admin_account",
    "ensure_commercial_demo_account",
    "ensure_commercial_demo_preview_membership",
    "get_commercial_demo_status",
    "list_admin_account_audit_logs",
    "list_admin_accounts",
    "mint_bootstrap_password",
    "reset_admin_account_password",
    "serialize_admin_account_audit_csv",
    "serialize_admin_account_audit_json",
    "update_admin_account",
    "update_admin_tenant",
]
