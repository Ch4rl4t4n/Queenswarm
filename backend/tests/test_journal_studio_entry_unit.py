"""Unit tests for Track O TJ2 journal trade entry schema."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.journal_studio_entry_service import (
    JournalTradeEntryCreateIn,
    JournalTradeEntryImportIn,
    JournalTradeEntryPatchIn,
    create_journal_trade_entry,
    import_journal_entry_from_fill,
    list_journal_trade_entries,
    update_journal_trade_entry,
)


@pytest.mark.asyncio
async def test_create_and_list_journal_entry() -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {}
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.flush = AsyncMock()

    with patch(
        "app.application.services.journal_studio_entry_service.get_journal_studio_settings",
        AsyncMock(return_value=MagicMock(field_toggles={"thesis": True, "lesson": True})),
    ):
        created = await create_journal_trade_entry(
            session,
            tenant_id=tenant_id,
            body=JournalTradeEntryCreateIn(
                thesis="Breakout retest on BTC",
                outcome="win",
                lesson="Wait for confirmation",
                tags=["breakout"],
            ),
        )
        listing = await list_journal_trade_entries(session, tenant_id=tenant_id)

    assert created.thesis == "Breakout retest on BTC"
    assert listing.entry_count == 1
    assert listing.items[0].lesson == "Wait for confirmation"
    bucket = tenant.operator_settings["journal_studio"]["manual_entries"]
    assert len(bucket) == 1


@pytest.mark.asyncio
async def test_update_journal_entry_patch_lesson() -> None:
    tenant_id = uuid.uuid4()
    entry_id = str(uuid.uuid4())
    tenant = MagicMock()
    tenant.operator_settings = {
        "journal_studio": {
            "manual_entries": [
                {
                    "id": entry_id,
                    "thesis": "Old thesis",
                    "lesson": "Old lesson",
                    "occurred_at": datetime.now(tz=UTC).isoformat(),
                    "created_at": datetime.now(tz=UTC).isoformat(),
                    "updated_at": datetime.now(tz=UTC).isoformat(),
                },
            ],
        },
    }
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.flush = AsyncMock()

    updated = await update_journal_trade_entry(
        session,
        tenant_id=tenant_id,
        entry_id=entry_id,
        patch=JournalTradeEntryPatchIn(lesson="New lesson", outcome="loss"),
    )

    assert updated.lesson == "New lesson"
    assert updated.outcome == "loss"


@pytest.mark.asyncio
async def test_import_journal_entry_from_fill() -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fill_id = uuid.uuid4()
    project_id = uuid.uuid4()

    tenant = MagicMock()
    tenant.operator_settings = {"trading_lane": {}}

    fill = MagicMock()
    fill.id = fill_id
    fill.side = "buy"
    fill.symbol = "ETH"
    fill.signal_note = "Momentum continuation"
    fill.fill_price_usd = 3200.0
    fill.quantity = 0.5
    fill.created_at = datetime.now(tz=UTC)

    project = MagicMock()
    project.id = project_id

    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.scalar = AsyncMock(return_value=fill)
    session.flush = AsyncMock()

    with patch(
        "app.application.services.journal_studio_entry_service.ensure_primary_trading_project",
        AsyncMock(return_value=project),
    ):
        entry = await import_journal_entry_from_fill(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            fill_id=fill_id,
            overrides=JournalTradeEntryImportIn(lesson="Size was ok", tags=["momentum"]),
        )

    assert entry.source == "paper_fill"
    assert entry.fill_id == str(fill_id)
    assert entry.symbol == "ETH"
    assert entry.lesson == "Size was ok"


@pytest.mark.asyncio
async def test_import_fill_rejects_duplicate() -> None:
    tenant_id = uuid.uuid4()
    fill_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {
        "journal_studio": {
            "manual_entries": [{"id": "x", "fill_id": str(fill_id)}],
        },
    }
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)

    with pytest.raises(ValueError, match="already imported"):
        await import_journal_entry_from_fill(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=uuid.uuid4(),
            fill_id=fill_id,
        )
