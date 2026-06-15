"""LOOP4 — Mid-flight checkpoint UX: pause → review → approve → continue."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.checkpoint_resume import build_session_checkpoint_snapshot
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)

CheckpointState = Literal["running", "paused", "needs_input", "closed"]
ActionId = Literal[
    "pause_loop",
    "approve_continue",
    "reject_revise",
    "resume_session",
    "resume_checkpoint",
]
ActionVariant = Literal["primary", "secondary", "danger", "ghost"]


class MidFlightCheckpointActionOut(BaseModel):
    """One operator control for mid-flight checkpoint bar."""

    model_config = ConfigDict(extra="ignore")

    action_id: ActionId
    label: str
    enabled: bool = True
    variant: ActionVariant = "ghost"
    reason_disabled: str | None = None


class MidFlightCheckpointSummaryOut(BaseModel):
    """Compact checkpoint resume metadata."""

    model_config = ConfigDict(extra="ignore")

    can_resume_from_checkpoint: bool = False
    resume_hint: str = ""
    last_verified_role: str | None = None
    next_resumable_role: str | None = None
    verified_steps: int = 0
    total_steps: int = 0


class MidFlightCheckpointOut(BaseModel):
    """Session mid-flight checkpoint snapshot for LOOP4 UI."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    visible: bool = False
    session_id: uuid.UUID
    session_status: str
    checkpoint_state: CheckpointState
    loop_phase: str | None = None
    loop_chip: str | None = None
    headline: str = ""
    operator_guidance: str = ""
    primary_action_id: ActionId | None = None
    pending_approval: bool = False
    approval_reason: str | None = None
    checkpoint: MidFlightCheckpointSummaryOut = Field(default_factory=MidFlightCheckpointSummaryOut)
    actions: list[MidFlightCheckpointActionOut] = Field(default_factory=list)


def _resolve_checkpoint_state(session_status: str) -> CheckpointState:
    """Map raw session status to checkpoint UX state."""

    normalized = session_status.strip().lower()
    if normalized == "paused":
        return "paused"
    if normalized == "needs_input":
        return "needs_input"
    if normalized in {"stopped", "completed", "failed", "cancelled"}:
        return "closed"
    return "running"


def _build_actions(
    *,
    checkpoint_state: CheckpointState,
    can_resume_checkpoint: bool,
    pending_approval: bool,
    light_control_plane_enabled: bool,
) -> list[MidFlightCheckpointActionOut]:
    """Derive enabled operator actions for mid-flight checkpoint bar."""

    actions: list[MidFlightCheckpointActionOut] = []

    pause_enabled = checkpoint_state in {"running", "needs_input"}
    actions.append(
        MidFlightCheckpointActionOut(
            action_id="pause_loop",
            label="Pause loop",
            enabled=pause_enabled,
            variant="ghost",
            reason_disabled=None if pause_enabled else "Session is not actively running.",
        ),
    )

    approve_enabled = checkpoint_state == "needs_input" and light_control_plane_enabled
    actions.append(
        MidFlightCheckpointActionOut(
            action_id="approve_continue",
            label="Approve & continue",
            enabled=approve_enabled,
            variant="primary",
            reason_disabled=(
                None
                if approve_enabled
                else "Available when session waits for operator input."
            ),
        ),
    )

    reject_enabled = checkpoint_state == "needs_input" and light_control_plane_enabled
    actions.append(
        MidFlightCheckpointActionOut(
            action_id="reject_revise",
            label="Reject & revise",
            enabled=reject_enabled,
            variant="danger",
            reason_disabled=(
                None
                if reject_enabled
                else "Available when session waits for operator input."
            ),
        ),
    )

    resume_session_enabled = checkpoint_state == "paused"
    actions.append(
        MidFlightCheckpointActionOut(
            action_id="resume_session",
            label="Resume session",
            enabled=resume_session_enabled,
            variant="secondary",
            reason_disabled=None if resume_session_enabled else "Pause the loop first to use Resume session.",
        ),
    )

    resume_checkpoint_enabled = can_resume_checkpoint and checkpoint_state in {"paused", "needs_input"}
    actions.append(
        MidFlightCheckpointActionOut(
            action_id="resume_checkpoint",
            label="Resume from checkpoint",
            enabled=resume_checkpoint_enabled,
            variant="secondary",
            reason_disabled=(
                None
                if resume_checkpoint_enabled
                else "No verified checkpoint with a retryable next step."
            ),
        ),
    )

    if pending_approval and checkpoint_state == "needs_input":
        for action in actions:
            if action.action_id == "approve_continue":
                action.label = "Approve gate & continue"

    return actions


def _resolve_primary_action(
    *,
    checkpoint_state: CheckpointState,
    can_resume_checkpoint: bool,
    actions: list[MidFlightCheckpointActionOut],
) -> ActionId | None:
    """Pick the dominant CTA for operator focus."""

    if checkpoint_state == "needs_input":
        return "approve_continue"
    if checkpoint_state == "paused":
        if can_resume_checkpoint:
            return "resume_checkpoint"
        return "resume_session"
    if checkpoint_state == "running":
        return "pause_loop"
    enabled = next((action.action_id for action in actions if action.enabled), None)
    return enabled


def _headline_for_state(
    *,
    checkpoint_state: CheckpointState,
    loop_phase: str | None,
    pending_approval: bool,
) -> str:
    """Short headline for checkpoint panel."""

    if checkpoint_state == "needs_input":
        if pending_approval:
            return "Mid-flight checkpoint — approval required"
        return "Mid-flight checkpoint — verify before continue"
    if checkpoint_state == "paused":
        return "Loop paused — review or resume when ready"
    if checkpoint_state == "running" and loop_phase:
        return f"Loop active — {loop_phase} phase"
    if checkpoint_state == "running":
        return "Loop running — pause to inspect mid-flight"
    return "Session closed"


def derive_mid_flight_checkpoint(
    *,
    session,
    checkpoint_snapshot,
    loop_phase: str | None = None,
    loop_chip: str | None = None,
) -> MidFlightCheckpointOut:  # noqa: ANN001
    """Build LOOP4 mid-flight checkpoint panel from session + checkpoint snapshot."""

    session_status = str(getattr(session, "status", ""))
    summary = dict(getattr(session, "context_summary", None) or {})
    pending_approval = bool(summary.get("approval_required"))
    approval_reason = str(summary.get("approval_reason") or "").strip() or None

    checkpoint_state = _resolve_checkpoint_state(session_status)
    verified_steps = sum(1 for step in checkpoint_snapshot.steps if step.is_verified_checkpoint)
    checkpoint_summary = MidFlightCheckpointSummaryOut(
        can_resume_from_checkpoint=checkpoint_snapshot.can_resume_from_checkpoint,
        resume_hint=checkpoint_snapshot.resume_hint,
        last_verified_role=checkpoint_snapshot.last_verified_role,
        next_resumable_role=checkpoint_snapshot.next_resumable_role,
        verified_steps=verified_steps,
        total_steps=len(checkpoint_snapshot.steps),
    )

    actions = _build_actions(
        checkpoint_state=checkpoint_state,
        can_resume_checkpoint=checkpoint_snapshot.can_resume_from_checkpoint,
        pending_approval=pending_approval,
        light_control_plane_enabled=settings.light_control_plane_enabled,
    )
    primary_action_id = _resolve_primary_action(
        checkpoint_state=checkpoint_state,
        can_resume_checkpoint=checkpoint_snapshot.can_resume_from_checkpoint,
        actions=actions,
    )

    visible = checkpoint_state in {"needs_input", "paused"} or (
        checkpoint_state == "running" and pending_approval
    )

    if checkpoint_state == "needs_input":
        operator_guidance = (
            "Review tool outcomes and critic score, then Approve & continue or Reject & revise. "
            "Pause first if you need more time."
        )
        if pending_approval and approval_reason:
            operator_guidance = (
                f"{approval_reason} — inspect evidence below, then Approve gate & continue or Reject & revise."
            )
    elif checkpoint_state == "paused":
        operator_guidance = checkpoint_snapshot.resume_hint or "Resume session or jump from last verified checkpoint."
    elif checkpoint_state == "running":
        operator_guidance = "Pause the loop to hold execution while you review mid-flight progress."
    else:
        operator_guidance = "No mid-flight actions available for closed sessions."

    return MidFlightCheckpointOut(
        enabled=True,
        visible=visible,
        session_id=session.id,
        session_status=session_status,
        checkpoint_state=checkpoint_state,
        loop_phase=loop_phase,
        loop_chip=loop_chip,
        headline=_headline_for_state(
            checkpoint_state=checkpoint_state,
            loop_phase=loop_phase,
            pending_approval=pending_approval,
        ),
        operator_guidance=operator_guidance,
        primary_action_id=primary_action_id,
        pending_approval=pending_approval,
        approval_reason=approval_reason,
        checkpoint=checkpoint_summary,
        actions=actions,
    )


async def compose_mid_flight_checkpoint(
    session: AsyncSession,
    *,
    supervisor_session,
) -> MidFlightCheckpointOut:  # noqa: ANN001
    """Load loop phase and compose LOOP4 mid-flight checkpoint panel."""

    if not settings.mid_flight_checkpoint_enabled:
        return MidFlightCheckpointOut(
            enabled=False,
            visible=False,
            session_id=supervisor_session.id,
            session_status=str(getattr(supervisor_session, "status", "")),
            checkpoint_state="closed",
        )

    checkpoint_snapshot = build_session_checkpoint_snapshot(supervisor_session)

    loop_phase: str | None = None
    loop_chip: str | None = None
    if settings.agent_loop_timeline_enabled:
        from app.application.services.agent_loop_timeline_service import compose_agent_loop_timeline

        timeline = await compose_agent_loop_timeline(session, supervisor_session=supervisor_session)
        if timeline.enabled:
            loop_phase = timeline.current_phase
            loop_chip = timeline.loop_chip

    panel = derive_mid_flight_checkpoint(
        session=supervisor_session,
        checkpoint_snapshot=checkpoint_snapshot,
        loop_phase=loop_phase,
        loop_chip=loop_chip,
    )
    _logger.info(
        "mid_flight_checkpoint.composed",
        agent_id="mid_flight_checkpoint",
        swarm_id=str(supervisor_session.id),
        task_id=str(supervisor_session.task_id) if supervisor_session.task_id else None,
        checkpoint_state=panel.checkpoint_state,
        visible=panel.visible,
    )
    return panel


__all__ = [
    "MidFlightCheckpointActionOut",
    "MidFlightCheckpointOut",
    "MidFlightCheckpointSummaryOut",
    "compose_mid_flight_checkpoint",
    "derive_mid_flight_checkpoint",
]
