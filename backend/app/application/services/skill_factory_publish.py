"""Publish verified skill forge proposals into tenant registry + recipes."""

from __future__ import annotations

import re
import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.skill_factory_service import (
    complete_opportunity_with_skill,
    register_tenant_skill_from_markdown,
    slugify_skill_name,
)
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

logger = structlog.get_logger(__name__)

_TITLE_RE = re.compile(r"^#\s+(.+)", re.MULTILINE)


def _extract_title(markdown: str, fallback: str) -> str:
    match = _TITLE_RE.search(markdown)
    if match:
        return match.group(1).strip()[:200]
    return fallback[:200]


async def publish_verified_skill_forge(
    session: AsyncSession,
    *,
    suggestion: AgentSuggestion,
    tenant_id: uuid.UUID,
) -> dict[str, Any] | None:
    """On approve: persist tenant skill + link factory opportunity if present."""

    if suggestion.proposal_type != "verified_skill_forge":
        return None
    if suggestion.status != "approved":
        return None

    payload = dict(suggestion.proposal_payload or {})
    skill_md = str(payload.get("skill_markdown") or "").strip()
    if len(skill_md) < 40:
        return {"ok": False, "error": "empty_skill_markdown"}

    sup: SupervisorSession | None = None
    if suggestion.supervisor_session_id is not None:
        sup = await session.get(SupervisorSession, suggestion.supervisor_session_id)

    goal = str(sup.goal if sup else suggestion.title or "Verified skill")
    title = _extract_title(skill_md, suggestion.title or "Verified skill")
    slug = slugify_skill_name(title)
    keywords = ["skill-factory", "verified"]
    if "skill-factory-ready" in goal.lower():
        keywords.append("factory-ready")

    skill_row = await register_tenant_skill_from_markdown(
        session,
        tenant_id=tenant_id,
        slug=slug,
        title=title,
        markdown_body=skill_md,
        description=suggestion.description or "",
        roles=["researcher", "coder", "orchestrator"],
        keywords=keywords,
        source="verified_skill_forge",
        mark_verified=True,
        recipe_name=f"Skill Factory — {title[:160]}",
        workflow_template={
            "seed_key": "SKILL_FACTORY_FORGE",
            "steps": [
                {
                    "description": "Apply exported SKILL.md workflow",
                    "agent_role": "researcher",
                    "guardrails": {"simulate_first": True},
                    "evaluation_criteria": {"critic_approve": True},
                },
            ],
        },
    )

    opportunity: SkillOpportunityORM | None = None
    if sup is not None:
        opportunity = await session.scalar(
            select(SkillOpportunityORM).where(
                SkillOpportunityORM.tenant_id == tenant_id,
                SkillOpportunityORM.supervisor_session_id == sup.id,
            ),
        )
    if opportunity is not None:
        await complete_opportunity_with_skill(
            session,
            tenant_id=tenant_id,
            opportunity_id=opportunity.id,
            skill=skill_row,
        )

    logger.info(
        "skill_factory.forge_published",
        agent_id="skill_factory",
        swarm_id=str(tenant_id),
        task_id=str(suggestion.id),
        skill_slug=skill_row.slug,
    )
    return {
        "ok": True,
        "tenant_skill_id": str(skill_row.id),
        "slug": skill_row.slug,
        "recipe_id": str(skill_row.recipe_id) if skill_row.recipe_id else None,
        "opportunity_id": str(opportunity.id) if opportunity else None,
    }


__all__ = ["publish_verified_skill_forge"]
