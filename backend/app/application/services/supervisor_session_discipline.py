"""ST1 discipline — OP1 critic/LLM failure detection, halt + Celery revoke, LN1 hooks."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.hivemind_verify import critic_verdict_approved
from app.application.services.supervisor.session_service import apply_session_control
from app.application.services.supervisor.sub_agent_job import extract_celery_task_id
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession

logger = structlog.get_logger(__name__)

DisciplineReason = Literal["critic_failure", "llm_failure", "same_failure_twice"]


def _sub_agent_text(sub: SubAgentSession | Any) -> str:
    memory = dict(getattr(sub, "short_memory", None) or {})
    return str(memory.get("last_summary") or getattr(sub, "last_output", "") or "").strip()


def session_has_critic_failure(
    *,
    context_summary: dict[str, Any] | None,
    sub_agents: list[SubAgentSession | Any] | None = None,
) -> bool:
    """Return True when critic rubric / verification did not pass."""

    summary = dict(context_summary or {})
    if summary.get("critic_failure") is True:
        return True
    verify_status = str(summary.get("hivemind_verify_status") or "").strip().lower()
    if verify_status in {"rejected", "failed"}:
        return True

    from app.application.services.loop_guardrails_service import (
        is_loop_guardrails_active,
        last_rubric_score_from_summary,
        loop_min_score_from_summary,
    )

    if is_loop_guardrails_active(summary):
        last_score = last_rubric_score_from_summary(summary)
        min_score = loop_min_score_from_summary(summary)
        if last_score is not None and last_score < min_score:
            return True

    for sub in sub_agents or []:
        role = str(getattr(sub, "role", "") or "").lower()
        if role != "critic":
            continue
        text = _sub_agent_text(sub)
        if not text:
            continue
        first_line = next((line.strip().lower() for line in text.splitlines() if line.strip()), "")
        if first_line == "critic verdict: approve":
            continue
        if first_line == "critic verdict: reject":
            return True
        if "verification verdict" in text.lower() and not critic_verdict_approved(text):
            return True
        from app.application.services.loop_anti_cheat_service import loop_anti_cheat_blocks_critic_pass

        if loop_anti_cheat_blocks_critic_pass(output_text=text):
            return True
    return False


def session_has_llm_failure(
    *,
    context_summary: dict[str, Any] | None,
    sub_agents: list[SubAgentSession | Any] | None = None,
) -> bool:
    """Return True when LLM/self-heal exhausted without a verified pass."""

    summary = dict(context_summary or {})
    if summary.get("llm_failure") is True or summary.get("self_heal_exhausted") is True:
        return True
    reason = str(summary.get("discipline_halt_reason") or "").lower()
    if reason.startswith("llm") or "execution error" in reason:
        return True

    for sub in sub_agents or []:
        error = str(getattr(sub, "error_text", "") or "").lower()
        if "self-healing exhausted" in error or "llm execution error" in error:
            return True
        head = _sub_agent_text(sub).lower()[:240]
        if head.startswith("llm execution error") or " execution error:" in head:
            return True
    return False


def critic_failure_blocks_auto_approve(
    *,
    goal: str,
    context_summary: dict[str, Any] | None,
    sub_agents: list[SubAgentSession | Any] | None = None,
) -> bool:
    """OP1 / ST1.1 — block_auto_approve_on_critic_failure when critic or LLM failed."""

    del goal  # reserved for future goal-scoped rules
    return session_has_critic_failure(context_summary=context_summary, sub_agents=sub_agents) or session_has_llm_failure(
        context_summary=context_summary,
        sub_agents=sub_agents,
    )


def mark_discipline_failure_summary(
    summary: dict[str, Any],
    *,
    reason: DisciplineReason,
    detail: str = "",
) -> dict[str, Any]:
    """Stamp context_summary flags for downstream gates (distill, auto-approve)."""

    out = dict(summary)
    if reason == "critic_failure":
        out["critic_failure"] = True
    elif reason == "llm_failure":
        out["llm_failure"] = True
        out["self_heal_exhausted"] = True
    elif reason == "same_failure_twice":
        out["same_failure_twice"] = True
    if detail.strip():
        out["discipline_halt_reason"] = detail.strip()[:500]
    return out


async def revoke_durable_celery_tasks_for_session(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
    sub_agents: list[SubAgentSession] | None = None,
) -> int:
    """Revoke pending durable Celery sub-agent tasks (OP1 hard stop)."""

    from sqlalchemy import select

    subs = list(sub_agents or getattr(session_row, "sub_agents", None) or [])
    if not subs:
        subs = list(
            (
                await db.scalars(
                    select(SubAgentSession).where(SubAgentSession.supervisor_session_id == session_row.id),
                )
            ).all(),
        )

    from app.worker.celery_app import celery_app

    revoked = 0
    for sub in subs:
        task_id = extract_celery_task_id(dict(sub.short_memory or {}))
        if not task_id:
            continue
        try:
            celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
            revoked += 1
        except Exception as exc:  # noqa: BLE001 — best-effort revoke
            logger.warning(
                "supervisor_discipline.celery_revoke_failed",
                agent_id="supervisor_session_discipline",
                swarm_id=str(session_row.tenant_id),
                task_id=str(session_row.id),
                celery_task_id=task_id,
                error=str(exc),
            )
    return revoked


async def apply_session_discipline_halt(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
    reason: DisciplineReason,
    detail: str = "",
    sub_agents: list[SubAgentSession] | None = None,
) -> SupervisorSession:
    """Hard stop + Celery revoke when AFK discipline fails (OP1)."""

    summary = mark_discipline_failure_summary(
        dict(session_row.context_summary or {}),
        reason=reason,
        detail=detail or reason,
    )
    summary["discipline_halt_at"] = datetime.now(tz=UTC).isoformat()
    session_row.context_summary = summary

    revoked = await revoke_durable_celery_tasks_for_session(db, session_row=session_row, sub_agents=sub_agents)
    await apply_session_control(db, session_row=session_row, action="stop")

    from app.application.services.supervisor.runtime import append_event

    await append_event(
        db,
        supervisor_session=session_row,
        sub_agent=None,
        event_type="discipline_halt",
        message=f"Session halted: {reason} ({detail or reason}).",
        payload={"reason": reason, "detail": detail[:500], "celery_revoked": revoked},
        level="error",
    )
    logger.info(
        "supervisor_session_discipline_halt",
        agent_id="supervisor_session_discipline",
        swarm_id=str(session_row.tenant_id),
        task_id=str(session_row.id),
        reason=reason,
        celery_revoked=revoked,
    )
    return session_row


async def handle_unresolved_supervisor_step(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
    sub_agent: SubAgentSession,
    issues: list[str],
) -> bool:
    """LN1 + OP1 — halt instead of false auto-approve. Returns True when halted."""

    from app.application.services.loop_guardrails_service import record_same_failure_signature

    summary = dict(session_row.context_summary or {})
    halt_same, summary = record_same_failure_signature(
        summary,
        issues=issues,
        role=str(sub_agent.role or ""),
        error_text=str(sub_agent.error_text or ""),
    )
    session_row.context_summary = summary
    if halt_same:
        await apply_session_discipline_halt(
            db,
            session_row=session_row,
            reason="same_failure_twice",
            detail=str(summary.get("discipline_halt_reason") or "same_failure_twice"),
            sub_agents=[sub_agent],
        )
        return True

    await apply_session_discipline_halt(
        db,
        session_row=session_row,
        reason="llm_failure",
        detail="Self-healing exhausted without verified pass.",
        sub_agents=[sub_agent],
    )
    return True


async def handle_critic_rejection_if_any(
    db: AsyncSession,
    *,
    session_row: SupervisorSession,
    sub_agent: SubAgentSession,
) -> bool:
    """Halt durable/inprocess session when critic verdict fails."""

    if str(sub_agent.role or "").strip().lower() != "critic":
        return False
    if not session_has_critic_failure(
        context_summary=dict(session_row.context_summary or {}),
        sub_agents=[sub_agent],
    ):
        return False

    summary = mark_discipline_failure_summary(
        dict(session_row.context_summary or {}),
        reason="critic_failure",
        detail="Critic verdict did not pass verification.",
    )
    session_row.context_summary = summary
    await apply_session_discipline_halt(
        db,
        session_row=session_row,
        reason="critic_failure",
        detail="Critic verdict did not pass verification.",
        sub_agents=[sub_agent],
    )
    return True


__all__ = [
    "apply_session_discipline_halt",
    "critic_failure_blocks_auto_approve",
    "handle_critic_rejection_if_any",
    "handle_unresolved_supervisor_step",
    "mark_discipline_failure_summary",
    "revoke_durable_celery_tasks_for_session",
    "session_has_critic_failure",
    "session_has_llm_failure",
]
