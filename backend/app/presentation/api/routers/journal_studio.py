"""Journal Studio API — Track O TJ4 settings + review routine bootstrap."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.journal_studio_entry_service import (
    JournalTradeEntryCreateIn,
    JournalTradeEntryImportIn,
    JournalTradeEntryListOut,
    JournalTradeEntryOut,
    JournalTradeEntryPatchIn,
    create_journal_trade_entry,
    import_journal_entry_from_fill,
    list_journal_trade_entries,
    update_journal_trade_entry,
)
from app.application.services.journal_studio_gardener_service import (
    JournalDraftReviewIn,
    JournalDraftReviewOut,
    JournalGardenerSnapshotOut,
    compose_journal_gardener_snapshot,
    review_journal_draft,
    run_journal_studio_gardener_sweep,
)
from app.application.services.journal_studio_pattern_service import (
    JournalPatternStripOut,
    compose_journal_pattern_strip,
)
from app.application.services.journal_studio_pretrade_recall_service import (
    PreTradeRecallOut,
    compose_pretrade_recall,
)
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


@router.get("/entries", summary="TJ2 List journal trade entries")
async def journal_studio_entries_get(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return thesis/outcome/tags/lesson entries for trading journal."""

    _require_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    payload = await list_journal_trade_entries(db, tenant_id=tenant_id)
    return JournalTradeEntryListOut.model_validate(payload).model_dump(mode="json")


@router.post("/entries", summary="TJ2 Create manual journal entry")
async def journal_studio_entries_post(
    body: dict[str, Any],
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Create manual trade journal entry."""

    _require_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    try:
        payload = JournalTradeEntryCreateIn.model_validate(body)
        entry = await create_journal_trade_entry(db, tenant_id=tenant_id, body=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return JournalTradeEntryOut.model_validate(entry).model_dump(mode="json")


@router.patch("/entries/{entry_id}", summary="TJ2 Update journal entry")
async def journal_studio_entries_patch(
    entry_id: str,
    body: dict[str, Any],
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Patch thesis, outcome, tags, or lesson on an entry."""

    _require_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    try:
        patch = JournalTradeEntryPatchIn.model_validate(body)
        entry = await update_journal_trade_entry(db, tenant_id=tenant_id, entry_id=entry_id, patch=patch)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return JournalTradeEntryOut.model_validate(entry).model_dump(mode="json")


@router.post("/entries/import-fill/{fill_id}", summary="TJ2 Import paper fill as journal entry")
async def journal_studio_entries_import_fill(
    fill_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Seed journal entry from verified paper trading fill."""

    _require_enabled()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    try:
        overrides = JournalTradeEntryImportIn.model_validate(body or {})
        entry = await import_journal_entry_from_fill(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=user.id,
            fill_id=fill_id,
            overrides=overrides,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return JournalTradeEntryOut.model_validate(entry).model_dump(mode="json")


def _require_gardener_enabled() -> None:
    _require_enabled()
    if not settings.journal_studio_gardener_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal gardener disabled.")


@router.get("/gardener", summary="TJ3 Journal gardener snapshot")
async def journal_studio_gardener_get(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return pending draft lessons and last overnight sweep metadata."""

    _require_gardener_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    snapshot = await compose_journal_gardener_snapshot(db, tenant_id=tenant_id)
    return JournalGardenerSnapshotOut.model_validate(snapshot).model_dump(mode="json")


@router.post("/gardener/run", summary="TJ3 Run journal gardener sweep")
async def journal_studio_gardener_run(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Manually scan recent paper fills and queue draft lessons."""

    _require_gardener_enabled()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    try:
        result = await run_journal_studio_gardener_sweep(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return result


@router.post("/gardener/drafts/{draft_id}/review", summary="TJ3 Approve or reject journal draft")
async def journal_studio_gardener_draft_review(
    draft_id: str,
    body: dict[str, Any],
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """HITL approve publishes wiki page and updates journal entry lesson."""

    _require_gardener_enabled()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    try:
        review = JournalDraftReviewIn.model_validate(body)
        result = await review_journal_draft(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=user.id,
            draft_id=draft_id,
            body=review,
            reviewed_by=str(principal.get("sub") or "operator"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return JournalDraftReviewOut.model_validate(result).model_dump(mode="json")


@router.get("/pretrade-recall", summary="TJ5 Pre-trade recall snapshot")
async def journal_studio_pretrade_recall_get(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    window_days: int = 30,
) -> dict[str, Any]:
    """Return ranked mistakes, thesis snippet, and injection block before trading."""

    _require_enabled()
    if not settings.journal_studio_pretrade_recall_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pre-trade recall disabled.")
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    recall = await compose_pretrade_recall(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        window_days=window_days,
    )
    return PreTradeRecallOut.model_validate(recall).model_dump(mode="json")


@router.get("/pattern-strip", summary="TJ6 30/90-day pattern strip")
async def journal_studio_pattern_strip_get(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return win rate by tag, repeat-mistake alerts, and edge tags for 30d/90d windows."""

    _require_enabled()
    if not settings.journal_studio_pattern_strip_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pattern strip disabled.")
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    strip = await compose_journal_pattern_strip(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
    )
    return JournalPatternStripOut.model_validate(strip).model_dump(mode="json")


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
