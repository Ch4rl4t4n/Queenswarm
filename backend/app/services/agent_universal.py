"""Queue + payload helpers for the universal bee executor."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.agent_config import AgentConfig
from app.models.enums import TaskStatus, TaskType
from app.models.task import Task
from app.schemas.agent_factory_http import UniversalAgentRunOverlay
from app.services.task_ledger import create_task_record


def universal_execution_payload(agent: Agent, cfg: AgentConfig | None) -> dict[str, Any]:
    """Serialize ORM rows into Celery-compatible JSON payloads."""

    if cfg is None:
        merged_output: dict[str, Any] = {}
        return {
            "agent_id": str(agent.id),
            "name": agent.name,
            "system_prompt": "You are a helpful AI agent. Report what you find.",
            "user_prompt_template": "Execute your configured mission now.",
            "tools": [],
            "output_format": "markdown",
            "output_destination": "dashboard",
            "output_config": merged_output,
        }
    merged_output = dict(cfg.output_config or {})
    return {
        "agent_id": str(agent.id),
        "name": agent.name,
        "system_prompt": cfg.system_prompt,
        "user_prompt_template": cfg.user_prompt_template or "Execute your task now.",
        "tools": cfg.tools or [],
        "output_format": cfg.output_format or "text",
        "output_destination": cfg.output_destination or "dashboard",
        "output_config": merged_output,
    }


async def has_recent_duplicate_run(session: AsyncSession, *, agent_id: uuid.UUID) -> bool:
    """Throttle scheduled ticks so we avoid double-queueing inside the Celery drift window."""

    gate = datetime.now(tz=UTC)
    from datetime import timedelta

    window = timedelta(minutes=2)
    cutoff = gate - window
    stmt = (
        select(Task.id)
        .where(Task.agent_id == agent_id)
        .where(Task.task_type == TaskType.AGENT_RUN)
        .where(Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING]))
        .where(Task.created_at >= cutoff)
        .limit(1)
    )
    hit = await session.scalar(stmt)
    return hit is not None


async def enqueue_universal_agent_run(
    session: AsyncSession,
    *,
    agent: Agent,
    cfg: AgentConfig | None,
    title: str,
    priority: int = 6,
    guard_duplicates: bool = False,
    overlay: UniversalAgentRunOverlay | None = None,
) -> Task:
    """Create a backlog row marked ``agent_run`` and return it after flush."""

    if guard_duplicates and await has_recent_duplicate_run(session, agent_id=agent.id):
        msg = "An agent_run task is already pending for this bee."
        raise ValueError(msg)

    payload_snapshot = universal_execution_payload(agent, cfg)
    payload = dict(payload_snapshot)
    if overlay is not None:
        for field, val in overlay.model_dump(exclude_unset=True).items():
            if val is None:
                continue
            payload[field] = val

    row = await create_task_record(
        session,
        title=title,
        task_type_value=TaskType.AGENT_RUN,
        priority=priority,
        payload=payload,
        swarm_id=agent.swarm_id,
        workflow_id=None,
        parent_task_id=None,
    )
    await session.flush()
    row.agent_id = agent.id
    row.status = TaskStatus.PENDING
    await session.flush()
    return row


__all__ = [
    "enqueue_universal_agent_run",
    "has_recent_duplicate_run",
    "universal_execution_payload",
]
