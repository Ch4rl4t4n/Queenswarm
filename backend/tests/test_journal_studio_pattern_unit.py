"""Unit tests for Track O TJ6 journal pattern strip service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.journal_studio_entry_service import JournalTradeEntryOut, JournalTradeEntryListOut
from app.application.services.journal_studio_pattern_service import (
    JournalPatternStripOut,
    JournalPatternWindowOut,
    compose_journal_pattern_strip,
    compose_journal_pattern_strip_kpi,
)
from app.application.services.journal_studio_settings_service import JournalStudioSettingsOut


def _entry(
    *,
    tag: str | None,
    outcome: str,
    days_ago: int,
    tags: list[str] | None = None,
) -> JournalTradeEntryOut:
    now = datetime.now(tz=UTC)
    return JournalTradeEntryOut(
        id=str(uuid.uuid4()),
        source="manual",
        fill_id=None,
        thesis="Test thesis",
        setup="",
        entry_price=None,
        exit_price=None,
        position_size=None,
        outcome=outcome,
        pnl_usd=None,
        emotion="",
        lesson="Lesson text",
        tags=tags or ([tag] if tag else []),
        mistake_tag=tag,
        symbol="BTC",
        side="buy",
        venue=None,
        occurred_at=now - timedelta(days=days_ago),
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_compose_journal_pattern_strip_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.journal_studio_pattern_service.settings",
        MagicMock(journal_studio_enabled=False, journal_studio_pattern_strip_enabled=False),
    )
    strip = await compose_journal_pattern_strip(AsyncMock(), tenant_id=uuid.uuid4(), dashboard_user_id=uuid.uuid4())
    assert strip.enabled is False
    assert "disabled" in strip.operator_hint.lower()


@pytest.mark.asyncio
async def test_compose_journal_pattern_strip_repeat_mistake_alert(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()
    studio = JournalStudioSettingsOut(
        enabled=True,
        field_toggles={"mistake_tag": True},
        review_cron_enabled=True,
        review_cron_preset="daily_0600",
        review_cron="0 6 * * *",
        obsidian_subfolder="Trading/Journal",
        mistake_tags=["fomo", "revenge_trade"],
        source="deployment",
        updated_at=None,
    )
    listing = JournalTradeEntryListOut(
        enabled=True,
        entry_count=2,
        enabled_fields=["mistake_tag"],
        items=[
            _entry(tag="fomo", outcome="loss", days_ago=3),
            _entry(tag="fomo", outcome="loss", days_ago=5),
            _entry(tag="breakout", outcome="win", days_ago=10, tags=["breakout"]),
        ],
        operator_hint="3 entries",
    )

    monkeypatch.setattr(
        "app.application.services.journal_studio_pattern_service.settings",
        MagicMock(journal_studio_enabled=True, journal_studio_pattern_strip_enabled=True),
    )
    with (
        patch(
            "app.application.services.journal_studio_pattern_service.get_journal_studio_settings",
            AsyncMock(return_value=studio),
        ),
        patch(
            "app.application.services.journal_studio_pattern_service.list_journal_trade_entries",
            AsyncMock(return_value=listing),
        ),
    ):
        strip = await compose_journal_pattern_strip(session, tenant_id=tenant_id, dashboard_user_id=user_id)

    assert strip.enabled is True
    assert "fomo" in strip.repeat_mistake_alerts
    window_30 = next(row for row in strip.windows if row.window_days == 30)
    assert window_30.overall_win_rate == pytest.approx(1 / 3, rel=1e-3)
    assert any(row.tag == "fomo" and row.repeat_mistake_alert for row in window_30.tag_stats)
    assert "repeat mistake" in strip.operator_hint.lower()


@pytest.mark.asyncio
async def test_compose_journal_pattern_strip_kpi_from_strip(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(tz=UTC)
    strip = JournalPatternStripOut(
        enabled=True,
        generated_at=now,
        windows=[
            JournalPatternWindowOut(window_days=30, overall_win_rate=0.5, edge_tags=["breakout"], repeat_mistakes=["fomo"]),
            JournalPatternWindowOut(window_days=90, overall_win_rate=0.6, edge_tags=[], repeat_mistakes=[]),
        ],
        repeat_mistake_alerts=["fomo"],
        operator_hint="hint",
        morning_brief_line="brief line",
    )
    with patch(
        "app.application.services.journal_studio_pattern_service.compose_journal_pattern_strip",
        AsyncMock(return_value=strip),
    ):
        kpi = await compose_journal_pattern_strip_kpi(AsyncMock(), tenant_id=uuid.uuid4(), dashboard_user_id=uuid.uuid4())

    assert kpi.window_30_win_rate == 0.5
    assert kpi.window_90_win_rate == 0.6
    assert kpi.repeat_mistake_count == 1
    assert kpi.repeat_mistakes == ["fomo"]
    assert kpi.edge_tags == ["breakout"]
