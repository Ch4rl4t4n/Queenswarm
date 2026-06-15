"""REST CRUD routes for tenant-scoped dynamic foragers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.forager_service import ForagerService
from app.application.services.forager_spawn_policy import (
    forager_spawn_policy,
    merge_forager_spawn_policy_patch,
)
from app.application.services.rbac import has_permission
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/foragers", tags=["Foragers"])


async def _forager_response(db: DbSession, row: object) -> ForagerResponse:
    """Refresh ORM row before pydantic serialization (async SQLAlchemy timestamps)."""

    await db.refresh(row)
    return ForagerResponse.model_validate(row, from_attributes=True)


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


class DataMonitorSubmitRequest(BaseModel):
    """DG1 — one-line monitor intent wizard submit."""

    model_config = ConfigDict(extra="forbid")

    intent: str = Field(min_length=12, max_length=2000)
    schedule_preset: Literal["6h", "12h", "24h", "daily_6utc"] = Field(default="24h")
    trigger_first_run: bool = Field(default=True)


class ForagerSpawnPolicyView(BaseModel):
    """Tenant forager auto-spawn approval policy."""

    model_config = ConfigDict(extra="forbid")

    auto_spawn_auto_approve_enabled: bool


class ForagerSpawnPolicyPatch(BaseModel):
    """Partial patch for forager spawn approval policy."""

    model_config = ConfigDict(extra="forbid")

    auto_spawn_auto_approve_enabled: bool | None = None


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


async def _tenant_from_principal(db: DbSession, principal: dict[str, Any]) -> Tenant:
    """Load tenant row for policy mutations."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    return tenant


@router.get(
    "/spawn-control-policy",
    response_model=ForagerSpawnPolicyView,
    summary="Forager auto-spawn approval policy (auto vs manual)",
)
async def get_forager_spawn_control_policy(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ForagerSpawnPolicyView:
    """Return tenant auto-spawn vs manual review policy for forager harvests."""

    _require_forager_read(principal)
    tenant = await _tenant_from_principal(db, principal)
    payload = forager_spawn_policy(tenant)
    return ForagerSpawnPolicyView(**payload)


@router.patch(
    "/spawn-control-policy",
    response_model=ForagerSpawnPolicyView,
    summary="Update forager auto-spawn approval policy",
)
async def patch_forager_spawn_control_policy(
    body: ForagerSpawnPolicyPatch,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ForagerSpawnPolicyView:
    """Persist auto-spawn approval toggle for forager configurations."""

    _require_forager_write(principal)
    tenant = await _tenant_from_principal(db, principal)
    patch = body.model_dump(exclude_unset=True)
    if patch:
        tenant.operator_settings = merge_forager_spawn_policy_patch(tenant.operator_settings, patch)
        await db.commit()
        await db.refresh(tenant)
    payload = forager_spawn_policy(tenant)
    return ForagerSpawnPolicyView(**payload)


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
    return await _forager_response(db, row)


@router.get("/data-monitor-wizard", summary="DG1 Data Monitor wizard snapshot")
async def data_monitor_wizard_snapshot(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return examples, niches, and schedule presets for monitor wizard."""

    _require_forager_read(principal)
    from app.application.services.data_monitor_wizard_service import compose_data_monitor_wizard_snapshot

    return compose_data_monitor_wizard_snapshot().model_dump(mode="json")


@router.post("/data-monitor-wizard/preview", summary="DG1 Preview monitor plan from intent")
async def data_monitor_wizard_preview(
    body: DataMonitorSubmitRequest,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Derive forager plan without creating rows."""

    _require_forager_read(principal)
    from app.application.services.data_monitor_wizard_service import derive_data_monitor_plan

    plan = derive_data_monitor_plan(body.intent, schedule_preset=body.schedule_preset)
    return plan.model_dump(mode="json")


@router.post(
    "/data-monitor-wizard/submit",
    summary="DG1 Create scheduled forager from monitor intent",
    status_code=status.HTTP_201_CREATED,
)
async def data_monitor_wizard_submit(
    body: DataMonitorSubmitRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """One-line intent → forager + Celery schedule + extract schema."""

    _require_forager_write(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.data_monitor_wizard_service import (
        DataMonitorSubmitIn,
        submit_data_monitor_wizard,
    )

    try:
        result = await submit_data_monitor_wizard(
            db,
            tenant_id=tenant_id,
            body=DataMonitorSubmitIn(
                intent=body.intent,
                schedule_preset=body.schedule_preset,
                trigger_first_run=body.trigger_first_run,
            ),
            created_by_subject=str(principal.get("sub") or "dashboard:data-monitor-wizard"),
        )
    except ValueError as exc:
        if str(exc) == "data_monitor_wizard_disabled":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Wizard disabled.") from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return result.model_dump(mode="json")


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
    return await _forager_response(db, row)


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
    return await _forager_response(db, row)


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
    mode: str | None = None
    new_item_count: int | None = None
    skill_slugs: list[str] = Field(default_factory=list)
    error: str | None = None


class ForagerPromoteTaskRequest(BaseModel):
    """Optional overrides when promoting forager harvest or goldmine alert to triage."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=500)
    mode: Literal["digest", "alert"] = Field(default="digest")
    knowledge_item_ids: list[uuid.UUID] | None = Field(default=None, max_length=24)
    include_skill_bundle: bool = Field(default=True)


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
        mode=body.mode,
        knowledge_item_ids=body.knowledge_item_ids,
        include_skill_bundle=body.include_skill_bundle,
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
        mode=str(result.get("mode") or body.mode),
        new_item_count=int(result.get("new_item_count") or 0),
        skill_slugs=list(result.get("skill_slugs") or []),
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
    return await _forager_response(db, row)


class ForagerHarvestFindingView(BaseModel):
    """One harvested knowledge row in an operator report."""

    title: str
    body: str
    source_url: str | None = None
    scraped_at: datetime | None = None
    confidence: float = 0.0
    source_type: str = ""


class ForagerHarvestReportView(BaseModel):
    """JSON preview for forager harvest report dialog."""

    forager_id: uuid.UUID
    name: str
    description: str
    source_type: str
    items_total: int
    executive_summary: str
    items: list[ForagerHarvestFindingView]
    generated_at: datetime


@router.get(
    "/{id}/report",
    response_model=ForagerHarvestReportView,
    summary="Forager harvest intelligence report (JSON preview)",
)
async def get_forager_harvest_report(
    id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    item_limit: int = Query(default=25, ge=1, le=50),
) -> ForagerHarvestReportView:
    """Return structured harvest report for operator UI and export."""

    _require_forager_read(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.forager_harvest_report import load_forager_harvest_report

    report = await load_forager_harvest_report(
        db,
        tenant_id=tenant_id,
        forager_id=id,
        item_limit=item_limit,
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forager not found.")
    return ForagerHarvestReportView(
        forager_id=uuid.UUID(str(report["forager_id"])),
        name=str(report["name"]),
        description=str(report.get("description") or ""),
        source_type=str(report.get("source_type") or ""),
        items_total=int(report.get("items_total") or 0),
        executive_summary=str(report.get("executive_summary") or ""),
        items=[ForagerHarvestFindingView.model_validate(row) for row in list(report.get("items") or [])],
        generated_at=report.get("generated_at") or datetime.now(tz=UTC),
    )


@router.get(
    "/{id}/report/export",
    summary="Export forager harvest report (HTML, Markdown, or PDF)",
)
async def export_forager_harvest_report(
    id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    export_format: Literal["html", "markdown", "pdf"] = Query(default="pdf", alias="format"),
    item_limit: int = Query(default=25, ge=1, le=50),
) -> Response:
    """Download a printable intelligence report from HiveMind harvest."""

    _require_forager_read(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.forager_harvest_report import (
        build_forager_harvest_report_markdown,
        build_forager_harvest_report_pdf,
        build_forager_harvest_report_print_html,
        load_forager_harvest_report,
    )

    report = await load_forager_harvest_report(
        db,
        tenant_id=tenant_id,
        forager_id=id,
        item_limit=item_limit,
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forager not found.")

    tail = str(id).replace("-", "")[-8:].upper()
    safe_name = "".join(ch if ch.isalnum() else "-" for ch in str(report.get("name") or "forager")).strip("-")[:40]
    if export_format == "markdown":
        content = build_forager_harvest_report_markdown(report)
        media_type = "text/markdown; charset=utf-8"
        filename = f"forager-{safe_name}-{tail}.md"
        body: str | bytes = content
    elif export_format == "pdf":
        content = build_forager_harvest_report_pdf(report)
        media_type = "application/pdf"
        filename = f"forager-{safe_name}-{tail}.pdf"
        body = content
    else:
        content = build_forager_harvest_report_print_html(report)
        media_type = "text/html; charset=utf-8"
        filename = f"forager-{safe_name}-{tail}.html"
        body = content

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=body, media_type=media_type, headers=headers)


__all__ = ["router"]
