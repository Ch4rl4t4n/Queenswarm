"""Morning → Publish pipeline — Phase D solo operator workflow snapshot + trigger."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.morning_hive_brief import compose_morning_hive_brief
from app.application.services.publish_queue import build_publish_queue_snapshot
from app.application.services.solo_operator_trio import (
    TRIO_LANE_META,
    get_solo_trio_status,
    resolve_lane_routine,
    run_solo_trio_cycle,
)
from app.application.services.supervisor.routine_service import trigger_supervisor_routine_now
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

logger = get_logger(__name__)

CONTENT_PUBLISH_LANE_KEY = "solo_publish_lane"

CONTENT_PUBLISH_NAME_PATTERNS: tuple[str, ...] = (
    "marketing ops",
    "publish pack",
    "content flywheel",
    "marketing",
    "instagram",
)

PipelineStepId = Literal["life_os_brief", "content_draft", "critic_verify", "publish_queue"]
PipelineStepStatus = Literal["ready", "pending", "running", "done", "skipped", "blocked"]


class MorningPublishPipelineStepOut(BaseModel):
    """One timeline step in the morning publish workflow."""

    model_config = ConfigDict(extra="ignore")

    id: PipelineStepId
    label: str
    scheduled_at: str
    status: PipelineStepStatus
    detail: str = ""
    routine_id: str | None = None
    routine_name: str | None = None
    last_session_status: str | None = None


class MorningPublishPipelineSnapshotOut(BaseModel):
    """Single snapshot for Settings harness morning publish panel."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    life_os_bound: bool = False
    content_routine_bound: bool = False
    publish_queue_enabled: bool = False
    pending_publish_count: int = 0
    approved_publish_count: int = 0
    brief_markdown_preview: str = ""
    steps: list[MorningPublishPipelineStepOut] = Field(default_factory=list)
    links: dict[str, str] = Field(default_factory=dict)


def _lane_from_publish_payload(context_payload: dict[str, Any] | None) -> bool:
    if not isinstance(context_payload, dict):
        return False
    flag = context_payload.get(CONTENT_PUBLISH_LANE_KEY)
    return flag is True or str(flag).strip().lower() in {"1", "true", "yes", "content"}


def _matches_content_publish_name(name: str) -> bool:
    lowered = name.strip().lower()
    return any(token in lowered for token in CONTENT_PUBLISH_NAME_PATTERNS)


def resolve_content_publish_routine(
    *,
    routines: list[SupervisorRoutine],
) -> tuple[SupervisorRoutine | None, str]:
    """Pick the best content/marketing routine for the morning publish lane."""

    for row in routines:
        if not row.is_active:
            continue
        if _lane_from_publish_payload(dict(row.context_payload or {})):
            return row, "context_payload"

    for row in routines:
        if not row.is_active:
            continue
        if _matches_content_publish_name(row.name):
            return row, "name_pattern"

    return None, "missing"


def _step_status_from_session(last_status: str | None) -> PipelineStepStatus:
    if last_status is None:
        return "pending"
    normalized = last_status.strip().lower()
    if normalized in {"completed", "done", "success"}:
        return "done"
    if normalized in {"running", "active", "in_progress"}:
        return "running"
    if normalized in {"failed", "error", "cancelled"}:
        return "blocked"
    return "ready"


def build_pipeline_steps(
    *,
    life_os_lane: dict[str, Any],
    content_routine: SupervisorRoutine | None,
    content_binding: str,
    content_last_status: str | None,
    publish_queue_enabled: bool,
    pending_publish_count: int,
) -> list[MorningPublishPipelineStepOut]:
    """Derive the four-step morning timeline from lane + queue telemetry."""

    life_status = _step_status_from_session(str(life_os_lane.get("last_session_status") or "") or None)
    if life_os_lane.get("binding") == "missing":
        life_status = "skipped"

    content_status: PipelineStepStatus = "skipped"
    content_detail = "Bind Marketing Ops or tag routine with solo_publish_lane."
    if content_routine is not None:
        content_status = _step_status_from_session(content_last_status)
        content_detail = f"Binding: {content_binding}"

    critic_status: PipelineStepStatus = "ready"
    critic_detail = "Automatic when publish packs carry publish-pack-verified tag."
    if pending_publish_count > 0:
        critic_status = "done"
        critic_detail = f"{pending_publish_count} verified pack(s) awaiting operator review."

    queue_status: PipelineStepStatus = "pending"
    queue_detail = "Open Publish Queue in Execution Studio."
    if not publish_queue_enabled:
        queue_status = "blocked"
        queue_detail = "Publish Queue disabled (PUBLISH_QUEUE_ENABLED=false)."
    elif pending_publish_count == 0:
        queue_status = "ready"
        queue_detail = "No pending items — run content bee or approve prior batch."

    return [
        MorningPublishPipelineStepOut(
            id="life_os_brief",
            label="Life OS brief",
            scheduled_at="08:00",
            status=life_status,
            detail=str(life_os_lane.get("description") or TRIO_LANE_META["life_os"]["description"]),
            routine_id=str(life_os_lane.get("routine_id") or "") or None,
            routine_name=str(life_os_lane.get("routine_name") or "") or None,
            last_session_status=str(life_os_lane.get("last_session_status") or "") or None,
        ),
        MorningPublishPipelineStepOut(
            id="content_draft",
            label="Content bee draft",
            scheduled_at="08:15",
            status=content_status,
            detail=content_detail,
            routine_id=str(content_routine.id) if content_routine is not None else None,
            routine_name=content_routine.name if content_routine is not None else None,
            last_session_status=content_last_status,
        ),
        MorningPublishPipelineStepOut(
            id="critic_verify",
            label="Critic verify",
            scheduled_at="08:30",
            status=critic_status,
            detail=critic_detail,
        ),
        MorningPublishPipelineStepOut(
            id="publish_queue",
            label="Publish Queue approve",
            scheduled_at="09:00",
            status=queue_status,
            detail=queue_detail,
        ),
    ]


async def _latest_session_for_routine(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    routine_id: uuid.UUID,
) -> SupervisorSession | None:
    stmt = (
        select(SupervisorSession)
        .where(
            SupervisorSession.tenant_id == tenant_id,
            SupervisorSession.context_summary["routine_id"].astext == str(routine_id),
        )
        .order_by(desc(SupervisorSession.created_at))
        .limit(1)
    )
    return await db.scalar(stmt)


async def compose_morning_publish_pipeline_snapshot(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> MorningPublishPipelineSnapshotOut:
    """Read-only morning publish pipeline snapshot (brief + queue + step timeline)."""

    enabled = bool(settings.morning_publish_pipeline_enabled)
    trio = await get_solo_trio_status(db, tenant_id=tenant_id)
    life_os_lane = next(
        (lane for lane in trio.get("lanes") or [] if str(lane.get("lane_id")) == "life_os"),
        {},
    )

    routines = list(
        (
            await db.scalars(
                select(SupervisorRoutine)
                .where(
                    SupervisorRoutine.tenant_id == tenant_id,
                    SupervisorRoutine.is_active.is_(True),
                )
                .order_by(SupervisorRoutine.name.asc()),
            )
        ).all(),
    )
    content_routine, content_binding = resolve_content_publish_routine(routines=routines)
    content_last_status: str | None = None
    if content_routine is not None:
        last_session = await _latest_session_for_routine(
            db,
            tenant_id=tenant_id,
            routine_id=content_routine.id,
        )
        content_last_status = last_session.status if last_session else None

    queue_enabled = bool(settings.publish_queue_enabled)
    pending_count = approved_count = 0
    if queue_enabled:
        queue = await build_publish_queue_snapshot(db, dashboard_user_id=dashboard_user_id)
        pending_count = int(queue.pending_count)
        approved_count = int(queue.approved_count)

    brief = await compose_morning_hive_brief(db, tenant_id=tenant_id)
    brief_preview = str(brief.get("markdown") or "")[:800]

    steps = build_pipeline_steps(
        life_os_lane=life_os_lane,
        content_routine=content_routine,
        content_binding=content_binding,
        content_last_status=content_last_status,
        publish_queue_enabled=queue_enabled,
        pending_publish_count=pending_count,
    )

    return MorningPublishPipelineSnapshotOut(
        enabled=enabled,
        generated_at=datetime.now(tz=UTC),
        life_os_bound=life_os_lane.get("binding") != "missing",
        content_routine_bound=content_routine is not None,
        publish_queue_enabled=queue_enabled,
        pending_publish_count=pending_count,
        approved_publish_count=approved_count,
        brief_markdown_preview=brief_preview,
        steps=steps,
        links={
            "publish_queue": "/integrations?tab=studio#publish-queue",
            "outputs": "/outputs?ready_to_publish=true",
            "swarm_builder": "/swarms/new",
        },
    )


async def run_morning_publish_pipeline(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    trigger_content: bool = True,
) -> dict[str, Any]:
    """Trigger Life OS lane + optional content routine; return snapshot + triggers."""

    if not settings.morning_publish_pipeline_enabled:
        return {
            "enabled": False,
            "message": "Morning publish pipeline disabled.",
            "snapshot": (
                await compose_morning_publish_pipeline_snapshot(
                    db,
                    tenant_id=tenant_id,
                    dashboard_user_id=dashboard_user_id,
                )
            ).model_dump(mode="json"),
        }

    life_os_run = await run_solo_trio_cycle(db, tenant_id=tenant_id, lane_ids=["life_os"])

    content_triggered: dict[str, Any] | None = None
    if trigger_content:
        routines = list(
            (
                await db.scalars(
                    select(SupervisorRoutine).where(
                        SupervisorRoutine.tenant_id == tenant_id,
                        SupervisorRoutine.is_active.is_(True),
                    ),
                )
            ).all(),
        )
        content_routine, binding = resolve_content_publish_routine(routines=routines)
        if content_routine is not None:
            session_id = await trigger_supervisor_routine_now(db, routine=content_routine)
            content_triggered = {
                "routine_id": str(content_routine.id),
                "routine_name": content_routine.name,
                "binding": binding,
                "session_id": str(session_id),
            }
            logger.info(
                "morning_publish.content_triggered",
                agent_id="morning_publish_pipeline",
                swarm_id=str(content_routine.id),
                task_id=str(session_id),
            )

    snapshot = await compose_morning_publish_pipeline_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
    )

    return {
        "enabled": True,
        "triggered_at": datetime.now(tz=UTC).isoformat(),
        "life_os": life_os_run,
        "content": content_triggered,
        "snapshot": snapshot.model_dump(mode="json"),
    }


__all__ = [
    "CONTENT_PUBLISH_LANE_KEY",
    "CONTENT_PUBLISH_NAME_PATTERNS",
    "MorningPublishPipelineSnapshotOut",
    "MorningPublishPipelineStepOut",
    "build_pipeline_steps",
    "compose_morning_publish_pipeline_snapshot",
    "resolve_content_publish_routine",
    "run_morning_publish_pipeline",
]
