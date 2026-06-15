"""AL4 — Pattern + tool explainer chips per loop phase and sub-agent step."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.agent_loop_timeline_service import LoopPhaseId, PHASE_LABELS
from app.application.services.supervisor.pattern_router import (
    PATTERN_GUARDRAILS,
    PATTERN_HUMAN_IN_LOOP,
    PATTERN_MULTI_AGENT,
    PATTERN_PLANNING,
    PATTERN_RAG,
    PATTERN_REFLECTION,
    PATTERN_RESOURCE_AWARE,
    PATTERN_ROUTING,
    PATTERN_TOOL_USE,
    select_patterns_for_task,
)
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)

PATTERN_LABELS: dict[str, str] = {
    "prompt_chaining": "Prompt Chaining",
    "routing": "Routing",
    "parallelization": "Parallelization",
    "reflection": "Reflection",
    "tool_use": "Tool Use",
    "planning": "Planning",
    "multi_agent": "Multi-Agent",
    "memory_management": "Memory",
    "learning_adaptation": "Learning",
    "goal_monitoring": "Goal Monitoring",
    "exception_handling": "Exception Handling",
    "human_in_the_loop": "Human-in-the-Loop",
    "rag": "RAG",
    "inter_agent_communication": "Inter-Agent Comms",
    "resource_aware": "Resource-Aware",
    "reasoning": "Reasoning",
    "guardrails": "Guardrails",
    "prioritization": "Prioritization",
    "exploration": "Exploration",
}

_PHASE_PATTERNS: dict[LoopPhaseId, list[str]] = {
    "goal": [PATTERN_PLANNING, "goal_monitoring", PATTERN_HUMAN_IN_LOOP],
    "plan": [PATTERN_MULTI_AGENT, PATTERN_ROUTING, "parallelization"],
    "tool": [PATTERN_TOOL_USE, PATTERN_RAG, PATTERN_RESOURCE_AWARE],
    "verify": [PATTERN_REFLECTION, PATTERN_GUARDRAILS, PATTERN_HUMAN_IN_LOOP],
}

_ROLE_PATTERN: dict[str, str] = {
    "researcher": PATTERN_RAG,
    "research": PATTERN_RAG,
    "coder": PATTERN_TOOL_USE,
    "browser": PATTERN_TOOL_USE,
    "publisher": PATTERN_TOOL_USE,
    "critic": PATTERN_REFLECTION,
    "reviewer": PATTERN_REFLECTION,
    "planner": PATTERN_PLANNING,
    "orchestrator": PATTERN_ROUTING,
}

_PATTERN_WHY: dict[str, str] = {
    PATTERN_PLANNING: "Break the mission into ordered sub-steps before execution.",
    PATTERN_MULTI_AGENT: "Split responsibilities across specialized sub-agents.",
    PATTERN_ROUTING: "Route each lane to the right specialist role.",
    "parallelization": "Run independent lanes concurrently when safe.",
    PATTERN_TOOL_USE: "Execute actions via connectors instead of guessing.",
    PATTERN_RAG: "Ground answers with retrieved context before publishing.",
    PATTERN_RESOURCE_AWARE: "Prefer economy hops for lightweight sub-steps.",
    PATTERN_REFLECTION: "Critic reviews output quality before the verify gate.",
    PATTERN_GUARDRAILS: "SLO and rubric floors block premature live actions.",
    PATTERN_HUMAN_IN_LOOP: "Operator must approve risky live steps.",
    "goal_monitoring": "Track durable progress against the mission goal.",
    "reasoning": "Chain reasoning steps for research-heavy goals.",
    "memory_management": "Reuse hive memory so agents do not repeat work.",
}


class PatternToolExplainerChipOut(BaseModel):
    """One explainer chip for a loop phase or sub-agent step."""

    model_config = ConfigDict(extra="ignore")

    chip_id: str
    phase_id: LoopPhaseId | None = None
    phase_label: str | None = None
    sub_agent_role: str | None = None
    pattern_id: str
    pattern_label: str
    tool_name: str | None = None
    tool_label: str | None = None
    explainer: str


class PatternToolExplainerOut(BaseModel):
    """Session drawer pattern + tool explainer snapshot for AL4."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    visible: bool = False
    session_id: uuid.UUID
    session_status: str
    chips: list[PatternToolExplainerChipOut] = Field(default_factory=list)
    pattern_rationale: list[str] = Field(default_factory=list)
    operator_hint: str = "Why this tool — without reading raw JSON events."


def _pattern_label(pattern_id: str) -> str:
    norm = pattern_id.strip()
    if not norm:
        return "—"
    return PATTERN_LABELS.get(norm, norm.replace("_", " ").title())


def _tool_display_label(tool_name: str, registry: dict[str, dict[str, Any]]) -> str:
    key = tool_name.strip().lower()
    if not key:
        return "—"
    row = registry.get(key)
    if row is None:
        return tool_name.replace("_", " ").title()
    display = str(row.get("display_name") or row.get("connector_display_name") or "").strip()
    if display:
        return display
    description = str(row.get("description") or "").strip()
    if description and len(description) <= 48:
        return description
    return tool_name.replace("_", " ").title()


def _build_registry_lookup(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        tool_name = str(row.get("tool_name") or row.get("name") or "").strip().lower()
        if not tool_name:
            continue
        lookup[tool_name] = row
    return lookup


def _extract_patterns(session) -> tuple[list[str], list[str]]:  # noqa: ANN001
    """Return primary + secondary pattern IDs from session context or router fallback."""

    summary = dict(getattr(session, "context_summary", None) or {})
    agentic = summary.get("agentic_patterns")
    if isinstance(agentic, dict):
        primary = [str(item).strip() for item in agentic.get("primary") or [] if str(item).strip()]
        secondary = [str(item).strip() for item in agentic.get("secondary") or [] if str(item).strip()]
        if primary or secondary or "primary" in agentic or "secondary" in agentic:
            return primary, secondary

    goal = str(summary.get("raw_goal") or getattr(session, "goal", "") or "").strip()
    roles = [str(sub.role or "").strip() for sub in getattr(session, "sub_agents", None) or [] if sub.role]
    selection = select_patterns_for_task(goal=goal, roles=roles)
    return selection.primary, selection.secondary


def _pattern_rationale(session) -> list[str]:  # noqa: ANN001
    summary = dict(getattr(session, "context_summary", None) or {})
    agentic = summary.get("agentic_patterns")
    if isinstance(agentic, dict):
        rationale = agentic.get("rationale")
        if isinstance(rationale, list):
            return [str(item).strip() for item in rationale if str(item).strip()][:4]
    goal = str(summary.get("raw_goal") or getattr(session, "goal", "") or "").strip()
    roles = [str(sub.role or "").strip() for sub in getattr(session, "sub_agents", None) or [] if sub.role]
    return select_patterns_for_task(goal=goal, roles=roles).rationale[:4]


def _primary_tool_for_sub(sub) -> str | None:  # noqa: ANN001
    memory = dict(getattr(sub, "short_memory", None) or {})
    discovered = memory.get("discovered_tools")
    if isinstance(discovered, list):
        for item in discovered:
            name = str(item).strip()
            if name:
                return name
    toolset = getattr(sub, "toolset", None) or []
    if isinstance(toolset, list):
        for item in toolset:
            name = str(item).strip()
            if name:
                return name
    return None


def _compose_explainer(
    *,
    pattern_id: str,
    tool_name: str | None,
    tool_label: str | None,
) -> str:
    why = _PATTERN_WHY.get(pattern_id, "Selected for this loop step.")
    if tool_name:
        label = tool_label or tool_name.replace("_", " ")
        return f"{why} Tool: {label}."
    return why


def _phase_chip(
    *,
    phase_id: LoopPhaseId,
    pattern_id: str,
    tool_name: str | None,
    registry: dict[str, dict[str, Any]],
) -> PatternToolExplainerChipOut:
    tool_label = _tool_display_label(tool_name, registry) if tool_name else None
    return PatternToolExplainerChipOut(
        chip_id=f"phase:{phase_id}:{pattern_id}:{tool_name or 'none'}",
        phase_id=phase_id,
        phase_label=PHASE_LABELS[phase_id],
        pattern_id=pattern_id,
        pattern_label=_pattern_label(pattern_id),
        tool_name=tool_name,
        tool_label=tool_label,
        explainer=_compose_explainer(pattern_id=pattern_id, tool_name=tool_name, tool_label=tool_label),
    )


def _sub_agent_chip(
    *,
    role: str,
    pattern_id: str,
    tool_name: str | None,
    registry: dict[str, dict[str, Any]],
) -> PatternToolExplainerChipOut:
    tool_label = _tool_display_label(tool_name, registry) if tool_name else None
    norm_role = role.strip().lower() or "sub-agent"
    return PatternToolExplainerChipOut(
        chip_id=f"sub:{norm_role}:{pattern_id}:{tool_name or 'none'}",
        sub_agent_role=norm_role,
        pattern_id=pattern_id,
        pattern_label=_pattern_label(pattern_id),
        tool_name=tool_name,
        tool_label=tool_label,
        explainer=_compose_explainer(pattern_id=pattern_id, tool_name=tool_name, tool_label=tool_label),
    )


def _tools_from_events(events, *, role_map: dict[str, str]) -> dict[str, str]:  # noqa: ANN001
    """Map sub-agent role → first tool name seen in timeline."""

    role_tools: dict[str, str] = {}
    for event in sorted(events, key=lambda row: row.occurred_at):
        event_type = str(getattr(event, "event_type", "")).strip()
        if event_type not in {"tool_execute", "dynamic_tools_discovered"}:
            continue
        sub_id = getattr(event, "sub_agent_session_id", None)
        sub_role = role_map.get(str(sub_id)) if sub_id else None
        if not sub_role:
            continue
        payload = dict(getattr(event, "payload", None) or {})
        tool_name = str(payload.get("tool_name") or "").strip()
        if not tool_name and event_type == "dynamic_tools_discovered":
            tools = payload.get("tools") or payload.get("discovered_tools") or []
            if isinstance(tools, list) and tools:
                tool_name = str(tools[0]).strip()
        if tool_name and sub_role not in role_tools:
            role_tools[sub_role] = tool_name
    return role_tools


def derive_pattern_tool_explainer(
    *,
    session,
    events,
    registry_rows: list[dict[str, Any]] | None = None,
) -> PatternToolExplainerOut:  # noqa: ANN001
    """Build AL4 explainer chips from session row, events, and optional registry."""

    session_status = str(getattr(session, "status", ""))
    primary, secondary = _extract_patterns(session)
    active_patterns = primary + [p for p in secondary if p not in primary]
    registry = _build_registry_lookup(registry_rows or [])
    rationale = _pattern_rationale(session)

    role_map = {
        str(sub.id): str(sub.role or "sub-agent").strip().lower()
        for sub in getattr(session, "sub_agents", None) or []
    }
    role_tools = _tools_from_events(events, role_map=role_map)

    chips: list[PatternToolExplainerChipOut] = []
    seen: set[str] = set()

    if not active_patterns and not getattr(session, "sub_agents", None):
        return PatternToolExplainerOut(
            enabled=True,
            visible=False,
            session_id=session.id,
            session_status=session_status,
            chips=[],
            pattern_rationale=rationale,
        )

    for phase_id, candidates in _PHASE_PATTERNS.items():
        chosen = next((pid for pid in candidates if pid in active_patterns), candidates[0])
        tool_name: str | None = None
        if phase_id == "tool":
            if role_tools:
                tool_name = next(iter(role_tools.values()))
            else:
                for sub in getattr(session, "sub_agents", None) or []:
                    tool_name = _primary_tool_for_sub(sub)
                    if tool_name:
                        break
        chip = _phase_chip(phase_id=phase_id, pattern_id=chosen, tool_name=tool_name, registry=registry)
        if chip.chip_id not in seen:
            seen.add(chip.chip_id)
            chips.append(chip)

    for sub in getattr(session, "sub_agents", None) or []:
        role = str(sub.role or "sub-agent").strip().lower()
        norm_key = role.replace("-", "_")
        pattern_id = _ROLE_PATTERN.get(norm_key) or _ROLE_PATTERN.get(role)
        if pattern_id is None:
            pattern_id = PATTERN_TOOL_USE if _primary_tool_for_sub(sub) else PATTERN_ROUTING
        tool_name = role_tools.get(role) or _primary_tool_for_sub(sub)
        chip = _sub_agent_chip(role=role, pattern_id=pattern_id, tool_name=tool_name, registry=registry)
        if chip.chip_id not in seen:
            seen.add(chip.chip_id)
            chips.append(chip)

    visible = bool(chips) and (bool(active_patterns) or bool(getattr(session, "sub_agents", None)))

    return PatternToolExplainerOut(
        enabled=True,
        visible=visible,
        session_id=session.id,
        session_status=session_status,
        chips=chips[:12],
        pattern_rationale=rationale,
    )


async def compose_pattern_tool_explainer(
    session: AsyncSession,
    *,
    supervisor_session,
    event_limit: int = 500,
) -> PatternToolExplainerOut:  # noqa: ANN001
    """Load events + registry and compose AL4 pattern/tool explainer."""

    if not settings.pattern_tool_explainer_enabled:
        return PatternToolExplainerOut(
            enabled=False,
            visible=False,
            session_id=supervisor_session.id,
            session_status=str(getattr(supervisor_session, "status", "")),
        )

    from app.application.services.supervisor.session_service import list_session_events
    from app.application.services.tool_marketplace import tool_registry_snapshot

    events = await list_session_events(
        session,
        session_id=supervisor_session.id,
        limit=event_limit,
        offset=0,
    )
    summary = dict(getattr(supervisor_session, "context_summary", None) or {})
    goal = str(summary.get("raw_goal") or getattr(supervisor_session, "goal", "") or "").strip()
    registry_rows = await tool_registry_snapshot(session, goal=goal, limit=32)

    panel = derive_pattern_tool_explainer(
        session=supervisor_session,
        events=events,
        registry_rows=registry_rows,
    )
    _logger.info(
        "pattern_tool_explainer.composed",
        agent_id="pattern_tool_explainer",
        swarm_id=str(supervisor_session.id),
        task_id=str(supervisor_session.task_id) if supervisor_session.task_id else None,
        visible=panel.visible,
        chip_count=len(panel.chips),
    )
    return panel


__all__ = [
    "PatternToolExplainerChipOut",
    "PatternToolExplainerOut",
    "compose_pattern_tool_explainer",
    "derive_pattern_tool_explainer",
]
