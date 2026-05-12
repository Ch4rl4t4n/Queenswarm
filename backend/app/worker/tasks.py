"""Declarative Celery tasks backing the bee-hive rapid loop (off the HTTP path)."""

from __future__ import annotations

import asyncio
import traceback
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.agents.executor import execute_universal_agent, mark_task_failed
from app.agents.scheduler import should_run_dynamic_agent
from app.core.database import async_session
from app.core.metrics import observe_hourly_roll_tick
from app.services.agent_universal import enqueue_universal_agent_run
from app.services.hive_async_workflow_run_ledger import (
    finalize_failed_hive_async_workflow_run,
    finalize_successful_hive_async_workflow_run,
)
from app.models.agent import Agent
from app.models.agent_config import AgentConfig
from app.models.enums import AgentStatus, TaskType
from app.models.task import Task
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


async def _mark_universal_failure(task_id_str: str, message: str) -> None:
    """Persist terminal failure state for operator dashboards."""

    async with async_session() as session:
        await mark_task_failed(session, uuid.UUID(task_id_str), message)
        await session.commit()


@celery_app.task(name="agent.execute_universal", bind=True, max_retries=3, queue="hive")
def execute_universal_agent_task(self, task_id_str: str) -> dict[str, Any]:
    """Load ``Task.payload`` JSON and feed the universal executor."""

    async def _run() -> dict[str, Any]:
        task_uuid = uuid.UUID(task_id_str)
        async with async_session() as session:
            row = await session.get(Task, task_uuid)
            if row is None:
                msg = f"Missing task row {task_id_str}"
                raise RuntimeError(msg)
            if row.task_type != TaskType.AGENT_RUN:
                msg = f"Task {task_id_str} is not agent_run"
                raise RuntimeError(msg)
            agent_payload = dict(row.payload or {})
            if row.agent_id is not None:
                agent_payload.setdefault("agent_id", str(row.agent_id))
            snapshot = await execute_universal_agent(
                session,
                agent_config=agent_payload,
                task_id=task_uuid,
            )
            agent_uuid = uuid.UUID(str(agent_payload.get("agent_id") or row.agent_id))
            cfg_row = await session.scalar(select(AgentConfig).where(AgentConfig.agent_id == agent_uuid))
            if cfg_row is not None:
                cfg_row.last_run_at = datetime.now(tz=UTC)
                cfg_row.run_count = int(cfg_row.run_count or 0) + 1
                cfg_row.last_run_result = {
                    "preview": snapshot.get("output_preview", ""),
                    "status": "completed",
                }
            agent_row = await session.get(Agent, agent_uuid)
            if agent_row is not None:
                agent_row.pollen_points = float(agent_row.pollen_points or 0.0) + 10.0
                agent_row.status = AgentStatus.IDLE
            await session.commit()
            return snapshot

    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001 — Celery coordinates retries
        retries = int(getattr(self.request, "retries", 0) or 0)
        max_r = 3
        if retries >= max_r:
            try:
                asyncio.run(_mark_universal_failure(task_id_str, str(exc)))
            except Exception:
                pass
            raise
        raise self.retry(exc=exc, countdown=60 * (retries + 1))


@celery_app.task(name="hive.dynamic_agent_schedule_tick", queue="hive")
def dynamic_agent_schedule_tick_task() -> dict[str, Any]:
    """Scan ``AgentConfig`` rows and enqueue due universal runs."""

    async def _tick() -> dict[str, int]:
        queued = 0
        inspected = 0
        skipped_dup = 0
        async with async_session() as session:
            result = await session.execute(select(AgentConfig).where(AgentConfig.is_active.is_(True)))
            configs = list(result.scalars().all())
            for cfg in configs:
                inspected += 1
                if not should_run_dynamic_agent(cfg):
                    continue
                agent = await session.get(Agent, cfg.agent_id)
                if agent is None:
                    continue
                if agent.status == AgentStatus.PAUSED:
                    continue
                try:
                    backlog = await enqueue_universal_agent_run(
                        session,
                        agent=agent,
                        cfg=cfg,
                        title=f"{agent.name} — scheduled hive pulse",
                        priority=8,
                        guard_duplicates=True,
                    )
                    await session.commit()
                    execute_universal_agent_task.delay(str(backlog.id))
                    queued += 1
                except ValueError:
                    await session.rollback()
                    skipped_dup += 1
        return {"queued": queued, "inspected": inspected, "skipped_duplicates": skipped_dup}

    return asyncio.run(_tick())


__all__ = [
    "dynamic_agent_schedule_tick_task",
    "echo_hive_pulse",
    "execute_universal_agent_task",
    "hourly_youtube_crypto_roll_task",
    "run_sub_swarm_workflow_cycle_task",
]