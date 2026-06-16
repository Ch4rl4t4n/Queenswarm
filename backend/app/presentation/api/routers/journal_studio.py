"""Journal Studio API — Track O TJ4 settings + review routine bootstrap."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.journal_studio_settings_service import (
    JournalStudioRoutineKpiOut,
    JournalStudioSettingsOut,
    JournalStudioSettingsPatchIn,
    compose_journal_studio_routine_kpi,
    ensure_journal_review_routine,
    get_journal_studio_settings,
    save_journal_studio_settings,
)
from app.application.services.journal_studio_timeline_service import (
    JournalStudioWorkspaceSnapshotOut,
    JournalTimelineOut,
    compose_journal_studio_workspace_snapshot,
    compose_journal_timeline,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/journal-studio", tags=["Journal Studio"])


def _require_enabled() -> None:
    if not settings.journal_studio_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal studio disabled.")


async def _tenant_from_principal(db: DbSession, principal: dict[str, Any]) -> Tenant | None:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        return None
    return await db.get(Tenant, tenant_id)


@router.get("/snapshot", summary="TJ1 Journal studio workspace snapshot")
async def journal_studio_snapshot_get(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return timeline preview, routine KPI, and panel map."""

    _require_enabled()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await _tenant_from_principal(db, principal)
    snapshot = await compose_journal_studio_workspace_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
    )
    return JournalStudioWorkspaceSnapshotOut.model_validate(snapshot).model_dump(mode="json")


@router.get("/timeline", summary="TJ1 Journal studio timeline")
async def journal_studio_timeline_get(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = 50,
    window_days: int = 90,
) -> dict[str, Any]:
    """Return merged journal timeline (paper fills, live runs, manual entries, reviews)."""

    _require_enabled()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await _tenant_from_principal(db, principal)
    timeline = await compose_journal_timeline(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
        limit=limit,
        window_days=window_days,
    )
    return JournalTimelineOut.model_validate(timeline).model_dump(mode="json")


@router.get("/settings", summary="TJ4 Journal studio settings snapshot")
async def journal_studio_settings_get(
    db: DbSession,
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return field toggles, review cron, Obsidian subfolder, and mistake tags."""

    _require_enabled()
    tenant_id = _principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    snapshot = await get_journal_studio_settings(db, tenant_id=tenant_id)
    return JournalStudioSettingsOut.model_validate(snapshot).model_dump(mode="json")


@router.patch("/settings", summary="TJ4 Update journal studio settings")
async def journal_studio_settings_patch(
    body: dict[str, Any],
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Persist operator journal studio overrides."""

    _require_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    try:
        patch = JournalStudioSettingsPatchIn.model_validate(body)
        saved = await save_journal_studio_settings(db, tenant_id=tenant_id, patch=patch)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    if saved.review_cron_enabled and saved.review_cron_preset != "off":
        await ensure_journal_review_routine(
            db,
            tenant_id=tenant_id,
            created_by_subject=str(principal.get("sub") or "operator"),
        )
    await db.commit()
    return saved.model_dump(mode="json")


@router.get("/routine", summary="TJ4 Journal review routine KPI")
async def journal_studio_routine_get(
    db: DbSession,
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return review cron routine status for trading journal workspace."""

    _require_enabled()
    tenant_id = _principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    kpi = await compose_journal_studio_routine_kpi(db, tenant_id=tenant_id)
    return JournalStudioRoutineKpiOut.model_validate(kpi).model_dump(mode="json")


@router.post("/routine/bootstrap", summary="TJ4 Bootstrap journal review routine")
async def journal_studio_routine_bootstrap(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Register supervisor cron routine from current journal studio settings."""

    _require_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    result = await ensure_journal_review_routine(
        db,
        tenant_id=tenant_id,
        created_by_subject=str(principal.get("sub") or "operator"),
    )
    await db.commit()
    return result
