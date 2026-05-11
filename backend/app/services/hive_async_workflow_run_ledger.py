"""Postgres bookkeeping for Celery-backed swarm LangGraph executions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import HiveAsyncRunLifecycle
from app.models.hive_async_workflow_run import HiveAsyncWorkflowRun


async def enqueue_hive_async_workflow_run(
    session: AsyncSession,
    *,
    celery_task_id: str,
    swarm_id: uuid.UUID,
    workflow_id: uuid.UUID,
    hive_task_id: uuid.UUID | None,
    requested_by_subject: str | None,
) -> HiveAsyncWorkflowRun:
    """Insert a queued audit row keyed by deterministic Celery task id."""

    row = HiveAsyncWorkflowRun(
        celery_task_id=celery_task_id,
        swarm_id=swarm_id,
        workflow_id=workflow_id,
        hive_task_id=hive_task_id,
        requested_by_subject=requested_by_subject,
        lifecycle=HiveAsyncRunLifecycle.QUEUED,
    )
    session.add(row)
    await session.flush()
    return row


async def finalize_successful_hive_async_workflow_run(
    session: AsyncSession,
    *,
    celery_task_id: str,
    result_snapshot: dict[str, Any],
) -> HiveAsyncWorkflowRun | None:
    """Mark ledger succeeded and stash the sanitized API-shaped snapshot."""

    row = await _load_run(session, celery_task_id)
    if row is None:
        return None

    ts = datetime.now(tz=UTC)
    row.lifecycle = HiveAsyncRunLifecycle.SUCCEEDED
    row.result_snapshot = result_snapshot
    row.error_text = None
    row.finished_at = ts
    await session.flush()
    return row


async def finalize_failed_hive_async_workflow_run(
    session: AsyncSession,
    *,
    celery_task_id: str,
    error_text: str,
) -> HiveAsyncWorkflowRun | None:
    """Mark ledger failures from worker-visible exceptions."""

    row = await _load_run(session, celery_task_id)
    if row is None:
        return None

    ts = datetime.now(tz=UTC)
    row.lifecycle = HiveAsyncRunLifecycle.FAILED
    row.error_text = error_text[:8000]
    row.result_snapshot = None
    row.finished_at = ts
    await session.flush()
    return row


async def fetch_hive_async_workflow_run(
    session: AsyncSession,
    celery_task_id: str,
) -> HiveAsyncWorkflowRun | None:
    """Return audit row for poll endpoints + dashboards."""

    return await _load_run(session, celery_task_id)


async def _load_run(session: AsyncSession, celery_task_id: str) -> HiveAsyncWorkflowRun | None:
    stmt = select(HiveAsyncWorkflowRun).where(HiveAsyncWorkflowRun.celery_task_id == celery_task_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


__all__ = [
    "enqueue_hive_async_workflow_run",
    "fetch_hive_async_workflow_run",
    "finalize_failed_hive_async_workflow_run",
    "finalize_successful_hive_async_workflow_run",
]
