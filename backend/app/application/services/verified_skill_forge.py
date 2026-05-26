"""Verified Skill Forge — draft skill proposals from critic-approved HiveMind sessions."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

logger = get_logger(__name__)

_RE_INSIGHT = re.compile(r"\[INSIGHT\][^\n]*", re.IGNORECASE)


def _extract_skill_title(*, goal: str, draft_excerpt: str) -> str:
    goal_line = (goal or "").split("\n", 1)[0].strip()
    if goal_line:
        return f"Verified skill: {goal_line[:120]}"
    first_insight = _RE_INSIGHT.search(draft_excerpt or "")
    if first_insight:
        return f"Verified skill: {first_insight.group(0)[:120]}"
    return "Verified skill from HiveMind session"


def _build_skill_markdown(*, goal: str, draft: str, critic_excerpt: str) -> str:
    return (
        "---\n"
        "name: hivemind-verified-skill\n"
        "description: Auto-drafted from critic-approved supervisor session\n"
        "level: 1\n"
        "---\n\n"
        "# Verified workflow skill\n\n"
        f"## Goal pattern\n{goal[:800]}\n\n"
        f"## Researcher draft (excerpt)\n{draft[:2500]}\n\n"
        f"## Critic verification\n{critic_excerpt[:1200]}\n"
    )


async def propose_verified_skill_from_session(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
    researcher_draft: str,
    critic_output: str,
    insight_doc_ids: list[str],
) -> AgentSuggestion | None:
    """Create a pending skill proposal when HiveMind verify lane approves ingest."""

    if not settings.agent_initiative_enabled:
        return None
    if supervisor_session.tenant_id is None:
        return None
    if not insight_doc_ids:
        return None

    existing = await db.scalar(
        select(AgentSuggestion).where(
            AgentSuggestion.tenant_id == supervisor_session.tenant_id,
            AgentSuggestion.supervisor_session_id == supervisor_session.id,
            AgentSuggestion.proposal_type == "verified_skill_forge",
        ),
    )
    if existing is not None:
        return existing

    goal = str(supervisor_session.goal or "")
    skill_md = _build_skill_markdown(
        goal=goal,
        draft=researcher_draft,
        critic_excerpt=critic_output,
    )
    title = _extract_skill_title(goal=goal, draft_excerpt=researcher_draft)
    payload: dict[str, Any] = {
        "skill_markdown": skill_md,
        "insight_doc_ids": insight_doc_ids,
        "hivemind_verify_status": "approved",
        "source": "verified_skill_forge",
    }

    row = AgentSuggestion(
        tenant_id=supervisor_session.tenant_id,
        supervisor_session_id=supervisor_session.id,
        sub_agent_session_id=None,
        proposal_type="verified_skill_forge",
        proposed_by_role="critic",
        title=title,
        description=(
            "Critic-approved HiveMind session — publish as reusable skill + recipe after operator review."
        ),
        proposal_payload=payload,
        risk_level="low",
        impact_score=0.72,
        status="pending",
        requires_manual_approval=True,
        evaluation_reason="verified_hivemind_critic_approved",
    )
    db.add(row)
    await db.flush()
    logger.info(
        "verified_skill_forge.proposed",
        agent_id="critic",
        swarm_id=str(supervisor_session.id),
        task_id=str(row.id),
        insight_count=len(insight_doc_ids),
    )
    return row


__all__ = ["propose_verified_skill_from_session"]
