"""Poll Celery result backend for deferred swarm workflow runs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession, JwtSubject
from app.core.logging import get_logger
from app.models.hive_async_workflow_run import HiveAsyncWorkflowRun
from app.schemas.hive_jobs import HiveAsyncJobStatusResponse, HivePostgresLedgerBrief
from app.services.hive_async_workflow_run_ledger import fetch_hive_async_workflow_run
from app.worker.celery_app import celery_app

router = APIRouter(tags=["Hive jobs"])
logger = get_logger(__name__)


def _brief_from_row(row: HiveAsyncWorkflowRun | None) -> HivePostgresLedgerBrief | None:
    """Map ORM hive ledger row into a transport-friendly projection."""

    if row is None:
        return None
    err_txt = row.error_text
    preview = None
    if isinstance(err_txt, str) and err_txt.strip():
        preview = err_txt.strip().split("\n", 1)[0][:500]

    return HivePostgresLedgerBrief(
        id=row.id,
        swarm_id=row.swarm_id,
        workflow_id=row.workflow_id,
        hive_task_id=row.hive_task_id,
        lifecycle=row.lifecycle.value,
        created_at=row.created_at,
        updated_at=row.updated_at,
        finished_at=row.finished_at,
        error_preview=preview,
    )


@router.get(
    "/{celery_task_id}",
    response_model=HiveAsyncJobStatusResponse,
    summary="Poll a deferred swarm workflow job",
)
async def get_hive_async_job_snapshot(
    celery_task_id: str,
    db: DbSession,
    _subject: JwtSubject,
) -> HiveAsyncJobStatusResponse:
    """Return Celery AsyncResult telemetry mirrored with optional Postgres audit rows."""

    try:
        row = await fetch_hive_async_workflow_run(db, celery_task_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ledger lookup failed.",
        )

    postgres_ledger = _brief_from_row(row)

    async_result = celery_app.AsyncResult(celery_task_id)
    state = async_result.state
    ready = async_result.ready()
    successful = async_result.successful() if ready else None
    workflow_result: dict | None = None
    err: str | None = None

    if successful is True:
        raw = async_result.result
        if isinstance(raw, dict):
            workflow_result = raw
        else:
            err = f"Unexpected result payload type: {type(raw).__name__}"
    elif successful is False:
        try:
            maybe_exc = async_result.result
            err = repr(maybe_exc) if maybe_exc is not None else "Celery reported failure without details."
        except Exception as exc:  # noqa: BLE001 — surface broker oddities
            err = f"Could not read failure payload: {exc!s}"

    logger.info(
        "hive_job.poll",
        celery_task_id=celery_task_id,
        state=state,
        ready=ready,
        successful=successful,
        ledger_lifecycle=postgres_ledger.lifecycle if postgres_ledger else None,
    )
    return HiveAsyncJobStatusResponse(
        celery_task_id=celery_task_id,
        state=state,
        ready=ready,
        successful=successful,
        workflow_result=workflow_result,
        error=err,
        postgres_ledger=postgres_ledger,
    )


__all__ = ["router"]
