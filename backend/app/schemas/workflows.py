"""Workflow HTTP contracts (Phase C — execution + detail projections)."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AgentRole, StepStatus, WorkflowStatus
from app.schemas.workflow_breaker import DecomposeWorkflowRequest

TaskDecomposeRequest = DecomposeWorkflowRequest  # Same as DecomposeWorkflowRequest (Phase C alias)

class WorkflowStepResponse(BaseModel):
    """Full breaker step payload including guardrails."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: uuid.UUID
    step_order: int
    description: str
    agent_role: AgentRole
    status: StepStatus
    guardrails: dict[str, Any]
    evaluation_criteria: dict[str, Any]
    result: dict[str, Any] | None = None
    error_msg: str | None = None


class WorkflowResponse(BaseModel):
    """Workflow list / summary view."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: uuid.UUID
    original_task_text: str
    status: WorkflowStatus
    total_steps: int
    completed_steps: int
    matching_recipe_id: uuid.UUID | None
    estimated_duration_sec: int | None
    actual_duration_sec: int | None


class WorkflowDetailResponse(WorkflowResponse):
    """Single workflow with ordered guardrailed steps."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    decomposition_rationale: str | None
    parallel_groups: list[list[int]] = Field(default_factory=list)
    steps: list[WorkflowStepResponse] = Field(default_factory=list)


class ExecutionResultResponse(BaseModel):
    """End-to-end executor summary (simulation + evaluation aggregate)."""

    model_config = ConfigDict(extra="ignore")

    workflow_id: uuid.UUID
    success: bool
    total_pollen_earned: float
    step_results: list[dict[str, Any]]
    error_msg: str | None = None


__all__ = [
    "ExecutionResultResponse",
    "TaskDecomposeRequest",
    "WorkflowDetailResponse",
    "WorkflowResponse",
    "WorkflowStepResponse",
]
