"""Faceless content pipeline — idea intake, template draft pack, schedule (POS-C)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.mission_kanban import create_mission_triage_task
from app.application.services.publish_pack import (
    TAG_PUBLISH_PACK,
    TAG_PUBLISH_PACK_VERIFIED,
    TAG_READY_TO_PUBLISH,
    TAG_SIMULATE_ONLY,
    PublishChannel,
    PublishPackArtifact,
    build_publish_pack_markdown,
)
from app.application.services.publish_queue import classify_publish_queue_status
from app.application.services.scheduled_publish import _parse_scheduled_at
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.outputs.engine import OutputEngine
from app.domain.outputs.service import list_owned_deliverables, slugify_fragment
from app.infrastructure.persistence.models.task import Task
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

_logger = get_logger(__name__)

TAG_FACELESS_PIPELINE = "faceless_pipeline"

FacelessIntakeSource = Literal["manual", "forager", "task"]


class FacelessIntakeIn(BaseModel):
    """Operator idea → Mission Kanban triage."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    idea: str = Field(min_length=8, max_length=2000)
    channel: PublishChannel = "instagram"
    source: FacelessIntakeSource = "manual"
    forager_id: uuid.UUID | None = None


class FacelessDraftIn(BaseModel):
    """Template draft publish pack from idea (simulate-first)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    idea: str = Field(min_length=8, max_length=2000)
    channel: PublishChannel = "instagram"
    scheduled_at: str | None = Field(default=None, max_length=64)
    create_intake_task: bool = False


class FacelessScheduleIn(BaseModel):
    """Set scheduled_at on an existing publish pack deliverable."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    scheduled_at: str = Field(min_length=10, max_length=64)


class FacelessPipelineItemOut(BaseModel):
    """Recent faceless draft in pipeline."""

    model_config = ConfigDict(extra="ignore")

    deliverable_id: uuid.UUID
    title: str
    channel: str
    status: str
    scheduled_at: datetime | None = None
    body_preview: str = ""
    href: str


class FacelessPipelineSnapshotOut(BaseModel):
    """Marketing Team faceless lane snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    draft_count: int = 0
    scheduled_count: int = 0
    recent_items: list[FacelessPipelineItemOut] = Field(default_factory=list)
    links: dict[str, str] = Field(default_factory=dict)
    operator_hint: str = ""


class FacelessIntakeOut(BaseModel):
    """Result of faceless idea intake."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    task_id: uuid.UUID | None = None
    title: str = ""
    href: str = ""


class FacelessDraftOut(BaseModel):
    """Result of template draft pack creation."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    deliverable_id: uuid.UUID | None = None
    title: str = ""
    channel: str = "instagram"
    scheduled_at: str | None = None
    queue_status: str = "pending"
    href: str = ""
    task_id: uuid.UUID | None = None


def build_faceless_draft_pack(
    *,
    idea: str,
    channel: PublishChannel = "instagram",
    scheduled_at: str | None = None,
) -> PublishPackArtifact:
    """Build a simulate-first publish pack from a short idea (template — no LLM)."""

    hook = idea.strip().split("\n", maxsplit=1)[0][:120]
    title = f"Faceless · {hook[:72]}".strip()
    body = (
        f"Hook: {hook}\n\n"
        "3 insights (edit before publish):\n"
        "1. What changed in your niche this week\n"
        "2. One counter-intuitive lesson from building with agents\n"
        "3. Actionable step the viewer can take today\n\n"
        "CTA: Save this + follow for verified agent workflows."
    )
    default_schedule = scheduled_at
    if default_schedule is None:
        due = datetime.now(tz=UTC) + timedelta(days=1)
        default_schedule = due.replace(hour=9, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")

    hashtags = ["faceless", "aiworkflow", "buildinpublic"]
    if channel == "instagram":
        hashtags.append("reels")
    elif channel == "tiktok":
        hashtags = ["faceless", "tiktok", "ai"]

    return PublishPackArtifact(
        channel=channel,
        title=title,
        body=body,
        hashtags=hashtags,
        cta="Follow for more verified workflows",
        scheduled_at=default_schedule,
        simulate_only=True,
    )


async def archive_faceless_publish_pack(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    pack: PublishPackArtifact,
    task_id: uuid.UUID | None = None,
    verified: bool = True,
) -> TaskFinalDeliverable:
    """Persist faceless template pack to Outputs → Publish Queue pending."""

    markdown = build_publish_pack_markdown(
        pack,
        critic_excerpt="Faceless template draft — operator edit + critic before live.",
    )
    structured = pack.model_dump()
    structured["faceless_pipeline"] = True
    structured["pipeline_source"] = "faceless_template_v1"
    if task_id is not None:
        structured["source_task_id"] = str(task_id)

    tag_base = [TAG_PUBLISH_PACK, TAG_SIMULATE_ONLY, TAG_FACELESS_PIPELINE, pack.channel, "marketing"]
    if verified:
        tag_base.extend([TAG_PUBLISH_PACK_VERIFIED, TAG_READY_TO_PUBLISH])

    lineage_id = task_id or uuid.uuid4()
    row = await OutputEngine.create_final_deliverable(
        session,
        lineage_id=lineage_id,
        markdown_body=markdown,
        structured=structured,
        title_hint=pack.title[:200],
        slug_hint=slugify_fragment(pack.title[:120]),
        tags=sorted(dict.fromkeys(tag_base)),
        voice_script=None,
        dashboard_user_id=dashboard_user_id,
        ballroom_session_id=None,
        mission_id=task_id,
        source_task_id=task_id,
    )
    await session.flush()
    _logger.info(
        "faceless_pipeline.draft_archived",
        agent_id="faceless_pipeline",
        task_id=str(row.id),
        channel=pack.channel,
    )
    return row


async def create_faceless_intake_task(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    body: FacelessIntakeIn,
) -> FacelessIntakeOut:
    """Park faceless idea on Mission Kanban triage."""

    if not settings.faceless_content_pipeline_enabled:
        return FacelessIntakeOut(ok=False, title="Faceless pipeline disabled")

    task_text = (
        f"FACELESS PIPELINE — {body.channel}\n\n"
        f"Idea:\n{body.idea.strip()}\n\n"
        "Steps:\n"
        "1. Expand hook + 3 beats (script)\n"
        "2. Generate carousel/reel caption draft\n"
        "3. Critic verify → Publish Queue → schedule\n"
        "Simulate-first only."
    )
    extra: dict[str, Any] = {
        "faceless_pipeline": True,
        "faceless_channel": body.channel,
        "faceless_source": body.source,
        "simulate_first": True,
    }
    if body.forager_id is not None:
        extra["forager_id"] = str(body.forager_id)

    result = await create_mission_triage_task(
        session,
        task_text=task_text,
        title=f"Faceless · {body.idea.strip()[:64]}",
        priority=5,
        swarm_id=None,
        skills=["publish_pack", "execution-studio", "marketing-campaign-playbook"],
        extra_payload=extra,
    )
    task_id = uuid.UUID(str(result.task.id))
    task_row = await session.get(Task, task_id)
    if task_row is not None:
        task_row.tenant_id = tenant_id
        await session.flush()

    return FacelessIntakeOut(
        ok=True,
        task_id=task_id,
        title=result.task.title,
        href=f"/tasks?highlight={task_id}",
    )


async def run_faceless_draft(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    body: FacelessDraftIn,
) -> FacelessDraftOut:
    """Create template publish pack and optional intake task."""

    if not settings.faceless_content_pipeline_enabled:
        return FacelessDraftOut(ok=False, title="Faceless pipeline disabled")

    task_id: uuid.UUID | None = None
    if body.create_intake_task:
        intake = await create_faceless_intake_task(
            session,
            tenant_id=tenant_id,
            body=FacelessIntakeIn(
                idea=body.idea,
                channel=body.channel,
                source="manual",
            ),
        )
        task_id = intake.task_id

    pack = build_faceless_draft_pack(
        idea=body.idea,
        channel=body.channel,
        scheduled_at=body.scheduled_at,
    )
    row = await archive_faceless_publish_pack(
        session,
        dashboard_user_id=dashboard_user_id,
        pack=pack,
        task_id=task_id,
        verified=True,
    )
    row.tenant_id = tenant_id
    await session.flush()

    queue_status = classify_publish_queue_status(row) or "pending"
    return FacelessDraftOut(
        ok=True,
        deliverable_id=row.id,
        title=pack.title,
        channel=pack.channel,
        scheduled_at=pack.scheduled_at,
        queue_status=queue_status,
        href=f"/apps-tools/marketing-team?section=queue#publish-queue&pack={row.id}",
        task_id=task_id,
    )


async def schedule_faceless_deliverable(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    deliverable_id: uuid.UUID,
    scheduled_at: str,
) -> dict[str, Any]:
    """Update scheduled_at on a faceless publish pack."""

    from app.domain.outputs.service import fetch_owned_deliverable

    row = await fetch_owned_deliverable(session, deliverable_id=deliverable_id, dashboard_user_id=dashboard_user_id)
    if row is None:
        return {"ok": False, "error": "not_found"}

    parsed = _parse_scheduled_at(scheduled_at)
    if parsed is None:
        return {"ok": False, "error": "invalid_scheduled_at"}

    structured = dict(row.structured_json or {})
    structured["scheduled_at"] = parsed.isoformat().replace("+00:00", "Z")
    row.structured_json = structured
    await session.flush()
    return {
        "ok": True,
        "deliverable_id": str(row.id),
        "scheduled_at": structured["scheduled_at"],
        "href": "/apps-tools/marketing-team?section=calendar#marketing-calendar",
    }


async def compose_faceless_pipeline_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
) -> FacelessPipelineSnapshotOut:
    """Recent faceless drafts for Marketing Team studio panel."""

    now = datetime.now(tz=UTC)
    if not settings.faceless_content_pipeline_enabled:
        return FacelessPipelineSnapshotOut(
            enabled=False,
            generated_at=now,
            operator_hint="Faceless pipeline disabled.",
        )

    rows = await list_owned_deliverables(
        session,
        dashboard_user_id=dashboard_user_id,
        limit=40,
        ready_to_publish=True,
    )
    recent: list[FacelessPipelineItemOut] = []
    scheduled_count = 0
    for row in rows:
        tags = {str(t).lower() for t in (row.tags or [])}
        structured = dict(row.structured_json or {})
        if TAG_FACELESS_PIPELINE not in tags and not structured.get("faceless_pipeline"):
            continue
        scheduled_at = _parse_scheduled_at(str(structured.get("scheduled_at") or "") or None)
        if scheduled_at is not None:
            scheduled_count += 1
        status = classify_publish_queue_status(row) or "draft"
        channel = str(structured.get("channel") or "instagram")
        preview = str(structured.get("body") or row.markdown_body or "").replace("\n", " ")[:200]
        recent.append(
            FacelessPipelineItemOut(
                deliverable_id=row.id,
                title=str(row.title or "Faceless draft"),
                channel=channel,
                status=status,
                scheduled_at=scheduled_at,
                body_preview=preview,
                href=f"/apps-tools/marketing-team?section=queue#publish-queue&pack={row.id}",
            ),
        )
        if len(recent) >= 8:
            break

    return FacelessPipelineSnapshotOut(
        enabled=True,
        generated_at=now,
        draft_count=len(recent),
        scheduled_count=scheduled_count,
        recent_items=recent,
        links={
            "studio": "/apps-tools/marketing-team?section=studio#faceless-studio",
            "queue": "/apps-tools/marketing-team?section=queue#publish-queue",
            "agents": "/agents?preset=faceless-video#sessions",
        },
        operator_hint=(
            "Paste a hook → Draft creates simulate pack in Publish Queue. "
            "Approve → Social publish simulate → schedule or live."
        ),
    )
