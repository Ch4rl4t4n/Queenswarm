"""Autonomous bee registry (JWT guarded)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.deps import DbSession, JwtSubject
from app.models.agent import Agent
from app.models.enums import AgentRole, AgentStatus
from app.schemas.agent import AgentCreateRequest, AgentPatchRequest, AgentSnapshot
from app.services.agent_catalog import (
    AgentCatalogError,
    apply_agent_updates,
    create_agent_record,
    fetch_agent,
    list_agents,
)
from app.services.agent_task_hints import latest_open_tasks_for_agents

router = APIRouter(tags=["Agents"])


async def _to_agent_snapshot(db: DbSession, row: Agent) -> AgentSnapshot:
    """Attach the newest pending/running backlog row for dashboard context."""

    hints = await latest_open_tasks_for_agents(db, [row.id])
    linked = hints.get(row.id)
    base = AgentSnapshot.model_validate(row)
    return base.model_copy(
        update={
            "current_task_id": linked.id if linked else None,
            "current_task_title": linked.title if linked else None,
        },
    )


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
    """Create an agent row and optionally attach it to an existing sub-swarm."""

    try:
        row = await create_agent_record(
            db,
            name=body.name,
            role=body.role,
            status=body.status,
            swarm_id=body.swarm_id,
            config=dict(body.config),
        )
        await db.commit()
        await db.refresh(row)
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
            detail="Persistence rejected agent insert.",
        )
    return await _to_agent_snapshot(db, row)


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
    snapshots: list[AgentSnapshot] = []
    for row in rows:
        linked = hints.get(row.id)
        base = AgentSnapshot.model_validate(row)
        snapshots.append(
            base.model_copy(
                update={
                    "current_task_id": linked.id if linked else None,
                    "current_task_title": linked.title if linked else None,
                },
            ),
        )
    return snapshots


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
