"""Skill Factory — verified_skill_forge proposals when factory sessions complete."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.skill_factory_quality_gate import evaluate_factory_outputs
from app.application.services.verified_skill_forge import _extract_skill_title
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession

logger = get_logger(__name__)

_SKILL_FENCE_RE = re.compile(
    r"```(?:yaml|markdown|md)?\s*\n(---\nname:[\s\S]*?\n---[\s\S]*?)```",
    re.IGNORECASE,
)
_SKILL_FRONTMATTER_RE = re.compile(
    r"(---\nname:[\s\S]*?\n---[\s\S]{80,}?)(?=\n#{1,3}\s+[A-Z]|\n---\n|\Z)",
    re.IGNORECASE,
)


def is_content_pack_factory_session(session: SupervisorSession) -> bool:
    """Return True when session goal targets Content Pack Factory production."""

    ctx = dict(session.context_summary or {})
    if ctx.get("content_pack_factory") is True:
        return True
    raw = str(ctx.get("raw_goal") or session.goal or "").lower()
    return "content pack factory" in raw or "content-pack-factory-ready" in raw


def is_skill_factory_session(session: SupervisorSession) -> bool:
    """Return True when session goal targets Skill Factory production."""

    if is_content_pack_factory_session(session):
        return False
    ctx = dict(session.context_summary or {})
    if ctx.get("skill_factory") is True:
        return True
    raw = str(ctx.get("raw_goal") or session.goal or "").lower()
    return "skill factory" in raw or "skill-factory-ready" in raw


def extract_skill_markdown_from_outputs(*, coder_output: str, critic_output: str, goal: str) -> str:
    """Best-effort SKILL.md extraction from factory session sub-agent outputs."""

    for source in (coder_output, critic_output, f"{coder_output}\n\n{critic_output}"):
        text = source.strip()
        if not text:
            continue
        match = _SKILL_FENCE_RE.search(text)
        if match and len(match.group(1).strip()) >= 80:
            return match.group(1).strip()[:20_000]
        match = _SKILL_FRONTMATTER_RE.search(text)
        if match and len(match.group(1).strip()) >= 80:
            return match.group(1).strip()[:20_000]
    return _build_fallback_skill_markdown(goal=goal, coder_output=coder_output, critic_output=critic_output)


def _build_fallback_skill_markdown(*, goal: str, coder_output: str, critic_output: str) -> str:
    """Minimal SKILL.md when structured extraction fails."""

    if len(coder_output.strip()) < 40:
        return ""
    return (
        "---\n"
        "name: skill-factory-output\n"
        "description: Draft from Skill Factory session — review before publish\n"
        "level: 1\n"
        "---\n\n"
        "# Skill Factory draft\n\n"
        f"## Goal\n{goal[:1200]}\n\n"
        f"## Coder draft (excerpt)\n{coder_output.strip()[:4000]}\n\n"
        f"## Critic notes (excerpt)\n{critic_output.strip()[:2000]}\n"
    )


async def _load_sub_agent_output(
    db: AsyncSession,
    *,
    supervisor_session_id: uuid.UUID,
    role: str,
) -> str:
    """Load latest output text for one sub-agent role."""

    row = await db.scalar(
        select(SubAgentSession)
        .where(
            SubAgentSession.supervisor_session_id == supervisor_session_id,
            SubAgentSession.role == role,
        )
        .order_by(SubAgentSession.spawn_order.asc())
        .limit(1),
    )
    if row is None:
        return ""
    memory = dict(row.short_memory or {})
    return str(memory.get("last_summary") or row.last_output or "").strip()


async def propose_skill_factory_forge_from_session(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
) -> AgentSuggestion | None:
    """Create pending verified_skill_forge when a Skill Factory session completes."""

    if not settings.agent_initiative_enabled or not settings.skill_factory_enabled:
        return None
    if supervisor_session.tenant_id is None:
        return None
    if not is_skill_factory_session(supervisor_session):
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

    coder_output = await _load_sub_agent_output(
        db,
        supervisor_session_id=supervisor_session.id,
        role="coder",
    )
    critic_output = await _load_sub_agent_output(
        db,
        supervisor_session_id=supervisor_session.id,
        role="critic",
    )
    ctx = dict(supervisor_session.context_summary or {})
    goal = str(ctx.get("raw_goal") or supervisor_session.goal or "")
    skill_md = extract_skill_markdown_from_outputs(
        coder_output=coder_output,
        critic_output=critic_output,
        goal=goal,
    )
    quality = evaluate_factory_outputs(
        skill_markdown=skill_md,
        critic_output=critic_output,
        coder_output=coder_output,
    )
    if len(quality.skill_markdown) < 40:
        logger.info(
            "skill_factory.forge_skipped_empty",
            agent_id="skill_factory",
            swarm_id=str(supervisor_session.tenant_id),
            task_id=str(supervisor_session.id),
            issues=quality.issues,
        )
        return None

    opportunity = await db.scalar(
        select(SkillOpportunityORM).where(
            SkillOpportunityORM.tenant_id == supervisor_session.tenant_id,
            SkillOpportunityORM.supervisor_session_id == supervisor_session.id,
        ),
    )
    title_base = opportunity.title if opportunity is not None else _extract_skill_title(goal=goal, draft_excerpt=coder_output)
    payload: dict[str, Any] = {
        "skill_markdown": quality.skill_markdown,
        "source": "skill_factory",
        "factory_opportunity_id": str(opportunity.id) if opportunity else None,
        **quality.to_payload(),
    }
    description = (
        "Skill Factory session passed quality gate — approve to publish into Library and enable GitHub export."
        if quality.passed
        else (
            "Skill Factory session completed with quality warnings — review critic verdict and SKILL.md "
            f"before publish. Issues: {', '.join(quality.issues[:6]) or 'unknown'}."
        )
    )

    row = AgentSuggestion(
        tenant_id=supervisor_session.tenant_id,
        supervisor_session_id=supervisor_session.id,
        sub_agent_session_id=None,
        proposal_type="verified_skill_forge",
        proposed_by_role="skill_factory",
        title=title_base[:260],
        description=description[:2000],
        proposal_payload=payload,
        risk_level="low" if quality.passed else "medium",
        impact_score=0.82 if quality.passed else 0.55,
        status="pending",
        requires_manual_approval=True,
        evaluation_reason=(
            "skill_factory_session_completed"
            if quality.passed
            else "skill_factory_quality_gate_warnings"
        ),
    )
    db.add(row)
    await db.flush()
    logger.info(
        "skill_factory.forge_proposed",
        agent_id="skill_factory",
        swarm_id=str(supervisor_session.tenant_id),
        task_id=str(supervisor_session.id),
        suggestion_id=str(row.id),
    )
    return row


__all__ = [
    "extract_skill_markdown_from_outputs",
    "is_skill_factory_session",
    "propose_skill_factory_forge_from_session",
]
