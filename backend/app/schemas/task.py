"""HTTP contracts for swarm task backlog rows."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TaskStatus, TaskType


class TaskCreateRequest(BaseModel):
    """Operator intake for backlog items prior to breaker / LangGraph pickup."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    title: str = Field(..., min_length=2, max_length=500)
    task_type: TaskType = Field(..., description="Routing hint for scout/eval/sim actors.")
    priority: int = Field(default=5, ge=1, le=99)
    payload: dict[str, Any] = Field(default_factory=dict)
    swarm_id: uuid.UUID | None = None
    workflow_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None


class TaskPatchRequest(BaseModel):
    """Selective ledger updates surfaced to dashboards."""

    model_config = ConfigDict(extra="ignore")

    status: TaskStatus | None = None
    result: dict[str, Any] | None = None
    error_msg: str | None = Field(default=None, max_length=8000)


class TaskSnapshot(BaseModel):
    """Rounded projection mirrored from Postgres for API consumers."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: uuid.UUID
    title: str
    task_type: TaskType
    status: TaskStatus
    priority: int
    payload: dict[str, Any]
    result: dict[str, Any] | None = None
    agent_id: uuid.UUID | None = None
    swarm_id: uuid.UUID | None = None
    workflow_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None
    pollen_awarded: float = 0.0
    error_msg: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    agent_name: str | None = Field(
        default=None,
        description="Resolved bee display name when agent_id links to roster.",
    )
    output_format: str | None = Field(
        default=None,
        description="Executor output discriminator mirrored from ``result.format``.",
    )
    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Normalized 0–1 confidence when executor embeds telemetry in result.",
    )
    cost_usd: float | None = Field(
        default=None,
        description="Optional spend estimate when executor records ``cost_usd`` in result JSON.",
    )


__all__ = ["TaskCreateRequest", "TaskPatchRequest", "TaskSnapshot"]
