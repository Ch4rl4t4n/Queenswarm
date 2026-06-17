"""Marketing Team unified snapshot — calendar, queue, and channel readiness."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.publish_queue import (
    PublishQueueSnapshotOut,
    build_publish_queue_snapshot,
    classify_publish_queue_status,
)
from app.application.services.scheduled_publish import _already_live, _parse_scheduled_at
from app.application.services.social_publish import build_social_publish_snapshot
from app.core.config import settings
from app.domain.outputs.service import list_owned_deliverables
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable
from app.infrastructure.persistence.models.tenant import Tenant

MarketingTeamEntryStatus = Literal[
    "pending",
    "approved",
    "scheduled",
    "published",
    "rejected",
]


class MarketingTeamCalendarEntryOut(BaseModel):
    """One publish pack on the marketing calendar."""

    model_config = ConfigDict(extra="ignore")

    id: uuid.UUID
    title: str
    channel: str
    status: MarketingTeamEntryStatus
    scheduled_at: datetime | None = None
    body_preview: str = ""
    media_kind: str | None = None
    href: str


class MarketingTeamChannelSummaryOut(BaseModel):
    """Compact channel readiness row."""

    model_config = ConfigDict(extra="ignore")

    channel: str
    label: str
    active: bool
    live_allowed: bool


class MarketingTeamSnapshotOut(BaseModel):
    """Unified Marketing Team dashboard payload."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    horizon_days: int = 14
    calendar_entries: list[MarketingTeamCalendarEntryOut] = Field(default_factory=list)
    unscheduled_approved_count: int = 0
    queue_pending_count: int = 0
    queue_approved_count: int = 0
    channels_ready_count: int = 0
    channels_total: int = 0
    channel_summaries: list[MarketingTeamChannelSummaryOut] = Field(default_factory=list)
    live_publish_enabled: bool = False
    scheduled_publish_enabled: bool = False
    links: dict[str, str] = Field(default_factory=dict)
    operator_hint: str = ""


def _entry_status(
    row: TaskFinalDeliverable,
    *,
    queue_status: str,
    scheduled_at: datetime | None,
) -> MarketingTeamEntryStatus:
    tags = list(row.tags or [])
    if _already_live(tags):
        return "published"
    if queue_status == "rejected":
        return "rejected"
    if queue_status == "pending":
        return "pending"
    if scheduled_at is not None:
        return "scheduled"
    return "approved"


def _structured_preview(row: TaskFinalDeliverable) -> tuple[str, str, str | None]:
    structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
    channel = str(structured.get("channel") or "instagram").strip() or "instagram"
    body = str(structured.get("body") or row.markdown_body or "").replace("\n", " ").strip()
    preview = body[:240]
    media_kind = str(structured.get("media_kind") or "").strip() or None
    return channel, preview, media_kind


async def compose_marketing_team_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None = None,
    horizon_days: int = 14,
    limit: int = 60,
) -> MarketingTeamSnapshotOut:
    """Compose calendar + queue + channel readiness for Marketing Team module."""

    now = datetime.now(tz=UTC)
    if not settings.marketing_team_enabled:
        return MarketingTeamSnapshotOut(
            enabled=False,
            generated_at=now,
            operator_hint="Marketing Team module disabled.",
        )

    horizon = max(1, min(horizon_days, 30))
    window_end = now + timedelta(days=horizon)

    rows = await list_owned_deliverables(
        session,
        dashboard_user_id=dashboard_user_id,
        limit=max(limit, 80),
        ready_to_publish=True,
    )

    calendar_entries: list[MarketingTeamCalendarEntryOut] = []
    unscheduled_approved = 0

    for row in rows:
        queue_status = classify_publish_queue_status(row)
        if queue_status is None:
            continue
        channel, preview, media_kind = _structured_preview(row)
        structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
        scheduled_at = _parse_scheduled_at(str(structured.get("scheduled_at") or "") or None)
        status = _entry_status(row, queue_status=queue_status, scheduled_at=scheduled_at)

        if queue_status == "approved" and scheduled_at is None:
            unscheduled_approved += 1

        include = False
        if scheduled_at is not None and scheduled_at <= window_end:
            include = True
        elif status in {"pending", "published"} and row.created_at >= now - timedelta(days=7):
            include = True
        elif queue_status == "approved" and scheduled_at is None:
            include = True

        if not include:
            continue

        calendar_entries.append(
            MarketingTeamCalendarEntryOut(
                id=row.id,
                title=str(row.title or "Publish pack"),
                channel=channel,
                status=status,
                scheduled_at=scheduled_at,
                body_preview=preview,
                media_kind=media_kind,
                href=f"/apps-tools/marketing-team?section=publish#social-publish&pack={row.id}",
            ),
        )
        if len(calendar_entries) >= limit:
            break

    calendar_entries.sort(
        key=lambda item: (
            item.scheduled_at or datetime.max.replace(tzinfo=UTC),
            item.title.lower(),
        ),
    )

    queue: PublishQueueSnapshotOut = await build_publish_queue_snapshot(
        session,
        dashboard_user_id=dashboard_user_id,
        limit=40,
    )

    social = await build_social_publish_snapshot(
        session,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        limit=20,
    )
    channel_summaries = [
        MarketingTeamChannelSummaryOut(
            channel=str(row.channel),
            label=str(row.label),
            active=bool(row.active),
            live_allowed=bool(row.live_allowed),
        )
        for row in social.channels
    ]
    channels_ready = sum(1 for row in channel_summaries if row.active)

    hint_parts: list[str] = []
    if queue.pending_count:
        hint_parts.append(f"{queue.pending_count} pack(s) awaiting queue approval")
    if unscheduled_approved:
        hint_parts.append(f"{unscheduled_approved} approved without schedule — set scheduled_at")
    if channels_ready == 0:
        hint_parts.append("Connect OAuth in Integrations before live publish")
    operator_hint = " · ".join(hint_parts) if hint_parts else "Simulate-first — approve queue, then publish."

    return MarketingTeamSnapshotOut(
        enabled=True,
        generated_at=now,
        horizon_days=horizon,
        calendar_entries=calendar_entries,
        unscheduled_approved_count=unscheduled_approved,
        queue_pending_count=queue.pending_count,
        queue_approved_count=queue.approved_count,
        channels_ready_count=channels_ready,
        channels_total=len(channel_summaries),
        channel_summaries=channel_summaries,
        live_publish_enabled=bool(settings.social_publish_live_enabled),
        scheduled_publish_enabled=bool(settings.scheduled_publish_enabled),
        links={
            "queue": "/apps-tools/marketing-team?section=queue#publish-queue",
            "publish": "/apps-tools/marketing-team?section=publish#social-publish",
            "integrations": "/integrations?tab=studio&section=publish#social-publish",
            "agents": "/agents?preset=marketing-campaign#sessions",
        },
        operator_hint=operator_hint,
    )


__all__ = [
    "MarketingTeamCalendarEntryOut",
    "MarketingTeamChannelSummaryOut",
    "MarketingTeamSnapshotOut",
    "compose_marketing_team_snapshot",
]
