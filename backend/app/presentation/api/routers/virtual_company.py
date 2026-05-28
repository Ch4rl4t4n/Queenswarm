"""Virtual Company profile + bootstrap checklist API."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.rbac import has_permission
from app.application.services.virtual_company_profile import (
    VirtualCompanyProfilePatch,
    VirtualCompanyProfilePublic,
    apply_solo_free_first_bootstrap,
    build_bootstrap_checklist,
    build_oauth_progress,
    build_oauth_setup_guide,
    first_run_playbook,
    install_free_connectors,
    merge_profile_patch,
    oauth_vendor_env_status,
    profile_from_tenant,
    provision_solo_super_routers,
    seed_default_operator_profile,
    start_first_run_session,
)
from app.application.services.virtual_company_swarm_builder import (
    build_all_virtual_company_swarms,
    build_department_swarm,
)
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/virtual-company", tags=["Virtual Company"])


class BuildDepartmentSwarmBody(BaseModel):
    """Build one Virtual Company department swarm from wizard template."""

    model_config = ConfigDict(extra="forbid")

    template_id: str = Field(..., min_length=4, max_length=64)
    skip_if_exists: bool = True


class BuildAllSwarmsBody(BaseModel):
    """Build all department swarms (+ optional sentinel)."""

    model_config = ConfigDict(extra="forbid")

    include_sentinel: bool = True


def _tenant_id(principal: dict[str, Any]) -> uuid.UUID:
    raw = principal.get("tenant_id")
    if raw is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))


def _user_id(principal: dict[str, Any]) -> uuid.UUID:
    user = principal.get("user")
    if user is not None and hasattr(user, "id"):
        return user.id  # type: ignore[no-any-return]
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User context missing.")


def _ensure_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"} or not has_permission(role=role, permission="settings:view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin tenant role required.")


@router.get("/profile", response_model=VirtualCompanyProfilePublic, summary="Virtual Company operator profile")
async def get_virtual_company_profile(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> VirtualCompanyProfilePublic:
    """Return operator profile for swarm context bootstrap."""

    tenant = await db.get(Tenant, _tenant_id(principal))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    return profile_from_tenant(tenant)


@router.put("/profile", response_model=VirtualCompanyProfilePublic, summary="Update Virtual Company profile")
async def update_virtual_company_profile(
    body: VirtualCompanyProfilePatch,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> VirtualCompanyProfilePublic:
    """Persist operator profile (brand, industry, goals)."""

    _ensure_admin(principal)
    tenant = await db.get(Tenant, _tenant_id(principal))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    patch = body.model_dump(exclude_unset=True)
    try:
        tenant.operator_settings = merge_profile_patch(tenant.operator_settings, patch)
        await db.commit()
        await db.refresh(tenant)
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile persistence failed.",
        ) from exc
    return profile_from_tenant(tenant)


@router.get("/bootstrap-checklist", summary="Virtual Company free-first readiness checklist")
async def virtual_company_bootstrap_checklist(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Profile, routing, and connector readiness per department."""

    tenant = await db.get(Tenant, _tenant_id(principal))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    return await build_bootstrap_checklist(
        db,
        tenant=tenant,
        dashboard_user_id=_user_id(principal),
    )


@router.get("/oauth-setup-guide", summary="OAuth vendor registration checklist for solo Virtual Company")
async def virtual_company_oauth_setup_guide(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Redirect URI, env keys, and vendor console links — no secrets."""

    _ = principal
    return build_oauth_setup_guide()


@router.get("/readiness-audit", summary="Virtual Company readiness score + OAuth env + first-run")
async def virtual_company_readiness_audit(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Full solo Virtual Company audit for operator scripts."""

    tenant = await db.get(Tenant, _tenant_id(principal))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    checklist = await build_bootstrap_checklist(
        db,
        tenant=tenant,
        dashboard_user_id=_user_id(principal),
    )
    oauth_env = oauth_vendor_env_status()
    oauth_ready = all(
        oauth_env.get(key, False)
        for key in ("notion_workspace", "google_gmail", "github_rest")
    )
    oauth_progress = build_oauth_progress(
        connectors=checklist.get("connectors") or [],
        oauth_env=oauth_env,
    )
    return {
        "checklist": checklist,
        "oauth_env": oauth_env,
        "oauth_env_ready": oauth_ready,
        "oauth_progress": oauth_progress,
        "readiness_score": checklist.get("readiness_score", 0),
        "simulate_path_complete": checklist.get("simulate_path_complete", False),
        "blockers": list(checklist.get("blockers") or []),
        "optional_next_steps": list(checklist.get("optional_next_steps") or []),
    }


@router.post("/bootstrap-solo", summary="Apply solo free-first routing bootstrap")
async def virtual_company_bootstrap_solo(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Idempotent: set tenant LLM routing to free_first for €0 solo target."""

    _ensure_admin(principal)
    tenant = await db.get(Tenant, _tenant_id(principal))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    try:
        routing_result = await apply_solo_free_first_bootstrap(db, tenant=tenant)
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bootstrap failed.",
        ) from exc
    checklist = await build_bootstrap_checklist(
        db,
        tenant=tenant,
        dashboard_user_id=_user_id(principal),
    )
    return {"routing": routing_result, "checklist": checklist}


@router.post("/seed-default-profile", response_model=VirtualCompanyProfilePublic, summary="Seed solo default profile")
async def virtual_company_seed_default_profile(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> VirtualCompanyProfilePublic:
    """Idempotent: fill Queenswarm Solo defaults when profile is empty."""

    _ensure_admin(principal)
    tenant = await db.get(Tenant, _tenant_id(principal))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    try:
        profile, _changed = seed_default_operator_profile(tenant)
        await db.commit()
        await db.refresh(tenant)
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile seed failed.",
        ) from exc
    return profile


@router.post("/install-free-connectors", summary="Install Notion, Gmail, GitHub Phase 3 templates")
async def virtual_company_install_free_connectors(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Install free connector rows; operator completes OAuth in Execution Studio."""

    _ensure_admin(principal)
    tenant = await db.get(Tenant, _tenant_id(principal))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    try:
        installs = await install_free_connectors(db, dashboard_user_id=_user_id(principal))
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connector install failed.",
        ) from exc
    checklist = await build_bootstrap_checklist(
        db,
        tenant=tenant,
        dashboard_user_id=_user_id(principal),
    )
    return {"installs": installs, "checklist": checklist}


@router.post("/provision-solo-routers", summary="Provision solo Super Tool Routers for Virtual Company")
async def virtual_company_provision_solo_routers(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Idempotent: create vc_solo_app_actions + vc_solo_dev_workspace routers."""

    _ensure_admin(principal)
    tenant = await db.get(Tenant, _tenant_id(principal))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    try:
        routers = await provision_solo_super_routers(
            db,
            tenant=tenant,
            dashboard_user_id=_user_id(principal),
        )
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Super router provision failed.",
        ) from exc
    checklist = await build_bootstrap_checklist(
        db,
        tenant=tenant,
        dashboard_user_id=_user_id(principal),
    )
    return {"routers": routers, "checklist": checklist}


@router.get("/first-run/{template_id}", summary="Guided first simulate session playbook")
async def virtual_company_first_run_playbook(
    template_id: str,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return prefilled supervisor goal + skills for a department wizard template."""

    _ = principal
    playbook = first_run_playbook(template_id)
    if playbook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown template playbook.")
    return playbook


@router.post("/first-run/{template_id}/start-session", summary="Start first simulate supervisor session")
async def virtual_company_start_first_run_session(
    template_id: str,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """One-click Marketing Ops (or department) simulate session from playbook."""

    tenant = await db.get(Tenant, _tenant_id(principal))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    subject = str(principal.get("sub") or "")[:512] or None
    try:
        result = await start_first_run_session(
            db,
            tenant_id=tenant.id,
            template_id=template_id,
            created_by_subject=subject,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        marker = str(exc)
        if marker.startswith("billing_limit_exceeded:"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=marker.split(":", 1)[1],
            ) from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=marker) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session start failed.",
        ) from exc
    return result


@router.post("/build-department-swarm", summary="Build one Virtual Company department swarm")
async def virtual_company_build_department_swarm(
    body: BuildDepartmentSwarmBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Server-side Swarm Builder — idempotent when skip_if_exists=true."""

    _ensure_admin(principal)
    tenant = await db.get(Tenant, _tenant_id(principal))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    subject = str(principal.get("sub") or "")[:512] or None
    try:
        result = await build_department_swarm(
            db,
            tenant=tenant,
            template_id=body.template_id,
            created_by_subject=subject,
            skip_if_exists=body.skip_if_exists,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Swarm build failed.",
        ) from exc
    checklist = await build_bootstrap_checklist(
        db,
        tenant=tenant,
        dashboard_user_id=_user_id(principal),
    )
    return {"build": result, "checklist": checklist}


@router.post("/build-all-departments", summary="Build all Virtual Company department swarms")
async def virtual_company_build_all_departments(
    body: BuildAllSwarmsBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Build marketing, sales, finance, digital, rnd, product (+ optional sentinel)."""

    _ensure_admin(principal)
    tenant = await db.get(Tenant, _tenant_id(principal))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    subject = str(principal.get("sub") or "")[:512] or None
    try:
        builds = await build_all_virtual_company_swarms(
            db,
            tenant=tenant,
            created_by_subject=subject,
            include_sentinel=body.include_sentinel,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Swarm build failed.",
        ) from exc
    checklist = await build_bootstrap_checklist(
        db,
        tenant=tenant,
        dashboard_user_id=_user_id(principal),
    )
    return {"builds": builds, "checklist": checklist}
