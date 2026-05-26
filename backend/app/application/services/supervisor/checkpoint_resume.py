"""Checkpoint resume helpers for long-running durable supervisor sessions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.runtime import append_event
from app.application.services.supervisor.session_service import (
    RETRYABLE_SUB_AGENT_STATUSES,
    _list_session_sub_agents,
    enqueue_durable_sub_agent_step,
    resume_inprocess_sub_agents_after_approval,
)
from app.application.services.supervisor.shared_context import SharedContextService
from app.application.services.supervisor.skills import SkillLibrary
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession

logger = structlog.get_logger(__name__)

VERIFIED_CHECKPOINT_STATUS = "completed"
RESUMABLE_SESSION_STATUSES: frozenset[str] = frozenset(
    {"paused", "pending", "needs_input", "running", "failed"},
)


class SessionCheckpointStep(BaseModel):
    """One sub-agent row in spawn order with checkpoint semantics."""

    model_config = ConfigDict(extra="ignore")

    sub_agent_id: uuid.UUID
    role: str
    status: str
    spawn_order: int
    is_verified_checkpoint: bool
    is_resumable: bool


class SessionCheckpointSnapshot(BaseModel):
    """Structured checkpoint view for operator resume UI."""

    model_config = ConfigDict(extra="ignore")

    session_id: uuid.UUID
    session_status: str
    runtime_mode: str
    steps: list[SessionCheckpointStep] = Field(default_factory=list)
    last_verified_index: int = -1
    last_verified_role: str | None = None
    next_resumable_sub_agent_id: uuid.UUID | None = None
    next_resumable_role: str | None = None
    can_resume_from_checkpoint: bool = False
    resume_hint: str = ""


def _sorted_sub_agents(sub_agents: list[SubAgentSession]) -> list[SubAgentSession]:
    """Return sub-agents ordered by spawn_order."""

    return sorted(sub_agents, key=lambda row: int(row.spawn_order or 0))


def build_session_checkpoint_snapshot(
    session_row: SupervisorSession,
    sub_agents: list[SubAgentSession] | None = None,
) -> SessionCheckpointSnapshot:
    """Derive verified checkpoints and the next resumable sub-agent step."""

    subs = _sorted_sub_agents(sub_agents or list(getattr(session_row, "sub_agents", None) or []))
    session_status = str(session_row.status or "").strip().lower()
    runtime_mode = str(session_row.runtime_mode or "inprocess").strip().lower()

    last_verified_index = -1
    steps: list[SessionCheckpointStep] = []
    for index, sub in enumerate(subs):
        sub_status = str(sub.status or "").strip().lower()
        is_verified = sub_status == VERIFIED_CHECKPOINT_STATUS
        if is_verified:
            last_verified_index = index
        steps.append(
            SessionCheckpointStep(
                sub_agent_id=sub.id,
                role=str(sub.role or "agent"),
                status=sub_status,
                spawn_order=int(sub.spawn_order or 0),
                is_verified_checkpoint=is_verified,
                is_resumable=sub_status in RETRYABLE_SUB_AGENT_STATUSES,
            ),
        )

    next_resumable_sub_agent_id: uuid.UUID | None = None
    next_resumable_role: str | None = None
    for index, sub in enumerate(subs):
        if index <= last_verified_index:
            continue
        sub_status = str(sub.status or "").strip().lower()
        if sub_status in RETRYABLE_SUB_AGENT_STATUSES:
            next_resumable_sub_agent_id = sub.id
            next_resumable_role = str(sub.role or "agent")
            break

    has_verified = last_verified_index >= 0
    has_resumable = next_resumable_sub_agent_id is not None
    has_queued = any(str(sub.status or "").lower() in {"queued", "pending"} for sub in subs)
    session_open = session_status not in {"stopped", "completed"}

    can_resume = session_open and (
        (runtime_mode == "durable" and (has_resumable or (session_status == "paused" and has_queued)))
        or (
            runtime_mode == "inprocess"
            and session_status in {"needs_input", "paused", "running"}
            and any(str(sub.status or "").lower() == "needs_input" for sub in subs)
        )
    )

    if not session_open:
        resume_hint = "Session is closed."
    elif can_resume and has_verified and next_resumable_role:
        resume_hint = f"Resume from verified checkpoint after {steps[last_verified_index].role} → {next_resumable_role}."
    elif can_resume and next_resumable_role:
        resume_hint = f"Resume at first step: {next_resumable_role}."
    elif can_resume:
        resume_hint = "Resume queued durable steps."
    else:
        resume_hint = "No retryable steps after the last verified checkpoint."

    return SessionCheckpointSnapshot(
        session_id=session_row.id,
        session_status=session_status,
        runtime_mode=runtime_mode,
        steps=steps,
        last_verified_index=last_verified_index,
        last_verified_role=steps[last_verified_index].role if has_verified else None,
        next_resumable_sub_agent_id=next_resumable_sub_agent_id,
        next_resumable_role=next_resumable_role,
        can_resume_from_checkpoint=can_resume,
        resume_hint=resume_hint,
    )


async def resume_session_from_last_checkpoint(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
    shared_context: SharedContextService | None = None,
    skill_library: SkillLibrary | None = None,
) -> tuple[SupervisorSession, SessionCheckpointSnapshot, int]:
    """Resume a durable or in-process session from the last verified sub-agent checkpoint."""

    subs = list(getattr(session_row, "sub_agents", None) or [])
    if not subs:
        subs = await _list_session_sub_agents(db, session_row.id)

    snapshot = build_session_checkpoint_snapshot(session_row, subs)
    session_status = str(session_row.status or "").strip().lower()
    if session_status in {"stopped", "completed"}:
        msg = "Supervisor session is closed."
        raise ValueError(msg)
    if not snapshot.can_resume_from_checkpoint:
        msg = snapshot.resume_hint or "Session cannot resume from checkpoint."
        raise ValueError(msg)

    runtime_mode = str(session_row.runtime_mode or "inprocess").strip().lower()
    requeued = 0
    resumed_inprocess = 0

    if session_status == "paused":
        session_row.status = "running"

    if runtime_mode == "durable":
        sorted_subs = _sorted_sub_agents(subs)
        for sub in sorted_subs:
            sub_status = str(sub.status or "").strip().lower()
            if sub_status in {"queued", "pending"}:
                await enqueue_durable_sub_agent_step(
                    db,
                    supervisor_session=session_row,
                    sub_agent=sub,
                    reason="checkpoint_resume",
                )
                requeued += 1

        if requeued == 0 and snapshot.next_resumable_sub_agent_id is not None:
            target = next(
                (sub for sub in sorted_subs if sub.id == snapshot.next_resumable_sub_agent_id),
                None,
            )
            if target is not None:
                await enqueue_durable_sub_agent_step(
                    db,
                    supervisor_session=session_row,
                    sub_agent=target,
                    reason="checkpoint_resume",
                )
                requeued += 1

        if session_status == "needs_input" and requeued:
            session_row.status = "running"
    else:
        ctx = shared_context or SharedContextService()
        loader = skill_library or SkillLibrary()
        resumed_inprocess = await resume_inprocess_sub_agents_after_approval(
            db,
            session_row=session_row,
            shared_context=ctx,
            skill_library=loader,
        )
        requeued = resumed_inprocess

    summary = dict(session_row.context_summary or {})
    summary["checkpoint_resume_at"] = datetime.now(tz=UTC).isoformat()
    summary["last_verified_role"] = snapshot.last_verified_role
    summary["next_resumable_role"] = snapshot.next_resumable_role
    summary["requeued_sub_agents"] = requeued
    if resumed_inprocess:
        summary["resumed_sub_agents"] = resumed_inprocess
    session_row.context_summary = summary

    await append_event(
        db,
        supervisor_session=session_row,
        sub_agent=None,
        event_type="session_checkpoint_resume",
        message=snapshot.resume_hint[:2000],
        payload={
            "requeued_sub_agents": requeued,
            "last_verified_role": snapshot.last_verified_role,
            "next_resumable_role": snapshot.next_resumable_role,
            "runtime_mode": runtime_mode,
        },
    )
    logger.info(
        "supervisor.checkpoint_resume",
        session_id=str(session_row.id),
        requeued_sub_agents=requeued,
        last_verified_role=snapshot.last_verified_role,
        next_resumable_role=snapshot.next_resumable_role,
    )
    await db.flush()
    return session_row, snapshot, requeued


__all__ = [
    "SessionCheckpointSnapshot",
    "SessionCheckpointStep",
    "build_session_checkpoint_snapshot",
    "resume_session_from_last_checkpoint",
]
