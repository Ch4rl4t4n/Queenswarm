"""Enterprise workspace routes — white-label branding and compliance profile."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.billing import TIER_ENTERPRISE, ensure_tenant_subscription, resolve_plan_features
from app.application.services.enterprise_workspace import (
    build_compliance_export_bundle,
    enterprise_workspace_enabled,
    merge_enterprise_workspace_patch,
    serialize_enterprise_workspace_view,
)
from app.common.schemas.enterprise_workspace import (
    ComplianceExportBundle,
    EnterpriseWorkspacePatch,
    EnterpriseWorkspaceView,
)
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role
from app.application.services.rbac import has_permission

router = APIRouter(prefix="/settings/enterprise", tags=["Settings Enterprise"])


def _ensure_enterprise_workspace_enabled() -> None:
    if not enterprise_workspace_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enterprise workspace is disabled.",
        )


def _require_team_manage(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "")
    if not has_permission(role=role, permission="team:manage"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Team management permission required.")


async def _custom_branding_allowed(db: DbSession, tenant: Tenant) -> bool:
    if str(getattr(tenant, "platform_mode", "internal")).strip().lower() == "internal":
        return True
    subscription = await ensure_tenant_subscription(db, tenant_id=tenant.id)
    tier = str(subscription.tier)
    features = resolve_plan_features(tier)
    return bool(features.get("custom_branding")) or tier == TIER_ENTERPRISE


@router.get(
    "/config",
    response_model=EnterpriseWorkspaceView,
    summary="Get white-label and enterprise compliance workspace config",
)
async def get_enterprise_workspace_config(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> EnterpriseWorkspaceView:
    """Return tenant branding, compliance profile, and HA readiness."""

    _ensure_enterprise_workspace_enabled()
    _require_team_manage(principal)
    tenant = await db.get(Tenant, principal["tenant_id"])
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    allowed = await _custom_branding_allowed(db, tenant)
    payload = serialize_enterprise_workspace_view(tenant, custom_branding_allowed=allowed)
    return EnterpriseWorkspaceView.model_validate(payload)


@router.patch(
    "/config",
    response_model=EnterpriseWorkspaceView,
    summary="Update white-label and enterprise compliance workspace config",
)
async def patch_enterprise_workspace_config(
    body: EnterpriseWorkspacePatch,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> EnterpriseWorkspaceView:
    """Persist tenant white-label and compliance overrides."""

    _ensure_enterprise_workspace_enabled()
    _require_team_manage(principal)
    tenant = await db.get(Tenant, principal["tenant_id"])
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

    allowed = await _custom_branding_allowed(db, tenant)
    if body.white_label is not None and not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Custom branding requires Enterprise tier.",
        )

    white_patch = body.white_label.model_dump(exclude_unset=True) if body.white_label else None
    compliance_patch = body.compliance.model_dump(exclude_unset=True) if body.compliance else None
    tenant.operator_settings = merge_enterprise_workspace_patch(
        tenant,
        white_label=white_patch,
        compliance=compliance_patch,
    )
    try:
        await db.commit()
        await db.refresh(tenant)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected enterprise workspace update.",
        )
    payload = serialize_enterprise_workspace_view(tenant, custom_branding_allowed=allowed)
    return EnterpriseWorkspaceView.model_validate(payload)


@router.get(
    "/compliance-export",
    response_model=ComplianceExportBundle,
    summary="Export tenant compliance bundle for auditors",
)
async def export_enterprise_compliance_bundle(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ComplianceExportBundle:
    """Return JSON bundle with audit trail snapshot and compliance metadata."""

    _ensure_enterprise_workspace_enabled()
    _require_team_manage(principal)
    tenant = await db.get(Tenant, principal["tenant_id"])
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    try:
        payload = await build_compliance_export_bundle(db, tenant)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected compliance export.",
        )
    return ComplianceExportBundle.model_validate(payload)


@router.get(
    "/compliance-export/download",
    summary="Download compliance bundle as attachment JSON",
)
async def download_enterprise_compliance_bundle(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> Response:
    """Stream compliance bundle as downloadable JSON file."""

    _ensure_enterprise_workspace_enabled()
    _require_team_manage(principal)
    tenant = await db.get(Tenant, principal["tenant_id"])
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    try:
        payload = await build_compliance_export_bundle(db, tenant)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected compliance export.",
        )
    body = json.dumps(payload, indent=2, default=str).encode("utf-8")
    filename = f"queenswarm-compliance-{tenant.slug}.json"
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
