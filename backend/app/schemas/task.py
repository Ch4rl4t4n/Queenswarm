"""HTTP contracts for swarm task backlog rows."""

from __future__ import annotations

import uuid
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


__all__ = ["TaskCreateRequest", "TaskPatchRequest", "TaskSnapshot"]
