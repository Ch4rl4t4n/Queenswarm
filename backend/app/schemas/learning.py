"""HTTP contracts for Phase E Learning Engine surface."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AgentRole


class ReflectionCreate(BaseModel):
    """Operator or bee reflection for LearningLog persistence."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    agent_id: uuid.UUID
    insight: str = Field(min_length=4, max_length=20_000)
    task_id: uuid.UUID | None = None
    pollen_earned: float = Field(default=0.0, ge=0.0)


class RewardSignal(BaseModel):
    """Per-agent signal used for Maynard-Cross weighting."""

    model_config = ConfigDict(extra="ignore")

    agent_id: uuid.UUID
    signal: float = Field(ge=0.0, default=0.0, description="Confidence or fitness hint.")


class PollenAllocateRequest(BaseModel):
    """Partition a pollen pool with optional performance blend."""

    model_config = ConfigDict(extra="ignore")

    pool: float = Field(gt=0.0, le=1_000_000.0)
    task_id: uuid.UUID | None = None
    signals: list[RewardSignal] = Field(min_length=1)
    reason: str = Field(
        default="Maynard-Cross hive allocation",
        max_length=500,
    )
    blend_performance: bool = Field(
        default=True,
        description="When true, fuse signals with ``Agent.performance_score`` + pollen.",
    )


class PollenAllocateResponse(BaseModel):
    """Grant summary."""

    model_config = ConfigDict(extra="ignore")

    credited_agents: int
    allocations: dict[str, float]


class ExemplarBrief(BaseModel):
    """Imitation neighbor row."""

    model_config = ConfigDict(extra="ignore")

    agent_id: uuid.UUID
    name: str
    role: AgentRole
    performance_score: float
    pollen_points: float


class ImitationCopyRequest(BaseModel):
    """Explicit imitation edge for analytics."""

    model_config = ConfigDict(extra="ignore")

    copier_agent_id: uuid.UUID
    exemplar_agent_id: uuid.UUID
    recipe_id: uuid.UUID | None = None


class TaskReflectionRequest(BaseModel):
    """Structured rapid-loop reflection after LangGraph/task execution."""

    model_config = ConfigDict(extra="ignore")

    agent_id: uuid.UUID
    task_id: uuid.UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    outcome: str = Field(min_length=1, max_length=200)
    verified: bool = False
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class RecipeAutosaveRequest(BaseModel):
    """Alias around :class:`~app.schemas.recipes_write.RecipeCreateBody` fields."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    topic_tags: list[str] = Field(default_factory=list)
    workflow_template: dict[str, Any]
    created_by_agent_id: uuid.UUID | None = None
    mark_verified: bool = True


__all__ = [
    "ExemplarBrief",
    "ImitationCopyRequest",
    "PollenAllocateRequest",
    "PollenAllocateResponse",
    "RecipeAutosaveRequest",
    "ReflectionCreate",
    "RewardSignal",
    "TaskReflectionRequest",
]
