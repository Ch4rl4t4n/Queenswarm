"""HTTP contracts for UI-defined universal agents."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AgentStatus


class AgentDynamicCreate(BaseModel):
    """Create a swarm bee row plus persisted universal executor instructions."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(..., min_length=2, max_length=100)
    swarm_id: uuid.UUID | None = None
    system_prompt: str = Field(default="You are a helpful AI agent.", min_length=1)
    user_prompt_template: str | None = Field(default=None, max_length=20_000)
    tools: list[Any] = Field(default_factory=list)
    output_format: str = Field(default="text", max_length=50)
    output_destination: str = Field(default="dashboard", max_length=200)
    output_config: dict[str, Any] = Field(default_factory=dict)
    schedule_type: str = Field(default="on_demand", max_length=50)
    schedule_value: str | None = Field(default=None, max_length=200)
    agent_status: AgentStatus = AgentStatus.IDLE


class AgentConfigUpsert(BaseModel):
    """Partial or full update of persisted AgentConfig."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    system_prompt: str | None = Field(default=None, min_length=1)
    user_prompt_template: str | None = Field(default=None, max_length=20_000)
    tools: list[Any] | None = None
    output_format: str | None = Field(default=None, max_length=50)
    output_destination: str | None = Field(default=None, max_length=200)
    output_config: dict[str, Any] | None = None
    schedule_type: str | None = Field(default=None, max_length=50)
    schedule_value: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None


class AgentConfigSnapshot(BaseModel):
    """Expose AgentConfig safely for dashboards."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    system_prompt: str
    user_prompt_template: str | None
    tools: list[Any]
    output_format: str
    output_destination: str
    output_config: dict[str, Any]
    schedule_type: str
    schedule_value: str | None
    is_active: bool
    last_run_at: Any
    last_run_result: dict[str, Any] | None
    run_count: int
    created_at: Any
    updated_at: Any


class AgentDynamicCreateResponse(BaseModel):
    """Return both ORM payloads after factory insert."""

    model_config = ConfigDict(from_attributes=False)

    agent_id: uuid.UUID
    agent_name: str
    config_id: uuid.UUID


__all__ = [
    "AgentConfigSnapshot",
    "AgentConfigUpsert",
    "AgentDynamicCreate",
    "AgentDynamicCreateResponse",
]
