"""Tenant-scoped external API layer for project integrations."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings, get_settings
from app.core.tenant_context import set_current_tenant_id
from app.domain.external.gateway import execute_external_invocation
from app.domain.external.registry import normalize_external_slug, resolve_external_principal
from app.presentation.api.deps import DbSession

router = APIRouter(prefix="/ext-api/v1", tags=["External API"])


class ExternalApiRunBody(BaseModel):
    """External invoke payload."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(..., min_length=1, max_length=160)
    payload: dict[str, Any] = Field(default_factory=dict)


class ExternalApiProjectScope(BaseModel):
    """Caller scope descriptor for external API clients."""

    project_id: str
    project_slug: str
    project_kind: str
    tenant_id: str | None
    api_key_id: str
    permissions: list[str]


async def _external_api_credential(
    x_qs_external_key: Annotated[str | None, Header(alias="X-Queenswarm-External-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if x_qs_external_key and x_qs_external_key.strip():
        return x_qs_external_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(None, 1)[1].strip()
        if token:
            return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing external API key. Provide X-Queenswarm-External-Key or Authorization Bearer token.",
    )


async def _resolve_tenant_scoped_principal(
    db: DbSession,
    credential: Annotated[str, Depends(_external_api_credential)],
) -> tuple[Any, Any]:
    set_current_tenant_id(None)
    principal = await resolve_external_principal(db, raw_key=credential)
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid external API key.")
    project, api_key = principal
    if project.tenant_id != api_key.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key tenant scope mismatch.")
    set_current_tenant_id(str(project.tenant_id) if project.tenant_id is not None else None)
    return project, api_key


@router.get("/scope", response_model=ExternalApiProjectScope, summary="Current API key scope")
async def external_api_scope(
    principal: tuple[Any, Any] = Depends(_resolve_tenant_scoped_principal),
) -> ExternalApiProjectScope:
    project, api_key = principal
    permissions_raw = api_key.permissions if isinstance(api_key.permissions, list) else []
    permissions = [str(item) for item in permissions_raw]
    return ExternalApiProjectScope(
        project_id=str(project.id),
        project_slug=project.slug,
        project_kind=project.project_kind,
        tenant_id=str(project.tenant_id) if project.tenant_id else None,
        api_key_id=str(api_key.id),
        permissions=permissions,
    )


@router.post("/projects/{project_slug}/run", summary="Run external project action via tenant API key")
async def external_api_run_project(
    project_slug: str,
    body: ExternalApiRunBody,
    db: DbSession,
    cfg: Annotated[Settings, Depends(get_settings)],
    credential: Annotated[str, Depends(_external_api_credential)],
    principal: tuple[Any, Any] = Depends(_resolve_tenant_scoped_principal),
) -> dict[str, Any]:
    project, _api_key = principal
    if normalize_external_slug(project_slug) != project.slug:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key not scoped to this project.")
    return await execute_external_invocation(
        db,
        cfg=cfg,
        credential=credential,
        project_slug=project_slug,
        action=body.action,
        payload=dict(body.payload or {}),
        channel="rest",
    )


__all__ = ["router"]
