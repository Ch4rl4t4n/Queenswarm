"""REST CRUD routes for tenant-scoped dynamic agent templates."""

from __future__ import annotations

from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.agent_template_service import AgentTemplateService
from app.application.services.rbac import has_permission
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/agent-templates", tags=["Agent templates"])


class AgentTemplateCreateRequest(BaseModel):
    """Payload for creating a template."""

    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=4000)
    icon: str = Field(default="", max_length=32)
    category: str = Field(default="general", max_length=64)
    tools: list[str] = Field(default_factory=list)
    prompt_template: str = Field(default="", max_length=20000)
    is_default: bool = False


class AgentTemplateUpdateRequest(BaseModel):
    """Payload for updating a template."""

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    icon: str | None = Field(default=None, max_length=32)
    category: str | None = Field(default=None, max_length=64)
    tools: list[str] | None = None
    prompt_template: str | None = Field(default=None, max_length=20000)
    is_default: bool | None = None


class AgentTemplateResponse(BaseModel):
    """Template response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str
    icon: str
    category: str
    tools: list[str]
    prompt_template: str
    is_default: bool
    created_at: Any
    updated_at: Any


def _require_template_read(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if not has_permission(role=role, permission="settings:view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Template read permission denied.")


def _require_template_write(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin tenant role required.")


@router.get("", response_model=list[AgentTemplateResponse], summary="List agent templates for tenant")
async def list_agent_templates(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> list[AgentTemplateResponse]:
    """Return all templates owned by active tenant."""

    _require_template_read(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = AgentTemplateService(db=db)
    rows = await service.list_by_tenant(tenant_id)
    return [AgentTemplateResponse.model_validate(row, from_attributes=True) for row in rows]


@router.post("", response_model=AgentTemplateResponse, status_code=status.HTTP_201_CREATED, summary="Create template")
async def create_agent_template(
    body: AgentTemplateCreateRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AgentTemplateResponse:
    """Create tenant template."""

    _require_template_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = AgentTemplateService(db=db)
    row = await service.create(
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        icon=body.icon,
        category=body.category,
        tools=body.tools,
        prompt_template=body.prompt_template,
        is_default=body.is_default,
    )
    await db.commit()
    return AgentTemplateResponse.model_validate(row, from_attributes=True)


@router.get("/{template_id}", response_model=AgentTemplateResponse, summary="Get template by id")
async def get_agent_template(
    template_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AgentTemplateResponse:
    """Return one tenant template."""

    _require_template_read(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = AgentTemplateService(db=db)
    row = await service.get_by_id(tenant_id, template_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent template not found.")
    return AgentTemplateResponse.model_validate(row, from_attributes=True)


@router.put("/{template_id}", response_model=AgentTemplateResponse, summary="Update template")
async def update_agent_template(
    template_id: uuid.UUID,
    body: AgentTemplateUpdateRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AgentTemplateResponse:
    """Update one tenant template."""

    _require_template_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    if body.model_dump(exclude_none=True) == {}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="No update fields provided.")
    service = AgentTemplateService(db=db)
    row = await service.update(
        tenant_id=tenant_id,
        template_id=template_id,
        name=body.name,
        description=body.description,
        icon=body.icon,
        category=body.category,
        tools=body.tools,
        prompt_template=body.prompt_template,
        is_default=body.is_default,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent template not found.")
    await db.commit()
    return AgentTemplateResponse.model_validate(row, from_attributes=True)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete template")
async def delete_agent_template(
    template_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> Response:
    """Delete one tenant template."""

    _require_template_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = AgentTemplateService(db=db)
    deleted = await service.delete(tenant_id, template_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent template not found.")
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
