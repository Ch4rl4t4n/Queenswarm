"""Simulation audit ledger (JWT guarded — ops + compliance)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession, JwtSubject
from app.models.enums import SimulationResult
from app.schemas.simulations_audit import SimulationAuditItem
from app.services.simulation_audit import list_recent_simulation_audits

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


__all__ = ["router"]
