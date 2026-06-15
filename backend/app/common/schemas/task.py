"""HTTP contracts for swarm task backlog rows."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.persistence.models.enums import TaskStatus, TaskType


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
    operator_note: str | None = Field(
        default=None,
        max_length=4000,
        description="Append an operator note to payload.operator_notes (mission kanban thread).",
    )
    title: str | None = Field(default=None, min_length=2, max_length=500)
    task_text: str | None = Field(
        default=None,
        max_length=20_000,
        description="Replace mission kanban triage prompt stored in payload.task_text.",
    )
    priority: int | None = Field(default=None, ge=1, le=99)


class TaskBulkCancelRequest(BaseModel):
    """Bulk soft-remove for mission kanban housekeeping (e.g. clear Done column)."""

    model_config = ConfigDict(extra="ignore")

    task_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=200)


class TaskBulkCancelResponse(BaseModel):
    """Summary of bulk cancel attempt."""

    model_config = ConfigDict(extra="ignore")

    cancelled: int = Field(ge=0)
    skipped_running: int = Field(ge=0)
    not_found: int = Field(ge=0)


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


class TaskLineageResponse(BaseModel):
    """Parent/children tree for mission kanban task drawer."""

    model_config = ConfigDict(extra="ignore")

    task: TaskSnapshot
    parent: TaskSnapshot | None = None
    children: list[TaskSnapshot] = Field(default_factory=list)
    goal_progress: dict[str, Any] | None = Field(
        default=None,
        description="AL3 supervisor-linked goal progress strip (when enabled).",
    )


class TaskWorkspaceFileOut(BaseModel):
    """Deliverable or archive file linked to a kanban task."""

    model_config = ConfigDict(extra="ignore")

    deliverable_id: uuid.UUID
    title: str
    slug: str
    archive_relpath: str | None = None
    preview: str = ""


class TaskWorkspaceResponse(BaseModel):
    """Workspace files for a mission kanban task drawer."""

    model_config = ConfigDict(extra="ignore")

    task_id: uuid.UUID
    files: list[TaskWorkspaceFileOut] = Field(default_factory=list)


__all__ = [
    "TaskBulkCancelRequest",
    "TaskBulkCancelResponse",
    "TaskCreateRequest",
    "TaskLineageResponse",
    "TaskPatchRequest",
    "TaskSnapshot",
    "TaskWorkspaceFileOut",
    "TaskWorkspaceResponse",
]
