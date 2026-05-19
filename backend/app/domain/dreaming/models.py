"""Core domain models for nightly dream cycles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID
from typing import Any


class DreamCycleStatus(StrEnum):
    """Lifecycle status for one dream consolidation cycle."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class DreamCycle:
    """Domain representation of one nightly consolidation run."""

    id: UUID
    tenant_id: UUID
    started_at: datetime
    finished_at: datetime | None
    items_processed: int
    items_deduplicated: int
    items_consolidated: int
    digest_md: str
    dream_report: dict[str, Any]
    status: DreamCycleStatus


@dataclass(slots=True)
class DreamInsight:
    """One consolidated insight produced within a dream cycle."""

    cycle_id: UUID
    source_kind: str
    source_ref: str
    summary: str
    confidence: float
    neo4j_node_id: str | None
    chroma_doc_id: str | None
