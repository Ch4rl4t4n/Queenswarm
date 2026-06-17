"""POS-H4 — Weak Signal Bee: social intel → morning advisor hint (not future oracle)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.persistence.models.knowledge import KnowledgeItem

WEAK_SIGNAL_TAGS = frozenset({"weak-signal", "social-intel", "hivemind-candidate", "intel"})


class WeakSignalPreviewOut(BaseModel):
    """Compact weak-signal rollup for Jarvis advisor + morning brief."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    signal_count: int = 0
    top_title: str = ""
    advisor_hint: str | None = None
    review_href: str = "/cockpit#four-lanes"
    generated_at: datetime | None = None


async def compose_weak_signal_preview(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    window_days: int = 7,
    limit: int = 5,
) -> WeakSignalPreviewOut:
    """Surface recent social intel as weak-signal hint for operator advisor."""

    if not settings.weak_signal_bee_enabled:
        return WeakSignalPreviewOut(enabled=False)

    since = datetime.now(tz=UTC) - timedelta(days=window_days)
    stmt = (
        select(KnowledgeItem)
        .where(
            KnowledgeItem.tenant_id == tenant_id,
            KnowledgeItem.created_at >= since,
        )
        .order_by(desc(KnowledgeItem.created_at))
        .limit(limit * 4)
    )
    rows = list((await session.scalars(stmt)).all())

    matches: list[KnowledgeItem] = []
    for row in rows:
        tag_set = {str(tag).lower() for tag in (row.topic_tags or [])}
        if tag_set & WEAK_SIGNAL_TAGS or (row.source_type or "").lower() in {
            "forager",
            "social",
            "youtube",
            "x",
        }:
            matches.append(row)
        if len(matches) >= limit:
            break

    if not matches:
        return WeakSignalPreviewOut(
            enabled=True,
            signal_count=0,
            generated_at=datetime.now(tz=UTC),
        )

    top = matches[0]
    title = (top.content_text or "").split("\n", maxsplit=1)[0].strip().lstrip("#").strip()
    if not title:
        title = (top.topic_tags[0] if top.topic_tags else "Untitled signal").strip()
    hint = (
        f"{len(matches)} weak signal(s) this week — top: «{title[:80]}». "
        "Review in Digest Inbox; promote to Kanban only after simulate."
    )
    return WeakSignalPreviewOut(
        enabled=True,
        signal_count=len(matches),
        top_title=title,
        advisor_hint=hint,
        generated_at=datetime.now(tz=UTC),
    )


__all__ = ["WeakSignalPreviewOut", "compose_weak_signal_preview"]
