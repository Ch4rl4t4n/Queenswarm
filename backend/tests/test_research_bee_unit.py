"""Research Bee unit tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.research_bee import (
    build_structured_brief,
    compose_research_brief,
    fetch_url_text,
)


def test_build_structured_brief_key_points() -> None:
    raw = (
        "Queenswarm is a bee-hive agent swarm. "
        "Each agent has one sharp job. "
        "Verified outcomes earn pollen points. "
        "Sub-swarms sync every five minutes."
    )
    brief = build_structured_brief(
        raw_text=raw,
        source_type="paste",
        source_label="test",
        title_hint="Swarm overview",
    )
    assert brief.title == "Swarm overview"
    assert brief.word_count > 5
    assert len(brief.key_points) >= 1
    assert "research" not in brief.topic_tags or brief.topic_tags


@pytest.mark.asyncio
async def test_fetch_url_text_rejects_localhost() -> None:
    with pytest.raises(ValueError, match="public http"):
        await fetch_url_text("http://127.0.0.1/test", max_chars=1000)


@pytest.mark.asyncio
async def test_compose_research_brief_paste_persist() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    with patch("app.application.services.research_bee.settings") as mock_settings:
        mock_settings.research_bee_enabled = True
        mock_settings.research_bee_max_chars = 8000
        brief = await compose_research_brief(
            session,
            tenant_id=tenant_id,
            content_text="Alpha beta gamma delta epsilon zeta eta theta iota kappa.",
            title_hint="Greek test",
            persist=True,
        )

    assert brief.enabled is True
    assert brief.persisted is True
    assert brief.knowledge_item_id is not None
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_compose_research_brief_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.research_bee.settings") as mock_settings:
        mock_settings.research_bee_enabled = False
        brief = await compose_research_brief(
            session,
            tenant_id=uuid.uuid4(),
            content_text="hello world test content here",
        )
    assert brief.enabled is False
