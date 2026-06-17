"""Unit tests for POS-H3 research project batch brief."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.research_project_service import compose_research_project_brief


@pytest.mark.asyncio
async def test_research_project_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.research_project_service.settings") as mock_settings:
        mock_settings.research_bee_enabled = True
        mock_settings.research_project_enabled = False
        out = await compose_research_project_brief(
            session,
            tenant_id=uuid.uuid4(),
            source_urls=["https://example.com/a"],
        )
    assert out.enabled is False


@pytest.mark.asyncio
async def test_research_project_requires_urls() -> None:
    session = AsyncMock()
    with patch("app.application.services.research_project_service.settings") as mock_settings:
        mock_settings.research_bee_enabled = True
        mock_settings.research_project_enabled = True
        with pytest.raises(ValueError, match="At least one"):
            await compose_research_project_brief(
                session,
                tenant_id=uuid.uuid4(),
                source_urls=[],
            )


@pytest.mark.asyncio
async def test_research_project_merges_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    session.add = lambda row: None  # noqa: ARG005
    session.flush = AsyncMock()

    async def fake_fetch(url: str, *, max_chars: int) -> str:  # noqa: ARG001
        return f"Title from {url}. First sentence about bees. Second sentence about hive mind."

    monkeypatch.setattr(
        "app.application.services.research_project_service.fetch_url_text",
        fake_fetch,
    )
    with patch("app.application.services.research_project_service.settings") as mock_settings:
        mock_settings.research_bee_enabled = True
        mock_settings.research_project_enabled = True
        mock_settings.research_bee_max_chars = 8000

        out = await compose_research_project_brief(
            session,
            tenant_id=uuid.uuid4(),
            source_urls=["https://example.com/a", "https://example.com/b"],
            project_title="Bee research",
        )

    assert out.enabled is True
    assert out.source_count == 2
    assert out.project_title == "Bee research"
    assert len(out.key_points) >= 1
