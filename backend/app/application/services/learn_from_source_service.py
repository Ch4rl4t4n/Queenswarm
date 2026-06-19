"""HN6 / ST8 — verified URL/video learn-from-source (delegates to NP8 batch, single entry)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.video_url_batch_service import (
    VideoUrlBatchSubmitIn,
    VideoUrlBatchSubmitOut,
    submit_video_url_batch_wizard,
)
from app.core.config import settings


class LearnFromSourceIn(BaseModel):
    """Operator paste one URL → verified digest → optional Kanban task."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=8, max_length=2000)
    title: str | None = Field(default=None, min_length=3, max_length=500)
    wiki_capture: bool = True
    trigger_gardener: bool = False


class LearnFromSourceOut(BaseModel):
    """HN6 response — wraps NP8 batch output."""

    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    learn_from_source: bool = True
    hn6: bool = True
    url: str
    task_id: str = ""
    deliverable_id: str = ""
    knowledge_ids: list[str] = Field(default_factory=list)
    gardener_triggered: bool = False
    tasks_href: str = "/tasks"


async def submit_learn_from_source(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    body: LearnFromSourceIn,
) -> LearnFromSourceOut:
    """Ingest one URL with Grok cross-check path via NP8 intel fetch + triage task."""

    if not settings.learn_from_source_enabled:
        msg = "Learn from source is disabled."
        raise ValueError(msg)
    if not settings.video_url_batch_wizard_enabled:
        msg = "Video URL batch wizard is disabled (required for learn-from-source)."
        raise ValueError(msg)

    url = body.url.strip()
    batch = VideoUrlBatchSubmitIn(
        urls_text=url,
        title=body.title or f"Learn from source · {url[:64]}",
        wiki_capture=body.wiki_capture,
        trigger_gardener=body.trigger_gardener,
    )
    result: VideoUrlBatchSubmitOut = await submit_video_url_batch_wizard(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        body=batch,
    )
    task_id = str(result.task_id or "")
    return LearnFromSourceOut(
        url=url,
        task_id=task_id,
        deliverable_id=str(result.deliverable_id or ""),
        knowledge_ids=list(result.knowledge_ids or []),
        gardener_triggered=bool(result.gardener_triggered),
        tasks_href=f"/tasks?task={task_id}" if task_id else "/tasks",
    )


__all__ = ["LearnFromSourceIn", "LearnFromSourceOut", "submit_learn_from_source"]
