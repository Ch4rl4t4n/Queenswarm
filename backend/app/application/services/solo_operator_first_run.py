"""Solo operator first-run wizard — LLM keys → project brief → first session (OW5)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.llm_runtime_credentials import (
    provider_effective_anthropic,
    provider_effective_grok,
    provider_effective_openai,
)
from app.core.config import settings
from app.domain.memory.curated import CuratedFileKind
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

FirstRunStepId = Literal["llm_keys", "project_brief", "first_session"]

STARTER_PROJECT_BRIEF = """=== BEHAVIORAL INSTRUCTIONS ===

PROJECT: My first Queenswarm project

Goal: Run a verified discovery session — simulate-first only.

Deliverables:
- Structured analysis report (max 1500 words)
- Critic APPROVE before final output

Language: English
Simulate-first: yes — no live writes without approval
"""

_BRIEF_MIN_CHARS = 120


class FirstRunStepOut(BaseModel):
    """One checklist step in the solo first-run wizard."""

    model_config = ConfigDict(extra="ignore")

    id: FirstRunStepId
    label: str
    detail: str
    done: bool
    href: str
    link_label: str


class SoloFirstRunCapabilityOut(BaseModel):
    """Hero copy for first-run capability story (Track Q UX3)."""

    model_config = ConfigDict(extra="ignore")

    headline: str
    subhead: str
    bullets: list[str] = Field(default_factory=list)


CAPABILITY_STORY = SoloFirstRunCapabilityOut(
    headline="Your verified agent operating system",
    subhead="Queenswarm runs supervisor missions with simulate-first verify — not raw LLM dumps.",
    bullets=[
        "One Process Rail: Setup → Plan → Work → Verify → Learn → Done",
        "Mission Kanban tracks every deliverable from queue to export",
        "Brain Pack + curated memory stay human-editable in Knowledge",
    ],
)


class SoloFirstRunOut(BaseModel):
    """First-run wizard snapshot for solo operators."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    complete: bool
    progress_pct: int = Field(ge=0, le=100)
    generated_at: datetime
    steps: list[FirstRunStepOut] = Field(default_factory=list)
    capability: SoloFirstRunCapabilityOut = Field(default_factory=lambda: CAPABILITY_STORY.model_copy())


def _llm_keys_configured() -> bool:
    return bool(
        (provider_effective_grok() or "").strip()
        or (provider_effective_anthropic() or "").strip()
        or (provider_effective_openai() or "").strip(),
    )


def _brief_is_ready(content: str | None) -> bool:
    text = (content or "").strip()
    if len(text) < _BRIEF_MIN_CHARS:
        return False
    upper = text.upper()
    return "PROJECT:" in upper or "=== BEHAVIORAL" in upper


async def _session_count(db: AsyncSession, *, tenant_id: uuid.UUID) -> int:
    return int(
        await db.scalar(
            select(func.count())
            .select_from(SupervisorSession)
            .where(SupervisorSession.tenant_id == tenant_id),
        )
        or 0,
    )


async def compose_solo_first_run(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> SoloFirstRunOut:
    """Build first-run checklist for solo operator onboarding."""

    _ = dashboard_user_id
    if not settings.solo_mode_enabled and not settings.operator_loop_enabled:
        return SoloFirstRunOut(
            enabled=False,
            complete=True,
            progress_pct=100,
            generated_at=datetime.now(tz=UTC),
            steps=[],
        )

    svc = CuratedMemoryService(db=db)
    instructions = await svc.get(tenant_id, CuratedFileKind.INSTRUCTIONS)
    brief_ready = _brief_is_ready(instructions.content_md if instructions else None)
    llm_ready = _llm_keys_configured()
    sessions = await _session_count(db, tenant_id=tenant_id)
    session_ready = sessions > 0

    steps: list[FirstRunStepOut] = [
        FirstRunStepOut(
            id="llm_keys",
            label="LLM keys",
            detail="Add at least one provider (Grok recommended) and run Test. Optional: Tavily search in Settings → API keys.",
            done=llm_ready,
            href="/settings/llm-keys",
            link_label="Open LLM keys",
        ),
        FirstRunStepOut(
            id="project_brief",
            label="Project brief",
            detail="Write a PROJECT block in Curated memory → Instructions (goal, deliverables, simulate-first).",
            done=brief_ready,
            href="/knowledge#memory",
            link_label="Open Curated memory",
        ),
        FirstRunStepOut(
            id="first_session",
            label="First supervisor session",
            detail="Create a session with a structured goal — use a Goal template or write your own.",
            done=session_ready,
            href="/agents?preset=web-redesign-discovery#sessions",
            link_label="Open session composer",
        ),
    ]

    done_count = sum(1 for row in steps if row.done)
    progress = round((done_count / len(steps)) * 100) if steps else 100
    complete = done_count == len(steps)

    return SoloFirstRunOut(
        enabled=True,
        complete=complete,
        progress_pct=progress,
        generated_at=datetime.now(tz=UTC),
        steps=steps,
    )


async def apply_starter_project_brief(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> dict[str, object]:
    """Seed Instructions with a minimal PROJECT brief when empty or too short."""

    svc = CuratedMemoryService(db=db)
    existing = await svc.get(tenant_id, CuratedFileKind.INSTRUCTIONS)
    current = (existing.content_md if existing else "") or ""
    if _brief_is_ready(current):
        return {"ok": True, "applied": False, "reason": "brief_already_ready"}

    merged = current.strip()
    if merged:
        merged = f"{merged.rstrip()}\n\n{STARTER_PROJECT_BRIEF.strip()}\n"
    else:
        merged = f"{STARTER_PROJECT_BRIEF.strip()}\n"

    await svc.upsert(
        tenant_id,
        CuratedFileKind.INSTRUCTIONS,
        merged,
        dashboard_user_id,
    )
    await db.commit()
    return {"ok": True, "applied": True}


__all__ = [
    "CAPABILITY_STORY",
    "FirstRunStepOut",
    "SoloFirstRunCapabilityOut",
    "SoloFirstRunOut",
    "STARTER_PROJECT_BRIEF",
    "apply_starter_project_brief",
    "compose_solo_first_run",
]
