"""OBS2 — Knowledge elicitation: surface Brain Pack gaps for operator approval (no LLM)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.curated_memory_service import CuratedFileKind, CuratedMemoryService
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

ElicitationKind = Literal["mission", "ideal_state", "soul", "instructions", "skills_hierarchy"]


class KnowledgeElicitationPromptOut(BaseModel):
    """One question for the operator to answer."""

    model_config = ConfigDict(extra="ignore")

    id: str
    kind: ElicitationKind
    title: str
    question: str
    empty: bool = True
    current_preview: str = ""


class KnowledgeElicitationSnapshotOut(BaseModel):
    """Brain Pack gap prompts."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    prompts: list[KnowledgeElicitationPromptOut] = Field(default_factory=list)
    filled_count: int = 0
    gap_count: int = 0


class KnowledgeElicitationAnswerIn(BaseModel):
    """Operator answer to persist into curated memory."""

    model_config = ConfigDict(extra="forbid")

    kind: ElicitationKind
    answer: str = Field(min_length=8, max_length=12_000)


_KIND_MAP: dict[ElicitationKind, CuratedFileKind] = {
    "mission": CuratedFileKind.MISSION,
    "ideal_state": CuratedFileKind.IDEAL_STATE,
    "soul": CuratedFileKind.SOUL,
    "instructions": CuratedFileKind.INSTRUCTIONS,
    "skills_hierarchy": CuratedFileKind.SKILLS_HIERARCHY,
}

_QUESTIONS: dict[ElicitationKind, str] = {
    "mission": "What is your 90-day mission in one paragraph?",
    "ideal_state": "What does success look like when the harness is working perfectly?",
    "soul": "How should agents communicate with you (tone, language, boundaries)?",
    "instructions": "What behavioral rules must every agent follow?",
    "skills_hierarchy": "Which skills or workflows are non-negotiable for your projects?",
}


async def compose_knowledge_elicitation_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> KnowledgeElicitationSnapshotOut:
    """Detect empty Brain Pack files and emit elicitation prompts."""

    if not settings.knowledge_elicitation_enabled:
        return KnowledgeElicitationSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    curated = CuratedMemoryService(db=session)
    bundle = await curated.get_bundle(tenant_id)
    prompts: list[KnowledgeElicitationPromptOut] = []
    filled = 0
    for kind in _QUESTIONS:
        file_kind = _KIND_MAP[kind]
        body = str(bundle.get(file_kind) or "").strip()
        is_empty = len(body) < 40
        if not is_empty:
            filled += 1
        prompts.append(
            KnowledgeElicitationPromptOut(
                id=f"elicit_{kind}",
                kind=kind,
                title=kind.replace("_", " ").title(),
                question=_QUESTIONS[kind],
                empty=is_empty,
                current_preview=body[:240],
            ),
        )

    return KnowledgeElicitationSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        prompts=prompts,
        filled_count=filled,
        gap_count=sum(1 for row in prompts if row.empty),
    )


async def apply_knowledge_elicitation_answer(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID | None,
    body: KnowledgeElicitationAnswerIn,
) -> KnowledgeElicitationSnapshotOut:
    """Persist operator answer into curated memory (caller commits)."""

    curated = CuratedMemoryService(db=session)
    file_kind = _KIND_MAP[body.kind]
    await curated.upsert(tenant_id, file_kind, body.answer.strip(), dashboard_user_id)
    _logger.info(
        "knowledge_elicitation.answer_saved",
        agent_id="knowledge_elicitation",
        swarm_id=str(tenant_id),
        kind=body.kind,
    )
    return await compose_knowledge_elicitation_snapshot(session, tenant_id=tenant_id)


__all__ = [
    "KnowledgeElicitationAnswerIn",
    "KnowledgeElicitationSnapshotOut",
    "apply_knowledge_elicitation_answer",
    "compose_knowledge_elicitation_snapshot",
]
