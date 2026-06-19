"""Unified four-lane digest inbox — pending reports with one-click task promotion."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.services.solo_operator_four_lanes import (
    FOUR_LANE_IDS,
    FourLaneId,
    LANE_META,
    LANE_ROUTINE_NAMES,
    _is_queen_maintainer_routine,
    _lane_from_payload,
    _load_tenant_routines,
)
from app.application.services.supervisor.session_service import apply_session_review
from app.application.services.task_ledger import create_task_record
from app.core.logging import get_logger
from app.infrastructure.persistence.models.enums import TaskType
from app.infrastructure.persistence.models.supervisor_session import (
    SubAgentSession,
    SupervisorSession,
)

logger = get_logger(__name__)

DigestInboxStatus = Literal["pending_review", "approved", "rejected", "in_progress", "done", "failed"]


class DigestInboxItemOut(BaseModel):
    """One digest row in the operator inbox."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    lane_id: FourLaneId
    lane_label: str
    title: str
    excerpt: str
    session_status: str
    approval_state: str | None = None
    created_at: datetime
    routine_id: str | None = None
    task_id: str | None = None
    promote_ready: bool = False
    session_href: str


class DigestInboxOut(BaseModel):
    """Snapshot of pending four-lane digests."""

    model_config = ConfigDict(extra="ignore")

    generated_at: datetime
    pending_count: int = 0
    items: list[DigestInboxItemOut] = Field(default_factory=list)


def _lane_routine_map(routines: list[Any]) -> dict[str, FourLaneId]:
    """Map routine UUID string → four-lane id (excludes Queen Maintainer)."""

    out: dict[str, FourLaneId] = {}
    for row in routines:
        lane = _lane_from_payload(dict(row.context_payload or {}))
        if lane not in FOUR_LANE_IDS:
            continue
        if _is_queen_maintainer_routine(str(row.name)):
            continue
        out[str(row.id)] = lane
    return out


def _extract_excerpt(session_row: SupervisorSession, *, max_len: int = 420) -> str:
    """Best-effort digest excerpt from sub-agent outputs."""

    sub_agents: list[SubAgentSession] = list(getattr(session_row, "sub_agents", []) or [])
    priority_roles = ("critic", "researcher", "designer", "reporter")
    for role in priority_roles:
        match = next((s for s in sub_agents if str(s.role).lower() == role and s.last_output), None)
        if match is not None and match.last_output:
            text = str(match.last_output).strip()
            if len(text) > max_len:
                return f"{text[: max_len - 1]}…"
            return text
    for sub in sub_agents:
        if sub.last_output:
            text = str(sub.last_output).strip()
            if len(text) > max_len:
                return f"{text[: max_len - 1]}…"
            return text
    goal = str(session_row.goal or "").strip()
    if len(goal) > max_len:
        return f"{goal[: max_len - 1]}…"
    return goal


def _inbox_status(session_row: SupervisorSession, *, approval_state: str | None) -> DigestInboxStatus:
    status = str(session_row.status or "").lower()
    if session_row.task_id is not None:
        return "done"
    if approval_state == "reject" or approval_state == "rejected":
        return "rejected"
    if approval_state == "approve" or approval_state == "approved":
        if status in {"completed", "done", "success"}:
            return "approved"
        return "in_progress"
    if status in {"needs_input", "paused"}:
        return "pending_review"
    if status in {"running", "pending", "queued"}:
        return "in_progress"
    if status in {"failed", "error"}:
        return "failed"
    if status in {"completed", "done", "success"}:
        return "approved"
    return "pending_review"


def _digest_title(lane_id: FourLaneId, session_row: SupervisorSession) -> str:
    meta = LANE_META.get(lane_id, {})
    label = meta.get("label", lane_id)
    created = session_row.created_at.strftime("%Y-%m-%d") if session_row.created_at else "digest"
    return f"{label} · {created}"


async def compose_four_lane_digest_inbox(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 20,
) -> DigestInboxOut:
    """List recent four-lane digest sessions awaiting operator action."""

    routines = await _load_tenant_routines(db, tenant_id=tenant_id)
    routine_lane = _lane_routine_map(routines)
    if not routine_lane:
        return DigestInboxOut(generated_at=datetime.now(tz=UTC), pending_count=0, items=[])

    routine_ids = list(routine_lane.keys())
    rows = list(
        (
            await db.scalars(
                select(SupervisorSession)
                .where(SupervisorSession.tenant_id == tenant_id)
                .options(selectinload(SupervisorSession.sub_agents))
                .order_by(desc(SupervisorSession.created_at))
                .limit(max(limit * 4, 40)),
            )
        ).all(),
    )

    items: list[DigestInboxItemOut] = []
    pending_count = 0
    for session_row in rows:
        ctx = dict(session_row.context_summary or {})
        routine_id = str(ctx.get("routine_id") or "").strip()
        lane_id: FourLaneId | None = routine_lane.get(routine_id)
        if lane_id is None:
            goal_norm = str(session_row.goal or "").lower()
            for fid in FOUR_LANE_IDS:
                hint = LANE_ROUTINE_NAMES[fid][:20].lower()
                if hint and hint in goal_norm:
                    lane_id = fid
                    break
        if lane_id is None:
            continue

        approval_state = ctx.get("approval_state")
        if isinstance(approval_state, str):
            approval_state = approval_state.strip().lower()
        else:
            approval_state = None

        inbox_status = _inbox_status(session_row, approval_state=approval_state)
        if inbox_status in {"rejected", "failed"}:
            continue
        if session_row.task_id is not None and inbox_status == "done":
            continue

        promote_ready = inbox_status in {"approved", "pending_review"} and session_row.task_id is None
        if inbox_status == "pending_review":
            pending_count += 1

        meta = LANE_META[lane_id]
        items.append(
            DigestInboxItemOut(
                session_id=str(session_row.id),
                lane_id=lane_id,
                lane_label=meta["label"],
                title=_digest_title(lane_id, session_row),
                excerpt=_extract_excerpt(session_row),
                session_status=str(session_row.status),
                approval_state=approval_state,
                created_at=session_row.created_at or datetime.now(tz=UTC),
                routine_id=routine_id or None,
                task_id=str(session_row.task_id) if session_row.task_id else None,
                promote_ready=promote_ready,
                session_href=f"/agents?session={session_row.id}#sessions",
            ),
        )
        if len(items) >= limit:
            break

    return DigestInboxOut(
        generated_at=datetime.now(tz=UTC),
        pending_count=pending_count,
        items=items,
    )


async def promote_digest_session_to_task(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    reviewer_subject: str,
    title: str | None = None,
    approve_first: bool = True,
) -> dict[str, Any]:
    """Approve digest session (optional) and create a backlog task linked to it."""

    session_row = await db.scalar(
        select(SupervisorSession)
        .where(SupervisorSession.id == session_id)
        .options(selectinload(SupervisorSession.sub_agents))
        .limit(1),
    )
    if session_row is None or session_row.tenant_id != tenant_id:
        return {"ok": False, "error": "session_not_found"}

    if session_row.task_id is not None:
        return {
            "ok": True,
            "already_promoted": True,
            "task_id": str(session_row.task_id),
            "session_id": str(session_id),
        }

    routines = await _load_tenant_routines(db, tenant_id=tenant_id)
    routine_lane = _lane_routine_map(routines)
    ctx = dict(session_row.context_summary or {})
    routine_id = str(ctx.get("routine_id") or "")
    lane_id = routine_lane.get(routine_id)
    if lane_id is None:
        lane_id = "marketing_najman"

    approval_state = str(ctx.get("approval_state") or "").lower()
    if approve_first and approval_state not in {"approve", "approved"}:
        session_row = await apply_session_review(
            db,
            session_row=session_row,
            decision="approve",
            note="Promoted from four-lane digest inbox.",
        )

    task_title = (title or _digest_title(lane_id, session_row)).strip()[:500]
    excerpt = _extract_excerpt(session_row, max_len=2000)
    task_row = await create_task_record(
        db,
        title=task_title,
        task_type_value=TaskType.REPORT,
        priority=4 if lane_id == "marketing_najman" else 5,
        payload={
            "source": "four_lane_digest_inbox",
            "four_lane_id": lane_id,
            "supervisor_session_id": str(session_id),
            "routine_id": routine_id or None,
            "excerpt": excerpt,
            "simulate_first": True,
        },
        swarm_id=session_row.swarm_id,
        workflow_id=None,
        parent_task_id=None,
    )
    task_row.tenant_id = tenant_id
    session_row.task_id = task_row.id
    await db.flush()

    logger.info(
        "solo_four_lanes.digest_promoted",
        agent_id="four_lane_inbox",
        swarm_id=lane_id,
        task_id=str(task_row.id),
        session_id=str(session_id),
    )
    return {
        "ok": True,
        "task_id": str(task_row.id),
        "session_id": str(session_id),
        "lane_id": lane_id,
        "title": task_title,
        "tasks_href": f"/tasks?highlight={task_row.id}",
    }


__all__ = [
    "DigestInboxItemOut",
    "DigestInboxOut",
    "compose_four_lane_digest_inbox",
    "promote_digest_session_to_task",
]
