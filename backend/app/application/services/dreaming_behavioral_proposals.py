"""Dreaming → behavioral proposals — overnight instructions.md suggestions (P8)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.persistence.models.dump_sleep_batch import DumpSleepBatchORM, DumpSleepStatusORM

_PROPOSAL_RE = re.compile(
    r"(?i)(?:always|never|prefer|focus on|stop|start|prioritize|avoid)\s+[^.\n]{8,120}",
)


class BehavioralProposalOut(BaseModel):
    """One proposed addition to tenant instructions.md."""

    model_config = ConfigDict(extra="ignore")

    id: str
    proposal: str
    source: str
    priority: str = "medium"


class DreamingBehavioralSnapshotOut(BaseModel):
    """Overnight-derived behavioral proposals (approve-only)."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    batch_id: str | None = None
    proposals: list[BehavioralProposalOut] = Field(default_factory=list)


def _extract_proposals_from_briefing(briefing_md: str) -> list[str]:
    """Heuristic extraction of behavioral lines from overnight briefing."""

    found = _PROPOSAL_RE.findall(briefing_md or "")
    unique: list[str] = []
    seen: set[str] = set()
    for raw in found:
        text = raw.strip().rstrip(".")
        key = text.lower()
        if key in seen or len(text) < 12:
            continue
        seen.add(key)
        unique.append(text[:280])
        if len(unique) >= 5:
            break

    if not unique and "stalled" in (briefing_md or "").lower():
        unique.append("Prioritize triage of stalled projects flagged in overnight dump.")
    if not unique and briefing_md.strip():
        unique.append("Review overnight Swarm Report each morning before triggering live actions.")
    return unique


async def compose_dreaming_behavioral_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> DreamingBehavioralSnapshotOut:
    """Load latest completed dump batch and derive instruction proposals."""

    if not settings.dreaming_behavioral_proposals_enabled:
        return DreamingBehavioralSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    row = await session.scalar(
        select(DumpSleepBatchORM)
        .where(
            DumpSleepBatchORM.tenant_id == tenant_id,
            DumpSleepBatchORM.status == DumpSleepStatusORM.COMPLETED,
        )
        .order_by(desc(DumpSleepBatchORM.processed_at))
        .limit(1),
    )
    if row is None or not (row.briefing_md or "").strip():
        return DreamingBehavioralSnapshotOut(
            enabled=True,
            generated_at=datetime.now(tz=UTC),
            proposals=[],
        )

    raw_proposals = _extract_proposals_from_briefing(row.briefing_md or "")
    proposals = [
        BehavioralProposalOut(
            id=f"proposal-{idx}",
            proposal=text,
            source="overnight_dump",
            priority="high" if idx == 0 else "medium",
        )
        for idx, text in enumerate(raw_proposals)
    ]

    return DreamingBehavioralSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        batch_id=str(row.id),
        proposals=proposals,
    )


__all__ = ["DreamingBehavioralSnapshotOut", "compose_dreaming_behavioral_snapshot"]
