"""DG4 — Operator thumbs on forager hits → filter_config tuning + LearningLog."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.forager_harvest_report import _finding_title
from app.application.services.hive_tier import FIXED_ORCHESTRATOR_AGENT_NAME
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem, LearningLog

_logger = get_logger(__name__)

HitFeedback = Literal["up", "down"]
_TOKEN_RE = re.compile(r"[a-z0-9]{4,}", re.IGNORECASE)
_MAX_KEYWORDS = 24
_MAX_RECENT = 20


class ForagerHitFeedbackSnapshotOut(BaseModel):
    """DG4 capabilities snapshot."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    operator_hint: str


class ForagerHitFeedbackOut(BaseModel):
    """Result of one thumbs feedback action."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    forager_id: str
    knowledge_id: str
    feedback: HitFeedback
    up_count: int
    down_count: int
    keywords_boost: list[str]
    keywords_block: list[str]
    confidence_score: float
    learning_log_written: bool
    message: str


def compose_hit_feedback_snapshot() -> ForagerHitFeedbackSnapshotOut:
    """Static UI snapshot."""

    return ForagerHitFeedbackSnapshotOut(
        enabled=bool(settings.forager_hit_feedback_enabled),
        operator_hint="Thumbs on harvest hits tune keyword boost/block filters for future ingests.",
    )


def _default_feedback_loop() -> dict[str, Any]:
    return {
        "up_count": 0,
        "down_count": 0,
        "keywords_boost": [],
        "keywords_block": [],
        "recent": [],
    }


def _feedback_loop_from_config(filter_config: dict[str, Any]) -> dict[str, Any]:
    raw = filter_config.get("feedback_loop")
    if not isinstance(raw, dict):
        return _default_feedback_loop()
    loop = _default_feedback_loop()
    loop["up_count"] = int(raw.get("up_count") or 0)
    loop["down_count"] = int(raw.get("down_count") or 0)
    loop["keywords_boost"] = [
        str(item).strip().lower()
        for item in list(raw.get("keywords_boost") or [])
        if str(item).strip()
    ][: _MAX_KEYWORDS]
    loop["keywords_block"] = [
        str(item).strip().lower()
        for item in list(raw.get("keywords_block") or [])
        if str(item).strip()
    ][: _MAX_KEYWORDS]
    recent = list(raw.get("recent") or [])
    loop["recent"] = [item for item in recent if isinstance(item, dict)][:_MAX_RECENT]
    return loop


def _extract_keyword_tokens(*parts: str) -> list[str]:
    tokens: list[str] = []
    for part in parts:
        for token in _TOKEN_RE.findall(part):
            lowered = token.lower()
            if len(lowered) < 4:
                continue
            if lowered in tokens:
                continue
            tokens.append(lowered)
    return tokens[:6]


def evaluate_hit_against_feedback_filters(
    text: str,
    filter_config: dict[str, Any] | None,
) -> tuple[bool, float]:
    """Return whether ingest should skip row and optional confidence boost."""

    loop = _feedback_loop_from_config(dict(filter_config or {}))
    lowered = text.lower()
    for keyword in loop["keywords_block"]:
        if keyword and keyword in lowered:
            return True, -0.15
    boost = 0.0
    for keyword in loop["keywords_boost"]:
        if keyword and keyword in lowered:
            boost += 0.05
    return False, min(boost, 0.15)


async def _resolve_learning_agent(session: AsyncSession, *, tenant_id: uuid.UUID) -> Agent | None:
    orch = await session.scalar(
        select(Agent).where(Agent.name == FIXED_ORCHESTRATOR_AGENT_NAME).limit(1),
    )
    if orch is not None:
        return orch
    rows = list((await session.scalars(select(Agent).order_by(Agent.created_at.asc()).limit(40))).all())
    _ = tenant_id
    return rows[0] if rows else None


async def submit_forager_hit_feedback(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    knowledge_id: uuid.UUID,
    feedback: HitFeedback,
) -> ForagerHitFeedbackOut | None:
    """Apply operator thumbs → knowledge confidence, filter_config, LearningLog."""

    if not settings.forager_hit_feedback_enabled:
        raise ValueError("forager_hit_feedback_disabled")

    forager = await session.scalar(
        select(ForagerORM).where(
            ForagerORM.id == forager_id,
            ForagerORM.tenant_id == tenant_id,
        ),
    )
    if forager is None:
        return None

    tag = f"forager:{forager.id}"
    knowledge = await session.scalar(
        select(KnowledgeItem).where(
            KnowledgeItem.id == knowledge_id,
            KnowledgeItem.tenant_id == tenant_id,
            KnowledgeItem.topic_tags.contains([tag]),
        ),
    )
    if knowledge is None:
        raise ValueError("knowledge_not_found_for_forager")

    title = _finding_title(str(knowledge.content_text or ""), knowledge.source_url)
    tokens = _extract_keyword_tokens(title, str(knowledge.content_text or "")[:500])

    filter_cfg = dict(forager.filter_config or {})
    loop = _feedback_loop_from_config(filter_cfg)
    if feedback == "up":
        loop["up_count"] = int(loop["up_count"]) + 1
        for token in tokens[:3]:
            if token not in loop["keywords_boost"]:
                loop["keywords_boost"].append(token)
        loop["keywords_boost"] = loop["keywords_boost"][:_MAX_KEYWORDS]
        knowledge.confidence_score = min(1.0, float(knowledge.confidence_score or 0.5) + 0.08)
        feedback_tag = "forager-hit-up"
    else:
        loop["down_count"] = int(loop["down_count"]) + 1
        for token in tokens[:3]:
            if token not in loop["keywords_block"]:
                loop["keywords_block"].append(token)
        loop["keywords_block"] = loop["keywords_block"][:_MAX_KEYWORDS]
        knowledge.confidence_score = max(0.05, float(knowledge.confidence_score or 0.5) - 0.12)
        feedback_tag = "forager-hit-down"

    item_tags = list(knowledge.topic_tags or [])
    if feedback_tag not in item_tags:
        item_tags.append(feedback_tag)
    knowledge.topic_tags = item_tags[:32]

    recent = list(loop.get("recent") or [])
    recent.insert(
        0,
        {
            "knowledge_id": str(knowledge.id),
            "feedback": feedback,
            "title": title[:240],
            "at": datetime.now(tz=UTC).isoformat(),
        },
    )
    loop["recent"] = recent[:_MAX_RECENT]
    filter_cfg["feedback_loop"] = loop
    forager.filter_config = filter_cfg

    learning_written = False
    agent = await _resolve_learning_agent(session, tenant_id=tenant_id)
    if agent is not None:
        session.add(
            LearningLog(
                tenant_id=tenant_id,
                agent_id=agent.id,
                task_id=None,
                insight_text=(
                    f"DG4 forager hit {feedback}: {title[:200]} · "
                    f"boost={loop['keywords_boost'][:5]} block={loop['keywords_block'][:5]}"
                )[:20_000],
                applied_at=datetime.now(tz=UTC),
                pollen_earned=0.05 if feedback == "up" else 0.0,
            ),
        )
        learning_written = True

    await session.flush()

    _logger.info(
        "forager.hit_feedback",
        agent_id="forager_hub",
        swarm_id=str(tenant_id),
        forager_id=str(forager.id),
        knowledge_id=str(knowledge.id),
        feedback=feedback,
    )

    return ForagerHitFeedbackOut(
        ok=True,
        forager_id=str(forager.id),
        knowledge_id=str(knowledge.id),
        feedback=feedback,
        up_count=int(loop["up_count"]),
        down_count=int(loop["down_count"]),
        keywords_boost=list(loop["keywords_boost"]),
        keywords_block=list(loop["keywords_block"]),
        confidence_score=float(knowledge.confidence_score or 0.0),
        learning_log_written=learning_written,
        message=(
            f"Feedback recorded — future ingests will "
            f"{'boost' if feedback == 'up' else 'block'} similar keywords."
        ),
    )


__all__ = [
    "compose_hit_feedback_snapshot",
    "evaluate_hit_against_feedback_filters",
    "submit_forager_hit_feedback",
    "ForagerHitFeedbackOut",
    "ForagerHitFeedbackSnapshotOut",
]
