"""HTTP contracts for tracer-bullet vertical slices mapped to Kanban backlog rows."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.common.schemas.task import TaskSnapshot


class SliceToKanbanRequest(BaseModel):
    """Operator request to materialize workflow steps as child backlog slices."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    swarm_id: uuid.UUID | None = Field(
        default=None,
        description="Optional swarm anchor; inferred from existing workflow task when omitted.",
    )
    parent_title: str | None = Field(
        default=None,
        min_length=2,
        max_length=500,
        description="Override parent Kanban row title (defaults to workflow task text).",
    )
    priority: int = Field(default=5, ge=1, le=99)
    force_reslice: bool = Field(
        default=False,
        description="When True, recreate child slices even if a prior slice set exists.",
    )


class SliceToKanbanResponse(BaseModel):
    """Confirmation payload after workflow steps land as Kanban vertical slices."""

    model_config = ConfigDict(extra="ignore")

    workflow_id: uuid.UUID
    parent_task_id: uuid.UUID
    slice_count: int
    idempotent_reuse: bool = Field(
        default=False,
        description="True when an existing slice set was returned without mutation.",
    )
    parent: TaskSnapshot
    slices: list[TaskSnapshot]


__all__ = ["SliceToKanbanRequest", "SliceToKanbanResponse"]
