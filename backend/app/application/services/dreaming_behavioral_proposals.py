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


_NIGHTLY_MARKER = "<!-- qs-nightly-learning"


def _proposal_already_applied(instructions: str, *, proposal_id: str, batch_id: str | None) -> bool:
    text = instructions or ""
    if f"proposal_id={proposal_id}" in text:
        return True
    if batch_id and f"batch_id={batch_id}" in text and proposal_id in text:
        return True
    return False


def _nightly_learning_block(
    *,
    proposal: str,
    proposal_id: str,
    batch_id: str | None,
    source: str,
) -> str:
    stamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    meta = f"proposal_id={proposal_id}"
    if batch_id:
        meta = f"{meta} batch_id={batch_id}"
    return (
        f"## Nightly learning · {stamp}\n"
        f"{_NIGHTLY_MARKER} {meta} source={source} -->\n"
        f"- {proposal.strip()}"
    )


class ApplyBehavioralProposalsOut(BaseModel):
    """Result of applying overnight proposals to curated instructions."""

    model_config = ConfigDict(extra="ignore")

    applied: int
    skipped: int
    char_count: int
    version: int


async def apply_behavioral_proposals(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    proposal_ids: list[str],
    author: str = "agent_os",
) -> ApplyBehavioralProposalsOut:
    """Merge up to 3 verified overnight proposals into tenant INSTRUCTIONS."""

    from app.application.services.curated_memory_service import CuratedMemoryService
    from app.application.services.slack_harness_trainer import merge_instructions_append
    from app.domain.memory.curated import CuratedFileKind

    if not settings.dreaming_behavioral_proposals_enabled:
        raise ValueError("behavioral_proposals_disabled")

    snapshot = await compose_dreaming_behavioral_snapshot(session, tenant_id=tenant_id)
    if not snapshot.proposals:
        raise ValueError("no_proposals")

    wanted = {pid.strip() for pid in proposal_ids if pid.strip()}
    if not wanted:
        raise ValueError("no_proposal_ids")

    max_apply = min(3, max(1, int(getattr(settings, "nightly_learnings_max_preferences", 3) or 3)))
    selected = [p for p in snapshot.proposals if p.id in wanted][:max_apply]
    if not selected:
        raise ValueError("proposals_not_found")

    svc = CuratedMemoryService(db=session)
    current = await svc.get(tenant_id, CuratedFileKind.INSTRUCTIONS)
    base = (current.content_md if current else "") or ""
    applied = 0
    skipped = 0
    merged = base

    for proposal in selected:
        if _proposal_already_applied(merged, proposal_id=proposal.id, batch_id=snapshot.batch_id):
            skipped += 1
            continue
        block = _nightly_learning_block(
            proposal=proposal.proposal,
            proposal_id=proposal.id,
            batch_id=snapshot.batch_id,
            source=proposal.source,
        )
        merged = merge_instructions_append(merged, block)
        applied += 1

    if applied == 0:
        return ApplyBehavioralProposalsOut(
            applied=0,
            skipped=skipped,
            char_count=len(merged),
            version=int(current.version if current else 0),
        )

    row = await svc.upsert(
        tenant_id,
        CuratedFileKind.INSTRUCTIONS,
        merged,
        user_id=None,
    )
    return ApplyBehavioralProposalsOut(
        applied=applied,
        skipped=skipped,
        char_count=len(merged),
        version=int(row.version),
    )


__all__ = [
    "ApplyBehavioralProposalsOut",
    "BehavioralProposalOut",
    "DreamingBehavioralSnapshotOut",
    "apply_behavioral_proposals",
    "compose_dreaming_behavioral_snapshot",
]

