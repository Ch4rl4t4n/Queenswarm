"""Aggregated telemetry for simplified hive dashboards."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.presentation.api.deps import DbSession, JwtSubject
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.agent_config import AgentConfig
from app.infrastructure.persistence.models.enums import TaskStatus
from app.infrastructure.persistence.models.task import Task
from app.application.services.dashboard_swarm_board import build_swarm_board_payload
from app.application.services.dashboard_task_queue import build_task_queue_payload
from app.application.services.dashboard_workflows import build_workflows_dashboard_payload
from app.application.services.hive_tier import resolve_hive_tier

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def dashboard_summary(db: DbSession, _subject: JwtSubject) -> dict[str, object]:
    """Return minimal counts grouped by hive tier plus task backlog."""

    agent_total = await db.scalar(select(func.count()).select_from(Agent))

    stmt_agents_cfg = (
        select(Agent, AgentConfig)
        .outerjoin(AgentConfig, AgentConfig.agent_id == Agent.id)
    )
    rows = (await db.execute(stmt_agents_cfg)).all()

    by_hive_tier: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for agent_row, cfg_row in rows:
        tier_bucket = resolve_hive_tier(agent=agent_row, agent_config=cfg_row) or "unknown"
        by_hive_tier[tier_bucket] = by_hive_tier.get(tier_bucket, 0) + 1
        stat = getattr(agent_row.status, "value", str(agent_row.status))
        by_status[stat] = by_status.get(stat, 0) + 1

    tasks_pending = await db.scalar(
        select(func.count()).select_from(Task).where(Task.status == TaskStatus.PENDING),
    )

    now = datetime.now(tz=UTC)

    return {
        "generated_at": now.isoformat(),
        "agents": {
            "total": int(agent_total or 0),
            "by_status": by_status,
            "by_hive_tier": by_hive_tier,
        },
        "tasks": {
            "pending": int(tasks_pending or 0),
        },
    }


@router.get("/task-queue")
async def dashboard_task_queue(
    db: DbSession,
    _subject: JwtSubject,
    limit: int = Query(default=100, ge=1, le=200),
) -> dict[str, object]:
    """Backlog queue with workflow step progress for operator task boards."""

    return await build_task_queue_payload(db, list_limit=limit)


@router.get("/workflows")
async def dashboard_workflows(
    db: DbSession,
    _subject: JwtSubject,
    limit: int = Query(default=50, ge=1, le=100),
    focus: uuid.UUID | None = Query(
        default=None,
        description="Pin this workflow as the featured DAG card when present.",
    ),
) -> dict[str, object]:
    """Featured workflow DAG plus recent workflow rows for operator boards."""

    return await build_workflows_dashboard_payload(
        db,
        list_limit=limit,
        focus_workflow_id=focus,
    )


@router.get("/swarm-board")
async def dashboard_swarm_board(db: DbSession, _subject: JwtSubject) -> dict[str, object]:
    """Sub-swarm telemetry cards and cross-swarm task handoff feed for operator UI."""

    return await build_swarm_board_payload(db)


__all__ = ["router"]
