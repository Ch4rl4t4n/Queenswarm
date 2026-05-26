"""ICM-inspired operator tools — Link Drop, Dialogue Extract, keyword hints (compose-only, no LLM)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.research_bee import ResearchBriefOut, compose_research_brief
from app.application.services.slack_harness_trainer import (
    format_slack_feedback_block,
    merge_instructions_append,
)
from app.application.services.curated_memory_service import CuratedMemoryService
from app.core.config import settings
from app.domain.memory.curated import CuratedFileKind
from app.infrastructure.persistence.models.supervisor_session import (
    SubAgentSession,
    SupervisorSession,
)

logger = structlog.get_logger(__name__)

ApplyTarget = Literal["preview", "harness", "knowledge"]


class DialogueExtractItemOut(BaseModel):
    """One extracted row from operator/user dialogue."""

    model_config = ConfigDict(extra="ignore")

    kind: Literal["goal", "constraint", "decision", "next_step", "question"]
    speaker: Literal["operator", "model", "unknown"] = "unknown"
    text: str


class DialogueExtractOut(BaseModel):
    """Structured dialogue extraction — ICM layer 1→3 bridge."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    char_count: int = 0
    goals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    items: list[DialogueExtractItemOut] = Field(default_factory=list)
    summary_md: str = ""
    task_prefill: str = ""


class KeywordSuggestionOut(BaseModel):
    """Human-approved action hint from transcript keywords."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    detail: str
    priority: Literal["high", "medium", "low"]
    href: str | None = None
    action: str | None = None


class KeywordScanOut(BaseModel):
    """Keyword scan over pasted transcript — suggest only, never auto-fire."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    matches: list[KeywordSuggestionOut] = Field(default_factory=list)


class QuickAutomationPresetOut(BaseModel):
    """One-tap preset mapped to existing CP actions or ICM tools."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    detail: str
    kind: Literal["action", "link_drop", "dialogue_extract", "href"]
    action: str | None = None
    href: str | None = None


class IcmToolsSnapshotOut(BaseModel):
    """Cockpit block for ICM / Lindy-mode tools."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    link_drop_enabled: bool = False
    dialogue_extract_enabled: bool = False
    keyword_scan_enabled: bool = False
    quick_automations: list[QuickAutomationPresetOut] = Field(default_factory=list)
    min_dialogue_chars: int = 40
    min_url_chars: int = 8


_GOAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*(?:can you|could you|please|i want|we need|goal:|objective:)\b", re.I),
    re.compile(r"\b(?:need to|want to|trying to|aim to)\b", re.I),
)
_CONSTRAINT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:must|should not|don't|do not|without|never|only|max|min|by \w+day)\b", re.I),
    re.compile(r"\b(?:constraint|limit|deadline|asap|urgent)\b", re.I),
)
_DECISION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*(?:let's|we'll|decided|going with|use \w+|approved)\b", re.I),
    re.compile(r"\b(?:decision:|agreed|confirmed|final)\b", re.I),
)
_NEXT_STEP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:next step|action item|follow[- ]?up|todo|to-do|will do)\b", re.I),
    re.compile(r"^\s*[-*]\s+\S", re.I),
)

_KEYWORD_RULES: tuple[tuple[re.Pattern[str], str, str, str, Literal["high", "medium", "low"], str | None, str | None], ...] = (
    (
        re.compile(r"\b(?:deadline|due|asap|urgent|by (?:mon|tue|wed|thu|fri|tomorrow|eod))\b", re.I),
        "deadline",
        "Deadline mentioned",
        "Create a tracked task with the extracted goal.",
        "high",
        "/tasks/new",
        None,
    ),
    (
        re.compile(r"\b(?:bug|broken|incident|outage|error|500|crash)\b", re.I),
        "incident",
        "Possible incident",
        "Open a Supervisor session to investigate with simulate-first guardrails.",
        "high",
        "/agents",
        None,
    ),
    (
        re.compile(r"\b(?:publish|post|tweet|linkedin|social)\b", re.I),
        "publish",
        "Publish intent",
        "Review publish queue before any live post.",
        "medium",
        "/integrations?tab=studio#publish-queue",
        None,
    ),
    (
        re.compile(r"\b(?:meeting|call|sync|standup|retro)\b", re.I),
        "meeting",
        "Meeting context",
        "Run Dialogue Extract on the transcript for follow-up actions.",
        "medium",
        None,
        "dialogue_extract_hint",
    ),
    (
        re.compile(r"\b(?:research|article|paper|read this|youtube|http)\b", re.I),
        "research",
        "Research / URL",
        "Use Link Drop for a structured brief (read-only fetch).",
        "low",
        "/cockpit#link-drop",
        None,
    ),
)


def _icm_enabled() -> bool:
    return bool(settings.operator_control_plane_enabled and settings.operator_icm_tools_enabled)


def compose_icm_tools_snapshot() -> IcmToolsSnapshotOut:
    """Static ICM tools catalog for cockpit — no I/O."""

    enabled = _icm_enabled()
    presets = [
        QuickAutomationPresetOut(
            id="morning_check",
            label="Morning check",
            detail="Run solo trio cycle + refresh Operator Loop.",
            kind="action",
            action="start_day",
        ),
        QuickAutomationPresetOut(
            id="summarize_link",
            label="Summarize link",
            detail="Paste a URL in Link Drop for a structured brief.",
            kind="link_drop",
        ),
        QuickAutomationPresetOut(
            id="meeting_follow_up",
            label="Meeting follow-up",
            detail="Paste transcript → goals, constraints, next steps.",
            kind="dialogue_extract",
        ),
        QuickAutomationPresetOut(
            id="research_url",
            label="Research URL",
            detail="Read-only fetch → HiveMind brief (on approve).",
            kind="link_drop",
        ),
        QuickAutomationPresetOut(
            id="operator_loop",
            label="Refresh command center",
            detail="Open harness Operator Loop for overnight + publish status.",
            kind="href",
            href="/settings/harness",
        ),
    ]
    return IcmToolsSnapshotOut(
        enabled=enabled,
        link_drop_enabled=enabled and settings.research_bee_enabled,
        dialogue_extract_enabled=enabled,
        keyword_scan_enabled=enabled,
        quick_automations=presets if enabled else [],
    )


def _guess_speaker(line: str) -> Literal["operator", "model", "unknown"]:
    lowered = line.lower()
    if lowered.startswith(("user:", "operator:", "human:", "me:")):
        return "operator"
    if lowered.startswith(("assistant:", "model:", "ai:", "claude:", "gpt:")):
        return "model"
    return "unknown"


def _strip_speaker_prefix(line: str) -> str:
    return re.sub(r"^\s*(?:user|operator|human|assistant|model|ai|claude|gpt)\s*:\s*", "", line, flags=re.I).strip()


def extract_dialogue_structure(text: str) -> DialogueExtractOut:
    """Heuristic dialogue → goals/constraints/decisions (no LLM)."""

    now = datetime.now(tz=UTC)
    if not _icm_enabled():
        return DialogueExtractOut(enabled=False, generated_at=now)

    raw = text.strip()
    if len(raw) < 40:
        return DialogueExtractOut(
            enabled=True,
            generated_at=now,
            char_count=len(raw),
            summary_md="Provide at least 40 characters of dialogue.",
        )

    lines = [_strip_speaker_prefix(line) for line in raw.splitlines() if line.strip()]
    if not lines:
        lines = [raw]

    goals: list[str] = []
    constraints: list[str] = []
    decisions: list[str] = []
    next_steps: list[str] = []
    items: list[DialogueExtractItemOut] = []

    for line in lines[:120]:
        if len(line) < 8:
            continue
        speaker = _guess_speaker(line)
        snippet = line[:320]
        if any(p.search(line) for p in _GOAL_PATTERNS):
            goals.append(snippet)
            items.append(DialogueExtractItemOut(kind="goal", speaker=speaker, text=snippet))
        elif any(p.search(line) for p in _CONSTRAINT_PATTERNS):
            constraints.append(snippet)
            items.append(DialogueExtractItemOut(kind="constraint", speaker=speaker, text=snippet))
        elif any(p.search(line) for p in _DECISION_PATTERNS):
            decisions.append(snippet)
            items.append(DialogueExtractItemOut(kind="decision", speaker=speaker, text=snippet))
        elif any(p.search(line) for p in _NEXT_STEP_PATTERNS):
            next_steps.append(snippet)
            items.append(DialogueExtractItemOut(kind="next_step", speaker=speaker, text=snippet))
        elif line.endswith("?"):
            items.append(DialogueExtractItemOut(kind="question", speaker=speaker, text=snippet))

    if not goals and lines:
        goals.append(lines[0][:280])
        items.insert(0, DialogueExtractItemOut(kind="goal", speaker=_guess_speaker(lines[0]), text=lines[0][:280]))

    task_prefill = goals[0] if goals else raw[:400]

    def _bullet_lines(values: list[str]) -> list[str]:
        if values:
            return [f"- {value}" for value in values[:6]]
        return ["- _none detected_"]

    summary_lines = [
        "## Dialogue extract",
        "",
        "### Goals",
        *_bullet_lines(goals),
        "",
        "### Constraints",
        *_bullet_lines(constraints),
        "",
        "### Decisions",
        *_bullet_lines(decisions),
        "",
        "### Next steps",
        *_bullet_lines(next_steps),
    ]
    return DialogueExtractOut(
        enabled=True,
        generated_at=now,
        char_count=len(raw),
        goals=goals[:8],
        constraints=constraints[:8],
        decisions=decisions[:8],
        next_steps=next_steps[:8],
        items=items[:24],
        summary_md="\n".join(summary_lines),
        task_prefill=task_prefill[:500],
    )


def scan_transcript_keywords(text: str) -> KeywordScanOut:
    """Suggest operator actions from keywords — never auto-execute."""

    now = datetime.now(tz=UTC)
    if not _icm_enabled():
        return KeywordScanOut(enabled=False, generated_at=now)

    blob = text.strip()
    matches: list[KeywordSuggestionOut] = []
    seen: set[str] = set()
    for pattern, kid, label, detail, priority, href, action in _KEYWORD_RULES:
        if kid in seen:
            continue
        if pattern.search(blob):
            seen.add(kid)
            matches.append(
                KeywordSuggestionOut(
                    id=kid,
                    label=label,
                    detail=detail,
                    priority=priority,
                    href=href,
                    action=action,
                ),
            )
    return KeywordScanOut(enabled=True, generated_at=now, matches=matches[:8])


async def preview_link_drop(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    url: str,
) -> ResearchBriefOut:
    """Read-only URL → structured brief via Research Bee."""

    if not _icm_enabled():
        return ResearchBriefOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            source_type="disabled",
            source_label="",
            title="",
            summary="",
        )
    return await compose_research_brief(
        session,
        tenant_id=tenant_id,
        source_url=url.strip(),
        persist=False,
    )


async def apply_dialogue_extract(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    extraction: DialogueExtractOut,
    target: ApplyTarget,
    source_url: str | None = None,
) -> dict[str, Any]:
    """Apply extraction to harness memory or Knowledge — explicit operator approve only."""

    if target == "preview":
        return {"ok": True, "target": target}

    if target == "harness":
        service = CuratedMemoryService(db=session)
        current = await service.get(tenant_id, CuratedFileKind.INSTRUCTIONS)
        existing = current.content_md if current is not None else ""
        block = format_slack_feedback_block(
            feedback=extraction.summary_md[:3500],
            author="operator",
            source="dialogue_extract",
        )
        merged = merge_instructions_append(existing, block)
        out = await service.upsert(
            tenant_id=tenant_id,
            kind=CuratedFileKind.INSTRUCTIONS,
            content_md=merged,
            user_id=dashboard_user_id,
        )
        logger.info(
            "operator_icm_tools.harness_applied",
            agent_id="operator_icm_tools",
            swarm_id=str(tenant_id),
            task_id=str(out.version),
        )
        return {"ok": True, "target": target, "version": out.version, "char_count": out.char_count}

    if target == "knowledge":
        brief = await compose_research_brief(
            session,
            tenant_id=tenant_id,
            source_url=source_url,
            content_text=extraction.summary_md if not source_url else None,
            title_hint="Dialogue extract",
            persist=True,
        )
        return {
            "ok": True,
            "target": target,
            "knowledge_item_id": brief.knowledge_item_id,
            "title": brief.title,
        }

    return {"ok": False, "target": target, "message": "Unsupported target."}


async def build_session_recipe_draft(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
) -> dict[str, Any]:
    """Build recipe draft payload from a completed supervisor session."""

    row = await session.get(SupervisorSession, session_id)
    if row is None or row.tenant_id != tenant_id:
        msg = "Session not found."
        raise ValueError(msg)
    if row.status not in {"completed", "needs_input"}:
        msg = "Session must be completed or needs_input to save as recipe."
        raise ValueError(msg)

    sub_result = await session.execute(
        select(SubAgentSession)
        .where(SubAgentSession.supervisor_session_id == session_id)
        .order_by(SubAgentSession.spawn_order.asc()),
    )
    subs = list(sub_result.scalars().all())

    from app.application.services.supervisor.session_playbook import map_supervisor_role_to_agent_role

    steps: list[dict[str, Any]] = []
    for idx, sub in enumerate(subs[:7]):
        desc = (sub.last_output or sub.role or "Execute step").strip()
        if len(desc) < 8:
            desc = f"Run {sub.role} step for session goal."
        mapped = map_supervisor_role_to_agent_role(sub.role or "reporter")
        steps.append(
            {
                "step_order": idx + 1,
                "description": desc[:4000],
                "agent_role": mapped,
                "guardrails": {"simulate_first": True},
                "evaluation_criteria": {"verified_outcome": True},
            },
        )

    while len(steps) < 3:
        steps.append(
            {
                "step_order": len(steps) + 1,
                "description": f"Verify outcome for: {row.goal[:200]}",
                "agent_role": map_supervisor_role_to_agent_role("critic"),
                "guardrails": {"simulate_first": True},
                "evaluation_criteria": {"verified_outcome": True},
            },
        )

    name = f"Session template {str(session_id)[-8:]}"
    return {
        "name": name[:200],
        "description": f"Draft from supervisor session {session_id}",
        "topic_tags": ["session_template", "icm_tools"],
        "task_text": row.goal[:50_000],
        "steps": steps[:7],
        "mark_verified": False,
        "session_id": str(session_id),
        "session_status": row.status,
    }


__all__ = [
    "ApplyTarget",
    "DialogueExtractOut",
    "IcmToolsSnapshotOut",
    "KeywordScanOut",
    "QuickAutomationPresetOut",
    "apply_dialogue_extract",
    "build_session_recipe_draft",
    "compose_icm_tools_snapshot",
    "extract_dialogue_structure",
    "preview_link_drop",
    "scan_transcript_keywords",
]
