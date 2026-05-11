"""Autonomous bee registry (JWT guarded)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.deps import DbSession, JwtSubject
from app.models.enums import AgentRole, AgentStatus
from app.schemas.agent import AgentCreateRequest, AgentPatchRequest, AgentSnapshot
from app.services.agent_catalog import (
    AgentCatalogError,
    apply_agent_updates,
    create_agent_record,
    fetch_agent,
    list_agents,
)

router = APIRouter(tags=["Agents"])


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
    return row


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
    return rows


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
    return row


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
    return row


__all__ = ["router"]
