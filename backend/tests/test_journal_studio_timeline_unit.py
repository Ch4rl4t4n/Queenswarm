"""Unit tests for Track O TJ1 journal timeline and workspace snapshot."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.journal_studio_timeline_service import (
    compose_journal_studio_workspace_snapshot,
    compose_journal_timeline,
)


@pytest.mark.asyncio
async def test_compose_journal_timeline_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.journal_studio_timeline_service.settings",
        MagicMock(journal_studio_enabled=False),
    )
    timeline = await compose_journal_timeline(
        AsyncMock(),
        tenant_id=uuid.uuid4(),
        dashboard_user_id=uuid.uuid4(),
        tenant=None,
    )
    assert timeline.enabled is False


@pytest.mark.asyncio
async def test_compose_journal_timeline_includes_manual_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()
    tenant = MagicMock(
        operator_settings={
            "journal_studio": {
                "manual_entries": [
                    {
                        "id": "e1",
                        "title": "FOMO re-entry",
                        "lesson": "Wait for setup confirmation",
                        "occurred_at": datetime.now(tz=UTC).isoformat(),
                        "tags": ["fomo"],
                    },
                ],
            },
        },
    )
    session.scalars = AsyncMock(return_value=MagicMock(all=lambda: []))

    monkeypatch.setattr(
        "app.application.services.journal_studio_timeline_service.settings",
        MagicMock(journal_studio_enabled=True),
    )

    with patch(
        "app.application.services.journal_studio_timeline_service.ensure_primary_trading_project",
        AsyncMock(side_effect=RuntimeError("no project")),
    ):
        timeline = await compose_journal_timeline(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            tenant=tenant,
        )

    assert timeline.enabled is True
    assert timeline.manual_entry_count == 1
    assert timeline.items[0].kind == "manual_entry"
    assert timeline.items[0].title == "FOMO re-entry"


@pytest.mark.asyncio
async def test_compose_journal_timeline_includes_paper_fill(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()
    tenant = MagicMock(operator_settings={})
    project = MagicMock()
    project.id = uuid.uuid4()
    project.settings = {"venue": "polymarket"}

    fill = MagicMock()
    fill.id = uuid.uuid4()
    fill.side = "buy"
    fill.symbol = "BTC"
    fill.signal_note = "Breakout retest"
    fill.fill_price_usd = 42000.0
    fill.notional_usd = 100.0
    fill.created_at = datetime.now(tz=UTC)

    class _ScalarRows:
        def __init__(self, rows: list[MagicMock]) -> None:
            self._rows = rows

        def __iter__(self):
            return iter(self._rows)

    async def _scalars(stmt: object) -> _ScalarRows:
        sql = str(stmt).lower()
        if "paper_trading" in sql:
            return _ScalarRows([fill])
        return _ScalarRows([])

    session.scalars = _scalars

    monkeypatch.setattr(
        "app.application.services.journal_studio_timeline_service.settings",
        MagicMock(journal_studio_enabled=True),
    )

    with patch(
        "app.application.services.journal_studio_timeline_service.ensure_primary_trading_project",
        AsyncMock(return_value=project),
    ):
        timeline = await compose_journal_timeline(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            tenant=tenant,
        )

    assert timeline.paper_fill_count == 1
    assert timeline.items[0].symbol == "BTC"


@pytest.mark.asyncio
async def test_compose_journal_workspace_snapshot_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.journal_studio_settings_service import JournalStudioRoutineKpiOut

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()

    monkeypatch.setattr(
        "app.application.services.journal_studio_timeline_service.settings",
        MagicMock(journal_studio_enabled=True),
    )

    routine = JournalStudioRoutineKpiOut(
        enabled=True,
        routine_status="scheduled",
        routine_id=None,
        routine_name="Trading journal review",
        next_run_at=None,
        review_cron="0 6 * * *",
        review_cron_preset="daily_0600",
        obsidian_subfolder="Trading/Journal",
        enabled_field_count=2,
        mistake_tag_count=1,
        operator_hint="ok",
    )

    with (
        patch(
            "app.application.services.journal_studio_timeline_service.get_journal_studio_settings",
            AsyncMock(
                return_value=MagicMock(
                    enabled=True,
                    field_toggles={"thesis": True, "lesson": True},
                    mistake_tags=["fomo"],
                    obsidian_subfolder="Trading/Journal",
                    review_cron_enabled=True,
                ),
            ),
        ),
        patch(
            "app.application.services.journal_studio_timeline_service.compose_journal_studio_routine_kpi",
            AsyncMock(return_value=routine),
        ),
        patch(
            "app.application.services.journal_studio_timeline_service.compose_journal_timeline",
            AsyncMock(return_value=MagicMock(items=[], operator_hint="empty")),
        ),
    ):
        snap = await compose_journal_studio_workspace_snapshot(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            tenant=MagicMock(),
        )

    assert snap.enabled is True
    assert len(snap.panels) == 3
    assert snap.enabled_field_count == 2
