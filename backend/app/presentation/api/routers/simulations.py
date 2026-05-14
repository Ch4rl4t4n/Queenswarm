"""Simulation audit ledger (JWT guarded — ops + compliance)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from app.presentation.api.deps import DbSession, JwtSubject
from app.infrastructure.persistence.models.enums import SimulationResult
from app.common.schemas.simulations_audit import (
    SimulationAuditItem,
    SimulationCreateRequest,
    SimulationDetailItem,
)
from app.application.services.simulation_audit import (
    SimulationAuditError,
    create_simulation_record,
    fetch_simulation_audit,
    list_recent_simulation_audits,
)

router = APIRouter(tags=["Simulations"])


@router.get(
    "",
    response_model=list[SimulationAuditItem],
    summary="List recent simulation audit snapshots",
)
async def list_simulation_audits(
    db: DbSession,
    _subject: JwtSubject,
    task_id: uuid.UUID | None = Query(default=None, description="Filter by hive backlog lineage."),
    result_type: SimulationResult | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Return Postgres ``simulations`` rows newest-first."""

    try:
        rows = await list_recent_simulation_audits(
            db,
            task_id=task_id,
            result_type=result_type,
            limit=limit,
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected simulation audit query.",
        )
    return rows


@router.get(
    "/{simulation_id}",
    response_model=SimulationDetailItem,
    summary="Fetch a simulation audit record",
)
async def get_simulation_audit(
    simulation_id: uuid.UUID,
    db: DbSession,
    _subject: JwtSubject,
):
    """Return stdout/stderr-capable detail for compliance review."""

    try:
        row = await fetch_simulation_audit(db, simulation_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected simulation lookup.",
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found.")
    return row


@router.post(
    "",
    response_model=SimulationDetailItem,
    status_code=status.HTTP_201_CREATED,
    summary="Record a simulation audit entry",
)
async def create_simulation_audit(
    body: SimulationCreateRequest,
    db: DbSession,
    _subject: JwtSubject,
):
    """Create ledger metadata after Docker sandbox execution."""

    try:
        row = await create_simulation_record(
            db,
            task_id=body.task_id,
            scenario=dict(body.scenario),
            result_type=body.result_type,
            confidence_pct=body.confidence_pct,
            result_data=dict(body.result_data) if body.result_data is not None else None,
            docker_container_id=body.docker_container_id,
            duration_sec=body.duration_sec,
            stdout=body.stdout,
            stderr=body.stderr,
        )
        await db.commit()
        await db.refresh(row)
    except SimulationAuditError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected simulation insert.",
        )
    return row


__all__ = ["router"]
