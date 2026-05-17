"""Curated memory domain entities for Queen context bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class CuratedFileKind(StrEnum):
    """Supported curated memory document kinds."""

    MISSION = "mission"
    IDEAL_STATE = "ideal_state"
    SOUL = "soul"
    SKILLS_HIERARCHY = "skills_hierarchy"


@dataclass(slots=True)
class CuratedMemoryFile:
    """Tenant-scoped curated memory document."""

    tenant_id: UUID
    kind: CuratedFileKind
    content_md: str
    version: int
    updated_at: datetime
    updated_by_user_id: UUID | None
    char_count: int
