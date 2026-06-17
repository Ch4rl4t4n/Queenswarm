"""Unit tests for SIG3 Capabilities Atlas highlight diff."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.capabilities_atlas_highlight_service import (
    CapabilitiesAtlasHighlightAckIn,
    acknowledge_capabilities_atlas_highlights,
    compose_capabilities_atlas_highlights,
    match_signals_to_highlights,
)


def _row(*, text: str, tags: list[str]) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.source_type = "youtube"
    row.source_url = "https://youtube.com/watch?v=test"
    row.content_text = text
    row.topic_tags = tags
    row.scraped_at = datetime.now(tz=UTC)
    row.confidence_score = 0.8
    return row


def test_match_signals_memory_theme() -> None:
    highlights = match_signals_to_highlights(
        [_row(text="Hermes memory beats MemSearch recall", tags=["social-intel"])],
    )
    ids = {row.capability_id for row in highlights}
    assert "hivemind" in ids


def test_match_signals_trading_journal_theme() -> None:
    highlights = match_signals_to_highlights(
        [_row(text="Obsidian trading journal studio pre-trade recall", tags=["hivemind-candidate"])],
    )
    ids = {row.capability_id for row in highlights}
    assert "trading-cockpit-live" in ids


@pytest.mark.asyncio
async def test_compose_highlights_unseen_count(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "capabilities_atlas_highlight_enabled", True)

    tenant_id = uuid.uuid4()
    tenant = MagicMock(operator_settings={})
    session = AsyncMock()
    signal = _row(text="Agent loop closed loop rubric", tags=["social-intel"])
    monkeypatch.setattr(
        "app.application.services.capabilities_atlas_highlight_service._load_synthesis_signals",
        AsyncMock(return_value=[signal]),
    )

    snap = await compose_capabilities_atlas_highlights(
        session,
        tenant_id=tenant_id,
        tenant=tenant,
    )
    assert snap.enabled is True
    assert snap.signal_count == 1
    assert snap.highlight_count >= 1
    assert snap.unseen_count >= 1


@pytest.mark.asyncio
async def test_acknowledge_highlights_persists_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.id = tenant_id
    tenant.operator_settings = {}
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.flush = AsyncMock()

    monkeypatch.setattr(
        "app.application.services.capabilities_atlas_highlight_service.compose_capabilities_atlas_highlights",
        AsyncMock(
            return_value=MagicMock(
                highlights=[
                    MagicMock(kind="live", capability_id="hivemind"),
                ],
            ),
        ),
    )

    result = await acknowledge_capabilities_atlas_highlights(
        session,
        tenant_id=tenant_id,
        body=CapabilitiesAtlasHighlightAckIn(ack_all=True),
    )
    assert result.acked_count == 1
    assert "live:hivemind" in tenant.operator_settings["capabilities_atlas_highlights"]["acked_keys"]
