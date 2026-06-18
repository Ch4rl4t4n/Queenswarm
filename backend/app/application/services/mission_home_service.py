"""Mission Home snapshot — Process Rail + brief + actions + approvals + sessions (Track Q UX2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.approval_inbox import compose_approval_inbox_snapshot
from app.application.services.agent_quality_scorecard_service import (
    MissionAgentQualityStripOut,
    compose_agent_quality_strip,
)
from app.application.services.brain_pack_starters import starter_kinds
from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.jarvis_advisor_service import (
    JarvisActionIn,
    JarvisApprovalIn,
    JarvisAutopilotIn,
    JarvisLifeOsIn,
    JarvisMemoryIn,
    JarvisCalendarEventIn,
    JarvisMemoryLayerIn,
    JarvisSessionIn,
    MissionJarvisAdvisorStripOut,
    _compose_jarvis_advisor_strip,
)
from app.application.services.jarvis_weekly_reflection_service import (
    MissionJarvisWeeklyReflectionStripOut,
    compose_jarvis_weekly_reflection_strip,
)
from app.application.services.weekly_compound_gardener_service import (
    MissionWeeklyCompoundStripOut,
    compose_mission_weekly_compound_strip,
)
from app.application.services.morning_hive_brief import compose_morning_hive_brief
from app.application.services.parallel_hive_view import (
    ParallelBeeLaneOut,
    compose_parallel_hive_view_snapshot,
)
from app.application.services.solo_daily_plan import compose_solo_daily_plan
from app.application.services.solo_operator_first_run import compose_solo_first_run
from app.application.services.weak_signal_bee_service import compose_weak_signal_preview
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
    loop_timeline_href: str = ""
    tool_outcome_href: str = ""


class MissionAgentLoopStripOut(BaseModel):
    """AL1/LOOP3 agent loop visibility on Mission Home (POS-O)."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    headline: str = "Agent loop"
    message: str = ""
    active_count: int = 0
    primary_session_id: str = ""
    loop_chip: str = "Work"
    progress_pct: int = Field(ge=0, le=100, default=0)
    loop_timeline_href: str = "/agents#sessions"


class MissionToolOutcomeStripOut(BaseModel):
    """AL2 tool outcome visibility on Mission Home (POS-P)."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    headline: str = "Verify · tool outcomes"
    message: str = ""
    pending_count: int = 0
    primary_session_id: str = ""
    tool_outcome_href: str = "/agents#sessions"


class MissionLoopGuardrailsStripOut(BaseModel):
    """LOOP2 closed-loop guardrails visibility on Mission Home (POS-P)."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    headline: str = "Closed loop · guardrails"
    message: str = ""
    max_turns: int = 5
    min_score_label: str = "4.0/5"
    cost_cap_usd: float = 2.0
    active_count: int = 0
    guardrails_href: str = "/settings/harness#harness-closed-loop-presets"
    session_guardrails_href: str = ""


class MissionGoldmineStripOut(BaseModel):
    """DG3/DG7 goldmine delta alerts on Mission Home (POS-Q)."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    headline: str = "Goldmine · delta alerts"
    message: str = ""
    alert_count: int = 0
    new_items_total: int = 0
    primary_forager_name: str = ""
    primary_forager_id: str = ""
    foragers_href: str = "/foragers#goldmine-alerts"
    cockpit_href: str = "/cockpit#approvals"


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


class MissionCalendarEventOut(BaseModel):
    """One Google Calendar block on Mission Home (POS-D Life OS strip)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    start_at: datetime | None = None
    end_at: datetime | None = None
    detail: str = ""
    href: str = "/integrations?tab=connectors"


class MissionLifeOsStripOut(BaseModel):
    """Life OS morning strip — calendar + connect state for Mission Home."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    connected: bool = False
    event_count: int = 0
    message: str = ""
    events: list[MissionCalendarEventOut] = Field(default_factory=list)
    connect_href: str = "/integrations?tab=connectors"


class MissionAutopilotLaneOut(BaseModel):
    """One autopilot lane row (My 3 Bees or Four Lanes)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    group: Literal["trio", "four_lane"] = "trio"
    status: Literal["active", "bound", "missing", "paused"] = "missing"
    detail: str = ""
    schedule_cron: str | None = None


class MissionAutopilotStripOut(BaseModel):
    """Background autopilot status — My 3 Bees + Four Lanes (POS-E)."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    routines_enabled: bool = False
    trio_bound: int = 0
    trio_total: int = 3
    four_lanes_active: int = 0
    four_lanes_total: int = 4
    digest_pending: int = 0
    cron_lane_count: int = 0
    message: str = ""
    lanes: list[MissionAutopilotLaneOut] = Field(default_factory=list)
    harness_href: str = "/settings/harness"
    four_lanes_href: str = "/agentic-os#lanes"
    digest_href: str = "/cockpit#four-lanes"


class MissionSecondBrainStripOut(BaseModel):
    """Wiki Layer + SB3 capture approve + LOOP1 presets on Mission Home (POS-N)."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    headline: str = "Second brain · Wiki Layer"
    message: str = ""
    pending_captures: int = 0
    connection_intelligence_weekly: bool = False
    wiki_href: str = "/knowledge?tab=wiki"
    captures_href: str = "/knowledge?tab=wiki#second-brain-capture-approve"
    closed_loop_href: str = "/settings/harness#harness-closed-loop-presets"


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
    life_os_strip: MissionLifeOsStripOut = Field(default_factory=MissionLifeOsStripOut)
    autopilot_strip: MissionAutopilotStripOut = Field(default_factory=MissionAutopilotStripOut)
    jarvis_advisor_strip: MissionJarvisAdvisorStripOut = Field(
        default_factory=lambda: MissionJarvisAdvisorStripOut(enabled=False),
    )
    agent_quality_strip: MissionAgentQualityStripOut = Field(
        default_factory=lambda: MissionAgentQualityStripOut(enabled=False),
    )
    jarvis_weekly_reflection_strip: MissionJarvisWeeklyReflectionStripOut = Field(
        default_factory=lambda: MissionJarvisWeeklyReflectionStripOut(enabled=False),
    )
    weekly_compound_strip: MissionWeeklyCompoundStripOut = Field(
        default_factory=lambda: MissionWeeklyCompoundStripOut(enabled=False),
    )
    second_brain_strip: MissionSecondBrainStripOut = Field(
        default_factory=lambda: MissionSecondBrainStripOut(enabled=False),
    )
    agent_loop_strip: MissionAgentLoopStripOut = Field(
        default_factory=lambda: MissionAgentLoopStripOut(enabled=False),
    )
    tool_outcome_strip: MissionToolOutcomeStripOut = Field(
        default_factory=lambda: MissionToolOutcomeStripOut(enabled=False),
    )
    loop_guardrails_strip: MissionLoopGuardrailsStripOut = Field(
        default_factory=lambda: MissionLoopGuardrailsStripOut(enabled=False),
    )
    goldmine_strip: MissionGoldmineStripOut = Field(
        default_factory=lambda: MissionGoldmineStripOut(enabled=False),
    )
    first_run_complete: bool = True
    links: dict[str, str] = Field(default_factory=dict)
    rapid_loop_widget_enabled: bool = False
    sub_swarm_fleet_widget_enabled: bool = False
    factory_launch_widget_enabled: bool = False
    catalog_wave_widget_enabled: bool = False
    revenue_funnel_widget_enabled: bool = False


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
            id="agent_loop",
            title="Agent loop timeline",
            detail="Goal → Plan → Tool → Verify — watch the real agent loop.",
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
        MissionStudioEntryOut(
            id="closed_loop",
            title="Closed loop presets",
            detail="Greptile-style rubric loops — max turns, min score before merge.",
            href="/settings/harness#harness-closed-loop-presets",
        ),
        MissionStudioEntryOut(
            id="tool_outcomes",
            title="Tool outcomes",
            detail="AL2 evidence — sim results, critic score before approve.",
            href="/agents#sessions",
        ),
        MissionStudioEntryOut(
            id="goldmine_alerts",
            title="Goldmine deltas",
            detail="DG3 new-since-last-run — dispatch to Kanban with skill bundle.",
            href="/foragers#goldmine-alerts",
        ),
    ],
    "learn": [
        MissionStudioEntryOut(
            id="wiki",
            title="Wiki capture",
            detail="Capture → approve → MOC refresh — second-brain closed loop.",
            href="/knowledge?tab=wiki",
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


async def _compose_second_brain_strip(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    first_run_complete: bool,
) -> MissionSecondBrainStripOut:
    """Wiki Layer adoption strip — pending captures + weekly connection intelligence (POS-N)."""

    if not settings.wiki_layer_enabled or not first_run_complete:
        return MissionSecondBrainStripOut(enabled=False)

    pending_count = 0
    if settings.second_brain_capture_approve_enabled:
        from app.application.services.second_brain_capture import list_pending_capture_notes

        pending = await list_pending_capture_notes(session, tenant_id=tenant_id, limit=20)
        pending_count = len(pending)

    conn_weekly = settings.second_brain_connection_intelligence_tick_enabled
    message_parts: list[str] = []
    if pending_count:
        message_parts.append(f"{pending_count} capture(s) awaiting approve")
    if conn_weekly:
        message_parts.append("weekly MOC + connection-intelligence tick")
    message = (
        " · ".join(message_parts) + " — capture → approve → cited recall."
        if message_parts
        else "Capture ideas in Wiki Layer — approve before Obsidian export and recall."
    )

    return MissionSecondBrainStripOut(
        enabled=True,
        headline="Second brain · Wiki Layer",
        message=message,
        pending_captures=pending_count,
        connection_intelligence_weekly=conn_weekly,
    )


def _compose_agent_loop_strip(
    active_sessions: list[MissionActiveSessionOut],
) -> MissionAgentLoopStripOut:
    """AL1 visibility strip when supervisor sessions are in flight (POS-O)."""

    if not settings.agent_loop_timeline_enabled or not active_sessions:
        return MissionAgentLoopStripOut(enabled=False)

    primary = active_sessions[0]
    timeline_href = primary.loop_timeline_href or f"/agents?session={primary.session_id}#agent-loop-timeline"
    running = sum(1 for row in active_sessions if row.status == "running")
    message = (
        f"{primary.loop_chip} · {primary.progress_pct}% — Goal → Plan → Tool → Verify."
        if running
        else f"{len(active_sessions)} session(s) in flight — open loop timeline before approve."
    )

    return MissionAgentLoopStripOut(
        enabled=True,
        headline="Agent loop · in flight",
        message=message,
        active_count=len(active_sessions),
        primary_session_id=primary.session_id,
        loop_chip=primary.loop_chip,
        progress_pct=primary.progress_pct,
        loop_timeline_href=timeline_href,
    )


def _compose_tool_outcome_strip(
    active_sessions: list[MissionActiveSessionOut],
) -> MissionToolOutcomeStripOut:
    """AL2 visibility strip when supervisor sessions await operator verify (POS-P)."""

    if not settings.tool_outcome_panel_enabled:
        return MissionToolOutcomeStripOut(enabled=False)

    pending = [row for row in active_sessions if row.status == "needs_input"]
    if not pending:
        return MissionToolOutcomeStripOut(enabled=False)

    primary = pending[0]
    tool_href = primary.tool_outcome_href or f"/agents?session={primary.session_id}#tool-outcome-panel"
    message = (
        f"{len(pending)} session(s) need approve — review sim results and critic score before live."
        if len(pending) > 1
        else (primary.goal[:120] or "Supervisor session") + " — tool evidence ready for verify."
    )

    return MissionToolOutcomeStripOut(
        enabled=True,
        headline="Verify · tool outcomes",
        message=message,
        pending_count=len(pending),
        primary_session_id=primary.session_id,
        tool_outcome_href=tool_href,
    )


async def _compose_loop_guardrails_strip(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    active_sessions: list[MissionActiveSessionOut],
) -> MissionLoopGuardrailsStripOut:
    """LOOP2 guardrails strip when in-flight sessions run under closed-loop caps (POS-P)."""

    if not settings.loop_guardrails_enabled or not active_sessions:
        return MissionLoopGuardrailsStripOut(enabled=False)

    from app.application.services.loop_guardrails_service import (
        get_loop_guardrails_policy,
        min_score_to_five_scale,
    )

    policy = await get_loop_guardrails_policy(session, tenant_id=tenant_id)
    if not policy.enabled:
        return MissionLoopGuardrailsStripOut(enabled=False)

    primary = active_sessions[0]
    min_label = min_score_to_five_scale(policy.min_score)
    message = (
        f"Max {policy.max_turns} turns · min {min_label} · ${policy.cost_cap_usd:.2f} cap — "
        f"{len(active_sessions)} session(s) in flight."
    )

    return MissionLoopGuardrailsStripOut(
        enabled=True,
        headline="Closed loop · guardrails",
        message=message,
        max_turns=policy.max_turns,
        min_score_label=min_label,
        cost_cap_usd=policy.cost_cap_usd,
        active_count=len(active_sessions),
        guardrails_href="/settings/harness#harness-closed-loop-presets",
        session_guardrails_href=f"/agents?session={primary.session_id}#session-loop-guardrails",
    )


async def _compose_goldmine_strip(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> MissionGoldmineStripOut:
    """DG3/DG7 visibility strip when forager monitors have new delta signals (POS-Q)."""

    if not settings.forager_goldmine_dispatch_enabled:
        return MissionGoldmineStripOut(enabled=False)

    from app.application.services.forager_goldmine_dispatch_service import compose_goldmine_alert_inbox_items

    rows = await compose_goldmine_alert_inbox_items(session, tenant_id=tenant_id, limit=5)
    if not rows:
        return MissionGoldmineStripOut(enabled=False)

    primary = rows[0]
    alert_count = len(rows)
    new_items_total = sum(int(row.get("new_item_count") or 0) for row in rows)
    forager_name = str(primary.get("forager_name") or "Forager")
    forager_id = str(primary.get("forager_id") or "")
    message = (
        f"{alert_count} monitor(s) · {new_items_total} new signal(s) — approve dispatch to Mission Kanban."
        if alert_count > 1
        else f"{forager_name} · {new_items_total} new since last run — review before dispatch."
    )

    return MissionGoldmineStripOut(
        enabled=True,
        headline="Goldmine · delta alerts",
        message=message,
        alert_count=alert_count,
        new_items_total=new_items_total,
        primary_forager_name=forager_name,
        primary_forager_id=forager_id,
        foragers_href="/foragers#goldmine-alerts",
        cockpit_href="/cockpit#approvals",
    )


async def _compose_life_os_strip(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
) -> MissionLifeOsStripOut:
    """Build Life OS calendar strip from Google Calendar connector (read-only)."""

    connect_href = "/integrations?tab=connectors"
    if not settings.calendar_daily_planner_enabled:
        return MissionLifeOsStripOut(
            enabled=False,
            message="Calendar daily planner disabled.",
            connect_href=connect_href,
        )

    from app.application.services.calendar_daily_planner import compose_calendar_daily_planner

    calendar = await compose_calendar_daily_planner(
        session,
        dashboard_user_id=dashboard_user_id,
    )
    events = [
        MissionCalendarEventOut(
            id=row.id,
            title=row.title,
            start_at=row.start_at,
            end_at=row.end_at,
            detail=row.detail,
            href=row.href,
        )
        for row in calendar.items[:5]
    ]
    return MissionLifeOsStripOut(
        enabled=calendar.enabled,
        connected=calendar.connected,
        event_count=calendar.event_count,
        message=calendar.message,
        events=events,
        connect_href=connect_href,
    )


async def _compose_autopilot_strip(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> MissionAutopilotStripOut:
    """Build My 3 Bees + Four Lanes autopilot status for Mission Home."""

    harness_href = "/settings/harness"
    four_lanes_href = "/agentic-os#lanes"
    digest_href = "/cockpit#four-lanes"

    if not settings.routines_enabled:
        return MissionAutopilotStripOut(
            enabled=False,
            routines_enabled=False,
            message="Background routines disabled — enable in Settings → AI harness.",
            harness_href=harness_href,
            four_lanes_href=four_lanes_href,
            digest_href=digest_href,
        )

    from app.application.services.solo_operator_digest_inbox import compose_four_lane_digest_inbox
    from app.application.services.solo_operator_four_lanes import (
        FOUR_LANE_IDS,
        LANE_CRON,
        LANE_META,
        _lane_from_payload,
        _load_tenant_routines,
    )
    from app.application.services.solo_operator_trio import get_solo_trio_status

    trio = await get_solo_trio_status(session, tenant_id=tenant_id)
    digest = await compose_four_lane_digest_inbox(session, tenant_id=tenant_id, limit=20)
    routines = await _load_tenant_routines(session, tenant_id=tenant_id)

    lanes: list[MissionAutopilotLaneOut] = []
    for row in trio.get("lanes") or []:
        if not isinstance(row, dict):
            continue
        binding = str(row.get("binding") or "missing")
        routine_active = bool(row.get("routine_active"))
        if binding == "missing":
            status: Literal["active", "bound", "missing", "paused"] = "missing"
        elif routine_active:
            status = "active"
        else:
            status = "paused"
        lanes.append(
            MissionAutopilotLaneOut(
                id=str(row.get("lane_id") or ""),
                label=str(row.get("label") or "Bee"),
                group="trio",
                status=status,
                detail=str(row.get("description") or "")[:120],
            ),
        )

    active_four = 0
    cron_lane_count = 0
    for lane_id in FOUR_LANE_IDS:
        meta = LANE_META[lane_id]
        routine_row = next(
            (
                r
                for r in routines
                if _lane_from_payload(dict(r.context_payload or {})) == lane_id
            ),
            None,
        )
        cron = LANE_CRON.get(lane_id)
        if routine_row is not None and routine_row.is_active:
            active_four += 1
            if cron:
                cron_lane_count += 1
            lane_status: Literal["active", "bound", "missing", "paused"] = "active"
        elif routine_row is not None:
            lane_status = "paused"
        else:
            lane_status = "missing"
        lanes.append(
            MissionAutopilotLaneOut(
                id=lane_id,
                label=str(meta.get("label") or lane_id),
                group="four_lane",
                status=lane_status,
                detail=str(meta.get("operator_hint") or "")[:120],
                schedule_cron=cron,
            ),
        )

    trio_bound = int(trio.get("lanes_bound") or trio.get("bound_lane_count") or 0)
    digest_pending = int(digest.pending_count or 0)

    if active_four == 0:
        message = "Bootstrap Four Lanes in Agentic OS → Lanes to enable background digests."
    elif trio_bound < 2:
        message = f"My 3 Bees {trio_bound}/3 bound — link routines in Settings → AI harness."
    elif digest_pending > 0:
        message = f"{digest_pending} digest(s) waiting — review in Digest Inbox."
    else:
        message = f"Autopilot live — {cron_lane_count} cron lane(s), {active_four}/4 four-lanes active."

    return MissionAutopilotStripOut(
        enabled=True,
        routines_enabled=True,
        trio_bound=trio_bound,
        trio_total=int(trio.get("lanes_total") or 3),
        four_lanes_active=active_four,
        four_lanes_total=len(FOUR_LANE_IDS),
        digest_pending=digest_pending,
        cron_lane_count=cron_lane_count,
        message=message,
        lanes=lanes,
        harness_href=harness_href,
        four_lanes_href=four_lanes_href,
        digest_href=digest_href,
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
            factory_launch_widget_enabled=False,
            catalog_wave_widget_enabled=False,
            revenue_funnel_widget_enabled=False,
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
                loop_timeline_href=f"/agents?session={row.session_id}#agent-loop-timeline",
                tool_outcome_href=f"/agents?session={row.session_id}#tool-outcome-panel",
            ),
        )
    active_sessions = active_sessions[:3]
    agent_loop_strip = _compose_agent_loop_strip(active_sessions)
    tool_outcome_strip = _compose_tool_outcome_strip(active_sessions)
    loop_guardrails_strip = await _compose_loop_guardrails_strip(
        session,
        tenant_id=tenant_id,
        active_sessions=active_sessions,
    )
    goldmine_strip = await _compose_goldmine_strip(session, tenant_id=tenant_id)

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

    from app.application.services.personal_os_mode import personal_os_mission_home_revenue_widgets_enabled

    revenue_widgets = personal_os_mission_home_revenue_widgets_enabled()
    if settings.revenue_funnel_mission_home_enabled and revenue_widgets:
        from app.application.services.revenue_funnel_widget_service import (
            compose_revenue_funnel_widget_snapshot,
        )

        funnel = await compose_revenue_funnel_widget_snapshot(session, tenant_id=tenant_id)
        if funnel.enabled and not funnel.funnel_complete and funnel.primary_action is not None:
            action = funnel.primary_action
            href = action.href or funnel.launch_href
            if action.post_path:
                href = "/tasks#revenue-funnel"
            next_actions.insert(
                0,
                MissionActionOut(
                    id=f"funnel_{action.id}",
                    title=action.label,
                    detail=funnel.operator_hint[:240],
                    href=href,
                    priority=action.priority,
                ),
            )

    current_step = _resolve_process_step(
        first_run_complete=first_run.complete,
        approval_count=inbox.counts.total if inbox.enabled else 0,
        active_sessions=active_sessions,
        has_daily_plan=bool(daily.enabled and daily.items),
    )
    memory_strip = await _compose_memory_strip(session, tenant_id=tenant_id)
    second_brain_strip = await _compose_second_brain_strip(
        session,
        tenant_id=tenant_id,
        first_run_complete=first_run.complete,
    )
    life_os_strip = await _compose_life_os_strip(
        session,
        dashboard_user_id=dashboard_user_id,
    )
    autopilot_strip = await _compose_autopilot_strip(session, tenant_id=tenant_id)

    weak_signal = await compose_weak_signal_preview(session, tenant_id=tenant_id)
    jarvis_advisor = _compose_jarvis_advisor_strip(
        first_run_complete=first_run.complete,
        approvals=[
            JarvisApprovalIn.model_validate(row.model_dump())
            for row in approvals
        ],
        active_sessions=[
            JarvisSessionIn(
                session_id=row.session_id,
                goal=row.goal,
                status=row.status,
                href=row.href,
            )
            for row in active_sessions
        ],
        next_actions=[
            JarvisActionIn.model_validate(row.model_dump()) for row in next_actions
        ],
        life_os=JarvisLifeOsIn(
            enabled=life_os_strip.enabled,
            connected=life_os_strip.connected,
            connect_href=life_os_strip.connect_href,
            events=[
                JarvisCalendarEventIn(
                    id=event.id,
                    title=event.title,
                    start_at=event.start_at,
                    href=event.href,
                )
                for event in life_os_strip.events
            ],
        ),
        autopilot=JarvisAutopilotIn(
            enabled=autopilot_strip.enabled,
            routines_enabled=autopilot_strip.routines_enabled,
            trio_bound=autopilot_strip.trio_bound,
            trio_total=autopilot_strip.trio_total,
            four_lanes_active=autopilot_strip.four_lanes_active,
            digest_pending=autopilot_strip.digest_pending,
            harness_href=autopilot_strip.harness_href,
            four_lanes_href=autopilot_strip.four_lanes_href,
            digest_href=autopilot_strip.digest_href,
        ),
        memory_strip=JarvisMemoryIn(
            usage_pct=memory_strip.usage_pct,
            layers=[
                JarvisMemoryLayerIn(id=layer.id, label=layer.label, filled=layer.filled)
                for layer in memory_strip.layers
            ],
        ),
        weak_signal_hint=weak_signal.advisor_hint,
        pending_wiki_captures=second_brain_strip.pending_captures,
        goldmine_alert_count=goldmine_strip.alert_count if goldmine_strip.enabled else 0,
    )
    agent_quality = await compose_agent_quality_strip(session, tenant_id=tenant_id)
    weekly_reflection = await compose_jarvis_weekly_reflection_strip(
        session,
        tenant_id=tenant_id,
        first_run_complete=first_run.complete,
    )
    weekly_compound = await compose_mission_weekly_compound_strip(
        session,
        tenant_id=tenant_id,
        first_run_complete=first_run.complete,
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
        memory_strip=memory_strip,
        step_studios=STEP_STUDIOS.get(current_step, [])[:2],
        life_os_strip=life_os_strip,
        autopilot_strip=autopilot_strip,
        jarvis_advisor_strip=jarvis_advisor,
        agent_quality_strip=agent_quality,
        jarvis_weekly_reflection_strip=weekly_reflection,
        weekly_compound_strip=weekly_compound,
        second_brain_strip=second_brain_strip,
        agent_loop_strip=agent_loop_strip,
        tool_outcome_strip=tool_outcome_strip,
        loop_guardrails_strip=loop_guardrails_strip,
        goldmine_strip=goldmine_strip,
        first_run_complete=first_run.complete,
        links={
            "new_session": "/agents?preset=web-redesign-discovery#sessions",
            "approvals": "/cockpit#approvals",
            "knowledge": "/knowledge#memory",
            "kanban": "/tasks",
            "calendar_connect": life_os_strip.connect_href,
            "marketing_team": "/apps-tools/marketing-team",
            "harness": autopilot_strip.harness_href,
            "four_lanes": autopilot_strip.four_lanes_href,
            "digest_inbox": autopilot_strip.digest_href,
            "analytics": "/apps-tools/analytics",
            "research_bee": "/knowledge#research-bee",
            "cited_recall": "/knowledge?tab=memory#cited-recall",
            "wiki_layer": "/knowledge?tab=wiki",
            "agent_loop": "/agents#sessions",
            "tool_outcomes": "/agents#sessions",
            "goldmine": "/foragers#goldmine-alerts",
            "foragers": "/foragers#goldmine-alerts",
            "loop_presets": "/settings/harness#harness-closed-loop-presets",
        },
        rapid_loop_widget_enabled=settings.rapid_loop_mission_home_enabled,
        sub_swarm_fleet_widget_enabled=settings.sub_swarm_fleet_mission_home_enabled,
        factory_launch_widget_enabled=(
            settings.factory_launch_mission_home_enabled and revenue_widgets
        ),
        catalog_wave_widget_enabled=(
            settings.catalog_wave_mission_home_enabled and revenue_widgets
        ),
        revenue_funnel_widget_enabled=(
            settings.revenue_funnel_mission_home_enabled and revenue_widgets
        ),
    )


__all__ = [
    "MissionAutopilotStripOut",
    "MissionHomeSnapshotOut",
    "MissionLifeOsStripOut",
    "MissionMemoryStripOut",
    "ProcessStepId",
    "ProcessStepOut",
    "STEP_STUDIOS",
    "_compose_autopilot_strip",
    "_compose_life_os_strip",
    "_compose_memory_strip",
    "compose_mission_home_snapshot",
]
