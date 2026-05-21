"""Tenant bootstrap + membership helpers for dashboard operators."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.platform_features import normalize_platform_mode
from app.core.config import settings
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.infrastructure.persistence.models.tenant import (
    DashboardUserTenantMembership,
    Tenant,
    TenantAuditLog,
)


def _slugify(raw: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", raw.strip().lower()).strip("-")
    return slug[:80] or "tenant"


async def ensure_default_tenant_for_user(db: AsyncSession, *, user: DashboardUser) -> Tenant:
    """Ensure a backward-compatible personal tenant exists and is active."""

    memberships = list(
        (
            await db.scalars(
                select(DashboardUserTenantMembership).where(
                    DashboardUserTenantMembership.dashboard_user_id == user.id,
                ),
            )
        ).all(),
    )
    if memberships:
        tenant = await db.get(Tenant, memberships[0].tenant_id)
        if tenant is not None:
            if user.active_tenant_id is None:
                user.active_tenant_id = tenant.id
                await db.flush()
            return tenant

    base_slug = _slugify((user.display_name or user.email or "personal").split("@")[0])
    default_mode = "internal" if user.is_admin else settings.default_tenant_platform_mode
    tenant = Tenant(
        slug=f"{base_slug}-{str(user.id)[:8]}",
        name=(user.display_name or user.email or "Personal Workspace").strip()[:120],
        status="active",
        platform_mode=normalize_platform_mode(default_mode),
    )
    db.add(tenant)
    await db.flush()
    membership = DashboardUserTenantMembership(
        dashboard_user_id=user.id,
        tenant_id=tenant.id,
        role="owner",
        joined_at=datetime.now(tz=UTC),
    )
    db.add(membership)
    user.active_tenant_id = tenant.id
    await db.flush()
    return tenant


async def list_user_tenants(db: AsyncSession, *, user: DashboardUser) -> list[dict[str, Any]]:
    """List all tenant memberships for one user."""

    rows = list(
        (
            await db.scalars(
                select(DashboardUserTenantMembership).where(
                    DashboardUserTenantMembership.dashboard_user_id == user.id,
                ),
            )
        ).all(),
    )
    out: list[dict[str, Any]] = []
    for membership in rows:
        tenant = await db.get(Tenant, membership.tenant_id)
        if tenant is None:
            continue
        out.append(
            {
                "id": str(tenant.id),
                "slug": tenant.slug,
                "name": tenant.name,
                "role": membership.role,
                "is_active": user.active_tenant_id == tenant.id,
                "platform_mode": normalize_platform_mode(getattr(tenant, "platform_mode", "internal")),
            },
        )
    return out


async def switch_active_tenant(
    db: AsyncSession,
    *,
    user: DashboardUser,
    tenant_id: str,
) -> Tenant | None:
    """Switch user's active tenant when membership exists."""

    memberships = list(
        (
            await db.scalars(
                select(DashboardUserTenantMembership).where(
                    DashboardUserTenantMembership.dashboard_user_id == user.id,
                ),
            )
        ).all(),
    )
    target = next((m for m in memberships if str(m.tenant_id) == tenant_id.strip()), None)
    if target is None:
        return None
    tenant = await db.get(Tenant, target.tenant_id)
    if tenant is None:
        return None
    user.active_tenant_id = tenant.id
    await db.flush()
    return tenant


async def get_active_membership(
    db: AsyncSession,
    *,
    user: DashboardUser,
) -> DashboardUserTenantMembership | None:
    """Resolve membership for user's active tenant."""

    if user.active_tenant_id is None:
        await ensure_default_tenant_for_user(db, user=user)
    if user.active_tenant_id is None:
        return None
    stmt = select(DashboardUserTenantMembership).where(
        DashboardUserTenantMembership.dashboard_user_id == user.id,
        DashboardUserTenantMembership.tenant_id == user.active_tenant_id,
    )
    return await db.scalar(stmt)


def enrich_audit_payload(
    payload: dict[str, object] | None,
    *,
    client_ip: str | None = None,
) -> dict[str, object]:
    """Merge client IP into audit JSONB when absent."""

    merged = dict(payload or {})
    if client_ip and not merged.get("ip"):
        merged["ip"] = client_ip
    return merged


async def write_tenant_audit_log(
    db: AsyncSession,
    *,
    tenant_id: str | uuid.UUID,
    actor_user_id: str | uuid.UUID | None,
    action: str,
    target_type: str,
    target_ref: str,
    payload: dict[str, object] | None = None,
    client_ip: str | None = None,
) -> TenantAuditLog:
    """Persist one tenant audit record."""

    row = TenantAuditLog(
        tenant_id=uuid.UUID(str(tenant_id)),
        actor_user_id=uuid.UUID(str(actor_user_id)) if actor_user_id is not None else None,
        action=action.strip().lower(),
        target_type=target_type.strip().lower(),
        target_ref=target_ref.strip()[:255],
        payload=enrich_audit_payload(payload, client_ip=client_ip),
    )
    db.add(row)
    await db.flush()
    return row


__all__ = [
    "ensure_default_tenant_for_user",
    "enrich_audit_payload",
    "get_active_membership",
    "list_user_tenants",
    "switch_active_tenant",
    "write_tenant_audit_log",
]
