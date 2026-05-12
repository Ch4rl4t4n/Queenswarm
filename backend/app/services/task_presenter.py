"""Map ORM backlog rows into API-facing task snapshots."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.task import Task
from app.schemas.task import TaskSnapshot


def confidence_from_task_result(result: dict[str, Any] | None) -> float | None:
    """Return a 0–1 confidence score derived from persisted ``Task.result`` JSON."""

    if not isinstance(result, dict):
        return None
    if "confidence_score" in result:
        try:
            v = float(result["confidence_score"])
        except (TypeError, ValueError):
            return None
        return v if 0 <= v <= 1 else max(0.0, min(1.0, v / 100.0))
    raw = result.get("confidence_pct")
    if raw is None:
        return None
    try:
        pct = float(raw)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, pct / 100.0))


def cost_usd_from_task_result(result: dict[str, Any] | None) -> float | None:
    """Return optional LLM/tool cost surfaced by executors."""

    if not isinstance(result, dict):
        return None
    raw = result.get("cost_usd")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def output_format_from_result(result: dict[str, Any] | None) -> str | None:
    """Infer output MIME-ish format label from executor payloads."""

    if not isinstance(result, dict):
        return None
    fmt = result.get("format")
    return str(fmt).lower().strip() if isinstance(fmt, str) and fmt.strip() else None


async def attach_agent_labels(session: AsyncSession, backlog: list[Task]) -> dict[uuid.UUID, str]:
    """Batch-resolve agent names for backlog rows."""

    ids = {row.agent_id for row in backlog if row.agent_id is not None}
    if not ids:
        return {}
    stmt = select(Agent.id, Agent.name).where(Agent.id.in_(ids))
    res = await session.execute(stmt)
    return dict(res.all())


def build_task_snapshot(row: Task, *, agent_label: str | None = None) -> TaskSnapshot:
    """Hydrate ``TaskSnapshot`` with optional cross-table enrichments."""

    result_dict = row.result if isinstance(row.result, dict) else None
    base = TaskSnapshot.model_validate(row)
    return base.model_copy(
        update={
            "agent_name": agent_label,
            "output_format": output_format_from_result(result_dict),
            "confidence_score": confidence_from_task_result(result_dict),
            "cost_usd": cost_usd_from_task_result(result_dict),
        },
    )


__all__ = [
    "attach_agent_labels",
    "build_task_snapshot",
    "confidence_from_task_result",
    "cost_usd_from_task_result",
    "output_format_from_result",
]
