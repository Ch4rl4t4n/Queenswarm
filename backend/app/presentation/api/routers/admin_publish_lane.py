"""Publish lane onboarding — platform admin endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.application.services.publish_operator_onboarding_admin import (
    PublishOnboardingAdminOverviewOut,
    compose_publish_onboarding_admin_overview,
)
from app.presentation.api.deps import DashboardAdmin, DbSession

router = APIRouter(prefix="/admin/publish-lane", tags=["Admin publish lane"])


@router.get(
    "/onboarding-overview",
    response_model=PublishOnboardingAdminOverviewOut,
    summary="Multi-tenant publish onboarding progress",
)
async def publish_onboarding_admin_overview(
    db: DbSession,
    _admin: DashboardAdmin,
    limit: int = Query(default=50, ge=1, le=100),
) -> PublishOnboardingAdminOverviewOut:
    """Return publish lane checklist progress for each tenant (platform admin)."""

    return await compose_publish_onboarding_admin_overview(db, limit=limit)


__all__ = ["router"]
