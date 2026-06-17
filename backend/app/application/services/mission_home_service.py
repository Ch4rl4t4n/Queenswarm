"""Mission Home snapshot — Process Rail + brief + actions + approvals + sessions (Track Q UX2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.approval_inbox import compose_approval_inbox_snapshot
from app.application.services.brain_pack_starters import starter_kinds
from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.morning_hive_brief import compose_morning_hive_brief
from app.application.services.parallel_hive_view import (
    ParallelBeeLaneOut,
    compose_parallel_hive_view_snapshot,
)
from app.application.services.solo_daily_plan import compose_solo_daily_plan
from app.application.services.solo_operator_first_run import compose_solo_first_run
from app.core.config import settings
from app.domain.memory.curated import CuratedFileKind
from app.infrastructure.persistence.models.tenant import Tenant

ProcessStepId = Literal["setup", "plan", "work", "verify", "learn", "done"]
MemoryLayerId = Literal["soul", "memory", "user"]


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
    progress_pct: int = Field(ge=0, le=100, default=0)
    loop_chip: str = "Work"
    href: str


class MissionMemoryLayerOut(BaseModel):
    """One Brain Pack layer preview (SOUL · MEMORY · USER)."""

    model_config = ConfigDict(extra="ignore")

    id: MemoryLayerId
    label: str
    preview: str
    char_count: int
    filled: bool
    href: str


class MissionMemoryStripOut(BaseModel):
    """Compact Brain Pack strip for Mission Home (Track Q UX5)."""

    model_config = ConfigDict(extra="ignore")

    layers: list[MissionMemoryLayerOut] = Field(default_factory=list)
    total_chars: int = 0
    max_chars: int = 0
    usage_pct: int = Field(ge=0, le=100, default=0)


class MissionStudioEntryOut(BaseModel):
    """Process-linked studio entry (Track Q UX7)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    detail: str
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
    memory_strip: MissionMemoryStripOut = Field(default_factory=MissionMemoryStripOut)
    step_studios: list[MissionStudioEntryOut] = Field(default_factory=list)
    first_run_complete: bool = True
    links: dict[str, str] = Field(default_factory=dict)
    rapid_loop_widget_enabled: bool = False
    sub_swarm_fleet_widget_enabled: bool = False


PROCESS_STEPS: list[ProcessStepOut] = [
    ProcessStepOut(id="setup", label="Setup", short_label="Setup"),
    ProcessStepOut(id="plan", label="Plan", short_label="Plan"),
    ProcessStepOut(id="work", label="Work", short_label="Work"),
    ProcessStepOut(id="verify", label="Verify", short_label="Verify"),
    ProcessStepOut(id="learn", label="Learn", short_label="Learn"),
    ProcessStepOut(id="done", label="Done", short_label="Done"),
]

STEP_STUDIOS: dict[ProcessStepId, list[MissionStudioEntryOut]] = {
    "setup": [
        MissionStudioEntryOut(
            id="llm_keys",
            title="LLM keys",
            detail="Configure Grok or OpenRouter and run smoke test.",
            href="/settings/llm-keys",
        ),
        MissionStudioEntryOut(
            id="brain_pack",
            title="Brain Pack",
            detail="Load SOUL · MEMORY · USER curated context.",
            href="/knowledge?tab=memory#brain-pack",
        ),
    ],
    "plan": [
        MissionStudioEntryOut(
            id="session_presets",
            title="Goal templates",
            detail="Pick a structured supervisor preset for today's mission.",
            href="/agents?preset=web-redesign-discovery#sessions",
        ),
        MissionStudioEntryOut(
            id="daily_plan",
            title="Today's plan",
            detail="PO · marketing · trading priorities from Operator Loop.",
            href="/agentic-os#solo-daily-plan",
        ),
    ],
    "work": [
        MissionStudioEntryOut(
            id="new_session",
            title="Supervisor session",
            detail="Dispatch bees with simulate-first verify.",
            href="/agents#sessions",
        ),
        MissionStudioEntryOut(
            id="skill_factory",
            title="Skill Factory",
            detail="Forge verified skills when a workflow repeats.",
            href="/apps-tools/skill-factory",
        ),
    ],
    "verify": [
        MissionStudioEntryOut(
            id="approvals",
            title="Approval inbox",
            detail="Simulate-first gates — publish, suggestions, digests.",
            href="/cockpit#approvals",
        ),
        MissionStudioEntryOut(
            id="publish_studio",
            title="Publish studio",
            detail="Social simulate before any live post.",
            href="/integrations?tab=studio#social-publish",
        ),
    ],
    "learn": [
        MissionStudioEntryOut(
            id="wiki",
            title="Wiki capture",
            detail="Promote verified session output to Hive Mind.",
            href="/knowledge#wiki",
        ),
        MissionStudioEntryOut(
            id="recipes",
            title="Recipe library",
            detail="Reuse verified workflows from past missions.",
            href="/knowledge#recipes",
        ),
    ],
    "done": [
        MissionStudioEntryOut(
            id="kanban",
            title="Mission Kanban",
            detail="Move deliverables to Done and export.",
            href="/tasks",
        ),
        MissionStudioEntryOut(
            id="apps_tools",
            title="Apps & Tools",
            detail="Trading cockpit, marketing automation, factories.",
            href="/apps-tools",
        ),
    ],
}


def _preview_text(text: str, *, max_chars: int = 140) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "Empty — load Brain Pack starter in Knowledge."
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[: max_chars - 1]}…"


async def _compose_memory_strip(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> MissionMemoryStripOut:
    """Build SOUL · MEMORY · USER previews from curated bundle."""

    svc = CuratedMemoryService(db=session)
    bundle = await svc.get_bundle(tenant_id)
    max_per_file = CuratedMemoryService.max_chars_per_file()

    soul_text = "\n\n".join(
        part.strip()
        for part in (
            bundle.get(CuratedFileKind.SOUL, ""),
            bundle.get(CuratedFileKind.SKILLS_HIERARCHY, ""),
        )
        if part.strip()
    )
    memory_text = "\n\n".join(
        part.strip()
        for part in (
            bundle.get(CuratedFileKind.MISSION, ""),
            bundle.get(CuratedFileKind.IDEAL_STATE, ""),
        )
        if part.strip()
    )
    user_text = (bundle.get(CuratedFileKind.INSTRUCTIONS) or "").strip()

    layers: list[MissionMemoryLayerOut] = [
        MissionMemoryLayerOut(
            id="soul",
            label="SOUL",
            preview=_preview_text(soul_text),
            char_count=len(soul_text),
            filled=bool(soul_text.strip()),
            href="/knowledge?tab=memory#brain-pack",
        ),
        MissionMemoryLayerOut(
            id="memory",
            label="MEMORY",
            preview=_preview_text(memory_text),
            char_count=len(memory_text),
            filled=bool(memory_text.strip()),
            href="/knowledge?tab=memory#brain-pack",
        ),
        MissionMemoryLayerOut(
            id="user",
            label="USER",
            preview=_preview_text(user_text),
            char_count=len(user_text),
            filled=bool(user_text.strip()),
            href="/knowledge?tab=memory#brain-pack",
        ),
    ]
    total_chars = sum(row.char_count for row in layers)
    max_chars = max_per_file * len(starter_kinds())
    usage_pct = min(100, round((total_chars / max_chars) * 100)) if max_chars else 0

    return MissionMemoryStripOut(
        layers=layers,
        total_chars=total_chars,
        max_chars=max_chars,
        usage_pct=usage_pct,
    )


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


def _loop_progress_from_lanes(
    *,
    status: str,
    lanes: list[ParallelBeeLaneOut],
) -> tuple[int, str]:
    """Derive Agent Loop progress chip from parallel bee lane completion (UX10 / AL1-lite)."""

    normalized = status.strip().lower()
    if normalized == "completed":
        return 100, "Done"
    if normalized == "needs_input":
        pct = _lane_completion_pct(lanes) if lanes else 75
        return max(pct, 70), "Verify"

    pct = _lane_completion_pct(lanes)
    return pct, f"Work · {pct}%"


def _lane_completion_pct(lanes: list[ParallelBeeLaneOut]) -> int:
    if not lanes:
        return 15
    done = sum(1 for lane in lanes if lane.status == "completed")
    total = len(lanes)
    if done >= total:
        return 99
    return max(5, min(98, int(round(100.0 * done / total))))


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
            rapid_loop_widget_enabled=False,
            sub_swarm_fleet_widget_enabled=False,
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
        progress_pct, loop_chip = _loop_progress_from_lanes(status=row.status, lanes=row.lanes)
        active_sessions.append(
            MissionActiveSessionOut(
                session_id=row.session_id,
                goal=row.goal,
                status=row.status,
                progress_label=_session_progress_label(row.status, len(row.lanes)),
                progress_pct=progress_pct,
                loop_chip=loop_chip,
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
    memory_strip = await _compose_memory_strip(session, tenant_id=tenant_id)

    return MissionHomeSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        current_step=current_step,
        process_steps=PROCESS_STEPS,
        brief_bullets=_brief_bullets_from_morning(morning),
        next_actions=next_actions,
        approvals=approvals,
        active_sessions=active_sessions,
        memory_strip=memory_strip,
        step_studios=STEP_STUDIOS.get(current_step, [])[:2],
        first_run_complete=first_run.complete,
        links={
            "new_session": "/agents?preset=web-redesign-discovery#sessions",
            "approvals": "/cockpit#approvals",
            "knowledge": "/knowledge#memory",
            "kanban": "/tasks",
        },
        rapid_loop_widget_enabled=settings.rapid_loop_mission_home_enabled,
        sub_swarm_fleet_widget_enabled=settings.sub_swarm_fleet_mission_home_enabled,
    )


__all__ = [
    "MissionHomeSnapshotOut",
    "MissionMemoryStripOut",
    "ProcessStepId",
    "ProcessStepOut",
    "STEP_STUDIOS",
    "_compose_memory_strip",
    "compose_mission_home_snapshot",
]
