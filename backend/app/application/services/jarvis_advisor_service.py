"""POS-H1 — Jarvis daily advisor: ordered operator steps from verified Mission Home signals."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

JarvisStepKind = Literal[
    "verify",
    "work",
    "setup",
    "learn",
    "calendar",
    "autopilot",
    "analytics",
    "research",
]


class JarvisActionIn(BaseModel):
    """Daily plan action input for advisor ordering."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    detail: str
    href: str | None = None
    priority: int = 2


class JarvisApprovalIn(BaseModel):
    """Approval inbox row for advisor ordering."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    detail: str
    href: str
    kind: str


class JarvisSessionIn(BaseModel):
    """Active session row for advisor ordering."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    goal: str
    status: str
    href: str


class JarvisCalendarEventIn(BaseModel):
    """Calendar event for advisor ordering."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    start_at: datetime | None = None
    href: str = "/integrations?tab=connectors"


class JarvisLifeOsIn(BaseModel):
    """Life OS strip input."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    connected: bool = False
    events: list[JarvisCalendarEventIn] = Field(default_factory=list)
    connect_href: str = "/integrations?tab=connectors"


class JarvisAutopilotIn(BaseModel):
    """Autopilot strip input."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    routines_enabled: bool = False
    trio_bound: int = 0
    trio_total: int = 3
    four_lanes_active: int = 0
    digest_pending: int = 0
    harness_href: str = "/settings/harness"
    four_lanes_href: str = "/agentic-os#lanes"
    digest_href: str = "/cockpit#four-lanes"


class JarvisMemoryLayerIn(BaseModel):
    """Brain Pack layer input."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    filled: bool = False


class JarvisMemoryIn(BaseModel):
    """Memory strip input."""

    model_config = ConfigDict(extra="ignore")

    usage_pct: int = 0
    layers: list[JarvisMemoryLayerIn] = Field(default_factory=list)


class MissionJarvisStepOut(BaseModel):
    """One ordered step in today's Jarvis advisor strip."""

    model_config = ConfigDict(extra="ignore")

    order: int = Field(ge=1, le=3)
    title: str
    detail: str
    href: str
    kind: JarvisStepKind = "work"


class _JarvisCandidate(BaseModel):
    """Internal candidate before order assignment."""

    model_config = ConfigDict(extra="ignore")

    title: str
    detail: str
    href: str
    kind: JarvisStepKind = "work"


class MissionJarvisAdvisorStripOut(BaseModel):
    """Proactive daily advisor — three steps max, simulate-first ordering."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    headline: str = "Today in order"
    message: str = ""
    steps: list[MissionJarvisStepOut] = Field(default_factory=list)
    analytics_href: str = "/apps-tools/analytics"
    research_href: str = "/knowledge#research-bee"
    loops_href: str = "/settings/harness#harness-closed-loop-presets"


def _compose_jarvis_advisor_strip(
    *,
    first_run_complete: bool,
    approvals: list[JarvisApprovalIn],
    active_sessions: list[JarvisSessionIn],
    next_actions: list[JarvisActionIn],
    life_os: JarvisLifeOsIn,
    autopilot: JarvisAutopilotIn,
    memory_strip: JarvisMemoryIn,
    weak_signal_hint: str | None = None,
    pending_wiki_captures: int = 0,
) -> MissionJarvisAdvisorStripOut:
    """Build up to three prioritized steps — verify blockers before new work."""

    if not settings.jarvis_advisor_mission_home_enabled:
        return MissionJarvisAdvisorStripOut(
            enabled=False,
            message="Jarvis advisor disabled in settings.",
        )

    candidates: list[tuple[int, _JarvisCandidate]] = []

    if not first_run_complete:
        candidates.append(
            (
                0,
                _JarvisCandidate(
                    title="Finish first-run setup",
                    detail="LLM keys → Brain Pack → first supervisor session unlocks the daily loop.",
                    href="/agents#first-run-wizard",
                    kind="setup",
                ),
            ),
        )

    if approvals:
        top = approvals[0]
        candidates.append(
            (
                1,
                _JarvisCandidate(
                    title=f"Review {len(approvals)} approval(s)",
                    detail=top.detail[:200] or "Simulate-first gates waiting for your sign-off.",
                    href=top.href,
                    kind="verify",
                ),
            ),
        )

    if pending_wiki_captures > 0:
        candidates.append(
            (
                2,
                _JarvisCandidate(
                    title=f"Approve {pending_wiki_captures} wiki capture(s)",
                    detail="Second-brain notes waiting — compile into Wiki Layer before cited recall.",
                    href="/knowledge?tab=wiki#second-brain-capture-approve",
                    kind="verify",
                ),
            ),
        )

    for session in active_sessions:
        if session.status == "needs_input":
            candidates.append(
                (
                    2,
                    _JarvisCandidate(
                        title="Unblock active session",
                        detail=session.goal[:200] or "Supervisor needs your input to continue verify loop.",
                        href=session.href,
                        kind="verify",
                    ),
                ),
            )
            break

    for session in active_sessions:
        if session.status == "running":
            candidates.append(
                (
                    8,
                    _JarvisCandidate(
                        title="Watch agent loop",
                        detail=(session.goal[:160] or "Supervisor session")
                        + " — Goal → Plan → Tool → Verify timeline.",
                        href=f"/agents?session={session.session_id}#agent-loop-timeline",
                        kind="work",
                    ),
                ),
            )
            break

    if autopilot.enabled and autopilot.digest_pending > 0:
        candidates.append(
            (
                3,
                _JarvisCandidate(
                    title=f"Review {autopilot.digest_pending} digest(s)",
                    detail="Four Lanes produced background intel — promote or dismiss before new work.",
                    href=autopilot.digest_href,
                    kind="verify",
                ),
            ),
        )

    if weak_signal_hint:
        candidates.append(
            (
                4,
                _JarvisCandidate(
                    title="Scan weak signals",
                    detail=weak_signal_hint[:220],
                    href="/cockpit#four-lanes",
                    kind="learn",
                ),
            ),
        )

    empty_layers = [layer for layer in memory_strip.layers if not layer.filled]
    if empty_layers and memory_strip.usage_pct < 25:
        labels = ", ".join(layer.label for layer in empty_layers[:2])
        candidates.append(
            (
                5,
                _JarvisCandidate(
                    title="Fill Brain Pack",
                    detail=f"{labels} empty — Queen prompts stay weak without curated memory.",
                    href="/knowledge?tab=memory#brain-pack",
                    kind="setup",
                ),
            ),
        )
    elif settings.cited_recall_panel_enabled and memory_strip.usage_pct >= 25:
        candidates.append(
            (
                7,
                _JarvisCandidate(
                    title="Test cited recall",
                    detail="Ask hive memory with source citations before dispatch — explicit not-in-memory when missing.",
                    href="/knowledge?tab=memory#cited-recall",
                    kind="learn",
                ),
            ),
        )

    if life_os.enabled and life_os.connected and life_os.events:
        event = life_os.events[0]
        time_label = "soon"
        if event.start_at is not None:
            time_label = event.start_at.strftime("%H:%M")
        candidates.append(
            (
                6,
                _JarvisCandidate(
                    title=f"Calendar: {event.title[:80]}",
                    detail=f"Starts {time_label} — block deep work before this meeting.",
                    href=event.href or life_os.connect_href,
                    kind="calendar",
                ),
            ),
        )

    for action in next_actions[:2]:
        if not action.href:
            continue
        candidates.append(
            (
                7,
                _JarvisCandidate(
                    title=action.title[:100],
                    detail=action.detail[:200],
                    href=action.href,
                    kind="work",
                ),
            ),
        )

    if autopilot.enabled and autopilot.four_lanes_active == 0:
        candidates.append(
            (
                8,
                _JarvisCandidate(
                    title="Bootstrap Four Lanes",
                    detail="Background digests power morning brief — enable lanes in Agentic OS.",
                    href=autopilot.four_lanes_href,
                    kind="autopilot",
                ),
            ),
        )
    elif autopilot.enabled and autopilot.trio_bound < 2:
        candidates.append(
            (
                9,
                _JarvisCandidate(
                    title="Bind My 3 Bees",
                    detail=f"{autopilot.trio_bound}/{autopilot.trio_total} routines linked — harness binds daily lanes.",
                    href=autopilot.harness_href,
                    kind="autopilot",
                ),
            ),
        )

    if settings.analytics_workspace_enabled:
        candidates.append(
            (
                10,
                _JarvisCandidate(
                    title="Ask your data analyst",
                    detail="NotebookLM-style reports with simulate-first critic — one question, verified export.",
                    href="/apps-tools/analytics",
                    kind="analytics",
                ),
            ),
        )

    if settings.research_bee_enabled:
        candidates.append(
            (
                11,
                _JarvisCandidate(
                    title="Run research project",
                    detail="Batch URLs → structured Hive Mind brief — no raw LLM dump.",
                    href="/knowledge#research-bee",
                    kind="research",
                ),
            ),
        )

    if settings.closed_loop_presets_enabled:
        candidates.append(
            (
                12,
                _JarvisCandidate(
                    title="Apply today's loop preset",
                    detail="Closed-loop guardrails — Factory, social intel, or publish bulk simulate-first.",
                    href="/settings/harness#harness-closed-loop-presets",
                    kind="work",
                ),
            ),
        )

    candidates.append(
        (
            20,
            _JarvisCandidate(
                title="Start supervisor session",
                detail="Dispatch bees with simulate-first verify when no higher-priority gate is open.",
                href="/agents?preset=web-redesign-discovery#sessions",
                kind="work",
            ),
        ),
    )

    candidates.sort(key=lambda row: row[0])
    seen_titles: set[str] = set()
    steps: list[MissionJarvisStepOut] = []
    for _, candidate in candidates:
        key = candidate.title.lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        steps.append(
            MissionJarvisStepOut(
                order=len(steps) + 1,
                title=candidate.title,
                detail=candidate.detail,
                href=candidate.href,
                kind=candidate.kind,
            ),
        )
        if len(steps) >= 3:
            break

    message = "Three steps — verify gates first, then work."
    if not first_run_complete:
        message = "Complete setup before background autopilot pays off."
    elif approvals:
        message = "Approvals block live actions — clear verify first."

    return MissionJarvisAdvisorStripOut(
        enabled=True,
        headline="Jarvis · today in order",
        message=message,
        steps=steps,
    )


__all__ = [
    "JarvisActionIn",
    "JarvisApprovalIn",
    "JarvisAutopilotIn",
    "JarvisLifeOsIn",
    "JarvisMemoryIn",
    "JarvisSessionIn",
    "MissionJarvisAdvisorStripOut",
    "MissionJarvisStepOut",
    "_compose_jarvis_advisor_strip",
]
