"""Analytics Workspace API — Track L DA3/DA11 snapshot + DA4 question wizard."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

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
    return await compose_analytics_workspace_snapshot(db, tenant_id=tenant_id)


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


__all__ = ["router"]
