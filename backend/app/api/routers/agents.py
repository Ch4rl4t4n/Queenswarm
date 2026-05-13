"""Autonomous bee registry (JWT guarded)."""

from __future__ import annotations

import uuid

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.deps import DbSession, JwtSubject
from app.models.agent import Agent
from app.models.agent_config import AgentConfig
from app.models.enums import AgentRole, AgentStatus, SwarmPurpose
from app.models.swarm import SubSwarm
from app.schemas.agent import AgentCreateRequest, AgentPatchRequest, AgentSnapshot
from app.schemas.agent_dynamic import (
    AgentConfigSnapshot,
    AgentConfigUpsert,
    AgentDynamicCreate,
    AgentDynamicCreateResponse,
)
from app.schemas.agent_factory_http import UniversalAgentRunOverlay, UniversalAgentRunQueued
from app.services.agent_catalog import (
    AgentCatalogError,
    apply_agent_updates,
    create_agent_record,
    fetch_agent,
    list_agents,
)
from app.services.agent_task_hints import latest_open_tasks_for_agents
from app.services.agent_universal import enqueue_universal_agent_run
from app.services.hive_tier import is_fixed_orchestrator_agent, resolve_hive_tier
from app.worker.tasks import execute_universal_agent_task

router = APIRouter(tags=["Agents"])


async def _swarm_fields_for_agents(db: DbSession, rows: list[Agent]) -> dict[uuid.UUID, tuple[str, SwarmPurpose]]:
    """Map ``swarm_id`` to ``(swarm.name, swarm.purpose)`` for hydrated snapshots."""

    ids = {r.swarm_id for r in rows if r.swarm_id is not None}
    if not ids:
        return {}
    stmt = select(SubSwarm).where(SubSwarm.id.in_(ids))
    found = await db.scalars(stmt)
    out: dict[uuid.UUID, tuple[str, SwarmPurpose]] = {}
    for swarm in found:
        out[swarm.id] = (swarm.name, swarm.purpose)
    return out


async def _to_agent_snapshot(db: DbSession, row: Agent) -> AgentSnapshot:
    """Attach the newest pending/running backlog row for dashboard context."""

    meta = await _swarm_fields_for_agents(db, [row])
    hints = await latest_open_tasks_for_agents(db, [row.id])
    linked = hints.get(row.id)
    cfg_row = await db.scalar(select(AgentConfig).where(AgentConfig.agent_id == row.id))
    base = AgentSnapshot.model_validate(row)
    tier = resolve_hive_tier(agent=row, agent_config=cfg_row)
    pair = meta.get(row.swarm_id) if row.swarm_id is not None else None
    swarm_name = pair[0] if pair else None
    swarm_purpose = pair[1] if pair else None
    return base.model_copy(
        update={
            "current_task_id": linked.id if linked else None,
            "current_task_title": linked.title if linked else None,
            "has_universal_config": cfg_row is not None,
            "hive_tier": tier,
            "swarm_name": swarm_name,
            "swarm_purpose": swarm_purpose,
        },
    )


@router.post(
    "/pause-all",
    summary="Emergency pause for every idle or running bee",
)
async def pause_all_agents(db: DbSession, _subject: JwtSubject) -> dict[str, Any]:
    """Mark ``idle`` / ``running`` bees as ``paused``."""

    result = await db.execute(
        select(Agent).where(Agent.status.in_((AgentStatus.IDLE, AgentStatus.RUNNING))),
    )
    rows = list(result.scalars().all())
    for row in rows:
        row.status = AgentStatus.PAUSED
    await db.commit()
    return {"paused": len(rows), "message": f"Paused {len(rows)} agents"}


@router.post(
    "/wake-all",
    summary="Return every paused bee to idle",
)
async def wake_all_agents(db: DbSession, _subject: JwtSubject) -> dict[str, Any]:
    """Operator reset — ``paused`` bees become ``idle``."""

    result = await db.execute(select(Agent).where(Agent.status == AgentStatus.PAUSED))
    rows = list(result.scalars().all())
    for row in rows:
        row.status = AgentStatus.IDLE
    await db.commit()
    return {"woken": len(rows), "message": f"Woke {len(rows)} agents"}


@router.post(
    "/dynamic",
    response_model=AgentDynamicCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create UI-defined bee + persisted universal executor config",
)
async def create_dynamic_agent(
    body: AgentDynamicCreate,
    db: DbSession,
    _subject: JwtSubject,
) -> AgentDynamicCreateResponse:
    """Factory endpoint used by the dashboard — managers and workers only."""

    normalized = body.name.strip().lower()
    if normalized == "orchestrator":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Orchestrator is fixed — use PATCH on its persisted config.",
        )

    oc = dict(body.output_config)
    oc["hive_tier"] = body.hive_tier

    try:
        agent = await create_agent_record(
            db,
            name=body.name,
            role=AgentRole.LEARNER,
            status=body.agent_status,
            swarm_id=body.swarm_id,
            config={"origin": "dynamic_factory", "hive_tier": body.hive_tier},
        )
        cfg = AgentConfig(
            agent_id=agent.id,
            system_prompt=body.system_prompt,
            user_prompt_template=body.user_prompt_template,
            tools=list(body.tools),
            output_format=body.output_format,
            output_destination=body.output_destination,
            output_config=oc,
            schedule_type=body.schedule_type,
            schedule_value=body.schedule_value,
            is_active=True,
        )
        db.add(cfg)
        await db.commit()
        await db.refresh(agent)
        await db.refresh(cfg)
    except AgentCatalogError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent name is already taken.",
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected dynamic agent insert.",
        )
    return AgentDynamicCreateResponse(
        agent_id=agent.id,
        agent_name=agent.name,
        config_id=cfg.id,
    )


@router.get(
    "/{agent_id}/config",
    response_model=AgentConfigSnapshot,
    summary="Fetch universal executor config for a bee",
)
async def get_agent_config_row(
    agent_id: uuid.UUID,
    db: DbSession,
    _subject: JwtSubject,
) -> AgentConfigSnapshot:
    """Return prompt + tool JSON for the agent editor."""

    agent = await fetch_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    cfg = await db.scalar(select(AgentConfig).where(AgentConfig.agent_id == agent_id))
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found.")
    return AgentConfigSnapshot.model_validate(cfg)


@router.put(
    "/{agent_id}/config",
    response_model=AgentConfigSnapshot,
    summary="Upsert universal executor config",
)
async def upsert_agent_config_row(
    agent_id: uuid.UUID,
    body: AgentConfigUpsert,
    db: DbSession,
    _subject: JwtSubject,
) -> AgentConfigSnapshot:
    """Create or update prompt-driven configuration for an existing agent row."""

    agent = await fetch_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    payload = body.model_dump(exclude_unset=True)
    if payload.get("system_prompt") is not None:
        payload["system_prompt"] = str(payload["system_prompt"]).strip()
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to upsert.",
        )

    if is_fixed_orchestrator_agent(agent):
        if payload.get("output_config") is not None:
            merged_oc = dict(payload["output_config"])
            merged_oc["hive_tier"] = "orchestrator"
            payload["output_config"] = merged_oc

    try:
        cfg = await db.scalar(select(AgentConfig).where(AgentConfig.agent_id == agent_id))
        if cfg is None:
            ia = payload.get("is_active")
            active_default = True if ia is None else bool(ia)
            if "system_prompt" in payload and payload["system_prompt"] is not None:
                system_prompt = str(payload["system_prompt"]).strip()
            elif not active_default:
                system_prompt = ""
            else:
                system_prompt = "You are a helpful AI agent."
            cfg = AgentConfig(
                agent_id=agent_id,
                system_prompt=system_prompt,
                user_prompt_template=payload.get("user_prompt_template"),
                tools=list(payload.get("tools") or []),
                output_format=str(payload.get("output_format") or "text"),
                output_destination=str(payload.get("output_destination") or "dashboard"),
                output_config=dict(payload.get("output_config") or {}),
                schedule_type=str(payload.get("schedule_type") or "on_demand"),
                schedule_value=payload.get("schedule_value"),
                is_active=bool(payload.get("is_active", True)),
            )
            db.add(cfg)
        else:
            for field, value in payload.items():
                if value is None:
                    continue
                if field == "output_config" and isinstance(value, dict):
                    merged_oc = dict(cfg.output_config or {})
                    merged_oc.update(value)
                    setattr(cfg, field, merged_oc)
                else:
                    setattr(cfg, field, value)
        await db.commit()
        await db.refresh(cfg)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected config upsert.",
        )
    return AgentConfigSnapshot.model_validate(cfg)


@router.post(
    "/{agent_id}/run",
    response_model=UniversalAgentRunQueued,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue an immediate universal executor run",
)
async def run_agent_now(
    agent_id: uuid.UUID,
    db: DbSession,
    _subject: JwtSubject,
    overlay: UniversalAgentRunOverlay | None = Body(default=None),
) -> UniversalAgentRunQueued:
    """Enqueue :func:`execute_universal_agent_task` for operator-triggered runs."""

    agent = await fetch_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    cfg = await db.scalar(select(AgentConfig).where(AgentConfig.agent_id == agent_id))
    try:
        backlog = await enqueue_universal_agent_run(
            db,
            agent=agent,
            cfg=cfg,
            title=f"{agent.name} — on-demand universal run",
            priority=3,
            guard_duplicates=False,
            overlay=overlay,
        )
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected task insert.",
        )
    execute_universal_agent_task.delay(str(backlog.id))
    return UniversalAgentRunQueued(task_id=backlog.id, status="queued")


@router.post(
    "",
    response_model=AgentSnapshot,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new autonomous bee",
)
async def register_agent(
    body: AgentCreateRequest,
    db: DbSession,
    _subject: JwtSubject,
):
    """Hard-disabled — callers must POST ``/agents/dynamic`` with a hive tier."""

    del body, db, _subject  # arity preserved for FastAPI OpenAPI stubs
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="POST /agents is retired — use POST /agents/dynamic (manager/worker tiers).",
    )


@router.get(
    "",
    response_model=list[AgentSnapshot],
    summary="List autonomous bees",
)
async def list_agent_registry(
    db: DbSession,
    _subject: JwtSubject,
    swarm_id: uuid.UUID | None = Query(default=None),
    role: AgentRole | None = Query(default=None),
    filter_status: AgentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Filter the colony worker pool for dashboards and routing bees."""

    try:
        rows = await list_agents(
            db,
            swarm_id=swarm_id,
            role=role,
            status=filter_status,
            limit=limit,
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected agent listing.",
        )
    hints = await latest_open_tasks_for_agents(db, [r.id for r in rows])
    swarm_meta = await _swarm_fields_for_agents(db, rows)
    cfg_by_id: dict[uuid.UUID, AgentConfig] = {}
    if rows:
        cfg_stmt = select(AgentConfig).where(AgentConfig.agent_id.in_([r.id for r in rows]))
        cfg_rows = (await db.scalars(cfg_stmt)).all()
        cfg_by_id = {c.agent_id: c for c in cfg_rows}
    snapshots: list[AgentSnapshot] = []
    for row in rows:
        linked = hints.get(row.id)
        cfg_row = cfg_by_id.get(row.id)
        base = AgentSnapshot.model_validate(row)
        tier = resolve_hive_tier(agent=row, agent_config=cfg_row)
        pair = swarm_meta.get(row.swarm_id) if row.swarm_id is not None else None
        snapshots.append(
            base.model_copy(
                update={
                    "current_task_id": linked.id if linked else None,
                    "current_task_title": linked.title if linked else None,
                    "has_universal_config": cfg_row is not None,
                    "hive_tier": tier,
                    "swarm_name": pair[0] if pair else None,
                    "swarm_purpose": pair[1] if pair else None,
                },
            ),
        )
    return snapshots


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a manager or worker bee",
)
async def delete_agent(agent_id: uuid.UUID, db: DbSession, _subject: JwtSubject) -> Response:
    """Orchestrator is immutable; cascades AgentConfig."""

    row = await fetch_agent(db, agent_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    if is_fixed_orchestrator_agent(row):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Orchestrator cannot be deleted.",
        )
    try:
        db.delete(row)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected agent deletion.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{agent_id}",
    response_model=AgentSnapshot,
    summary="Fetch a single bee",
)
async def get_agent(
    agent_id: uuid.UUID,
    db: DbSession,
    _subject: JwtSubject,
):
    """Return agent telemetry for waggle-dance relays and imitation."""

    try:
        row = await fetch_agent(db, agent_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected agent lookup.",
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    return await _to_agent_snapshot(db, row)


@router.patch(
    "/{agent_id}",
    response_model=AgentSnapshot,
    summary="Patch agent placement or status",
)
async def patch_agent(
    agent_id: uuid.UUID,
    body: AgentPatchRequest,
    db: DbSession,
    _subject: JwtSubject,
):
    """Update status, swarm membership, or performance fields."""

    if body.detach_from_swarm and body.swarm_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use detach_from_swarm or swarm_id, not both.",
        )

    if (
        body.status is None
        and not body.detach_from_swarm
        and body.swarm_id is None
        and body.config is None
        and body.performance_score is None
        and body.pollen_points is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one mutable field.",
        )

    row = await fetch_agent(db, agent_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    swarm_move = body.detach_from_swarm or (body.swarm_id is not None)
    new_swarm_id: uuid.UUID | None
    if body.detach_from_swarm:
        new_swarm_id = None
    elif body.swarm_id is not None:
        new_swarm_id = body.swarm_id
    else:
        new_swarm_id = row.swarm_id

    try:
        await apply_agent_updates(
            db,
            row,
            status=body.status,
            swarm_move=swarm_move,
            new_swarm_id=new_swarm_id,
            config=body.config,
            performance_score=body.performance_score,
            pollen_points=body.pollen_points,
        )
        await db.commit()
        await db.refresh(row)
    except AgentCatalogError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected agent update.",
        )
    return await _to_agent_snapshot(db, row)


@router.post(
    "/{agent_id}/pause",
    response_model=AgentSnapshot,
    summary="Pause bee execution (marks worker as paused)",
)
async def pause_agent(agent_id: uuid.UUID, db: DbSession, _subject: JwtSubject) -> AgentSnapshot:
    """Operator guardrail — pause busy workers without losing swarm membership."""

    row = await fetch_agent(db, agent_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    try:
        await apply_agent_updates(
            db,
            row,
            status=AgentStatus.PAUSED,
            swarm_move=False,
            new_swarm_id=row.swarm_id,
            config=None,
            performance_score=None,
            pollen_points=None,
        )
        await db.commit()
        await db.refresh(row)
    except AgentCatalogError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected agent pause.",
        )
    return await _to_agent_snapshot(db, row)


@router.post(
    "/{agent_id}/resume",
    response_model=AgentSnapshot,
    summary="Resume paused bee",
)
async def resume_agent(agent_id: uuid.UUID, db: DbSession, _subject: JwtSubject) -> AgentSnapshot:
    """Return paused agents to idle so LangGraph supervisors can dispatch again."""

    row = await fetch_agent(db, agent_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    try:
        await apply_agent_updates(
            db,
            row,
            status=AgentStatus.IDLE,
            swarm_move=False,
            new_swarm_id=row.swarm_id,
            config=None,
            performance_score=None,
            pollen_points=None,
        )
        await db.commit()
        await db.refresh(row)
    except AgentCatalogError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected agent resume.",
        )
    return await _to_agent_snapshot(db, row)


__all__ = ["router"]
