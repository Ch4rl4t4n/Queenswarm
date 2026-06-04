"""Content Pack Factory — verified_content_pack_forge proposals on session complete."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.content_pack_factory_quality_gate import evaluate_content_pack_outputs
from app.application.services.publish_pack import extract_publish_pack_json
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.content_pack_opportunity import ContentPackOpportunityORM
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession

logger = get_logger(__name__)

_LISTING_FENCE_RE = re.compile(r"```(?:markdown|md)?\s*\n(# LISTING[\s\S]*?)```", re.IGNORECASE)
_LISTING_HEADING_RE = re.compile(r"(# LISTING[^\n]*\n[\s\S]{80,}?)(?=\n#{1,3}\s|\Z)", re.IGNORECASE)


def is_content_pack_factory_session(session: SupervisorSession) -> bool:
    """Return True when session goal targets Content Pack Factory production."""

    ctx = dict(session.context_summary or {})
    if ctx.get("content_pack_factory") is True:
        return True
    raw = str(ctx.get("raw_goal") or session.goal or "").lower()
    return "content pack factory" in raw or "content-pack-factory-ready" in raw


def extract_listing_markdown(*, coder_output: str, critic_output: str) -> str:
    """Best-effort LISTING.md extraction from factory session outputs."""

    for source in (coder_output, critic_output, f"{coder_output}\n\n{critic_output}"):
        text = source.strip()
        if not text:
            continue
        match = _LISTING_FENCE_RE.search(text)
        if match and len(match.group(1).strip()) >= 80:
            return match.group(1).strip()[:20_000]
        match = _LISTING_HEADING_RE.search(text)
        if match and len(match.group(1).strip()) >= 80:
            return match.group(1).strip()[:20_000]
    return ""


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


async def propose_content_pack_factory_forge_from_session(
    db: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
) -> AgentSuggestion | None:
    """Create pending verified_content_pack_forge when a factory session completes."""

    if not settings.agent_initiative_enabled or not settings.content_pack_factory_enabled:
        return None
    if supervisor_session.tenant_id is None:
        return None
    if not is_content_pack_factory_session(supervisor_session):
        return None

    existing = await db.scalar(
        select(AgentSuggestion).where(
            AgentSuggestion.tenant_id == supervisor_session.tenant_id,
            AgentSuggestion.supervisor_session_id == supervisor_session.id,
            AgentSuggestion.proposal_type == "verified_content_pack_forge",
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
    listing_md = extract_listing_markdown(coder_output=coder_output, critic_output=critic_output)
    quality = evaluate_content_pack_outputs(
        coder_output=coder_output,
        critic_output=critic_output,
        listing_markdown=listing_md,
    )
    if not quality.pack_payload and not extract_publish_pack_json(coder_output):
        logger.info(
            "content_pack_factory.forge_skipped_empty",
            agent_id="content_pack_factory",
            swarm_id=str(supervisor_session.tenant_id),
            task_id=str(supervisor_session.id),
            issues=quality.issues,
        )
        return None

    opportunity = await db.scalar(
        select(ContentPackOpportunityORM).where(
            ContentPackOpportunityORM.tenant_id == supervisor_session.tenant_id,
            ContentPackOpportunityORM.supervisor_session_id == supervisor_session.id,
        ),
    )
    title_base = opportunity.title if opportunity is not None else str(quality.pack_payload.get("title") or "Content pack")
    payload: dict[str, Any] = {
        "pack_payload": quality.pack_payload,
        "listing_markdown": quality.listing_markdown,
        "source": "content_pack_factory",
        "factory_opportunity_id": str(opportunity.id) if opportunity else None,
        **quality.to_payload(),
    }
    description = (
        "Content Pack Factory session passed quality gate — approve to publish into Library and enable export."
        if quality.passed
        else (
            "Content Pack Factory session completed with quality warnings — review critic verdict and publish_pack "
            f"before publish. Issues: {', '.join(quality.issues[:6]) or 'unknown'}."
        )
    )

    row = AgentSuggestion(
        tenant_id=supervisor_session.tenant_id,
        supervisor_session_id=supervisor_session.id,
        sub_agent_session_id=None,
        proposal_type="verified_content_pack_forge",
        proposed_by_role="content_pack_factory",
        title=title_base[:260],
        description=description[:2000],
        proposal_payload=payload,
        risk_level="low" if quality.passed else "medium",
        impact_score=0.80 if quality.passed else 0.52,
        status="pending",
        requires_manual_approval=True,
        evaluation_reason=(
            "content_pack_factory_session_completed"
            if quality.passed
            else "content_pack_factory_quality_gate_warnings"
        ),
    )
    db.add(row)
    await db.flush()
    logger.info(
        "content_pack_factory.forge_proposed",
        agent_id="content_pack_factory",
        swarm_id=str(supervisor_session.tenant_id),
        task_id=str(supervisor_session.id),
        suggestion_id=str(row.id),
    )
    return row


__all__ = [
    "extract_listing_markdown",
    "is_content_pack_factory_session",
    "propose_content_pack_factory_forge_from_session",
]
