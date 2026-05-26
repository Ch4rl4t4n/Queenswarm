"""Publish lane onboarding — platform admin multi-tenant overview."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.publish_operator_onboarding import compose_publish_onboarding_snapshot
from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership, Tenant


class PublishOnboardingTenantRowOut(BaseModel):
    """One tenant row in admin publish onboarding overview."""

    model_config = ConfigDict(extra="ignore")

    tenant_id: uuid.UUID
    tenant_slug: str
    tenant_name: str
    dashboard_user_id: uuid.UUID | None = None
    progress_pct: int = Field(ge=0, le=100)
    steps_done: int = 0
    steps_total: int = 0
    flags: dict[str, bool] = Field(default_factory=dict)


class PublishOnboardingAdminOverviewOut(BaseModel):
    """Admin snapshot — publish lane progress across tenants."""

    model_config = ConfigDict(extra="ignore")

    generated_at: datetime
    tenant_count: int = 0
    average_progress_pct: int = Field(ge=0, le=100, default=0)
    tenants: list[PublishOnboardingTenantRowOut] = Field(default_factory=list)


async def _resolve_owner_user_id(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> uuid.UUID | None:
    """Pick earliest owner/admin membership for tenant onboarding context."""

    membership = await session.scalar(
        select(DashboardUserTenantMembership)
        .where(
            DashboardUserTenantMembership.tenant_id == tenant_id,
            DashboardUserTenantMembership.role.in_(("owner", "admin")),
        )
        .order_by(DashboardUserTenantMembership.created_at.asc())
        .limit(1),
    )
    return membership.dashboard_user_id if membership is not None else None


async def compose_publish_onboarding_admin_overview(
    session: AsyncSession,
    *,
    limit: int = 50,
) -> PublishOnboardingAdminOverviewOut:
    """Build multi-tenant publish onboarding progress for platform admins."""

    cap = max(1, min(limit, 100))
    tenant_rows = list(
        (await session.scalars(select(Tenant).order_by(Tenant.created_at.desc()).limit(cap))).all(),
    )

    overview_rows: list[PublishOnboardingTenantRowOut] = []
    progress_values: list[int] = []

    for tenant in tenant_rows:
        owner_id = await _resolve_owner_user_id(session, tenant_id=tenant.id)
        if owner_id is None:
            overview_rows.append(
                PublishOnboardingTenantRowOut(
                    tenant_id=tenant.id,
                    tenant_slug=str(tenant.slug or ""),
                    tenant_name=str(tenant.name or tenant.slug or "Tenant"),
                    dashboard_user_id=None,
                    progress_pct=0,
                    steps_done=0,
                    steps_total=11,
                ),
            )
            progress_values.append(0)
            continue

        snapshot = await compose_publish_onboarding_snapshot(
            session,
            tenant_id=tenant.id,
            dashboard_user_id=owner_id,
            tenant=tenant,
        )
        steps_done = sum(1 for step in snapshot.steps if step.status == "done")
        overview_rows.append(
            PublishOnboardingTenantRowOut(
                tenant_id=tenant.id,
                tenant_slug=str(tenant.slug or ""),
                tenant_name=str(tenant.name or tenant.slug or "Tenant"),
                dashboard_user_id=owner_id,
                progress_pct=snapshot.progress_pct,
                steps_done=steps_done,
                steps_total=len(snapshot.steps),
                flags=dict(snapshot.flags),
            ),
        )
        progress_values.append(snapshot.progress_pct)

    average = int(round(sum(progress_values) / max(len(progress_values), 1))) if progress_values else 0

    return PublishOnboardingAdminOverviewOut(
        generated_at=datetime.now(tz=UTC),
        tenant_count=len(overview_rows),
        average_progress_pct=average,
        tenants=overview_rows,
    )


__all__ = [
    "PublishOnboardingAdminOverviewOut",
    "PublishOnboardingTenantRowOut",
    "compose_publish_onboarding_admin_overview",
]
