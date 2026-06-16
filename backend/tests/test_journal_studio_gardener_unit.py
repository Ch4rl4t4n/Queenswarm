"""Unit tests for Track O TJ3 journal studio gardener."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.journal_studio_gardener_service import (
    JournalDraftReviewIn,
    build_draft_from_fill,
    compose_journal_gardener_snapshot,
    review_journal_draft,
    run_journal_studio_gardener_sweep,
    score_journal_draft_critic,
)


def test_score_journal_draft_critic_passes_rich_draft() -> None:
    score, passed = score_journal_draft_critic(
        thesis="Breakout retest on BTC with volume confirmation",
        draft_lesson="Wait for retest hold before sizing up; avoid FOMO on first touch.",
        symbol="BTC",
        tags=["paper", "breakout"],
    )
    assert score >= 3.5
    assert passed is True


def test_build_draft_from_fill_has_markdown_preview() -> None:
    fill = MagicMock()
    fill.id = uuid.uuid4()
    fill.side = "buy"
    fill.symbol = "ETH"
    fill.signal_note = "Momentum continuation"
    fill.fill_price_usd = 3200.0

    raw = build_draft_from_fill(
        fill,
        obsidian_subfolder="Trading/Journal",
        mistake_tags=["fomo", "no_stop"],
    )

    assert raw["fill_id"] == str(fill.id)
    assert "ETH" in raw["draft_lesson"]
    assert "Operator approve" in raw["markdown_preview"]


@pytest.mark.asyncio
async def test_run_journal_gardener_sweep_creates_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fill_id = uuid.uuid4()
    project_id = uuid.uuid4()

    fill = MagicMock()
    fill.id = fill_id
    fill.side = "buy"
    fill.symbol = "BTC"
    fill.signal_note = "Breakout"
    fill.fill_price_usd = 42000.0
    fill.created_at = datetime.now(tz=UTC)

    project = MagicMock()
    project.id = project_id

    tenant = MagicMock()
    tenant.operator_settings = {"journal_studio": {}}

    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)

    class _ScalarRows:
        def __init__(self, rows: list[MagicMock]) -> None:
            self._rows = rows

        def __iter__(self):
            return iter(self._rows)

    session.scalars = AsyncMock(return_value=_ScalarRows([fill]))

    monkeypatch.setattr(
        "app.application.services.journal_studio_gardener_service.settings",
        MagicMock(journal_studio_enabled=True, journal_studio_gardener_enabled=True, wiki_layer_enabled=True),
    )

    with (
        patch(
            "app.application.services.journal_studio_gardener_service.get_journal_studio_settings",
            AsyncMock(
                return_value=MagicMock(
                    enabled=True,
                    review_cron_enabled=True,
                    obsidian_subfolder="Trading/Journal",
                    mistake_tags=["fomo"],
                ),
            ),
        ),
        patch(
            "app.application.services.journal_studio_gardener_service.ensure_primary_trading_project",
            AsyncMock(return_value=project),
        ),
    ):
        result = await run_journal_studio_gardener_sweep(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
        )

    assert result["drafts_created"] == 1
    drafts = tenant.operator_settings["journal_studio"]["pending_drafts"]
    assert len(drafts) == 1
    assert drafts[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_compose_journal_gardener_snapshot_counts_pending() -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {
        "journal_studio": {
            "pending_drafts": [
                {
                    "id": "d1",
                    "status": "pending",
                    "thesis": "Test",
                    "draft_lesson": "Lesson",
                    "markdown_preview": "# draft",
                    "created_at": datetime.now(tz=UTC).isoformat(),
                },
            ],
            "gardener_last_run_at": datetime.now(tz=UTC).isoformat(),
            "gardener_last_run_drafts_created": 1,
        },
    }
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)

    with patch(
        "app.application.services.journal_studio_gardener_service.settings",
        MagicMock(journal_studio_enabled=True, journal_studio_gardener_enabled=True),
    ):
        snap = await compose_journal_gardener_snapshot(session, tenant_id=tenant_id)

    assert snap.pending_count == 1
    assert snap.items[0].thesis == "Test"


@pytest.mark.asyncio
async def test_review_journal_draft_reject() -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {
        "journal_studio": {
            "pending_drafts": [
                {
                    "id": "d1",
                    "status": "pending",
                    "thesis": "Test",
                    "draft_lesson": "Lesson",
                    "markdown_preview": "# draft",
                    "created_at": datetime.now(tz=UTC).isoformat(),
                },
            ],
        },
    }
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.flush = AsyncMock()

    with patch(
        "app.application.services.journal_studio_gardener_service.settings",
        MagicMock(journal_studio_enabled=True, journal_studio_gardener_enabled=True),
    ):
        result = await review_journal_draft(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            draft_id="d1",
            body=JournalDraftReviewIn(decision="reject", note="Not useful"),
        )

    assert result.status == "rejected"
    assert tenant.operator_settings["journal_studio"]["pending_drafts"][0]["status"] == "rejected"
