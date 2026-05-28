"""Single-admin mode invariants and destructive cutover helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.tenancy import ensure_default_tenant_for_user, write_tenant_audit_log
from app.core.config import settings
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership, Tenant


class SingleAdminInvariantError(RuntimeError):
    """Raised when strict single-admin invariants are violated."""


def _quote_identifier(name: str) -> str:
    """Quote an SQL identifier with double quotes safely."""

    return '"' + name.replace('"', '""') + '"'


async def collect_single_admin_snapshot(session: AsyncSession) -> dict[str, Any]:
    """Collect counts/ids required to assert single-admin correctness."""

    total_users = int(await session.scalar(select(func.count()).select_from(DashboardUser)) or 0)
    active_users = int(
        await session.scalar(select(func.count()).select_from(DashboardUser).where(DashboardUser.is_active.is_(True)))
        or 0
    )
    admin_users = int(
        await session.scalar(
            select(func.count()).select_from(DashboardUser).where(
                DashboardUser.is_active.is_(True),
                DashboardUser.is_admin.is_(True),
            ),
        )
        or 0
    )
    total_tenants = int(await session.scalar(select(func.count()).select_from(Tenant)) or 0)
    active_admin = await session.scalar(
        select(DashboardUser).where(
            DashboardUser.is_active.is_(True),
            DashboardUser.is_admin.is_(True),
        ),
    )
    keeper_tenant_id: uuid.UUID | None = None
    keeper_membership_role: str | None = None
    if active_admin is not None:
        tenant = await ensure_default_tenant_for_user(session, user=active_admin)
        keeper_tenant_id = tenant.id
        membership = await session.scalar(
            select(DashboardUserTenantMembership).where(
                DashboardUserTenantMembership.dashboard_user_id == active_admin.id,
                DashboardUserTenantMembership.tenant_id == tenant.id,
            ),
        )
        keeper_membership_role = str(membership.role) if membership is not None else None
    return {
        "total_users": total_users,
        "active_users": active_users,
        "admin_users": admin_users,
        "total_tenants": total_tenants,
        "keeper_user_id": str(active_admin.id) if active_admin is not None else None,
        "keeper_email": str(active_admin.email) if active_admin is not None else None,
        "keeper_tenant_id": str(keeper_tenant_id) if keeper_tenant_id is not None else None,
        "keeper_membership_role": keeper_membership_role,
    }


async def assert_single_admin_invariants(session: AsyncSession) -> dict[str, Any]:
    """Validate strict single-admin deployment invariants."""

    snapshot = await collect_single_admin_snapshot(session)
    problems: list[str] = []
    if snapshot["total_users"] != 1:
        problems.append(f"expected 1 dashboard user, found {snapshot['total_users']}")
    if snapshot["active_users"] != 1:
        problems.append(f"expected 1 active dashboard user, found {snapshot['active_users']}")
    if snapshot["admin_users"] != 1:
        problems.append(f"expected 1 active admin dashboard user, found {snapshot['admin_users']}")
    if snapshot["total_tenants"] != 1:
        problems.append(f"expected 1 tenant, found {snapshot['total_tenants']}")
    if snapshot["keeper_tenant_id"] is None:
        problems.append("active admin tenant context missing")
    if str(snapshot.get("keeper_membership_role") or "").lower() not in {"owner", "admin"}:
        problems.append("active admin tenant membership role must be owner/admin")
    if problems:
        details = "; ".join(problems)
        raise SingleAdminInvariantError(f"SINGLE_ADMIN_MODE invariant failed: {details}")
    return snapshot


async def run_single_admin_hard_cutover(
    session: AsyncSession,
    *,
    admin_email: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Delete all non-primary tenants/users and keep one admin tenant."""

    keeper = await session.scalar(
        select(DashboardUser).where(func.lower(DashboardUser.email) == admin_email.strip().lower()),
    )
    if keeper is None:
        raise SingleAdminInvariantError(f"Admin email not found: {admin_email}")
    keeper.is_active = True
    keeper.is_admin = True
    keeper_tenant = await ensure_default_tenant_for_user(session, user=keeper)
    keeper.active_tenant_id = keeper_tenant.id

    keeper_user_id = str(keeper.id)
    keeper_tenant_id = str(keeper_tenant.id)
    rows_deleted: dict[str, int] = {}
    rows_updated: dict[str, int] = {}

    if dry_run:
        return {
            "mode": "dry_run",
            "keeper_user_id": keeper_user_id,
            "keeper_tenant_id": keeper_tenant_id,
        }

    tenant_tables = (
        await session.execute(
            text(
                """
                select table_name
                from information_schema.columns
                where table_schema='public' and column_name='tenant_id'
                group by table_name
                order by table_name
                """,
            ),
        )
    ).all()
    for (table_name,) in tenant_tables:
        table = str(table_name)
        if table in {"tenants", "dashboard_user_tenants"}:
            continue
        sql = text(f"delete from {_quote_identifier(table)} where tenant_id <> :keeper_tenant_id")
        result = await session.execute(sql, {"keeper_tenant_id": keeper_tenant_id})
        rows_deleted[f"{table}.tenant_id"] = int(result.rowcount or 0)

    user_cols = (
        await session.execute(
            text(
                """
                select table_name, column_name, is_nullable
                from information_schema.columns
                where table_schema='public'
                  and data_type='uuid'
                  and (
                    column_name='dashboard_user_id'
                    or column_name='actor_user_id'
                    or column_name='created_by_user_id'
                    or column_name='updated_by_user_id'
                    or column_name='reviewer_user_id'
                    or column_name='invited_by_user_id'
                  )
                order by table_name, column_name
                """,
            ),
        )
    ).all()
    for table_name, column_name, is_nullable in user_cols:
        table = str(table_name)
        column = str(column_name)
        if table == "dashboard_users":
            continue
        if str(is_nullable).upper() == "YES":
            sql = text(
                f"update {_quote_identifier(table)} "
                f"set {_quote_identifier(column)} = null "
                f"where {_quote_identifier(column)} is not null and {_quote_identifier(column)} <> :keeper_user_id",
            )
            result = await session.execute(sql, {"keeper_user_id": keeper_user_id})
            rows_updated[f"{table}.{column}"] = int(result.rowcount or 0)
        else:
            sql = text(
                f"delete from {_quote_identifier(table)} "
                f"where {_quote_identifier(column)} <> :keeper_user_id",
            )
            result = await session.execute(sql, {"keeper_user_id": keeper_user_id})
            rows_deleted[f"{table}.{column}"] = rows_deleted.get(f"{table}.{column}", 0) + int(result.rowcount or 0)

    membership = await session.scalar(
        select(DashboardUserTenantMembership).where(
            DashboardUserTenantMembership.dashboard_user_id == keeper.id,
            DashboardUserTenantMembership.tenant_id == keeper_tenant.id,
        ),
    )
    if membership is None:
        membership = DashboardUserTenantMembership(
            dashboard_user_id=keeper.id,
            tenant_id=keeper_tenant.id,
            role="owner",
            joined_at=datetime.now(tz=UTC),
        )
        session.add(membership)
    else:
        membership.role = "owner"

    res_memberships = await session.execute(
        text(
            "delete from dashboard_user_tenants "
            "where dashboard_user_id <> :keeper_user_id or tenant_id <> :keeper_tenant_id",
        ),
        {"keeper_user_id": keeper_user_id, "keeper_tenant_id": keeper_tenant_id},
    )
    rows_deleted["dashboard_user_tenants"] = int(res_memberships.rowcount or 0)

    res_users = await session.execute(
        text("delete from dashboard_users where id <> :keeper_user_id"),
        {"keeper_user_id": keeper_user_id},
    )
    rows_deleted["dashboard_users"] = int(res_users.rowcount or 0)

    res_tenants = await session.execute(
        text("delete from tenants where id <> :keeper_tenant_id"),
        {"keeper_tenant_id": keeper_tenant_id},
    )
    rows_deleted["tenants"] = int(res_tenants.rowcount or 0)

    await write_tenant_audit_log(
        session,
        tenant_id=keeper_tenant.id,
        actor_user_id=keeper.id,
        action="single_admin_cutover",
        target_type="deployment",
        target_ref="single_admin_mode",
        payload={"deleted": rows_deleted, "updated": rows_updated},
        client_ip="localhost",
    )

    snapshot = await assert_single_admin_invariants(session)
    return {
        "mode": "apply",
        "keeper_user_id": keeper_user_id,
        "keeper_tenant_id": keeper_tenant_id,
        "rows_deleted": rows_deleted,
        "rows_updated": rows_updated,
        "post_snapshot": snapshot,
    }


__all__ = [
    "SingleAdminInvariantError",
    "assert_single_admin_invariants",
    "collect_single_admin_snapshot",
    "run_single_admin_hard_cutover",
]

