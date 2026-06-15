"""Operator actions for foragers — digest and goldmine alert task promotion."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.forager_goldmine_dispatch_service import promote_forager_goldmine_dispatch

PromoteMode = Literal["digest", "alert"]


async def promote_forager_digest_to_task(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    title: str | None = None,
    mode: PromoteMode = "digest",
    knowledge_item_ids: list[uuid.UUID] | None = None,
    include_skill_bundle: bool = True,
) -> dict[str, Any]:
    """Create a Mission Kanban triage task from forager digest or delta alert (DG7)."""

    return await promote_forager_goldmine_dispatch(
        session,
        tenant_id=tenant_id,
        forager_id=forager_id,
        title=title,
        mode=mode,
        knowledge_item_ids=knowledge_item_ids,
        include_skill_bundle=include_skill_bundle,
    )


__all__ = ["promote_forager_digest_to_task"]
