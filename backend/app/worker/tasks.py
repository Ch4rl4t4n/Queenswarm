"""Declarative Celery tasks backing the bee-hive rapid loop (off the HTTP path)."""

from __future__ import annotations

import asyncio
import traceback
import uuid
from typing import Any

from app.core.database import async_session
from app.core.metrics import observe_hourly_roll_tick
from app.services.hive_async_workflow_run_ledger import (
    finalize_failed_hive_async_workflow_run,
    finalize_successful_hive_async_workflow_run,
)
from app.services.sub_swarm.runner import run_sub_swarm_workflow_cycle
from app.worker.celery_app import celery_app


@celery_app.task(name="hive.hourly_youtube_crypto_roll")
def hourly_youtube_crypto_roll_task() -> dict[str, str]:
    """Queue a deterministic mock scrape backlog row for crypto YouTube ingest."""

    async def _queue() -> str:
        async with async_session() as session:
            from sqlalchemy import select

            from app.models.enums import TaskType
            from app.models.swarm import SubSwarm
            from app.models.task import Task
            from app.services.task_ledger import create_task_record

            scout = await session.scalar(select(SubSwarm).where(SubSwarm.name == "colony-scout"))
            if scout is None:
                return "no_scout_swarm_seed_first"
            title = "Hourly YouTube crypto pulse (Celery)"
            exists = await session.scalar(select(Task).where(Task.title == title))
            if exists:
                await session.commit()
                observe_hourly_roll_tick()
                return "task_exists"
            await create_task_record(
                session,
                title=title,
                task_type_value=TaskType.SCRAPE,
                priority=2,
                payload={"source": "youtube", "topic": "crypto", "producer": "celery_hourly_stub"},
                swarm_id=scout.id,
                workflow_id=None,
                parent_task_id=None,
            )
            await session.commit()
            observe_hourly_roll_tick()
            return "queued"

    return {"status": asyncio.run(_queue())}


@celery_app.task(name="hive.echo_pulse")
def echo_hive_pulse(signal: str) -> str:
    """Lightweight connectivity probe for worker ↔ broker ↔ result backend.

    Args:
        signal: Arbitrary correlator from an operator or CI smoke check.

    Returns:
        Echo string proving the task executed on a worker process.
    """

    cleaned = signal.strip() or "silent"
    return f"pong:{cleaned}"


@celery_app.task(name="hive.run_sub_swarm_workflow")
def run_sub_swarm_workflow_cycle_task(
    *,
    swarm_id: str,
    workflow_id: str,
    task_id: str | None = None,
    payload: dict[str, Any] | None = None,
    ledger_tracking_id: str | None = None,
) -> dict[str, Any]:
    """Execute :func:`run_sub_swarm_workflow_cycle` inside a dedicated worker process."""

    async def _execute_graph() -> dict[str, Any]:
        async with async_session() as session:
            try:
                outcome = await run_sub_swarm_workflow_cycle(
                    session,
                    swarm_id=uuid.UUID(swarm_id),
                    workflow_id=uuid.UUID(workflow_id),
                    task_id=uuid.UUID(task_id) if task_id else None,
                    payload=dict(payload or {}),
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            return outcome.model_dump(mode="json")

    async def _persist_ledger(snapshot: dict[str, Any] | None, error_blob: str | None) -> None:
        if ledger_tracking_id is None:
            return

        async with async_session() as ledger_session:
            try:
                if snapshot is not None:
                    await finalize_successful_hive_async_workflow_run(
                        ledger_session,
                        celery_task_id=ledger_tracking_id,
                        result_snapshot=snapshot,
                    )
                else:
                    await finalize_failed_hive_async_workflow_run(
                        ledger_session,
                        celery_task_id=ledger_tracking_id,
                        error_text=error_blob or "unknown_failure",
                    )
                await ledger_session.commit()
            except Exception:
                await ledger_session.rollback()

    graph_exc: BaseException | None = None
    try:
        snapshot = asyncio.run(_execute_graph())
    except BaseException as exc:
        graph_exc = exc

    error_blob: str | None = None
    if graph_exc is not None:
        error_blob = f"{graph_exc!s}\n{traceback.format_exc()}"

    asyncio.run(
        _persist_ledger(
            snapshot=snapshot if graph_exc is None else None,
            error_blob=error_blob,
        ),
    )

    if graph_exc is not None:
        raise graph_exc

    if snapshot is None:
        raise RuntimeError("hive.run_sub_swarm_workflow yielded empty snapshot")
    return snapshot


__all__ = [
    "echo_hive_pulse",
    "hourly_youtube_crypto_roll_task",
    "run_sub_swarm_workflow_cycle_task",
]
