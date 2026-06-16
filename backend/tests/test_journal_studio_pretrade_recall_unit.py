"""Unit tests for Track O TJ5 pre-trade recall service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.journal_studio_pretrade_recall_service import (
    PreTradeMistakeOut,
    compose_pretrade_recall,
    render_pretrade_injection_block,
    should_inject_pretrade_recall,
)


def test_should_inject_pretrade_recall_for_trading_lane() -> None:
    with patch(
        "app.application.services.journal_studio_pretrade_recall_service.settings",
        MagicMock(journal_studio_enabled=True, journal_studio_pretrade_recall_enabled=True),
    ):
        assert should_inject_pretrade_recall(context_seed={"lane": "trading"}, goal="Review markets") is True
        assert should_inject_pretrade_recall(context_seed={}, goal="Polymarket live trade") is True
        assert should_inject_pretrade_recall(context_seed={}, goal="Write blog post") is False


def test_render_pretrade_injection_block_includes_mistakes() -> None:
    block = render_pretrade_injection_block(
        top_mistakes=[
            PreTradeMistakeOut(tag="fomo", count=2, latest_lesson="Wait for confirmation", last_seen_at=datetime.now(tz=UTC)),
        ],
        edge_reminders=["Edge tag «breakout» appeared 2× in last 30d"],
        thesis_title="BTC thesis",
        thesis_snippet="Kill criteria: invalidation below support.",
        wiki_snippets=["Journal · BTC: lesson text"],
        window_days=30,
    )
    assert "PRE-TRADE RECALL" in block
    assert "fomo" in block
    assert "Kill criteria" in block


@pytest.mark.asyncio
async def test_compose_pretrade_recall_ranks_mistakes(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()

    now = datetime.now(tz=UTC)
    listing = MagicMock(
        items=[
            MagicMock(
                occurred_at=now,
                mistake_tag="fomo",
                tags=["fomo"],
                lesson="Do not chase",
                thesis="Chased BTC",
                outcome="loss",
                source="manual",
            ),
            MagicMock(
                occurred_at=now,
                mistake_tag="fomo",
                tags=["fomo"],
                lesson="Same mistake again",
                thesis="Re-entry",
                outcome="loss",
                source="manual",
            ),
        ],
    )

    monkeypatch.setattr(
        "app.application.services.journal_studio_pretrade_recall_service.settings",
        MagicMock(
            journal_studio_enabled=True,
            journal_studio_pretrade_recall_enabled=True,
            trading_thesis_wizard_enabled=True,
            wiki_layer_enabled=False,
        ),
    )

    with (
        patch(
            "app.application.services.journal_studio_pretrade_recall_service.get_journal_studio_settings",
            AsyncMock(return_value=MagicMock(mistake_tags=["fomo", "no_stop"])),
        ),
        patch(
            "app.application.services.journal_studio_pretrade_recall_service.list_journal_trade_entries",
            AsyncMock(return_value=listing),
        ),
        patch(
            "app.application.services.journal_studio_pretrade_recall_service._latest_thesis_snippet",
            AsyncMock(return_value=(None, "")),
        ),
    ):
        recall = await compose_pretrade_recall(session, tenant_id=tenant_id, dashboard_user_id=user_id)

    assert recall.enabled is True
    assert recall.mistake_count == 1
    assert recall.top_mistakes[0].tag == "fomo"
    assert recall.top_mistakes[0].count == 2
    assert "PRE-TRADE RECALL" in recall.injection_block
