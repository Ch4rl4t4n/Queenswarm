"""HTTP contracts for autonomous bee agents."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AgentRole, AgentStatus, SwarmPurpose


class AgentCreateRequest(BaseModel):
    """Register a new worker bee, optionally attaching to a sub-swarm."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(..., min_length=2, max_length=100)
    role: AgentRole
    status: AgentStatus = AgentStatus.IDLE
    swarm_id: uuid.UUID | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class AgentPatchRequest(BaseModel):
    """Operator or supervisor updates to placement and telemetry."""

    model_config = ConfigDict(extra="ignore")

    status: AgentStatus | None = None
    swarm_id: uuid.UUID | None = Field(
        default=None,
        description="When set (and detach_from_swarm is false), re-home the bee to this swarm.",
    )
    detach_from_swarm: bool = Field(
        default=False,
        description="When true, clears swarm membership (ignores swarm_id).",
    )
    config: dict[str, Any] | None = None
    performance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    pollen_points: float | None = Field(default=None, ge=0.0, le=1_000_000.0)


class AgentSnapshot(BaseModel):
    """Postgres-backed agent row for dashboards and imitation engines."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: uuid.UUID
    name: str
    role: AgentRole
    status: AgentStatus
    swarm_id: uuid.UUID | None
    swarm_name: str | None = Field(
        default=None,
        description="Owning sub-swarm display name after join (omit when unassigned).",
    )
    swarm_purpose: SwarmPurpose | None = Field(
        default=None,
        description="Colony lane discriminator when swarm_id anchors a SubSwarm row.",
    )
    config: dict[str, Any]
    pollen_points: float
    performance_score: float
    last_synced_at: datetime | None
    last_active_at: datetime | None
    created_at: datetime
    updated_at: datetime
    current_task_id: uuid.UUID | None = None
    current_task_title: str | None = Field(
        default=None,
        description="Most recent routed backlog hint for dashboards.",
    )
    has_universal_config: bool = Field(
        default=False,
        description="True when a persisted AgentConfig row exists for this bee.",
    )
    hive_tier: str | None = Field(
        default=None,
        description="orchestrator | manager | worker | None for legacy rows without ``output_config.hive_tier``.",
    )


__all__ = ["AgentCreateRequest", "AgentPatchRequest", "AgentSnapshot"]
