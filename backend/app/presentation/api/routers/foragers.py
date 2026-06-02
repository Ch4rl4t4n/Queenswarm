"""REST CRUD routes for tenant-scoped dynamic foragers."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.forager_service import ForagerService
from app.application.services.rbac import has_permission
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/foragers", tags=["Foragers"])


class ForagerScheduleRequest(BaseModel):
    """Optional routine scheduling configuration for one forager."""

    enabled: bool = False
    schedule_kind: str = Field(default="interval", max_length=16)
    interval_seconds: int | None = Field(default=900, ge=60, le=86_400)
    cron_expr: str | None = Field(default=None, max_length=64)
    runtime_mode: str = Field(default="durable", max_length=16)


class ForagerCreateRequest(BaseModel):
    """Payload for creating a dynamic forager."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=4000)
    source_type: str = Field(default="rss", max_length=32)
    source_config: dict[str, Any] = Field(default_factory=dict)
    filter_config: dict[str, Any] = Field(default_factory=dict)
    prompt_template: str = Field(default="", max_length=20000)
    tools: list[str] = Field(default_factory=list)
    is_active: bool = True
    agent_template_id: uuid.UUID | None = None
    schedule: ForagerScheduleRequest = Field(default_factory=ForagerScheduleRequest)


class ForagerUpdateRequest(BaseModel):
    """Payload for updating one dynamic forager."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=140)
    description: str | None = Field(default=None, max_length=4000)
    source_type: str | None = Field(default=None, max_length=32)
    source_config: dict[str, Any] | None = None
    filter_config: dict[str, Any] | None = None
    prompt_template: str | None = Field(default=None, max_length=20000)
    tools: list[str] | None = None
    is_active: bool | None = None
    agent_template_id: uuid.UUID | None = None
    schedule: ForagerScheduleRequest | None = None


class ForagerResponse(BaseModel):
    """Serialized forager row for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str
    source_type: str
    source_config: dict[str, Any]
    filter_config: dict[str, Any]
    prompt_template: str
    tools: list[str]
    is_active: bool
    agent_template_id: uuid.UUID | None
    supervisor_routine_id: uuid.UUID | None
    created_at: Any
    updated_at: Any


class ForagerIngestRecord(BaseModel):
    """One ingest payload item to project into KnowledgeItem rows."""

    source_url: str | None = Field(default=None, max_length=2048)
    content_text: str = Field(min_length=3, max_length=120000)
    confidence_score: float = Field(default=0.65, ge=0.0, le=1.0)
    topic_tags: list[str] = Field(default_factory=list)


class ForagerIngestRequest(BaseModel):
    """Manual ingest payload for one forager."""

    records: list[ForagerIngestRecord] = Field(default_factory=list, min_length=1, max_length=100)


class ForagerIngestResponse(BaseModel):
    """Acknowledgement for ingest operation."""

    ingested: int


class ForagerSpawnRequest(BaseModel):
    """Optional spawn override payload."""

    swarm_id: uuid.UUID | None = None


class ForagerSpawnResponse(BaseModel):
    """Spawned agent envelope."""

    agent_id: uuid.UUID
    config_id: uuid.UUID
    forager_id: uuid.UUID


class ForagerToggleRequest(BaseModel):
    """Enable/disable payload."""

    enabled: bool


class ForagerTriggerRequest(BaseModel):
    """Manual trigger payload for ingest + routine execution."""

    records: list[ForagerIngestRecord] = Field(default_factory=list)


class ForagerTriggerResponse(BaseModel):
    """Manual trigger execution summary."""

    forager_id: str
    ingested: int
    scraped: int = 0
    routine_triggered: bool
    routine_session_id: str | None
    status: str


class ForagerAppendSourcesRequest(BaseModel):
    """Append YouTube channels or X accounts to one forager."""

    platform: str = Field(pattern="^(youtube|x|twitter)$")
    sources: list[str] = Field(min_length=1, max_length=200)


class ForagerScrapeResponse(BaseModel):
    """Dedicated scrape + ingest summary."""

    forager_id: str
    scraped: int
    ingested: int
    routine_triggered: bool
    routine_session_id: str | None
    status: str


def _require_forager_read(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if not has_permission(role=role, permission="settings:view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forager read permission denied.")


def _require_forager_write(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin tenant role required.")


@router.get("", response_model=list[ForagerResponse], summary="List foragers for tenant")
async def list_foragers(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> list[ForagerResponse]:
    """Return all tenant-owned foragers."""

    _require_forager_read(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = ForagerService(db=db)
    rows = await service.list_by_tenant(tenant_id)
    return [ForagerResponse.model_validate(row, from_attributes=True) for row in rows]


@router.post("", response_model=ForagerResponse, status_code=status.HTTP_201_CREATED, summary="Create forager")
async def create_forager(
    body: ForagerCreateRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ForagerResponse:
    """Create one tenant-scoped forager."""

    _require_forager_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = ForagerService(db=db)
    row = await service.create(
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        source_type=body.source_type,
        source_config=body.source_config,
        filter_config=body.filter_config,
        prompt_template=body.prompt_template,
        tools=body.tools,
        is_active=body.is_active,
        agent_template_id=body.agent_template_id,
        schedule=body.schedule.model_dump(),
        created_by_subject=str(principal.get("sub") or "dashboard:forager"),
    )
    await db.commit()
    return ForagerResponse.model_validate(row, from_attributes=True)


@router.get("/{id}", response_model=ForagerResponse, summary="Get forager by id")
async def get_forager(
    id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ForagerResponse:
    """Return one tenant forager."""

    _require_forager_read(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = ForagerService(db=db)
    row = await service.get_by_id(tenant_id, id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forager not found.")
    return ForagerResponse.model_validate(row, from_attributes=True)


@router.put("/{id}", response_model=ForagerResponse, summary="Update forager")
async def update_forager(
    id: uuid.UUID,
    body: ForagerUpdateRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ForagerResponse:
    """Update one tenant forager."""

    _require_forager_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    if body.model_dump(exclude_none=True) == {}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="No update fields provided.")
    service = ForagerService(db=db)
    row = await service.update(
        tenant_id=tenant_id,
        forager_id=id,
        name=body.name,
        description=body.description,
        source_type=body.source_type,
        source_config=body.source_config,
        filter_config=body.filter_config,
        prompt_template=body.prompt_template,
        tools=body.tools,
        is_active=body.is_active,
        agent_template_id=body.agent_template_id,
        schedule=body.schedule.model_dump() if body.schedule is not None else None,
        created_by_subject=str(principal.get("sub") or "dashboard:forager"),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forager not found.")
    await db.commit()
    return ForagerResponse.model_validate(row, from_attributes=True)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete forager")
async def delete_forager(
    id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> Response:
    """Delete one tenant forager."""

    _require_forager_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = ForagerService(db=db)
    deleted = await service.delete(tenant_id, id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forager not found.")
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{id}/ingest", response_model=ForagerIngestResponse, summary="Ingest forager records to HiveMind")
async def ingest_forager_records(
    id: uuid.UUID,
    body: ForagerIngestRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ForagerIngestResponse:
    """Persist manual forager harvest records into knowledge memory."""

    _require_forager_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = ForagerService(db=db)
    inserted = await service.ingest_records(
        tenant_id=tenant_id,
        forager_id=id,
        records=[record.model_dump() for record in body.records],
    )
    if inserted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forager not found or no records ingested.")
    await db.commit()
    return ForagerIngestResponse(ingested=inserted)


@router.post("/{id}/spawn-agent", response_model=ForagerSpawnResponse, summary="Spawn agent from forager")
async def spawn_agent_from_forager(
    id: uuid.UUID,
    body: ForagerSpawnRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ForagerSpawnResponse:
    """Spawn one worker bee from forager config/template metadata."""

    _require_forager_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = ForagerService(db=db)
    out = await service.spawn_agent_from_forager(
        tenant_id=tenant_id,
        forager_id=id,
        swarm_id=body.swarm_id,
    )
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forager not found.")
    agent, cfg = out
    await db.commit()
    return ForagerSpawnResponse(agent_id=agent.id, config_id=cfg.id, forager_id=id)


@router.post("/{id}/toggle", response_model=ForagerResponse, summary="Enable or disable forager")
async def toggle_forager(
    id: uuid.UUID,
    body: ForagerToggleRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ForagerResponse:
    """Toggle forager and linked routine active state."""

    _require_forager_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = ForagerService(db=db)
    row = await service.toggle_enabled(tenant_id=tenant_id, forager_id=id, enabled=body.enabled)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forager not found.")
    await db.commit()
    return ForagerResponse.model_validate(row, from_attributes=True)


@router.post("/{id}/trigger", response_model=ForagerTriggerResponse, summary="Trigger manual forager run")
async def trigger_forager(
    id: uuid.UUID,
    body: ForagerTriggerRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ForagerTriggerResponse:
    """Manually trigger one forager run with optional ingest payload."""

    _require_forager_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    service = ForagerService(db=db)
    out = await service.trigger_manual_run(
        tenant_id=tenant_id,
        forager_id=id,
        records=[record.model_dump() for record in body.records],
    )
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forager not found.")
    await db.commit()
    return ForagerTriggerResponse.model_validate(out)


class ForagerPromoteTaskResponse(BaseModel):
    """Acknowledgement for forager digest → Mission Kanban triage."""

    ok: bool
    task_id: str | None = None
    forager_id: str | None = None
    title: str | None = None
    error: str | None = None


class ForagerPromoteTaskRequest(BaseModel):
    """Optional title override when promoting forager harvest to triage."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=500)


@router.post(
    "/{id}/promote-task",
    response_model=ForagerPromoteTaskResponse,
    summary="Promote forager harvest to Mission Kanban triage task",
)
async def promote_forager_task(
    id: uuid.UUID,
    body: ForagerPromoteTaskRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ForagerPromoteTaskResponse:
    """Create a triage task summarizing one forager's HiveMind items."""

    _require_forager_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.forager_operator_actions import promote_forager_digest_to_task

    result = await promote_forager_digest_to_task(
        db,
        tenant_id=tenant_id,
        forager_id=id,
        title=body.title,
    )
    if not result.get("ok"):
        err = str(result.get("error") or "promote_failed")
        if err == "forager_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forager not found.")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=err)
    await db.commit()
    return ForagerPromoteTaskResponse(
        ok=True,
        task_id=str(result.get("task_id") or ""),
        forager_id=str(result.get("forager_id") or ""),
        title=str(result.get("title") or ""),
    )


@router.post("/{id}/scrape", response_model=ForagerScrapeResponse, summary="Scrape YouTube/X sources and ingest")
async def scrape_forager(
    id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ForagerScrapeResponse:
    """Run platform scraper for one forager, ingest to Knowledge, trigger evaluator routine."""

    _require_forager_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.social_intel_runner import run_social_intel_forager

    dashboard_user = principal.get("user")
    operator_id = getattr(dashboard_user, "id", None)
    out = await run_social_intel_forager(
        db,
        tenant_id=tenant_id,
        forager_id=id,
        trigger_evaluator=True,
        operator_user_id=operator_id,
    )
    if out.get("status") == "not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forager not found.")
    await db.commit()
    return ForagerScrapeResponse.model_validate(out)


@router.post("/{id}/sources", response_model=ForagerResponse, summary="Append monitored channels or accounts")
async def append_forager_sources(
    id: uuid.UUID,
    body: ForagerAppendSourcesRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ForagerResponse:
    """Append unique YouTube channels or X handles (e.g. from Queen prompt)."""

    _require_forager_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.social_intel_runner import append_forager_sources as append_sources

    platform = "youtube" if body.platform == "youtube" else "x"
    row = await append_sources(
        db,
        tenant_id=tenant_id,
        forager_id=id,
        platform=platform,
        sources=body.sources,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forager not found.")
    await db.commit()
    await db.refresh(row)
    return ForagerResponse.model_validate(row, from_attributes=True)


__all__ = ["router"]
