"""LR1 — Checkpoint resume CTA for prominent session list affordance."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.checkpoint_resume import build_session_checkpoint_snapshot
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)

PROMINENT_SESSION_STATUSES = frozenset({"paused", "failed", "needs_input", "running"})


class CheckpointResumeCtaOut(BaseModel):
    """Session list checkpoint resume snapshot for LR1."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    visible: bool = False
    session_id: uuid.UUID
    session_status: str
    runtime_mode: str
    can_resume_from_checkpoint: bool = False
    resume_hint: str = ""
    last_verified_role: str | None = None
    next_resumable_role: str | None = None
    verified_steps: int = 0
    total_steps: int = 0
    loop_chip: str = ""
    primary_label: str = "Resume from checkpoint"
    operator_guidance: str = "Jump to the next retryable step after the last verified sub-agent."


def _loop_chip(*, verified: int, total: int, next_role: str | None) -> str:
    if total <= 0:
        return "Checkpoint"
    base = f"Checkpoint {verified}/{total}"
    if next_role:
        return f"{base} → {next_role}"
    return base


def derive_checkpoint_resume_cta(session) -> CheckpointResumeCtaOut:  # noqa: ANN001
    """Build LR1 checkpoint resume CTA from a supervisor session row."""

    snapshot = build_session_checkpoint_snapshot(session)
    session_status = str(getattr(session, "status", "")).strip().lower()
    runtime_mode = str(getattr(session, "runtime_mode", "inprocess")).strip().lower()
    verified_steps = sum(1 for step in snapshot.steps if step.is_verified_checkpoint)
    total_steps = len(snapshot.steps)

    visible = (
        snapshot.can_resume_from_checkpoint
        and session_status in PROMINENT_SESSION_STATUSES
        and total_steps > 0
    )

    guidance = snapshot.resume_hint
    if visible and snapshot.next_resumable_role and snapshot.last_verified_role:
        guidance = (
            f"Verified through {snapshot.last_verified_role}. "
            f"Resume continues at {snapshot.next_resumable_role} without replaying completed lanes."
        )
    elif visible and snapshot.next_resumable_role:
        guidance = f"Resume at {snapshot.next_resumable_role} — durable steps requeue from this checkpoint."

    return CheckpointResumeCtaOut(
        enabled=True,
        visible=visible,
        session_id=session.id,
        session_status=session_status,
        runtime_mode=runtime_mode,
        can_resume_from_checkpoint=snapshot.can_resume_from_checkpoint,
        resume_hint=snapshot.resume_hint,
        last_verified_role=snapshot.last_verified_role,
        next_resumable_role=snapshot.next_resumable_role,
        verified_steps=verified_steps,
        total_steps=total_steps,
        loop_chip=_loop_chip(
            verified=verified_steps,
            total=total_steps,
            next_role=snapshot.next_resumable_role,
        ),
        operator_guidance=guidance,
    )


async def compose_checkpoint_resume_cta(
    session: AsyncSession,
    *,
    supervisor_session,
) -> CheckpointResumeCtaOut:  # noqa: ANN001
    """Compose LR1 checkpoint resume CTA for one supervisor session."""

    if not settings.checkpoint_resume_cta_enabled:
        return CheckpointResumeCtaOut(
            enabled=False,
            visible=False,
            session_id=supervisor_session.id,
            session_status=str(getattr(supervisor_session, "status", "")),
            runtime_mode=str(getattr(supervisor_session, "runtime_mode", "inprocess")),
        )

    panel = derive_checkpoint_resume_cta(supervisor_session)
    _logger.info(
        "checkpoint_resume_cta.composed",
        agent_id="checkpoint_resume_cta",
        swarm_id=str(supervisor_session.id),
        task_id=str(supervisor_session.task_id) if supervisor_session.task_id else None,
        visible=panel.visible,
        verified_steps=panel.verified_steps,
        total_steps=panel.total_steps,
    )
    return panel


__all__ = [
    "CheckpointResumeCtaOut",
    "compose_checkpoint_resume_cta",
    "derive_checkpoint_resume_cta",
]
