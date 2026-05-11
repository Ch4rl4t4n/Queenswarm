"""Sub-swarm LangGraph supervisors (JWT guarded)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession, JwtSubject
from app.core.config import settings
from app.schemas.sub_swarm import (
    GlobalHiveSyncAck,
    RunWorkflowOnSwarmQueuedResponse,
    RunWorkflowOnSwarmRequest,
    RunWorkflowOnSwarmResponse,
)
from app.services.hive_async_workflow_run_ledger import enqueue_hive_async_workflow_run
from app.services.hive_sync import mark_sub_swarm_globally_synced
from app.services.sub_swarm.runner import run_sub_swarm_workflow_cycle

router = APIRouter(tags=["Swarms"])

_ERROR_HTTP_MAP: dict[str, int] = {
    "missing_session": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "swarm_not_found": status.HTTP_404_NOT_FOUND,
    "workflow_not_found": status.HTTP_404_NOT_FOUND,
    "task_not_found": status.HTTP_404_NOT_FOUND,
    "no_agents": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "task_swarm_mismatch": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "routing_failed": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "invalid_workflow_plan": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "budget_exceeded": status.HTTP_429_TOO_MANY_REQUESTS,
    "step_timeout": status.HTTP_504_GATEWAY_TIMEOUT,
}


@router.post(
    "/{swarm_id}/workflows/{workflow_id}/run",
    response_model=None,
    responses={
        200: {
            "model": RunWorkflowOnSwarmResponse,
            "description": "Executed inline inside the API process.",
        },
        202: {
            "model": RunWorkflowOnSwarmQueuedResponse,
            "description": "Handed off to Celery hive workers.",
        },
    },
    summary="Execute a breaker workflow inside a single sub-swarm colony",
)
async def run_workflow_through_sub_swarm(
    swarm_id: uuid.UUID,
    workflow_id: uuid.UUID,
    body: RunWorkflowOnSwarmRequest,
    db: DbSession,
    _subject: JwtSubject,
):
    """Materialize breaker steps locally, invoke bees, broadcast waggle telemetry."""

    if body.defer_to_worker:
        if not settings.celery_workflow_runs_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Celery workflow runs are disabled for this hive.",
            )
        from app.worker.tasks import run_sub_swarm_workflow_cycle_task

        task_key = str(uuid.uuid4())
        try:
            await enqueue_hive_async_workflow_run(
                db,
                celery_task_id=task_key,
                swarm_id=swarm_id,
                workflow_id=workflow_id,
                hive_task_id=body.task_id,
                requested_by_subject=_subject,
            )
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not persist hive async workflow ledger row.",
            )

        run_sub_swarm_workflow_cycle_task.apply_async(
            kwargs={
                "swarm_id": str(swarm_id),
                "workflow_id": str(workflow_id),
                "task_id": str(body.task_id) if body.task_id else None,
                "payload": body.payload,
                "ledger_tracking_id": task_key,
            },
            task_id=task_key,
        )

        ack = RunWorkflowOnSwarmQueuedResponse(
            swarm_id=swarm_id,
            workflow_id=workflow_id,
            task_id=body.task_id,
            celery_task_id=task_key,
        )
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=ack.model_dump(mode="json"))

    try:
        result = await run_sub_swarm_workflow_cycle(
            db,
            swarm_id=swarm_id,
            workflow_id=workflow_id,
            task_id=body.task_id,
            payload=body.payload,
        )
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence layer rejected swarm execution.",
        )

    if not result.ok:
        code = result.error_code or "unknown_error"
        status_code = _ERROR_HTTP_MAP.get(code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        raise HTTPException(
            status_code=status_code,
            detail={
                "code": code,
                "detail": result.error_detail,
                "traces": result.traces,
            },
        )
    return result


@router.post(
    "/{swarm_id}/global-sync",
    response_model=GlobalHiveSyncAck,
    summary="Record a global hive-mind synchronization checkpoint",
)
async def acknowledge_global_hive_sync(
    swarm_id: uuid.UUID,
    db: DbSession,
    _subject: JwtSubject,
) -> GlobalHiveSyncAck:
    """Stamp UTC ``last_global_sync_at`` after a colony merges with global state."""

    try:
        stamped = await mark_sub_swarm_globally_synced(db, swarm_id=swarm_id)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence layer rejected hive sync stamp.",
        )
    if stamped is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown sub-swarm identifier.",
        )
    sid, synced_at = stamped
    return GlobalHiveSyncAck(swarm_id=sid, last_global_sync_at=synced_at)


__all__ = ["router"]
