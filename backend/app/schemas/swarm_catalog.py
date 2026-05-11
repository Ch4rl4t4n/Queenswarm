"""HTTP contracts for sub-swarm colony records (catalog CRUD)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SwarmPurpose


class SubSwarmCreateRequest(BaseModel):
    """Stand up a local hive mind partition."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(..., min_length=2, max_length=100)
    purpose: SwarmPurpose
    local_memory: dict[str, Any] = Field(default_factory=dict)
    queen_agent_id: uuid.UUID | None = None
    is_active: bool = True


class SubSwarmPatchRequest(BaseModel):
    """Partial updates to colony metadata and queen linkage."""

    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(default=None, min_length=2, max_length=100)
    local_memory: dict[str, Any] | None = None
    queen_agent_id: uuid.UUID | None = Field(
        default=None,
        description="Assign a queen agent; omitted leaves queen unchanged unless clear_queen is set.",
    )
    clear_queen: bool = Field(
        default=False,
        description="When true, removes queen assignment (ignores queen_agent_id).",
    )
    is_active: bool | None = None
    total_pollen: float | None = Field(default=None, ge=0.0)


class SubSwarmSnapshot(BaseModel):
    """Operator projection including sync cadence hints."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: uuid.UUID
    name: str
    purpose: SwarmPurpose
    local_memory: dict[str, Any]
    queen_agent_id: uuid.UUID | None
    last_global_sync_at: datetime | None
    total_pollen: float
    member_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


__all__ = ["SubSwarmCreateRequest", "SubSwarmPatchRequest", "SubSwarmSnapshot"]
