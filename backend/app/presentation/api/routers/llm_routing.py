"""LLM routing mode + Cost Guardian settings (tenant-scoped)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.cost_savings import build_cost_savings_payload
from app.application.services.llm_routing import (
    load_routing_config,
    merge_routing_patch,
    normalize_routing_mode,
    routing_config_from_tenant,
)
from app.application.services.platform_features import resolve_platform_features_for_subscription
from app.application.services.billing import ensure_tenant_subscription
from app.application.services.rbac import has_permission
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/llm-routing", tags=["LLM Routing"])


class LlmRoutingSettingsResponse(BaseModel):
    """Effective routing + Cost Guardian flags."""

    routing_mode: str
    cost_guardian_enabled: bool
    auto_upgrade_on_failure: bool
    feature_enabled: bool
    quality_primary_model: str
    economy_primary_model: str
    local_llm_enabled: bool = False
    llm_airgap: bool = False
    ollama_default_model: str = ""
    configured_local_models: list[str] = Field(default_factory=list)


class LlmRoutingSettingsUpdateBody(BaseModel):
    """Partial routing settings patch."""

    model_config = ConfigDict(extra="forbid")

    routing_mode: str | None = None
    cost_guardian_enabled: bool | None = None
    auto_upgrade_on_failure: bool | None = None


async def _assert_routing_feature(db: DbSession, principal: dict[str, Any]) -> uuid.UUID:
    """Gate Free-First routing behind platform feature + global flag."""

    if not settings.free_first_routing_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Free-First routing is disabled on this deployment.",
        )
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant not found.")
    subscription = await ensure_tenant_subscription(db, tenant_id=tenant_id)
    role = str(principal.get("tenant_role") or "guest")
    features = resolve_platform_features_for_subscription(
        platform_mode=str(tenant.platform_mode or "internal"),
        is_admin=role in {"owner", "admin"},
        subscription=subscription,
    )
    if not features.get("free_first_routing"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Free-First routing requires Pro tier or internal operator mode.",
        )
    return tenant_id


def _ensure_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"} or not has_permission(role=role, permission="settings:view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin tenant role required.")


@router.get("/settings", response_model=LlmRoutingSettingsResponse, summary="LLM routing + Cost Guardian settings")
async def get_llm_routing_settings(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> LlmRoutingSettingsResponse:
    """Return tenant routing mode and Cost Guardian toggles."""

    tenant_id = await _assert_routing_feature(db, principal)
    cfg = await load_routing_config(db, tenant_id=tenant_id)
    from app.application.services.local_inference import (
        compose_local_inference_status,
        configured_local_model_slugs,
    )

    local = await compose_local_inference_status(run_ping=False)
    return LlmRoutingSettingsResponse(
        routing_mode=str(cfg.get("routing_mode", "quality")),
        cost_guardian_enabled=bool(cfg.get("cost_guardian_enabled", True)),
        auto_upgrade_on_failure=bool(cfg.get("auto_upgrade_on_failure", True)),
        feature_enabled=bool(cfg.get("feature_enabled", True)),
        quality_primary_model=settings.workflow_breaker_primary_model,
        economy_primary_model=settings.workflow_breaker_tertiary_model,
        local_llm_enabled=local.enabled,
        llm_airgap=local.llm_airgap,
        ollama_default_model=local.ollama_default_model,
        configured_local_models=configured_local_model_slugs(),
    )


@router.put("/settings", response_model=LlmRoutingSettingsResponse, summary="Update LLM routing settings")
async def update_llm_routing_settings(
    body: LlmRoutingSettingsUpdateBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> LlmRoutingSettingsResponse:
    """Patch routing mode / Cost Guardian flags for the active tenant."""

    _ensure_admin(principal)
    tenant_id = await _assert_routing_feature(db, principal)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

    patch: dict[str, Any] = {}
    if body.routing_mode is not None:
        patch["routing_mode"] = normalize_routing_mode(body.routing_mode)
    if body.cost_guardian_enabled is not None:
        patch["cost_guardian_enabled"] = body.cost_guardian_enabled
    if body.auto_upgrade_on_failure is not None:
        patch["auto_upgrade_on_failure"] = body.auto_upgrade_on_failure

    tenant.operator_settings = merge_routing_patch(tenant.operator_settings, patch)
    await db.commit()
    await db.refresh(tenant)
    cfg = routing_config_from_tenant(tenant)
    from app.application.services.local_inference import compose_local_inference_status, configured_local_model_slugs

    local = await compose_local_inference_status(run_ping=False)
    return LlmRoutingSettingsResponse(
        routing_mode=str(cfg["routing_mode"]),
        cost_guardian_enabled=bool(cfg["cost_guardian_enabled"]),
        auto_upgrade_on_failure=bool(cfg["auto_upgrade_on_failure"]),
        feature_enabled=True,
        quality_primary_model=settings.workflow_breaker_primary_model,
        economy_primary_model=settings.workflow_breaker_tertiary_model,
        local_llm_enabled=local.enabled,
        llm_airgap=local.llm_airgap,
        ollama_default_model=local.ollama_default_model,
        configured_local_models=configured_local_model_slugs(),
    )


@router.get("/cost-savings", summary="Token/cost savings vs quality baseline")
async def get_cost_savings(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    window_days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """Return estimated USD saved by economy/free-first routing."""

    tenant_id = await _assert_routing_feature(db, principal)
    return await build_cost_savings_payload(db, tenant_id=tenant_id, window_days=window_days)


@router.get("/local-inference", summary="Local Ollama/vLLM status (Track M LOC4)")
async def get_local_inference_status(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    ping: bool = Query(default=False, description="Probe Ollama/vLLM endpoints"),
) -> dict[str, Any]:
    """Return deployment local inference config and optional live ping."""

    if not settings.local_llm_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local LLM disabled on deployment.")
    _ensure_admin(principal)
    from app.application.services.local_inference import compose_local_inference_status

    status_out = await compose_local_inference_status(run_ping=ping)
    return status_out.model_dump(mode="json")


@router.post("/local-inference/ping", summary="Ping Ollama/vLLM now")
async def post_local_inference_ping(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Live health check for local inference endpoints."""

    if not settings.local_llm_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local LLM disabled on deployment.")
    _ensure_admin(principal)
    from app.application.services.local_inference import compose_local_inference_status

    status_out = await compose_local_inference_status(run_ping=True)
    return status_out.model_dump(mode="json")


@router.get(
    "/verified-dataset",
    summary="Verified dataset export snapshot (Track M LOC5)",
)
async def get_verified_dataset_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return critic-approved row counts for Alpaca JSONL export."""

    if not settings.local_llm_enabled or not settings.verified_dataset_export_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verified dataset export disabled on deployment.",
        )
    _ensure_admin(principal)
    from app.application.services.verified_dataset_export_service import compose_verified_dataset_snapshot

    uid = uuid.UUID(str(principal["dashboard_user_id"]))
    snap = await compose_verified_dataset_snapshot(db, dashboard_user_id=uid)
    return snap.model_dump(mode="json")


@router.get(
    "/verified-dataset/preview",
    summary="Preview verified dataset rows (Track M LOC5)",
)
async def get_verified_dataset_preview(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    sample_limit: int = Query(default=5, ge=1, le=20),
) -> dict[str, Any]:
    """Return sample Alpaca rows before JSONL download."""

    if not settings.local_llm_enabled or not settings.verified_dataset_export_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verified dataset export disabled on deployment.",
        )
    _ensure_admin(principal)
    from app.application.services.verified_dataset_export_service import compose_verified_dataset_preview

    uid = uuid.UUID(str(principal["dashboard_user_id"]))
    preview = await compose_verified_dataset_preview(
        db,
        dashboard_user_id=uid,
        sample_limit=sample_limit,
    )
    return preview.model_dump(mode="json")


@router.get(
    "/verified-dataset/export",
    summary="Download verified dataset JSONL (Track M LOC5)",
)
async def download_verified_dataset_jsonl(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> Response:
    """Download Alpaca-compatible JSONL from critic-approved harness outputs."""

    if not settings.local_llm_enabled or not settings.verified_dataset_export_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verified dataset export disabled on deployment.",
        )
    _ensure_admin(principal)
    from app.application.services.verified_dataset_export_service import (
        export_filename,
        export_verified_dataset_jsonl_bytes,
    )

    uid = uuid.UUID(str(principal["dashboard_user_id"]))
    blob, row_count = await export_verified_dataset_jsonl_bytes(db, dashboard_user_id=uid)
    if row_count == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No critic-approved rows to export — run closed review loop first.",
        )
    fname = export_filename(dashboard_user_id=uid)
    return Response(
        content=blob,
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "X-Queenswarm-Export-Rows": str(row_count),
        },
    )


__all__ = ["router"]
