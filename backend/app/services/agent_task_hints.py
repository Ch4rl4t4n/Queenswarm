"""Projection helpers tagging agents with lightweight backlog cues."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TaskStatus
from app.models.task import Task


async def latest_open_tasks_for_agents(
    session: AsyncSession,
    agent_ids: list[uuid.UUID],
) -> dict[uuid.UUID, Task]:
    """Map each busy agent id to its most recently updated pending/running task."""

    trimmed = sorted({agent_id for agent_id in agent_ids if agent_id is not None})
    if not trimmed:
        return {}

    statuses = {TaskStatus.PENDING, TaskStatus.RUNNING}
    stmt = (
        select(Task).where(Task.agent_id.in_(trimmed), Task.status.in_(statuses)).order_by(Task.updated_at.desc())
    )
    rows = await session.scalars(stmt)
    picks: dict[uuid.UUID, Task] = {}
    for row in rows:
        aid = row.agent_id
        if aid is None or aid in picks:
            continue
        picks[aid] = row
    return picks


__all__ = ["latest_open_tasks_for_agents"]
