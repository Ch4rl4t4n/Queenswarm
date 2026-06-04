"""Publish verified content pack forge proposals into tenant library."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.content_pack_factory_listing import (
    build_content_pack_listing_md,
    listing_context_from_pack_and_opportunity,
)
from app.application.services.content_pack_factory_service import (
    complete_opportunity_with_pack,
    register_tenant_content_pack,
    slugify_content_pack_name,
)
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion
from app.infrastructure.persistence.models.content_pack_opportunity import ContentPackOpportunityORM
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

logger = structlog.get_logger(__name__)


async def publish_verified_content_pack_forge(
    session: AsyncSession,
    *,
    suggestion: AgentSuggestion,
    tenant_id: uuid.UUID,
    tenant: Tenant | None = None,
    reviewer_subject: str | None = None,
) -> dict[str, Any] | None:
    """On approve: persist tenant content pack + link factory opportunity if present."""

    del tenant, reviewer_subject

    if suggestion.proposal_type != "verified_content_pack_forge":
        return None
    if suggestion.status != "approved":
        return None

    payload = dict(suggestion.proposal_payload or {})
    pack_payload = dict(payload.get("pack_payload") or {})
    if not pack_payload:
        return {"ok": False, "error": "empty_pack_payload"}

    listing_md = str(payload.get("listing_markdown") or "").strip()
    title = str(pack_payload.get("title") or suggestion.title or "Content pack")
    channel = str(pack_payload.get("channel") or "instagram")
    slug = slugify_content_pack_name(title)

    sup: SupervisorSession | None = None
    if suggestion.supervisor_session_id is not None:
        sup = await session.get(SupervisorSession, suggestion.supervisor_session_id)

    opportunity: ContentPackOpportunityORM | None = None
    if sup is not None:
        opportunity = await session.scalar(
            select(ContentPackOpportunityORM).where(
                ContentPackOpportunityORM.tenant_id == tenant_id,
                ContentPackOpportunityORM.supervisor_session_id == sup.id,
            ),
        )

    keywords = ["content-pack-factory", "verified", channel]
    if opportunity is not None:
        keywords.append(opportunity.niche[:48])

    pack_row = await register_tenant_content_pack(
        session,
        tenant_id=tenant_id,
        slug=slug,
        title=title[:200],
        description=suggestion.description or "",
        channel=channel,
        pack_payload=pack_payload,
        listing_markdown=listing_md,
        keywords=keywords,
        source="verified_content_pack_forge",
        mark_verified=True,
    )

    if not pack_row.listing_markdown.strip():
        ctx = listing_context_from_pack_and_opportunity(pack_row, opportunity)
        pack_row.listing_markdown = build_content_pack_listing_md(pack=pack_row, slug=slug, ctx=ctx)
        await session.flush()

    if opportunity is not None:
        await complete_opportunity_with_pack(
            session,
            tenant_id=tenant_id,
            opportunity_id=opportunity.id,
            pack=pack_row,
        )

    logger.info(
        "content_pack_factory.forge_published",
        agent_id="content_pack_factory",
        swarm_id=str(tenant_id),
        task_id=str(suggestion.id),
        pack_slug=pack_row.slug,
    )
    return {
        "ok": True,
        "tenant_content_pack_id": str(pack_row.id),
        "slug": pack_row.slug,
        "opportunity_id": str(opportunity.id) if opportunity else None,
    }


__all__ = ["publish_verified_content_pack_forge"]
