"""Unit tests for DG4 forager hit feedback loop."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.application.services.forager_hit_feedback_service import (
    compose_hit_feedback_snapshot,
    evaluate_hit_against_feedback_filters,
    submit_forager_hit_feedback,
)
from app.core import config
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.enums import AgentRole, AgentStatus
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem


def test_compose_hit_feedback_snapshot_enabled() -> None:
    snap = compose_hit_feedback_snapshot()
    assert snap.enabled is True
    assert "Thumbs" in snap.operator_hint


def test_evaluate_hit_blocks_keyword() -> None:
    skip, boost = evaluate_hit_against_feedback_filters(
        "spam listing with unwanted noise",
        {"feedback_loop": {"keywords_block": ["spam", "noise"]}},
    )
    assert skip is True
    assert boost == -0.15


def test_evaluate_hit_boosts_matching_keywords() -> None:
    skip, boost = evaluate_hit_against_feedback_filters(
        "senior python remote role in europe",
        {"feedback_loop": {"keywords_boost": ["python", "remote", "senior"]}},
    )
    assert skip is False
    assert boost == 0.15


def test_evaluate_hit_empty_config() -> None:
    skip, boost = evaluate_hit_against_feedback_filters("plain signal text", None)
    assert skip is False
    assert boost == 0.0


@pytest.mark.asyncio
async def test_submit_hit_feedback_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "forager_hit_feedback_enabled", False)
    session = AsyncMock()
    with pytest.raises(ValueError, match="forager_hit_feedback_disabled"):
        await submit_forager_hit_feedback(
            session,
            tenant_id=uuid.uuid4(),
            forager_id=uuid.uuid4(),
            knowledge_id=uuid.uuid4(),
            feedback="up",
        )


@pytest.mark.asyncio
async def test_submit_hit_feedback_up_updates_filter_and_confidence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "forager_hit_feedback_enabled", True)
    tenant_id = uuid.uuid4()
    forager_id = uuid.uuid4()
    knowledge_id = uuid.uuid4()

    forager = ForagerORM(
        tenant_id=tenant_id,
        name="EU Python Jobs",
        description="",
        source_type="rss",
        source_config={},
        filter_config={},
        prompt_template="",
        tools=[],
    )
    forager.id = forager_id

    knowledge = KnowledgeItem(
        tenant_id=tenant_id,
        source_url="https://jobs.example.com/1",
        source_type="forager:rss",
        content_text="# Senior Python Engineer\n\nRemote python role in EU.",
        confidence_score=0.5,
        topic_tags=[f"forager:{forager_id}"],
        decay_factor=1.0,
    )
    knowledge.id = knowledge_id

    agent = Agent(
        name="orchestrator",
        role=AgentRole.LEARNER,
        status=AgentStatus.IDLE,
    )
    agent.id = uuid.uuid4()

    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=[forager, knowledge, agent])
    session.add = AsyncMock()
    session.flush = AsyncMock()

    out = await submit_forager_hit_feedback(
        session,
        tenant_id=tenant_id,
        forager_id=forager_id,
        knowledge_id=knowledge_id,
        feedback="up",
    )

    assert out is not None
    assert out.ok is True
    assert out.feedback == "up"
    assert out.up_count == 1
    assert "python" in out.keywords_boost
    assert out.confidence_score > 0.5
    assert out.learning_log_written is True
    loop = dict(forager.filter_config or {}).get("feedback_loop", {})
    assert loop.get("up_count") == 1


@pytest.mark.asyncio
async def test_submit_hit_feedback_down_blocks_keywords(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "forager_hit_feedback_enabled", True)
    tenant_id = uuid.uuid4()
    forager_id = uuid.uuid4()
    knowledge_id = uuid.uuid4()

    forager = ForagerORM(
        tenant_id=tenant_id,
        name="Noise filter",
        description="",
        source_type="rss",
        source_config={},
        filter_config={},
        prompt_template="",
        tools=[],
    )
    forager.id = forager_id

    knowledge = KnowledgeItem(
        tenant_id=tenant_id,
        source_url=None,
        source_type="forager:rss",
        content_text="# Spam listing noise\n\nLow quality spam content.",
        confidence_score=0.6,
        topic_tags=[f"forager:{forager_id}"],
        decay_factor=1.0,
    )
    knowledge.id = knowledge_id

    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=[forager, knowledge, None])
    scalars_result = AsyncMock()
    scalars_result.all = lambda: []
    session.scalars = AsyncMock(return_value=scalars_result)
    session.add = AsyncMock()
    session.flush = AsyncMock()

    out = await submit_forager_hit_feedback(
        session,
        tenant_id=tenant_id,
        forager_id=forager_id,
        knowledge_id=knowledge_id,
        feedback="down",
    )

    assert out is not None
    assert out.down_count == 1
    assert "spam" in out.keywords_block
    assert out.confidence_score < 0.6
    assert out.learning_log_written is False
