"""Embed forager KnowledgeItems into HiveMind for Skill Factory research."""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chroma_client import HIVE_MIND_COLLECTION, embed_and_store
from app.core.config import settings
from app.infrastructure.persistence.models.knowledge import KnowledgeItem

logger = structlog.get_logger(__name__)

_SKILL_MARKET_TAGS: frozenset[str] = frozenset({"skill-market", "skill_market", "skill-market-intel"})


async def embed_pending_skill_market_items(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 40,
) -> int:
    """Embed unindexed Knowledge rows tagged for skill-market intel.

    Args:
        session: Async DB session.
        tenant_id: Tenant scope.
        limit: Max rows per tick.

    Returns:
        Count of newly embedded items.
    """

    if not settings.hive_mind_enabled or not settings.hive_mind_chroma_enabled:
        return 0

    tag_filters = [KnowledgeItem.topic_tags.contains([tag]) for tag in _SKILL_MARKET_TAGS]
    stmt = (
        select(KnowledgeItem)
        .where(
            KnowledgeItem.tenant_id == tenant_id,
            KnowledgeItem.embedding_id.is_(None),
            or_(
                *tag_filters,
                KnowledgeItem.source_type.in_(("forager", "skill_market_forager")),
            ),
        )
        .order_by(KnowledgeItem.scraped_at.desc())
        .limit(max(1, min(limit, 80)))
    )
    rows = list((await session.scalars(stmt)).all())
    embedded = 0

    for row in rows:
        text = row.content_text.strip()
        if len(text) < 40:
            continue
        tags = [str(tag) for tag in list(row.topic_tags or [])[:24]]
        try:
            embedding_id = await embed_and_store(
                text=text[:12_000],
                metadata={
                    "kind": "skill_market_forager",
                    "tenant_id": str(tenant_id),
                    "knowledge_item_id": str(row.id),
                    "source_type": row.source_type,
                    "tags": ",".join(tags),
                },
                collection_name=HIVE_MIND_COLLECTION,
            )
        except (RuntimeError, ValueError, TypeError) as exc:
            logger.warning(
                "forager_hivemind_embed.failed",
                agent_id="skill_factory",
                swarm_id=str(tenant_id),
                task_id=str(row.id),
                error=str(exc),
            )
            continue
        row.embedding_id = embedding_id
        embedded += 1

    if embedded:
        await session.flush()
        logger.info(
            "forager_hivemind_embed.complete",
            agent_id="skill_factory",
            swarm_id=str(tenant_id),
            embedded=embedded,
        )
    return embedded


async def embed_skill_market_items_all_tenants(
    session: AsyncSession,
    *,
    limit_per_tenant: int = 30,
) -> dict[str, int]:
    """Run embed pass for every tenant with pending skill-market knowledge."""

    from app.infrastructure.persistence.models.tenant import Tenant

    totals = {"tenants": 0, "embedded": 0}
    tenants = list((await session.scalars(select(Tenant).limit(32))).all())
    for tenant in tenants:
        count = await embed_pending_skill_market_items(
            session,
            tenant_id=tenant.id,
            limit=limit_per_tenant,
        )
        if count:
            totals["tenants"] += 1
            totals["embedded"] += count
    return totals


__all__ = ["embed_pending_skill_market_items", "embed_skill_market_items_all_tenants"]
