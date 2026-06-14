"""Mission Home snapshot — Process Rail + brief + actions + approvals + sessions (Track Q UX2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.approval_inbox import compose_approval_inbox_snapshot
from app.application.services.morning_hive_brief import compose_morning_hive_brief
from app.application.services.parallel_hive_view import compose_parallel_hive_view_snapshot
from app.application.services.solo_daily_plan import compose_solo_daily_plan
from app.application.services.solo_operator_first_run import compose_solo_first_run
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant

ProcessStepId = Literal["setup", "plan", "work", "verify", "learn", "done"]


class ProcessStepOut(BaseModel):
    """One step in the 6-step operator process rail."""

    model_config = ConfigDict(extra="ignore")

    id: ProcessStepId
    label: str
    short_label: str


class MissionBriefBulletOut(BaseModel):
    """Verified brief line for Mission Home."""

    model_config = ConfigDict(extra="ignore")

    text: str
    source: str = "morning_brief"


class MissionActionOut(BaseModel):
    """Prioritized next action on Mission Home."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    detail: str
    href: str | None = None
    priority: int = Field(ge=1, le=5, default=2)


class MissionApprovalOut(BaseModel):
    """Compact approval row for Mission Home."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    detail: str
    href: str
    kind: str


class MissionActiveSessionOut(BaseModel):
    """Active supervisor session card (UX10-lite)."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    goal: str
    status: str
    progress_label: str
    href: str


class MissionHomeSnapshotOut(BaseModel):
    """Unified Mission Home snapshot for /tasks solo default."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    current_step: ProcessStepId
    process_steps: list[ProcessStepOut] = Field(default_factory=list)
    brief_bullets: list[MissionBriefBulletOut] = Field(default_factory=list)
    next_actions: list[MissionActionOut] = Field(default_factory=list)
    approvals: list[MissionApprovalOut] = Field(default_factory=list)
    active_sessions: list[MissionActiveSessionOut] = Field(default_factory=list)
    first_run_complete: bool = True
    links: dict[str, str] = Field(default_factory=dict)


PROCESS_STEPS: list[ProcessStepOut] = [
    ProcessStepOut(id="setup", label="Setup", short_label="Setup"),
    ProcessStepOut(id="plan", label="Plan", short_label="Plan"),
    ProcessStepOut(id="work", label="Work", short_label="Work"),
    ProcessStepOut(id="verify", label="Verify", short_label="Verify"),
    ProcessStepOut(id="learn", label="Learn", short_label="Learn"),
    ProcessStepOut(id="done", label="Done", short_label="Done"),
]


def _brief_bullets_from_morning(morning: dict[str, object]) -> list[MissionBriefBulletOut]:
    """Extract up to three brief bullets from morning hive brief sections."""

    bullets: list[MissionBriefBulletOut] = []
    sections = morning.get("sections") or []
    if isinstance(sections, list):
        for section in sections[:4]:
            if not isinstance(section, dict):
                continue
            label = str(section.get("label") or section.get("lane_id") or "Brief").strip()
            excerpt = str(section.get("excerpt") or "").strip()
            binding = str(section.get("binding") or "")
            if binding == "missing":
                bullets.append(
                    MissionBriefBulletOut(
                        text=f"{label}: bind a routine to run today's lane.",
                        source="trio",
                    ),
                )
            elif excerpt:
                first_line = excerpt.split("\n", maxsplit=1)[0].strip()
                if len(first_line) > 160:
                    first_line = f"{first_line[:157]}…"
                bullets.append(MissionBriefBulletOut(text=f"{label}: {first_line}", source="trio"))
            elif section.get("last_session_status"):
                bullets.append(
                    MissionBriefBulletOut(
                        text=f"{label}: last session {section.get('last_session_status')}.",
                        source="trio",
                    ),
                )
            if len(bullets) >= 3:
                break

    tech_score = morning.get("tech_health_score")
    if len(bullets) < 3 and tech_score is not None:
        bullets.append(
            MissionBriefBulletOut(
                text=f"Tech health {float(tech_score):.0%} — run simulate-first before live.",
                source="tech_health",
            ),
        )

    if not bullets:
        bullets.append(
            MissionBriefBulletOut(
                text="Run the 3 Bees trio or start a supervisor session to populate today's brief.",
                source="empty_state",
            ),
        )
    return bullets[:3]


def _resolve_process_step(
    *,
    first_run_complete: bool,
    approval_count: int,
    active_sessions: list[MissionActiveSessionOut],
    has_daily_plan: bool,
) -> ProcessStepId:
    """Derive current process rail step from subsystem signals."""

    if not first_run_complete:
        return "setup"

    if approval_count > 0:
        return "verify"

    if any(row.status == "needs_input" for row in active_sessions):
        return "verify"

    if active_sessions:
        return "work"

    if has_daily_plan:
        return "plan"

    if any(row.status == "completed" for row in active_sessions):
        return "learn"

    return "done"


def _session_progress_label(status: str, lane_count: int) -> str:
    normalized = status.strip().lower()
    if normalized == "needs_input":
        return "Needs your input"
    if normalized == "running":
        return f"Running · {max(lane_count, 1)} lane(s)"
    if normalized == "completed":
        return "Completed"
    return normalized.replace("_", " ").title()


async def compose_mission_home_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> MissionHomeSnapshotOut:
    """Build Mission Home snapshot — single API for Process Rail + cards."""

    if not settings.solo_mode_enabled and not settings.operator_loop_enabled:
        return MissionHomeSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            current_step="done",
            process_steps=PROCESS_STEPS,
        )

    first_run = await compose_solo_first_run(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
    )
    morning = await compose_morning_hive_brief(session, tenant_id=tenant_id)
    daily = await compose_solo_daily_plan(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        max_items=3,
    )
    inbox = await compose_approval_inbox_snapshot(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        limit=5,
    )
    parallel = await compose_parallel_hive_view_snapshot(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        limit=3,
    )

    active_sessions: list[MissionActiveSessionOut] = []
    for row in parallel.sessions:
        if row.status not in {"running", "needs_input"}:
            continue
        active_sessions.append(
            MissionActiveSessionOut(
                session_id=row.session_id,
                goal=row.goal,
                status=row.status,
                progress_label=_session_progress_label(row.status, len(row.lanes)),
                href=f"/agents?session={row.session_id}",
            ),
        )
    active_sessions = active_sessions[:3]

    approvals: list[MissionApprovalOut] = []
    if inbox.enabled:
        for item in inbox.items[:5]:
            approvals.append(
                MissionApprovalOut(
                    id=item.id,
                    title=item.title,
                    detail=item.detail,
                    href=item.href,
                    kind=item.kind,
                ),
            )

    next_actions: list[MissionActionOut] = []
    if daily.enabled:
        for item in daily.items[:3]:
            next_actions.append(
                MissionActionOut(
                    id=item.id,
                    title=item.title,
                    detail=item.detail,
                    href=item.href,
                    priority=item.priority,
                ),
            )

    current_step = _resolve_process_step(
        first_run_complete=first_run.complete,
        approval_count=inbox.counts.total if inbox.enabled else 0,
        active_sessions=active_sessions,
        has_daily_plan=bool(daily.enabled and daily.items),
    )

    return MissionHomeSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        current_step=current_step,
        process_steps=PROCESS_STEPS,
        brief_bullets=_brief_bullets_from_morning(morning),
        next_actions=next_actions,
        approvals=approvals,
        active_sessions=active_sessions,
        first_run_complete=first_run.complete,
        links={
            "new_session": "/agents?preset=web-redesign-discovery#sessions",
            "approvals": "/cockpit#approvals",
            "knowledge": "/knowledge#memory",
            "kanban": "/tasks",
        },
    )


__all__ = [
    "MissionHomeSnapshotOut",
    "ProcessStepId",
    "ProcessStepOut",
    "compose_mission_home_snapshot",
]
