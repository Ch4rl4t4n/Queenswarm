"""Unit tests for SB2 connection-intelligence weekly refresh."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.connection_intelligence_bee import run_connection_intelligence_refresh
from app.application.services.wiki_layer_service import WikiLayerService
from app.infrastructure.persistence.models.wiki_layer import WikiGardenerStatusORM


@pytest.mark.asyncio
async def test_run_connection_intelligence_refresh_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "wiki_layer_enabled", False)
    db = AsyncMock()
    result = await run_connection_intelligence_refresh(db, tenant_id=uuid.uuid4())
    assert result["ok"] is False
    assert result["reason"] == "wiki_layer_disabled"


@pytest.mark.asyncio
async def test_run_connection_intelligence_refresh_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "wiki_layer_enabled", True)
    monkeypatch.setattr(settings, "second_brain_connection_intelligence_tick_enabled", True)

    run = MagicMock()
    run.id = uuid.uuid4()
    run.status = WikiGardenerStatusORM.COMPLETED
    run.pages_updated = 2
    run.raw_scanned = 3
    run.summary_md = "Weekly connection-intelligence refresh: updated 2 page(s) from 3 capture note(s)."
    run.pollen_awarded = 2.0

    db = AsyncMock()
    with patch.object(
        WikiLayerService,
        "run_connection_intelligence_refresh",
        new=AsyncMock(return_value=run),
    ):
        result = await run_connection_intelligence_refresh(db, tenant_id=uuid.uuid4())

    assert result["ok"] is True
    assert result["pages_updated"] == 2
    assert result["tick_type"] == "connection_intelligence_weekly"


def test_beat_schedule_includes_connection_intelligence_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config as config_module
    from app.worker.beat_schedule import build_beat_schedule

    monkeypatch.setattr(config_module.settings, "wiki_layer_enabled", True)
    monkeypatch.setattr(config_module.settings, "second_brain_connection_intelligence_tick_enabled", True)
    schedule = build_beat_schedule()
    assert "hive-connection-intelligence-weekly" in schedule
    entry = schedule["hive-connection-intelligence-weekly"]
    assert entry["task"] == "hive.connection_intelligence_refresh_tick"


def test_beat_schedule_omits_connection_intelligence_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config as config_module
    from app.worker.beat_schedule import build_beat_schedule

    monkeypatch.setattr(config_module.settings, "wiki_layer_enabled", True)
    monkeypatch.setattr(config_module.settings, "second_brain_connection_intelligence_tick_enabled", False)
    schedule = build_beat_schedule()
    assert "hive-connection-intelligence-weekly" not in schedule
