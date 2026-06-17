"""POS-I3 — Jarvis weekly reflection strip (Ballroom post-mortems + episodic → Hive Mind)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.episodic_capture_service import _captures_bucket
from app.core.config import settings
from app.infrastructure.persistence.models.knowledge import LearningLog
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

ReflectionSource = Literal["ballroom", "episodic", "learning", "session"]


def _clip(text: str | None, *, max_len: int = 200) -> str:
    raw = " ".join((text or "").strip().split())
    if len(raw) <= max_len:
        return raw
    return f"{raw[: max_len - 1]}…"


class MissionWeeklyReflectionHighlightOut(BaseModel):
    """One weekly highlight surfaced for operator review."""

    model_config = ConfigDict(extra="ignore")

    source: ReflectionSource
    title: str
    excerpt: str
    href: str


class MissionJarvisWeeklyReflectionStripOut(BaseModel):
    """Weekly reflection rollup — Ballroom + episodic signals routed to Hive Mind."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    headline: str = "This week · reflection"
    message: str = ""
    week_label: str = ""
    ballroom_post_mortems_7d: int = 0
    episodic_captures_7d: int = 0
    sessions_completed_7d: int = 0
    learning_logs_7d: int = 0
    highlights: list[MissionWeeklyReflectionHighlightOut] = Field(default_factory=list)
    hive_mind_href: str = "/knowledge#hivemind"
    episodic_href: str = "/knowledge#memory"
    ballroom_href: str = "/ballroom"


def _parse_capture_moment(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        moment = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment


def _week_label(now: datetime) -> str:
    start = now - timedelta(days=6)
    return f"{start.strftime('%b %d')} – {now.strftime('%b %d')}"


async def compose_jarvis_weekly_reflection_strip(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    first_run_complete: bool,
) -> MissionJarvisWeeklyReflectionStripOut:
    """Build weekly reflection strip from Ballroom post-mortems and episodic memory."""

    if not settings.jarvis_weekly_reflection_enabled or not first_run_complete:
        return MissionJarvisWeeklyReflectionStripOut(enabled=False)

    now = datetime.now(tz=UTC)
    cutoff = now - timedelta(days=7)
    week_label = _week_label(now)

    sessions_completed = int(
        (
            await session.scalar(
                select(func.count())
                .select_from(SupervisorSession)
                .where(
                    SupervisorSession.tenant_id == tenant_id,
                    SupervisorSession.status == "completed",
                    SupervisorSession.completed_at.is_not(None),
                    SupervisorSession.completed_at >= cutoff,
                ),
            )
        )
        or 0,
    )

    learning_logs = int(
        (
            await session.scalar(
                select(func.count())
                .select_from(LearningLog)
                .where(
                    LearningLog.tenant_id == tenant_id,
                    LearningLog.created_at >= cutoff,
                ),
            )
        )
        or 0,
    )

    post_mortem_stmt = (
        select(Recipe)
        .where(
            Recipe.created_at >= cutoff,
            or_(
                Recipe.workflow_template["kind"].astext == "ballroom_post_mortem",
                Recipe.topic_tags.contains(["qs.post_mortem"]),
            ),
        )
        .order_by(desc(Recipe.created_at))
        .limit(5)
    )
    post_mortem_rows = list((await session.scalars(post_mortem_stmt)).all())
    ballroom_count = len(post_mortem_rows)

    tenant = await session.get(Tenant, tenant_id)
    captures = _captures_bucket(tenant.operator_settings if tenant else None).get("captures") or []
    recent_captures = [
        row
        for row in captures
        if isinstance(row, dict)
        and (moment := _parse_capture_moment(str(row.get("captured_at") or ""))) is not None
        and moment >= cutoff
    ]
    episodic_count = len(recent_captures)

    total_activity = sessions_completed + learning_logs + ballroom_count + episodic_count
    if total_activity == 0:
        return MissionJarvisWeeklyReflectionStripOut(
            enabled=False,
            message="No Ballroom or episodic activity in the last 7 days.",
        )

    highlights: list[MissionWeeklyReflectionHighlightOut] = []

    if post_mortem_rows:
        latest = post_mortem_rows[0]
        highlights.append(
            MissionWeeklyReflectionHighlightOut(
                source="ballroom",
                title=latest.name or "Ballroom post-mortem",
                excerpt=_clip(latest.description or str(latest.workflow_template.get("post_mortem") or "")),
                href="/knowledge#hivemind",
            ),
        )

    for capture in recent_captures[:2]:
        goal = str(capture.get("goal") or "Supervisor session").strip()
        summary = _clip(str(capture.get("summary") or ""))
        href = str(capture.get("href") or "/knowledge#memory")
        highlights.append(
            MissionWeeklyReflectionHighlightOut(
                source="episodic",
                title=goal,
                excerpt=summary or "Episodic capture — open daily log for full summary.",
                href=href,
            ),
        )

    if len(highlights) < 3 and learning_logs > 0:
        latest_log = await session.scalar(
            select(LearningLog)
            .where(
                LearningLog.tenant_id == tenant_id,
                LearningLog.created_at >= cutoff,
            )
            .order_by(desc(LearningLog.created_at))
            .limit(1),
        )
        if latest_log is not None:
            highlights.append(
                MissionWeeklyReflectionHighlightOut(
                    source="learning",
                    title="Latest learning log",
                    excerpt=_clip(latest_log.insight_text),
                    href="/knowledge#hivemind",
                ),
            )

    highlights = highlights[:3]

    message_parts: list[str] = []
    if ballroom_count:
        message_parts.append(f"{ballroom_count} Ballroom post-mortem(s)")
    if episodic_count:
        message_parts.append(f"{episodic_count} episodic capture(s)")
    if sessions_completed:
        message_parts.append(f"{sessions_completed} completed session(s)")
    message = " · ".join(message_parts) + " — review patterns in Hive Mind."

    return MissionJarvisWeeklyReflectionStripOut(
        enabled=True,
        headline="This week · reflection",
        message=message,
        week_label=week_label,
        ballroom_post_mortems_7d=ballroom_count,
        episodic_captures_7d=episodic_count,
        sessions_completed_7d=sessions_completed,
        learning_logs_7d=learning_logs,
        highlights=highlights,
    )


__all__ = [
    "MissionJarvisWeeklyReflectionStripOut",
    "MissionWeeklyReflectionHighlightOut",
    "compose_jarvis_weekly_reflection_strip",
]
