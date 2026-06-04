"""Researcher → critic verification gate before HiveMind insight ingest."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.hivemind_insight_ingest import ingest_supervisor_insights
from app.application.services.supervisor.session_service import enqueue_durable_sub_agent_step
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession

HIVEMIND_VERIFY_KEY = "hivemind_verify_before_ingest"
_RE_APPROVED = re.compile(r"verification verdict:\s*approved\b", re.IGNORECASE)
_RE_REJECTED = re.compile(r"verification verdict:\s*rejected\b", re.IGNORECASE)


def is_hivemind_verify_session(context_summary: dict[str, Any] | None) -> bool:
    """Return True when insights must pass critic review before graph ingest."""

    if not isinstance(context_summary, dict):
        return False
    return bool(context_summary.get(HIVEMIND_VERIFY_KEY))


def enable_hivemind_verify_seed(*, roles: list[str] | None = None) -> dict[str, object]:
    """Context seed for Sentinel / HiveMind learning sessions."""

    normalized = [str(r).strip().lower() for r in (roles or []) if str(r).strip()]
    seed: dict[str, object] = {HIVEMIND_VERIFY_KEY: True}
    if "researcher" in normalized and "critic" in normalized:
        seed["hivemind_verify_roles"] = ["researcher", "critic"]
    return seed


def critic_verdict_approved(critic_output: str) -> bool:
    """Parse critic markdown for an explicit APPROVED verdict."""

    text = critic_output.strip()
    if not text:
        return False
    if _RE_REJECTED.search(text):
        return False
    return bool(_RE_APPROVED.search(text))


async def load_researcher_draft(
    db: AsyncSession,
    *,
    supervisor_session_id: uuid.UUID,
) -> str:
    """Load the latest completed researcher summary for critic verification."""

    row = await db.scalar(
        select(SubAgentSession)
        .where(
            SubAgentSession.supervisor_session_id == supervisor_session_id,
            SubAgentSession.role == "researcher",
        )
        .order_by(SubAgentSession.spawn_order.asc())
        .limit(1),
    )
    if row is None:
        return ""
    memory = dict(row.short_memory or {})
    draft = str(memory.get("last_summary") or row.last_output or "").strip()
    return draft


def build_critic_verify_user_block(*, researcher_draft: str) -> str:
    """Extra user prompt block for critic verification step."""

    return (
        "## Researcher draft (verify before HiveMind ingest)\n"
        f"{researcher_draft[:12000]}\n\n"
        "## Your task\n"
        "Review every claim for source URL evidence, duplication against HiveMind, and simulate-first guardrails.\n"
        "End your response with exactly one line:\n"
        "- `## Verification verdict: APPROVED` — draft is verified; insights may ingest.\n"
        "- `## Verification verdict: REJECTED — <short reason>` — block ingest.\n"
        "If APPROVED, you may add one short `[INSIGHT]` addendum tagged `hivemind-candidate`."
    )


async def finalize_hivemind_ingest_after_critic(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    critic_output: str,
    researcher_draft: str | None = None,
) -> tuple[bool, list[str]]:
    """Ingest researcher draft when critic approves; return (approved, doc_ids)."""

    if supervisor_session.tenant_id is None:
        return False, []
    if not critic_verdict_approved(critic_output):
        return False, []

    draft = (researcher_draft or "").strip()
    if not draft:
        draft = await load_researcher_draft(db, supervisor_session_id=supervisor_session.id)
    if not draft:
        return True, []

    combined = (
        f"{draft.rstrip()}\n\n---\n## Critic verification (approved)\n{critic_output.strip()[:8000]}"
    )
    doc_ids = await ingest_supervisor_insights(
        db,
        tenant_id=supervisor_session.tenant_id,
        supervisor_session_id=supervisor_session.id,
        sub_agent_role="researcher",
        llm_output=combined,
    )
    summary = dict(supervisor_session.context_summary or {})
    summary["hivemind_insights_ingested"] = len(doc_ids)
    summary["hivemind_verify_status"] = "approved"
    supervisor_session.context_summary = summary
    await db.flush()

    from app.application.services.verified_skill_forge import propose_verified_skill_from_session
    from app.application.services.publish_pack import try_archive_publish_pack_from_session_output

    await propose_verified_skill_from_session(
        db,
        supervisor_session=supervisor_session,
        researcher_draft=draft,
        critic_output=critic_output,
        insight_doc_ids=doc_ids,
    )
    await try_archive_publish_pack_from_session_output(
        db,
        supervisor_session=supervisor_session,
        combined_output=combined,
        critic_excerpt=critic_output,
    )
    return True, doc_ids


async def enqueue_next_verify_sub_agent(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    completed_sub: SubAgentSession,
) -> int:
    """After researcher completes in verify lane, enqueue the next sub-agent (critic)."""

    if not is_hivemind_verify_session(dict(supervisor_session.context_summary or {})):
        return 0
    if str(completed_sub.role or "").strip().lower() != "researcher":
        return 0

    summary = dict(supervisor_session.context_summary or {})
    summary["researcher_draft_for_verify"] = str(
        (completed_sub.short_memory or {}).get("last_summary") or completed_sub.last_output or "",
    )[:50_000]
    supervisor_session.context_summary = summary

    next_sub = await db.scalar(
        select(SubAgentSession)
        .where(
            SubAgentSession.supervisor_session_id == supervisor_session.id,
            SubAgentSession.spawn_order > int(completed_sub.spawn_order or 0),
            SubAgentSession.status.in_(("pending", "queued")),
        )
        .order_by(SubAgentSession.spawn_order.asc())
        .limit(1),
    )
    if next_sub is None:
        return 0
    await enqueue_durable_sub_agent_step(
        db,
        supervisor_session=supervisor_session,
        sub_agent=next_sub,
        reason="hivemind_verify_chain",
    )
    return 1


def should_enqueue_only_first_sub_agent(context_summary: dict[str, Any] | None) -> bool:
    """Durable verify/factory lanes start with one sub-agent; chain continues on completion."""

    if is_hivemind_verify_session(context_summary):
        return True
    from app.application.services.skill_factory_session_prompts import (
        should_enqueue_only_first_factory_sub_agent,
    )

    if should_enqueue_only_first_factory_sub_agent(context_summary):
        return True

    from app.application.services.content_pack_factory_session_prompts import (
        should_enqueue_only_first_content_pack_sub_agent,
    )

    return should_enqueue_only_first_content_pack_sub_agent(context_summary)


__all__ = [
    "HIVEMIND_VERIFY_KEY",
    "build_critic_verify_user_block",
    "critic_verdict_approved",
    "enable_hivemind_verify_seed",
    "enqueue_next_verify_sub_agent",
    "finalize_hivemind_ingest_after_critic",
    "is_hivemind_verify_session",
    "load_researcher_draft",
    "should_enqueue_only_first_sub_agent",
]
