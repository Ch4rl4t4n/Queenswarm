"""Unit tests for Track O TJ5 pre-trade recall service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.journal_studio_pretrade_recall_service import (
    PreTradeMistakeOut,
    compose_pretrade_recall,
    load_trading_pretrade_recall_injection,
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


def test_should_inject_pretrade_recall_disabled() -> None:
    with patch(
        "app.application.services.journal_studio_pretrade_recall_service.settings",
        MagicMock(journal_studio_enabled=False, journal_studio_pretrade_recall_enabled=False),
    ):
        assert should_inject_pretrade_recall(context_seed={"lane": "trading"}, goal="Polymarket") is False


def test_should_inject_pretrade_recall_harness_profile() -> None:
    with patch(
        "app.application.services.journal_studio_pretrade_recall_service.settings",
        MagicMock(journal_studio_enabled=True, journal_studio_pretrade_recall_enabled=True),
    ):
        assert should_inject_pretrade_recall(context_seed={"harness_profile_id": "trading"}, goal="Daily review") is True
        assert should_inject_pretrade_recall(context_seed={"trading_harness": True}, goal="Daily review") is True
        assert should_inject_pretrade_recall(context_seed={"lane": "journal_studio_review"}, goal="Review") is True


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


def test_render_pretrade_injection_block_without_mistakes() -> None:
    block = render_pretrade_injection_block(
        top_mistakes=[],
        edge_reminders=[],
        thesis_title=None,
        thesis_snippet="",
        wiki_snippets=[],
        window_days=14,
    )
    assert "No ranked mistakes yet" in block
    assert "END PRE-TRADE RECALL" in block


@pytest.mark.asyncio
async def test_compose_pretrade_recall_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.journal_studio_pretrade_recall_service.settings",
        MagicMock(journal_studio_enabled=False, journal_studio_pretrade_recall_enabled=False),
    )
    recall = await compose_pretrade_recall(AsyncMock(), tenant_id=uuid.uuid4(), dashboard_user_id=uuid.uuid4())
    assert recall.enabled is False
    assert "disabled" in recall.operator_hint.lower()


@pytest.mark.asyncio
async def test_load_trading_pretrade_recall_injection_skips_non_trading_goal() -> None:
    with patch(
        "app.application.services.journal_studio_pretrade_recall_service.settings",
        MagicMock(journal_studio_enabled=True, journal_studio_pretrade_recall_enabled=True),
    ):
        block = await load_trading_pretrade_recall_injection(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            context_seed={},
            goal="Write blog post",
        )
    assert block == ""


@pytest.mark.asyncio
async def test_load_trading_pretrade_recall_injection_returns_block(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    monkeypatch.setattr(
        "app.application.services.journal_studio_pretrade_recall_service.settings",
        MagicMock(journal_studio_enabled=True, journal_studio_pretrade_recall_enabled=True),
    )
    with patch(
        "app.application.services.journal_studio_pretrade_recall_service.compose_pretrade_recall",
        AsyncMock(
            return_value=MagicMock(
                injection_block="=== PRE-TRADE RECALL (TJ5) ===\n- fomo\n=== END PRE-TRADE RECALL ===",
                top_mistakes=[MagicMock(tag="fomo")],
            ),
        ),
    ):
        block = await load_trading_pretrade_recall_injection(
            AsyncMock(),
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            context_seed={"lane": "trading"},
            goal="Review markets",
        )
    assert "PRE-TRADE RECALL" in block


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


@pytest.mark.asyncio
async def test_compose_pretrade_recall_thesis_hint_when_no_mistakes(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()

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
            AsyncMock(return_value=MagicMock(mistake_tags=["fomo"])),
        ),
        patch(
            "app.application.services.journal_studio_pretrade_recall_service.list_journal_trade_entries",
            AsyncMock(return_value=MagicMock(items=[])),
        ),
        patch(
            "app.application.services.journal_studio_pretrade_recall_service._latest_thesis_snippet",
            AsyncMock(return_value=("BTC thesis", "Kill if support breaks.")),
        ),
    ):
        recall = await compose_pretrade_recall(session, tenant_id=tenant_id, dashboard_user_id=user_id)

    assert recall.mistake_count == 0
    assert recall.thesis_snippet.startswith("Kill if support")
    assert "Thesis brief loaded" in recall.operator_hint


@pytest.mark.asyncio
async def test_compose_pretrade_recall_includes_wiki_snippets(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()
    wiki_page = MagicMock(
        slug="trading-journal-btc-lesson",
        title="Journal · BTC",
        content_md="Wait for confirmation before sizing up.",
        updated_at=datetime.now(tz=UTC),
        created_at=datetime.now(tz=UTC),
    )

    monkeypatch.setattr(
        "app.application.services.journal_studio_pretrade_recall_service.settings",
        MagicMock(
            journal_studio_enabled=True,
            journal_studio_pretrade_recall_enabled=True,
            trading_thesis_wizard_enabled=False,
            wiki_layer_enabled=True,
        ),
    )

    with (
        patch(
            "app.application.services.journal_studio_pretrade_recall_service.get_journal_studio_settings",
            AsyncMock(return_value=MagicMock(mistake_tags=["fomo"])),
        ),
        patch(
            "app.application.services.journal_studio_pretrade_recall_service.list_journal_trade_entries",
            AsyncMock(return_value=MagicMock(items=[])),
        ),
        patch(
            "app.application.services.journal_studio_pretrade_recall_service._latest_thesis_snippet",
            AsyncMock(return_value=(None, "")),
        ),
        patch(
            "app.application.services.wiki_layer_service.WikiLayerService.list_wiki_pages",
            AsyncMock(return_value=[wiki_page]),
        ),
    ):
        recall = await compose_pretrade_recall(session, tenant_id=tenant_id, dashboard_user_id=user_id)

    assert recall.wiki_snippets
    assert "Journal · BTC" in recall.wiki_snippets[0]
