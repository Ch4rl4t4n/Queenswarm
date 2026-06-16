"""Analytics Workspace API — Track L DA3/DA11 snapshot + DA4 wizard + DA5 report artifact."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.services.analytics_business_question_wizard_service import (
    BusinessQuestionPreviewIn,
    BusinessQuestionPreviewOut,
    BusinessQuestionSubmitIn,
    BusinessQuestionSubmitOut,
    BusinessQuestionWizardOut,
    compose_business_question_wizard_snapshot,
    preview_business_question_wizard,
    submit_business_question_wizard,
)
from app.application.services.analytics_report_artifact_service import (
    AnalyticsReportArtifactPatchIn,
    AnalyticsReportArtifactOut,
    AnalyticsReportArtifactSnapshotOut,
    compose_analytics_report_artifact_snapshot,
    save_analytics_report_artifact,
)
from app.application.services.analytics_connector_profile_service import (
    AnalyticsConnectorProfileSnapshotOut,
    compose_analytics_connector_profile_snapshot,
)
from app.application.services.analytics_data_lineage_service import (
    AnalyticsDataLineageSnapshotOut,
    compose_analytics_data_lineage_snapshot,
)
from app.application.services.analytics_weekly_routine_service import (
    AnalyticsRoutineKpiOut,
    compose_analytics_routine_kpi,
    ensure_analytics_weekly_routine,
)
from app.application.services.analytics_export_lane_service import (
    AnalyticsExportLaneSnapshotOut,
    AnalyticsExportPreviewIn,
    AnalyticsExportPreviewOut,
    AnalyticsExportSubmitIn,
    AnalyticsExportSubmitOut,
    compose_analytics_export_lane_snapshot,
    preview_analytics_export,
    submit_analytics_export,
)
from app.application.services.analytics_report_critic_service import (
    AnalyticsReportCriticRunIn,
    AnalyticsReportCriticRunOut,
    AnalyticsReportCriticSnapshotOut,
    compose_analytics_report_critic_snapshot,
    run_analytics_report_critic_loop,
)
from app.application.services.analytics_workspace_service import (
    AnalyticsWorkspaceSnapshotOut,
    compose_analytics_workspace_snapshot,
)
from app.core.config import settings
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/analytics-workspace", tags=["Analytics Workspace"])


def _require_enabled() -> None:
    if not settings.analytics_workspace_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analytics workspace disabled.")


def _require_question_wizard() -> None:
    _require_enabled()
    if not settings.analytics_question_wizard_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business Question wizard disabled.")


def _require_report_artifact() -> None:
    _require_enabled()
    if not settings.analytics_report_artifact_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report artifact panel disabled.")


def _require_data_lineage() -> None:
    _require_enabled()
    if not settings.analytics_data_lineage_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data lineage strip disabled.")


def _require_connector_profile() -> None:
    _require_enabled()
    if not settings.analytics_connector_profile_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector profile disabled.")


def _require_export_lane() -> None:
    _require_enabled()
    if not settings.analytics_export_lane_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analytics export lane disabled.")


def _require_weekly_routine() -> None:
    _require_enabled()
    if not settings.analytics_weekly_routine_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analytics weekly routine disabled.")


def _require_report_critic() -> None:
    _require_enabled()
    if not settings.analytics_report_critic_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analytics report critic disabled.")


@router.get("/snapshot", response_model=AnalyticsWorkspaceSnapshotOut, summary="Analytics workspace snapshot")
async def get_analytics_workspace_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AnalyticsWorkspaceSnapshotOut:
    """Single cached read for Apps & Tools analytics module shell."""

    _require_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    user = principal.get("user")
    return await compose_analytics_workspace_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id if user is not None else None,
    )


@router.get("/question-wizard", response_model=BusinessQuestionWizardOut, summary="DA4 Business question wizard snapshot")
async def get_business_question_wizard_snapshot(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> BusinessQuestionWizardOut:
    """Return question wizard capabilities, source options, and date presets."""

    _require_question_wizard()
    return compose_business_question_wizard_snapshot()


@router.post(
    "/question-wizard/preview",
    response_model=BusinessQuestionPreviewOut,
    summary="DA4 Preview analytics brief from business question",
)
async def preview_business_question_wizard_route(
    body: BusinessQuestionPreviewIn,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> BusinessQuestionPreviewOut:
    """Preview markdown brief and session goal before dispatch."""

    _require_question_wizard()
    _ = principal
    try:
        return preview_business_question_wizard(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post(
    "/question-wizard/submit",
    response_model=BusinessQuestionSubmitOut,
    summary="DA4 Submit question → Kanban lineage + analytics session",
)
async def submit_business_question_wizard_route(
    body: BusinessQuestionSubmitIn,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> BusinessQuestionSubmitOut:
    """Create Mission Kanban task, workspace deliverable, and optional supervisor session."""

    _require_question_wizard()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    try:
        return await submit_business_question_wizard(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=user.id,
            created_by_subject=str(principal.get("sub") or "dashboard:analytics-question-wizard"),
            body=body,
        )
    except ValueError as exc:
        err = str(exc)
        if err == "analytics_question_wizard_disabled":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Wizard disabled.") from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=err) from exc


@router.get(
    "/report-artifact",
    response_model=AnalyticsReportArtifactSnapshotOut,
    summary="DA5 Active analytics report artifact snapshot",
)
async def get_analytics_report_artifact_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    task_id: uuid.UUID | None = Query(default=None),
    deliverable_id: uuid.UUID | None = Query(default=None),
) -> AnalyticsReportArtifactSnapshotOut:
    """Return latest session-bound analytics deliverable for operator editing."""

    _require_report_artifact()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    return await compose_analytics_report_artifact_snapshot(
        db,
        dashboard_user_id=user.id,
        task_id=task_id,
        deliverable_id=deliverable_id,
    )


@router.patch(
    "/report-artifact/{deliverable_id}",
    response_model=AnalyticsReportArtifactOut,
    summary="DA5 Save operator edits to analytics report artifact",
)
async def patch_analytics_report_artifact(
    deliverable_id: uuid.UUID,
    body: AnalyticsReportArtifactPatchIn,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AnalyticsReportArtifactOut:
    """Persist markdown + chart blocks as lineage version N+1."""

    _require_report_artifact()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    try:
        return await save_analytics_report_artifact(
            db,
            deliverable_id=deliverable_id,
            dashboard_user_id=user.id,
            body=body,
        )
    except ValueError as exc:
        err = str(exc)
        if err == "analytics_report_artifact_disabled":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Panel disabled.") from exc
        if err == "analytics_artifact_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analytics artifact not found.") from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=err) from exc


@router.get(
    "/connector-profile",
    response_model=AnalyticsConnectorProfileSnapshotOut,
    summary="DA7 Analytics connector profile snapshot",
)
async def get_analytics_connector_profile_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AnalyticsConnectorProfileSnapshotOut:
    """Return GA4 · Sheets · warehouse MCP readiness for analytics fetch lane."""

    _require_connector_profile()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    return await compose_analytics_connector_profile_snapshot(db, dashboard_user_id=user.id)


@router.get(
    "/data-lineage",
    response_model=AnalyticsDataLineageSnapshotOut,
    summary="DA6 Data lineage strip for active analytics report",
)
async def get_analytics_data_lineage_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    task_id: uuid.UUID | None = Query(default=None),
    deliverable_id: uuid.UUID | None = Query(default=None),
) -> AnalyticsDataLineageSnapshotOut:
    """Return connector · query · timestamp rows bound to report sections."""

    _require_data_lineage()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    return await compose_analytics_data_lineage_snapshot(
        db,
        dashboard_user_id=user.id,
        task_id=task_id,
        deliverable_id=deliverable_id,
    )


@router.get(
    "/export-lane",
    response_model=AnalyticsExportLaneSnapshotOut,
    summary="DA8 Analytics export lane snapshot",
)
async def get_analytics_export_lane_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AnalyticsExportLaneSnapshotOut:
    """Return Notion/Slides export capabilities for verified analytics reports."""

    _require_export_lane()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    return await compose_analytics_export_lane_snapshot(db, dashboard_user_id=user.id)


@router.post(
    "/export-lane/preview",
    response_model=AnalyticsExportPreviewOut,
    summary="DA8 Preview Notion/Slides export staging",
)
async def preview_analytics_export_lane(
    body: AnalyticsExportPreviewIn,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AnalyticsExportPreviewOut:
    """Build simulate-first export payload from active analytics artifact."""

    _require_export_lane()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    try:
        return await preview_analytics_export(db, dashboard_user_id=user.id, body=body)
    except ValueError as exc:
        err = str(exc)
        if err == "analytics_export_lane_disabled":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Export lane disabled.") from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=err) from exc


@router.post(
    "/export-lane/submit",
    response_model=AnalyticsExportSubmitOut,
    summary="DA8 Submit Notion/Slides export (simulate-first)",
)
async def submit_analytics_export_lane(
    body: AnalyticsExportSubmitIn,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AnalyticsExportSubmitOut:
    """Stage or live-export analytics report after critic rubric gate."""

    _require_export_lane()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    try:
        return await submit_analytics_export(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=user.id,
            body=body,
        )
    except ValueError as exc:
        err = str(exc)
        if err == "analytics_export_lane_disabled":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Export lane disabled.") from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=err) from exc


@router.get(
    "/routine",
    response_model=AnalyticsRoutineKpiOut,
    summary="DA9 Weekly analytics routine KPI snapshot",
)
async def get_analytics_weekly_routine_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AnalyticsRoutineKpiOut:
    """Return leadership deck routine schedule + latest report KPI for morning brief."""

    _require_weekly_routine()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    return await compose_analytics_routine_kpi(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
    )


@router.post(
    "/routine/bootstrap",
    summary="DA9 Bootstrap weekly analytics supervisor routine",
)
async def bootstrap_analytics_weekly_routine(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, object]:
    """Idempotently register Monday leadership deck routine for tenant."""

    _require_weekly_routine()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    result = await ensure_analytics_weekly_routine(
        db,
        tenant_id=tenant_id,
        created_by_subject=str(principal.get("sub") or "dashboard:analytics-routine"),
    )
    await db.commit()
    return result


@router.get(
    "/report-critic",
    response_model=AnalyticsReportCriticSnapshotOut,
    summary="DA10 Analytics report critic snapshot",
)
async def get_analytics_report_critic_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    task_id: uuid.UUID | None = Query(default=None),
    deliverable_id: uuid.UUID | None = Query(default=None),
) -> AnalyticsReportCriticSnapshotOut:
    """Return LOOP5 critic gate for active analytics report artifact."""

    _require_report_critic()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    return await compose_analytics_report_critic_snapshot(
        db,
        dashboard_user_id=user.id,
        task_id=task_id,
        deliverable_id=deliverable_id,
    )


@router.post(
    "/report-critic/run",
    response_model=AnalyticsReportCriticRunOut,
    summary="DA10 Run analytics report critic closed loop",
)
async def run_analytics_report_critic(
    db: DbSession,
    body: AnalyticsReportCriticRunIn,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AnalyticsReportCriticRunOut:
    """Run LOOP5 preset critic loop and persist rubric score on deliverable."""

    _require_report_critic()
    user = principal.get("user")
    tenant_id = principal.get("tenant_id")
    if user is None or tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard context missing.")
    try:
        result = await run_analytics_report_critic_loop(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=user.id,
            body=body,
        )
        await db.commit()
        return result
    except ValueError as exc:
        err = str(exc)
        if err == "analytics_report_critic_disabled":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Report critic disabled.") from exc
        if err == "analytics_report_critic_preset_unavailable":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Critic preset unavailable.") from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=err) from exc


__all__ = ["router"]
