"""POS-J1/J2 — Weekly auto-compound gardener (reflection → memory evolution + Brain Pack gaps)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.jarvis_weekly_reflection_service import (
    compose_jarvis_weekly_reflection_strip,
)
from app.application.services.knowledge_elicitation import compose_knowledge_elicitation_snapshot
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.memory_evolution import MemoryEvolutionProposal
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

WEEKLY_COMPOUND_SETTINGS_KEY = "weekly_compound_gardener"
MAX_PENDING_DRAFTS = 12
MAX_STORED_DRAFTS = 40

CompoundDraftStatus = Literal["pending", "approved", "rejected"]
CompoundDraftDecision = Literal["approve", "reject"]


class BrainPackGapSuggestionOut(BaseModel):
    """One Brain Pack gap surfaced by weekly gardener (J2)."""

    model_config = ConfigDict(extra="ignore")

    kind: str
    title: str
    question: str


class WeeklyCompoundDraftOut(BaseModel):
    """Weekly compound wiki draft awaiting operator approval."""

    model_config = ConfigDict(extra="ignore")

    id: str
    status: CompoundDraftStatus = "pending"
    week_label: str = ""
    title: str = ""
    markdown_preview: str = ""
    proposal_id: str | None = None
    brain_pack_gaps: list[BrainPackGapSuggestionOut] = Field(default_factory=list)
    created_at: datetime
    reviewed_at: datetime | None = None
    href: str = "/knowledge#hivemind"


class MissionWeeklyCompoundStripOut(BaseModel):
    """Mission Home strip for weekly compound gardener."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    headline: str = "Weekly compound"
    message: str = ""
    week_label: str = ""
    pending_drafts: int = 0
    brain_pack_gap_count: int = 0
    last_run_at: datetime | None = None
    hive_mind_href: str = "/knowledge#hivemind"
    evolution_href: str = "/knowledge?tab=hivemind#evolution"
    approvals_href: str = "/tasks?tab=approvals"


class WeeklyCompoundGardenerSnapshotOut(BaseModel):
    """Full gardener workspace snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    pending_count: int = 0
    last_run_at: datetime | None = None
    last_run_drafts_created: int = 0
    items: list[WeeklyCompoundDraftOut] = Field(default_factory=list)
    brain_pack_gaps: list[BrainPackGapSuggestionOut] = Field(default_factory=list)
    operator_hint: str = ""


class WeeklyCompoundDraftReviewIn(BaseModel):
    """Approve or reject a pending weekly compound draft."""

    model_config = ConfigDict(extra="forbid")

    decision: CompoundDraftDecision
    note: str = Field(default="", max_length=500)


class WeeklyCompoundDraftReviewOut(BaseModel):
    """Review action result."""

    model_config = ConfigDict(extra="ignore")

    id: str
    status: CompoundDraftStatus
    reviewed_at: datetime


def _bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    raw = root.get(WEEKLY_COMPOUND_SETTINGS_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def _drafts_list(operator_settings: dict[str, Any] | None) -> list[dict[str, Any]]:
    raw = _bucket(operator_settings).get("drafts")
    if not isinstance(raw, list):
        return []
    return [dict(row) for row in raw if isinstance(row, dict)]


def _iso_week_key(now: datetime) -> str:
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _build_compound_markdown(
    *,
    week_label: str,
    reflection_message: str,
    highlights: list[dict[str, str]],
    brain_gaps: list[BrainPackGapSuggestionOut],
) -> str:
    lines = [
        f"# Weekly compound · {week_label}",
        "",
        reflection_message,
        "",
        "## Highlights",
    ]
    for row in highlights:
        lines.append(f"- **{row.get('title', 'Highlight')}** ({row.get('source', 'note')}): {row.get('excerpt', '')}")
    if brain_gaps:
        lines.extend(["", "## Brain Pack gaps to fill"])
        for gap in brain_gaps[:5]:
            lines.append(f"- **{gap.title}**: {gap.question}")
    lines.extend(
        [
            "",
            "_Simulate-first draft — approve in Memory Evolution or reject to discard._",
        ],
    )
    return "\n".join(lines)


async def _persist_bucket(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    mutator: Any,
) -> dict[str, Any]:
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("tenant_not_found")
    root = dict(tenant.operator_settings or {})
    bucket = _bucket(root)
    updated = mutator(bucket)
    root[WEEKLY_COMPOUND_SETTINGS_KEY] = updated
    tenant.operator_settings = root
    await session.flush()
    return updated


def _parse_draft(row: dict[str, Any]) -> WeeklyCompoundDraftOut:
    gaps_raw = row.get("brain_pack_gaps") or []
    gaps = [
        BrainPackGapSuggestionOut(
            kind=str(g.get("kind") or ""),
            title=str(g.get("title") or ""),
            question=str(g.get("question") or ""),
        )
        for g in gaps_raw
        if isinstance(g, dict)
    ]
    created_raw = row.get("created_at")
    created = (
        datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
        if created_raw
        else datetime.now(tz=UTC)
    )
    reviewed_raw = row.get("reviewed_at")
    reviewed = (
        datetime.fromisoformat(str(reviewed_raw).replace("Z", "+00:00"))
        if reviewed_raw
        else None
    )
    return WeeklyCompoundDraftOut(
        id=str(row.get("id") or ""),
        status=str(row.get("status") or "pending"),  # type: ignore[arg-type]
        week_label=str(row.get("week_label") or ""),
        title=str(row.get("title") or ""),
        markdown_preview=str(row.get("markdown_preview") or "")[:480],
        proposal_id=str(row.get("proposal_id") or "") or None,
        brain_pack_gaps=gaps,
        created_at=created,
        reviewed_at=reviewed,
    )


async def compose_weekly_compound_gardener_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> WeeklyCompoundGardenerSnapshotOut:
    """Return pending weekly compound drafts and Brain Pack gap hints."""

    now = datetime.now(tz=UTC)
    if not settings.weekly_compound_gardener_enabled:
        return WeeklyCompoundGardenerSnapshotOut(enabled=False, generated_at=now)

    tenant = await session.get(Tenant, tenant_id)
    bucket = _bucket(tenant.operator_settings if tenant else None)
    drafts = [_parse_draft(row) for row in _drafts_list(tenant.operator_settings if tenant else None)]
    pending = [row for row in drafts if row.status == "pending"]
    gaps = [
        BrainPackGapSuggestionOut(
            kind=p.kind,
            title=p.title,
            question=p.question,
        )
        for p in (await compose_knowledge_elicitation_snapshot(session, tenant_id=tenant_id)).prompts
        if p.empty
    ]

    last_run_raw = bucket.get("last_run_at")
    last_run = (
        datetime.fromisoformat(str(last_run_raw).replace("Z", "+00:00"))
        if last_run_raw
        else None
    )

    hint = "Weekly compound runs Sunday UTC — approve drafts in Hive Mind → Evolution."
    if pending:
        hint = f"{len(pending)} weekly compound draft(s) await approval."
    elif gaps:
        hint = f"{len(gaps)} Brain Pack gap(s) — fill in Knowledge → Brain Pack."

    return WeeklyCompoundGardenerSnapshotOut(
        enabled=True,
        generated_at=now,
        pending_count=len(pending),
        last_run_at=last_run,
        last_run_drafts_created=int(bucket.get("last_run_drafts_created") or 0),
        items=drafts[:MAX_STORED_DRAFTS],
        brain_pack_gaps=gaps[:8],
        operator_hint=hint,
    )


async def compose_mission_weekly_compound_strip(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    first_run_complete: bool,
) -> MissionWeeklyCompoundStripOut:
    """Mission Home strip — pending compound drafts + Brain Pack gap count."""

    if not settings.weekly_compound_gardener_enabled or not first_run_complete:
        return MissionWeeklyCompoundStripOut(enabled=False)

    snap = await compose_weekly_compound_gardener_snapshot(session, tenant_id=tenant_id)
    if not snap.enabled:
        return MissionWeeklyCompoundStripOut(enabled=False)

    now = datetime.now(tz=UTC)
    week_label = _iso_week_key(now).replace("-W", " · week ")

    if snap.pending_count == 0 and not snap.brain_pack_gaps:
        return MissionWeeklyCompoundStripOut(
            enabled=False,
            message="No pending compound drafts this week.",
        )

    message_parts: list[str] = []
    if snap.pending_count:
        message_parts.append(f"{snap.pending_count} compound draft(s) to review")
    if snap.brain_pack_gaps:
        message_parts.append(f"{len(snap.brain_pack_gaps)} Brain Pack gap(s)")

    return MissionWeeklyCompoundStripOut(
        enabled=True,
        headline="Weekly compound · gardener",
        message=" · ".join(message_parts) + " — approve before Hive Mind apply.",
        week_label=week_label,
        pending_drafts=snap.pending_count,
        brain_pack_gap_count=len(snap.brain_pack_gaps),
        last_run_at=snap.last_run_at,
    )


async def run_weekly_compound_gardener_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    proposed_by_user_id: uuid.UUID | None = None,
) -> int:
    """Weekly tick — reflection rollup → memory evolution proposal + HITL draft."""

    if not settings.weekly_compound_gardener_enabled:
        return 0

    now = datetime.now(tz=UTC)
    week_key = _iso_week_key(now)

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return 0

    bucket = _bucket(tenant.operator_settings)
    if bucket.get("last_run_week") == week_key:
        return 0

    reflection = await compose_jarvis_weekly_reflection_strip(
        session,
        tenant_id=tenant_id,
        first_run_complete=True,
    )
    if not reflection.enabled:
        await _persist_bucket(
            session,
            tenant_id=tenant_id,
            mutator=lambda b: {**b, "last_run_week": week_key, "last_run_at": now.isoformat()},
        )
        return 0

    elicitation = await compose_knowledge_elicitation_snapshot(session, tenant_id=tenant_id)
    brain_gaps = [
        BrainPackGapSuggestionOut(kind=p.kind, title=p.title, question=p.question)
        for p in elicitation.prompts
        if p.empty
    ]

    highlights = [
        {"source": h.source, "title": h.title, "excerpt": h.excerpt}
        for h in reflection.highlights
    ]
    week_label = reflection.week_label or week_key
    title = f"Weekly compound · {week_label}"
    markdown = _build_compound_markdown(
        week_label=week_label,
        reflection_message=reflection.message,
        highlights=highlights,
        brain_gaps=brain_gaps,
    )

    importance = min(0.95, 0.62 + 0.05 * len(highlights))
    proposal = MemoryEvolutionProposal(
        tenant_id=tenant_id,
        proposal_kind="weekly_compound",
        title=title[:240],
        summary=reflection.message[:2000],
        payload={
            "week_key": week_key,
            "highlights": highlights,
            "brain_pack_gaps": [g.model_dump() for g in brain_gaps[:5]],
            "markdown_preview": markdown[:4000],
            "source": "weekly_compound_gardener",
        },
        status="pending",
        importance_score=importance,
        requires_manual_approval=True,
        proposed_by_user_id=proposed_by_user_id,
    )
    session.add(proposal)
    await session.flush()

    draft_id = str(uuid.uuid4())
    draft_row = {
        "id": draft_id,
        "status": "pending",
        "week_label": week_label,
        "title": title,
        "markdown_preview": markdown[:2000],
        "proposal_id": str(proposal.id),
        "brain_pack_gaps": [g.model_dump() for g in brain_gaps[:5]],
        "created_at": now.isoformat(),
    }

    def _mutator(b: dict[str, Any]) -> dict[str, Any]:
        drafts = [draft_row, *_drafts_list({"weekly_compound_gardener": b})]
        pending = [row for row in drafts if str(row.get("status") or "") == "pending"]
        if len(pending) > MAX_PENDING_DRAFTS:
            drafts = drafts[:MAX_STORED_DRAFTS]
        return {
            **b,
            "drafts": drafts[:MAX_STORED_DRAFTS],
            "last_run_week": week_key,
            "last_run_at": now.isoformat(),
            "last_run_drafts_created": 1,
        }

    await _persist_bucket(session, tenant_id=tenant_id, mutator=_mutator)

    _logger.info(
        "weekly_compound_gardener.draft_created",
        agent_id="weekly_compound_gardener",
        swarm_id=str(tenant_id),
        task_id=draft_id,
        proposal_id=str(proposal.id),
        gap_count=len(brain_gaps),
    )
    if proposed_by_user_id is not None:
        from app.application.services.personal_os_pending_notify_service import (
            notify_weekly_compound_draft_pending,
        )

        await notify_weekly_compound_draft_pending(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=proposed_by_user_id,
            week_key=week_key,
            draft_title=title,
        )
    return 1


async def compose_compound_draft_inbox_items(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Pending compound drafts for unified Approval Inbox."""

    if not settings.weekly_compound_gardener_enabled:
        return []
    snap = await compose_weekly_compound_gardener_snapshot(session, tenant_id=tenant_id)
    rows: list[dict[str, Any]] = []
    for item in snap.items:
        if item.status != "pending":
            continue
        rows.append(
            {
                "id": item.id,
                "title": item.title,
                "detail": item.markdown_preview[:320],
                "created_at": item.created_at,
            },
        )
        if len(rows) >= limit:
            break
    return rows


async def review_weekly_compound_draft(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    draft_id: str,
    body: WeeklyCompoundDraftReviewIn,
) -> WeeklyCompoundDraftReviewOut:
    """Approve or reject a pending weekly compound draft."""

    now = datetime.now(tz=UTC)
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("tenant_not_found")

    drafts = _drafts_list(tenant.operator_settings)
    target: dict[str, Any] | None = None
    for row in drafts:
        if str(row.get("id") or "") == draft_id:
            target = row
            break
    if target is None:
        raise ValueError("draft_not_found")
    if str(target.get("status") or "") != "pending":
        raise ValueError("draft_not_pending")

    new_status: CompoundDraftStatus = "approved" if body.decision == "approve" else "rejected"
    target["status"] = new_status
    target["reviewed_at"] = now.isoformat()
    if body.note.strip():
        target["review_note"] = body.note.strip()[:500]

    proposal_id = str(target.get("proposal_id") or "")
    if proposal_id:
        proposal = await session.get(MemoryEvolutionProposal, uuid.UUID(proposal_id))
        if proposal is not None and proposal.tenant_id == tenant_id:
            if new_status == "approved":
                proposal.status = "approved"
                proposal.approved_at = now
            else:
                proposal.status = "rejected"

    def _mutator(b: dict[str, Any]) -> dict[str, Any]:
        updated = []
        for row in drafts:
            if str(row.get("id") or "") == draft_id:
                updated.append(target)  # type: ignore[arg-type]
            else:
                updated.append(row)
        return {**b, "drafts": updated}

    await _persist_bucket(session, tenant_id=tenant_id, mutator=_mutator)

    _logger.info(
        "weekly_compound_gardener.draft_reviewed",
        agent_id="weekly_compound_gardener",
        swarm_id=str(tenant_id),
        task_id=draft_id,
        decision=body.decision,
    )
    return WeeklyCompoundDraftReviewOut(id=draft_id, status=new_status, reviewed_at=now)


__all__ = [
    "MissionWeeklyCompoundStripOut",
    "WeeklyCompoundDraftReviewIn",
    "WeeklyCompoundDraftReviewOut",
    "WeeklyCompoundGardenerSnapshotOut",
    "compose_compound_draft_inbox_items",
    "compose_mission_weekly_compound_strip",
    "compose_weekly_compound_gardener_snapshot",
    "review_weekly_compound_draft",
    "run_weekly_compound_gardener_for_tenant",
]
