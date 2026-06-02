"""Operator actions for foragers — digest task promotion."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.task_ledger import create_task_record
from app.core.logging import get_logger
from app.infrastructure.persistence.models.enums import TaskStatus, TaskType
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem

logger = get_logger(__name__)


async def _latest_forager_knowledge_excerpt(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    limit: int = 3,
    max_chars: int = 1800,
) -> tuple[int, str]:
    """Return item count tag match and a short excerpt from newest rows."""

    tag = f"forager:{forager_id}"
    stmt = (
        select(KnowledgeItem)
        .where(
            KnowledgeItem.tenant_id == tenant_id,
            KnowledgeItem.topic_tags.contains([tag]),
        )
        .order_by(desc(KnowledgeItem.scraped_at))
        .limit(limit)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    parts: list[str] = []
    for row in rows:
        text = str(row.content_text or "").strip()
        if text:
            parts.append(text[:600])
    excerpt = "\n\n---\n\n".join(parts).strip()[:max_chars]
    return len(rows), excerpt


async def promote_forager_digest_to_task(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    title: str | None = None,
) -> dict[str, Any]:
    """Create a Mission Kanban triage task summarizing one forager's HiveMind harvest."""

    forager = await session.scalar(
        select(ForagerORM).where(
            ForagerORM.id == forager_id,
            ForagerORM.tenant_id == tenant_id,
        ),
    )
    if forager is None:
        return {"ok": False, "error": "forager_not_found"}

    sample_n, excerpt = await _latest_forager_knowledge_excerpt(
        session,
        tenant_id=tenant_id,
        forager_id=forager_id,
    )
    task_title = (title or f"Forager digest · {forager.name}").strip()[:500]
    task_text = (
        f"Review forager harvest: {forager.name} ({forager.source_type}).\n\n"
        f"Sample items loaded: {sample_n}. Simulate-first — verify intel before downstream spawn.\n\n"
    )
    if excerpt:
        task_text += f"Latest excerpt:\n{excerpt}"
    else:
        task_text += "No ingested items yet — run the forager or check source config."

    row = await create_task_record(
        session,
        title=task_title,
        task_type_value=TaskType.REPORT,
        priority=5,
        payload={
            "mission_kanban": True,
            "triage": True,
            "source": "forager_digest",
            "forager_id": str(forager.id),
            "forager_name": forager.name,
            "source_type": forager.source_type,
            "task_text": task_text,
            "excerpt": excerpt,
            "simulate_first": True,
        },
        swarm_id=None,
        workflow_id=None,
        parent_task_id=None,
        status=TaskStatus.TRIAGE,
    )
    row.tenant_id = tenant_id
    await session.flush()

    logger.info(
        "forager.digest_promoted",
        agent_id="forager_hub",
        swarm_id=str(tenant_id),
        task_id=str(row.id),
        forager_id=str(forager.id),
    )
    return {
        "ok": True,
        "task_id": str(row.id),
        "forager_id": str(forager.id),
        "title": task_title,
    }


__all__ = ["promote_forager_digest_to_task"]
