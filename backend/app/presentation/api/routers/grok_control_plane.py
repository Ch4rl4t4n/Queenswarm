"""Grok Control Plane API routes (plan, approvals, execution, status)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.grok_control_plane import (
    GrokRunCreateIn,
    GrokRunDecisionIn,
    GrokRunApprovalOut,
    GrokRunArtifactOut,
    GrokIntakeAdviceIn,
    GrokPushArtifactToHiveMindIn,
    GrokHiveMindReviewDecisionIn,
    GrokRunStartIn,
    GrokTemplateCreateIn,
    GrokTemplateUpdateIn,
    approve_grok_run,
    build_grok_intake_advice,
    cancel_grok_run,
    compose_grok_control_plane_snapshot,
    create_grok_template,
    create_grok_run,
    delete_grok_template,
    get_grok_run,
    list_grok_templates,
    list_grok_run_approvals,
    list_grok_run_artifacts,
    list_grok_runs,
    queue_grok_run_execution,
    reject_grok_run,
    rerun_grok_run,
    push_grok_artifact_to_hivemind,
    list_grok_hivemind_review_queue,
    review_grok_hivemind_item,
    update_grok_template,
)
from app.core.config import settings
from app.presentation.api.deps import require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/operator/grok", tags=["Grok Control Plane"])


class GrokRunRerunIn(BaseModel):
    """Clone run payload with optional objective override."""

    model_config = ConfigDict(extra="forbid")

    objective_override: str | None = Field(default=None, min_length=8, max_length=4000)


def _require_enabled() -> None:
    if not settings.grok_control_plane_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grok Control Plane disabled.",
        )


def _require_owner_or_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin tenant role required.")


def _principal_ids(principal: dict[str, Any]) -> tuple[Any, Any]:
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    return tenant_id, user.id


def _actor(principal: dict[str, Any]) -> str:
    user = principal.get("user")
    email = getattr(user, "email", None) if user is not None else None
    return str(email or "operator")


@router.get("/snapshot", summary="Grok Control Plane module snapshot")
async def grok_snapshot(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_enabled()
    tenant_id, _ = _principal_ids(principal)
    snap = await compose_grok_control_plane_snapshot(tenant_id=tenant_id)
    return snap.model_dump(mode="json")


@router.get("/runs", summary="List Grok runs")
async def grok_list_runs(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = 30,
) -> list[dict[str, Any]]:
    _require_enabled()
    tenant_id, _ = _principal_ids(principal)
    rows = await list_grok_runs(tenant_id=tenant_id, limit=limit)
    return [row.model_dump(mode="json") for row in rows]


@router.get("/templates", summary="List Grok intake templates")
async def grok_list_templates(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = 24,
    offset: int = 0,
    include_archived: bool = False,
    archived_only: bool = False,
    query: str | None = None,
) -> list[dict[str, Any]]:
    _require_enabled()
    tenant_id, _ = _principal_ids(principal)
    rows = await list_grok_templates(
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
        archived_only=archived_only,
        query=query,
    )
    return [row.model_dump(mode="json") for row in rows]


@router.post("/templates", summary="Create Grok intake template")
async def grok_create_template(
    body: GrokTemplateCreateIn,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_enabled()
    _require_owner_or_admin(principal)
    tenant_id, _ = _principal_ids(principal)
    try:
        row = await create_grok_template(tenant_id=tenant_id, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return row.model_dump(mode="json")


@router.patch("/templates/{template_id}", summary="Patch Grok intake template")
async def grok_patch_template(
    template_id: str,
    body: GrokTemplateUpdateIn,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_enabled()
    _require_owner_or_admin(principal)
    tenant_id, _ = _principal_ids(principal)
    try:
        row = await update_grok_template(tenant_id=tenant_id, template_id=template_id, body=body)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return row.model_dump(mode="json")


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Grok intake template")
async def grok_delete_template(
    template_id: str,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> None:
    _require_enabled()
    _require_owner_or_admin(principal)
    tenant_id, _ = _principal_ids(principal)
    try:
        await delete_grok_template(tenant_id=tenant_id, template_id=template_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/runs", summary="Create Grok run")
async def grok_create_run(
    body: GrokRunCreateIn,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_enabled()
    _require_owner_or_admin(principal)
    tenant_id, user_id = _principal_ids(principal)
    try:
        run = await create_grok_run(tenant_id=tenant_id, dashboard_user_id=user_id, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return run.model_dump(mode="json")


@router.post("/intake-advice", summary="Recommend reuse/new strategy from Hive history")
async def grok_intake_advice(
    body: GrokIntakeAdviceIn,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_enabled()
    tenant_id, _ = _principal_ids(principal)
    advice = await build_grok_intake_advice(tenant_id=tenant_id, body=body)
    return advice.model_dump(mode="json")


@router.get("/runs/{run_id}", summary="Get Grok run detail")
async def grok_get_run(
    run_id: str,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_enabled()
    tenant_id, _ = _principal_ids(principal)
    try:
        run = await get_grok_run(tenant_id=tenant_id, run_id=run_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return run.model_dump(mode="json")


@router.get("/runs/{run_id}/approvals", summary="List approval history for Grok run")
async def grok_run_approvals(
    run_id: str,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = 50,
) -> list[dict[str, Any]]:
    _require_enabled()
    tenant_id, _ = _principal_ids(principal)
    try:
        rows: list[GrokRunApprovalOut] = await list_grok_run_approvals(tenant_id=tenant_id, run_id=run_id, limit=limit)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [row.model_dump(mode="json") for row in rows]


@router.post("/runs/{run_id}/artifacts/{artifact_id}/push-hivemind", summary="Persist artifact to HiveMind knowledge")
async def grok_push_artifact_hivemind(
    run_id: str,
    artifact_id: str,
    body: GrokPushArtifactToHiveMindIn,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_enabled()
    _require_owner_or_admin(principal)
    tenant_id, _ = _principal_ids(principal)
    try:
        out = await push_grok_artifact_to_hivemind(
            tenant_id=tenant_id,
            run_id=run_id,
            artifact_id=artifact_id,
            actor=_actor(principal),
            body=body,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return out.model_dump(mode="json")


@router.get("/runs/{run_id}/artifacts", summary="List run artifacts with optional kind filter")
async def grok_run_artifacts(
    run_id: str,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    kind: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    _require_enabled()
    tenant_id, _ = _principal_ids(principal)
    try:
        rows: list[GrokRunArtifactOut] = await list_grok_run_artifacts(
            tenant_id=tenant_id,
            run_id=run_id,
            kind=kind,
            limit=limit,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [row.model_dump(mode="json") for row in rows]


@router.get("/hivemind-review-queue", summary="List low-confidence Grok HiveMind items awaiting review")
async def grok_hivemind_review_queue(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = 30,
) -> dict[str, Any]:
    _require_enabled()
    _require_owner_or_admin(principal)
    tenant_id, _ = _principal_ids(principal)
    out = await list_grok_hivemind_review_queue(tenant_id=tenant_id, limit=limit)
    return out.model_dump(mode="json")


@router.post("/hivemind-review/{knowledge_item_id}", summary="Approve or reject low-confidence HiveMind item")
async def grok_hivemind_review_decision(
    knowledge_item_id: str,
    body: GrokHiveMindReviewDecisionIn,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_enabled()
    _require_owner_or_admin(principal)
    tenant_id, _ = _principal_ids(principal)
    try:
        out = await review_grok_hivemind_item(
            tenant_id=tenant_id,
            knowledge_item_id=knowledge_item_id,
            body=body,
            actor=_actor(principal),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return out.model_dump(mode="json")


@router.post("/runs/{run_id}/approve", summary="Approve Grok run")
async def grok_approve_run(
    run_id: str,
    body: GrokRunDecisionIn,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_enabled()
    _require_owner_or_admin(principal)
    tenant_id, _ = _principal_ids(principal)
    try:
        run = await approve_grok_run(tenant_id=tenant_id, run_id=run_id, approver=_actor(principal), note=body.note)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return run.model_dump(mode="json")


@router.post("/runs/{run_id}/reject", summary="Reject Grok run")
async def grok_reject_run(
    run_id: str,
    body: GrokRunDecisionIn,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_enabled()
    _require_owner_or_admin(principal)
    tenant_id, _ = _principal_ids(principal)
    try:
        run = await reject_grok_run(tenant_id=tenant_id, run_id=run_id, approver=_actor(principal), note=body.note)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return run.model_dump(mode="json")


@router.post("/runs/{run_id}/cancel", summary="Cancel Grok run")
async def grok_cancel_run(
    run_id: str,
    body: GrokRunDecisionIn,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_enabled()
    _require_owner_or_admin(principal)
    tenant_id, _ = _principal_ids(principal)
    try:
        run = await cancel_grok_run(tenant_id=tenant_id, run_id=run_id, actor=_actor(principal), note=body.note)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return run.model_dump(mode="json")


@router.post("/runs/{run_id}/start", summary="Queue approved Grok run to worker")
async def grok_start_run(
    run_id: str,
    body: GrokRunStartIn,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_enabled()
    _require_owner_or_admin(principal)
    tenant_id, _ = _principal_ids(principal)
    try:
        run = await queue_grok_run_execution(tenant_id=tenant_id, run_id=run_id, execute_commands=body.execute_commands)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return run.model_dump(mode="json")


@router.post("/runs/{run_id}/rerun", summary="Clone run into a new run (re-run template)")
async def grok_rerun(
    run_id: str,
    body: GrokRunRerunIn,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_enabled()
    _require_owner_or_admin(principal)
    tenant_id, user_id = _principal_ids(principal)
    try:
        run = await rerun_grok_run(
            tenant_id=tenant_id,
            run_id=run_id,
            dashboard_user_id=user_id,
            objective_override=body.objective_override,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return run.model_dump(mode="json")


__all__ = ["router"]
