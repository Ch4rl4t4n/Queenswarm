"""Pydantic DTOs for final deliverable payloads (Phase 0.51)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FinalDeliverableStructured(BaseModel):
    """Optional JSON bundle produced by orchestrator / review lane."""

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    summary: str = ""
    artefacts: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)


class FinalDeliverableEnvelope(BaseModel):
    """Engine input contract — markdown is canonical; structured augments search."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=500)
    markdown_body: str = Field(min_length=1)
    structured: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    voice_script: str | None = None


class FinalDeliverableSummaryOut(BaseModel):
    """List card projection."""

    model_config = ConfigDict(extra="ignore")

    id: uuid.UUID
    lineage_id: uuid.UUID
    version: int
    title: str
    slug: str
    created_at: datetime
    tags: list[str]
    preview: str


class FinalDeliverableDetailOut(FinalDeliverableSummaryOut):
    """Full row for UI modals."""

    markdown_body: str
    structured_json: dict[str, Any]
    voice_script: str | None
    archive_relpath: str | None
    chroma_embedding_id: str | None
    ballroom_session_id: uuid.UUID | None
    mission_id: uuid.UUID | None


class RegenerateDeliverableBody(BaseModel):
    """Operator instruction for a new revision."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    instruction: str = Field(min_length=4, max_length=8000)


class SearchOutputsQuery(BaseModel):
    """Semantic filter over Chroma ``task_deliverables``."""

    model_config = ConfigDict(extra="ignore")

    q: str = Field(min_length=2, max_length=2000)
    limit: int = Field(default=8, ge=1, le=30)


__all__ = [
    "FinalDeliverableDetailOut",
    "FinalDeliverableEnvelope",
    "FinalDeliverableStructured",
    "FinalDeliverableSummaryOut",
    "RegenerateDeliverableBody",
    "SearchOutputsQuery",
]
