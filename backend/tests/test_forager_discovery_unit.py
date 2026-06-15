"""Unit tests for DG6 forager discovery service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.forager_discovery_service import (
    ForagerDiscoveryUrlHit,
    classify_discovery_url,
    compose_forager_discovery_wizard_snapshot,
    search_forager_discovery_urls,
    submit_forager_discovery_bind,
)
from app.core import config


def test_classify_discovery_url_youtube() -> None:
    assert classify_discovery_url("https://www.youtube.com/@channel") == "youtube"


def test_classify_discovery_url_rss() -> None:
    assert classify_discovery_url("https://example.com/jobs/feed.xml") == "rss"


def test_classify_discovery_url_twitter() -> None:
    assert classify_discovery_url("https://x.com/somehandle") == "twitter"


@pytest.mark.asyncio
async def test_compose_forager_discovery_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "forager_discovery_enabled", False)
    session = AsyncMock()
    snap = await compose_forager_discovery_wizard_snapshot(session)
    assert snap.enabled is False


@pytest.mark.asyncio
async def test_search_forager_discovery_without_keys() -> None:
    session = AsyncMock()
    with patch(
        "app.application.services.forager_discovery_service.resolve_research_keys",
        AsyncMock(return_value={}),
    ):
        out = await search_forager_discovery_urls(session, query="python remote jobs EU")
    assert out.keys_configured is False
    assert "Tavily or Serper" in out.operator_hint


@pytest.mark.asyncio
async def test_search_forager_discovery_returns_serper_hits() -> None:
    session = AsyncMock()
    hits = [
        ForagerDiscoveryUrlHit(
            url="https://jobs.example.com/feed.xml",
            title="Jobs feed",
            snippet="Open roles",
            provider="serper",
            url_kind="rss",
        ),
    ]
    with patch(
        "app.application.services.forager_discovery_service.resolve_research_keys",
        AsyncMock(return_value={"serper": "test-key"}),
    ), patch(
        "app.application.services.forager_discovery_service._search_serper_hits",
        AsyncMock(return_value=hits),
    ), patch(
        "app.application.services.forager_discovery_service._search_tavily_hits",
        AsyncMock(return_value=[]),
    ):
        out = await search_forager_discovery_urls(session, query="python jobs europe", limit=5)
    assert len(out.hits) == 1
    assert out.hits[0].url_kind == "rss"
    assert "serper" in out.providers_used


@pytest.mark.asyncio
async def test_submit_forager_discovery_bind_existing_forager(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "forager_discovery_enabled", True)
    session = AsyncMock()
    forager_id = uuid.uuid4()
    with patch(
        "app.application.services.forager_discovery_service.bind_discovery_urls_to_forager",
        AsyncMock(return_value=(2, 0)),
    ), patch(
        "app.application.services.forager_discovery_service.ForagerService",
    ) as service_cls:
        row = MagicMock()
        row.name = "RSS Jobs"
        service_cls.return_value.get_by_id = AsyncMock(return_value=row)
        service_cls.return_value.trigger_manual_run = AsyncMock(return_value={})
        from app.application.services.forager_discovery_service import ForagerDiscoveryBindIn

        out = await submit_forager_discovery_bind(
            session,
            tenant_id=uuid.uuid4(),
            body=ForagerDiscoveryBindIn(
                forager_id=forager_id,
                urls=["https://jobs.example.com/feed.xml", "https://news.example.com/rss"],
                trigger_first_run=False,
            ),
            created_by_subject="test",
        )
    assert out.ok is True
    assert out.forager_id == str(forager_id)
    assert out.bound_count == 2
    assert out.created is False
