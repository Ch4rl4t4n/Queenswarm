"""AL2 — Tool Outcome Panel: tool evidence at needs_input / approve."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.loop_guardrails_service import (
    last_rubric_score_from_summary,
    loop_min_score_from_summary,
    min_score_to_five_scale,
)
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)

SimMode = Literal["draft", "simulate", "live", "unknown"]


class ToolOutcomeEntryOut(BaseModel):
    """One tool execution or discovery row for operator review."""

    model_config = ConfigDict(extra="ignore")

    tool_name: str
    connector_slug: str | None = None
    mode: SimMode = "unknown"
    risk_tier: str | None = None
    args_summary: str = "—"
    result_summary: str = ""
    simulated: bool | None = None
    executed: bool | None = None
    sub_agent_role: str | None = None
    event_type: str = "tool_execute"
    occurred_at: datetime | None = None


class CriticOutcomeOut(BaseModel):
    """Rubric / strategy score surfaced before approve."""

    model_config = ConfigDict(extra="ignore")

    score: float | None = None
    score_label: str | None = None
    min_score_label: str | None = None
    passed: bool | None = None
    feedback: str | None = None
    source: str | None = None


class ToolOutcomePanelOut(BaseModel):
    """Session drawer tool outcome snapshot for AL2."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    session_id: uuid.UUID
    session_status: str
    visible: bool = False
    pending_approval: bool = False
    approval_reason: str | None = None
    tools: list[ToolOutcomeEntryOut] = Field(default_factory=list)
    critic: CriticOutcomeOut | None = None
    operator_action: str = "Review tool outcomes before approving live actions."


TOOL_OUTCOME_EVENT_TYPES = frozenset({
    "tool_execute",
    "browser_step",
    "browser_auto_step",
    "browser_fallback_spawned",
    "dynamic_tools_discovered",
    "pr_draft",
    "maintainer_run",
    "handoff_maintainer",
    "approval_requested",
    "needs_input_requested",
})


def _clip(text: str, limit: int = 160) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1]}…"


def _args_summary(payload: dict[str, Any]) -> str:
    """Render compact argument preview from event payload."""

    raw = payload.get("arguments") or payload.get("args") or payload.get("preview")
    if isinstance(raw, dict):
        preview = raw.get("arguments") if isinstance(raw.get("arguments"), dict) else raw
        if isinstance(preview, dict):
            parts = [f"{key}={_clip(str(value), 36)}" for key, value in list(preview.items())[:4]]
            return ", ".join(parts) if parts else "—"
    if isinstance(raw, str) and raw.strip():
        return _clip(raw, 120)
    return "—"


def _normalize_mode(payload: dict[str, Any]) -> SimMode:
    raw = str(payload.get("mode") or "").strip().lower()
    if raw in {"draft", "simulate", "live"}:
        return raw  # type: ignore[return-value]
    executed = payload.get("executed")
    if executed is False:
        return "simulate"
    if executed is True:
        return "live"
    return "unknown"


def _parse_tool_from_message(message: str) -> tuple[str | None, str | None]:
    """Fallback parse connector/tool from event message."""

    text = message.strip()
    for prefix in ("Draft preview:", "Simulated:", "Executed:", "Failed:"):
        if prefix in text:
            tail = text.split(prefix, maxsplit=1)[1].strip()
            if "/" in tail:
                connector, tool = tail.split("/", maxsplit=1)
                return connector.strip(), tool.split("(", maxsplit=1)[0].strip()
    return None, None


def _tool_entry_from_event(event, *, sub_role: str | None = None) -> ToolOutcomeEntryOut | None:  # noqa: ANN001
    """Map one session event to a tool outcome row."""

    payload = dict(getattr(event, "payload", None) or {})
    event_type = str(getattr(event, "event_type", "")).strip()
    message = str(getattr(event, "message", "") or "")

    tool_name = str(payload.get("tool_name") or "").strip()
    connector_slug = str(payload.get("connector_slug") or payload.get("connector") or "").strip() or None

    if not tool_name:
        parsed_connector, parsed_tool = _parse_tool_from_message(message)
        tool_name = parsed_tool or ""
        connector_slug = connector_slug or parsed_connector

    if event_type == "dynamic_tools_discovered":
        tools = payload.get("tools") or payload.get("discovered_tools") or []
        if isinstance(tools, list) and tools:
            names = [str(item).strip() for item in tools[:6] if str(item).strip()]
            tool_name = names[0] if len(names) == 1 else f"{len(names)} tools"
            result_summary = ", ".join(names) if len(names) > 1 else "Discovered for sub-agent step."
        else:
            tool_name = tool_name or "dynamic tools"
            result_summary = message or "Tools discovered for execution."
        return ToolOutcomeEntryOut(
            tool_name=tool_name,
            connector_slug=connector_slug,
            mode="unknown",
            args_summary="—",
            result_summary=_clip(result_summary or message),
            sub_agent_role=sub_role,
            event_type=event_type,
            occurred_at=getattr(event, "occurred_at", None),
        )

    if event_type in {"approval_requested", "needs_input_requested"}:
        reason = str(payload.get("reason") or payload.get("message") or message).strip()
        request = payload.get("needs_input_request")
        if isinstance(request, dict) and not reason:
            reason = str(request.get("prompt") or request.get("reason") or "").strip()
        return ToolOutcomeEntryOut(
            tool_name="operator checkpoint",
            connector_slug=None,
            mode="unknown",
            args_summary=_clip(reason or "Awaiting operator decision", 120),
            result_summary=_clip(message or reason),
            sub_agent_role=sub_role,
            event_type=event_type,
            occurred_at=getattr(event, "occurred_at", None),
        )

    if event_type in {"browser_step", "browser_auto_step", "browser_fallback_spawned"}:
        tool_name = tool_name or "browser automation"
        step = str(payload.get("step") or payload.get("action") or "").strip()
        return ToolOutcomeEntryOut(
            tool_name=tool_name,
            connector_slug=connector_slug or "browser",
            mode=_normalize_mode(payload),
            risk_tier=str(payload.get("risk_tier") or "read") if payload.get("risk_tier") else "read",
            args_summary=_args_summary(payload) if step == "" else _clip(step, 120),
            result_summary=_clip(message or step or "Browser step recorded."),
            simulated=payload.get("executed") is False if "executed" in payload else None,
            executed=bool(payload.get("executed")) if isinstance(payload.get("executed"), bool) else None,
            sub_agent_role=sub_role,
            event_type=event_type,
            occurred_at=getattr(event, "occurred_at", None),
        )

    if not tool_name:
        if event_type in {"pr_draft", "maintainer_run", "handoff_maintainer"}:
            tool_name = event_type.replace("_", " ")
        else:
            return None

    mode = _normalize_mode(payload)
    simulated_result = payload.get("simulated_result")
    result_summary = message
    if isinstance(simulated_result, dict):
        result_summary = str(simulated_result.get("status") or simulated_result.get("echo") or message)
    elif payload.get("preview") and isinstance(payload["preview"], dict):
        result_summary = json.dumps(payload["preview"], default=str)[:160]

    return ToolOutcomeEntryOut(
        tool_name=tool_name,
        connector_slug=connector_slug,
        mode=mode,
        risk_tier=str(payload.get("risk_tier") or "").strip() or None,
        args_summary=_args_summary(payload),
        result_summary=_clip(str(result_summary)),
        simulated=mode == "simulate" or payload.get("executed") is False,
        executed=bool(payload.get("executed")) if isinstance(payload.get("executed"), bool) else None,
        sub_agent_role=sub_role,
        event_type=event_type,
        occurred_at=getattr(event, "occurred_at", None),
    )


def _sub_agent_role_map(session) -> dict[str, str]:  # noqa: ANN001
    mapping: dict[str, str] = {}
    for sub in getattr(session, "sub_agents", None) or []:
        mapping[str(sub.id)] = str(sub.role or "sub-agent")
    return mapping


def _entries_from_sub_agents(session) -> list[ToolOutcomeEntryOut]:  # noqa: ANN001
    """Supplement timeline with pending sub-agent toolsets and outputs."""

    rows: list[ToolOutcomeEntryOut] = []
    for sub in getattr(session, "sub_agents", None) or []:
        role = str(sub.role or "sub-agent")
        status = str(sub.status or "").strip().lower()
        if status not in {"needs_input", "running", "completed"}:
            continue

        memory = dict(getattr(sub, "short_memory", None) or {})
        discovered = memory.get("discovered_tools")
        if isinstance(discovered, list):
            for tool in discovered[:4]:
                name = str(tool).strip()
                if not name:
                    continue
                rows.append(
                    ToolOutcomeEntryOut(
                        tool_name=name,
                        connector_slug=None,
                        mode="unknown",
                        args_summary="Discovered in sub-agent memory",
                        result_summary=_clip(str(memory.get("last_summary") or "")),
                        sub_agent_role=role,
                        event_type="discovered_tool",
                    ),
                )

        toolset = getattr(sub, "toolset", None) or []
        if isinstance(toolset, list):
            for tool in toolset[:4]:
                name = str(tool).strip()
                if not name:
                    continue
                if any(row.tool_name == name and row.sub_agent_role == role for row in rows):
                    continue
                rows.append(
                    ToolOutcomeEntryOut(
                        tool_name=name,
                        connector_slug=None,
                        mode="unknown",
                        args_summary=f"Lane status: {status}",
                        result_summary=_clip(str(getattr(sub, "last_output", None) or memory.get("last_summary") or "")),
                        sub_agent_role=role,
                        event_type="toolset",
                    ),
                )
    return rows


def _compose_critic(session, events) -> CriticOutcomeOut | None:  # noqa: ANN001
    """Derive critic / rubric block from context and reflections."""

    summary = dict(getattr(session, "context_summary", None) or {})
    rubric_score = last_rubric_score_from_summary(summary)
    min_score = loop_min_score_from_summary(summary)

    feedback: str | None = None
    source: str | None = None

    strategy_score = summary.get("latest_strategy_score")
    if rubric_score is None and isinstance(strategy_score, (int, float)):
        rubric_score = max(0.0, min(float(strategy_score), 1.0))
        source = "strategy_score"

    for sub in getattr(session, "sub_agents", None) or []:
        memory = dict(getattr(sub, "short_memory", None) or {})
        reflections = memory.get("reflection_reports")
        if isinstance(reflections, list) and reflections:
            last = reflections[-1]
            if isinstance(last, dict):
                fb = str(last.get("feedback") or last.get("summary") or "").strip()
                if fb:
                    feedback = _clip(fb, 240)
                    source = source or "reflection"
                conf = last.get("confidence") or last.get("score")
                if rubric_score is None and isinstance(conf, (int, float)):
                    rubric_score = max(0.0, min(float(conf), 1.0))
                    source = source or "reflection"

    for event in sorted(events, key=lambda row: row.occurred_at, reverse=True):
        if getattr(event, "event_type", "") != "session_review":
            continue
        payload = dict(getattr(event, "payload", None) or {})
        note = str(payload.get("note") or "").strip()
        if note:
            feedback = feedback or _clip(note, 240)
            source = source or "session_review"
        break

    if rubric_score is None and feedback is None:
        return None

    passed: bool | None = None
    if rubric_score is not None:
        passed = rubric_score >= min_score

    return CriticOutcomeOut(
        score=rubric_score,
        score_label=min_score_to_five_scale(rubric_score) if rubric_score is not None else None,
        min_score_label=min_score_to_five_scale(min_score),
        passed=passed,
        feedback=feedback,
        source=source,
    )


def _resolve_operator_action(
    *,
    session_status: str,
    pending_approval: bool,
    approval_reason: str | None,
    critic: CriticOutcomeOut | None,
    tool_count: int,
) -> str:
    """Operator-facing next step for AL2 panel."""

    normalized = session_status.strip().lower()
    if normalized != "needs_input":
        if tool_count == 0:
            return "Tool outcomes appear when execution events are recorded."
        return "Tool evidence captured — open when session reaches verify."

    if pending_approval and approval_reason:
        return f"Critical action gate: {_clip(approval_reason, 140)} Review tools below, then Approve or Reject."

    if critic is not None and critic.passed is False:
        return (
            f"Critic below floor ({critic.min_score_label or 'threshold'}). "
            "Reject or revise before live publish/trade."
        )

    if tool_count == 0:
        return "Session needs input — inspect sub-agent outputs and approve when ready."

    return "Review simulate results and critic score below, then Approve to continue."


def derive_tool_outcome_panel(
    *,
    session,
    events,
) -> ToolOutcomePanelOut:  # noqa: ANN001
    """Build AL2 tool outcome panel from session row and timeline events."""

    session_status = str(getattr(session, "status", ""))
    summary = dict(getattr(session, "context_summary", None) or {})
    pending_approval = bool(summary.get("approval_required"))
    approval_reason = str(summary.get("approval_reason") or "").strip() or None

    role_map = _sub_agent_role_map(session)
    tool_rows: list[ToolOutcomeEntryOut] = []
    seen: set[tuple[str, str, str]] = set()

    ordered = sorted(events, key=lambda row: row.occurred_at, reverse=True)
    for event in ordered:
        if getattr(event, "event_type", "") not in TOOL_OUTCOME_EVENT_TYPES:
            continue
        sub_id = getattr(event, "sub_agent_session_id", None)
        sub_role = role_map.get(str(sub_id)) if sub_id else None
        entry = _tool_entry_from_event(event, sub_role=sub_role)
        if entry is None:
            continue
        dedupe_key = (entry.tool_name, entry.event_type, str(entry.occurred_at or ""))
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        tool_rows.append(entry)
        if len(tool_rows) >= 8:
            break

    if len(tool_rows) < 8:
        for entry in _entries_from_sub_agents(session):
            dedupe_key = (entry.tool_name, entry.event_type, entry.sub_agent_role or "")
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            tool_rows.append(entry)
            if len(tool_rows) >= 8:
                break

    critic = _compose_critic(session, events)
    visible = (
        session_status.strip().lower() == "needs_input"
        or pending_approval
        or len(tool_rows) > 0
        or critic is not None
    )

    operator_action = _resolve_operator_action(
        session_status=session_status,
        pending_approval=pending_approval,
        approval_reason=approval_reason,
        critic=critic,
        tool_count=len(tool_rows),
    )

    return ToolOutcomePanelOut(
        enabled=True,
        session_id=session.id,
        session_status=session_status,
        visible=visible,
        pending_approval=pending_approval,
        approval_reason=approval_reason,
        tools=tool_rows,
        critic=critic,
        operator_action=operator_action,
    )


async def compose_tool_outcome_panel(
    session: AsyncSession,
    *,
    supervisor_session,
    event_limit: int = 500,
) -> ToolOutcomePanelOut:  # noqa: ANN001
    """Load events and compose AL2 tool outcome panel."""

    if not settings.tool_outcome_panel_enabled:
        return ToolOutcomePanelOut(
            enabled=False,
            session_id=supervisor_session.id,
            session_status=str(getattr(supervisor_session, "status", "")),
            visible=False,
        )

    from app.application.services.supervisor.session_service import list_session_events

    events = await list_session_events(
        session,
        session_id=supervisor_session.id,
        limit=event_limit,
        offset=0,
    )
    panel = derive_tool_outcome_panel(session=supervisor_session, events=events)
    _logger.info(
        "tool_outcome_panel.composed",
        agent_id="tool_outcome_panel",
        swarm_id=str(supervisor_session.id),
        task_id=str(supervisor_session.task_id) if supervisor_session.task_id else None,
        visible=panel.visible,
        tool_count=len(panel.tools),
    )
    return panel


__all__ = [
    "CriticOutcomeOut",
    "ToolOutcomeEntryOut",
    "ToolOutcomePanelOut",
    "compose_tool_outcome_panel",
    "derive_tool_outcome_panel",
]
