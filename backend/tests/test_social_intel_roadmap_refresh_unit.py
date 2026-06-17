"""Unit tests for SIG2 social intel quarterly roadmap refresh."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.social_intel_roadmap_refresh_service import (
    compose_social_intel_roadmap_refresh_kpi,
    run_social_intel_roadmap_refresh,
)


def _knowledge_row(*, tags: list[str], content: str = "Insight title") -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.source_type = "youtube"
    row.source_url = "https://youtube.com/watch?v=abc"
    row.content_text = content
    row.topic_tags = tags
    row.scraped_at = datetime.now(tz=UTC)
    row.confidence_score = 0.8
    return row


@pytest.mark.asyncio
async def test_kpi_due_when_never_refreshed(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "social_intel_roadmap_refresh_enabled", True)
    monkeypatch.setattr(settings, "social_intel_roadmap_refresh_min_signals", 2)

    tenant_id = uuid.uuid4()
    session = AsyncMock()
    signals = [
        _knowledge_row(tags=["social-intel"]),
        _knowledge_row(tags=["hivemind-candidate"]),
    ]
    monkeypatch.setattr(
        "app.application.services.social_intel_roadmap_refresh_service._load_social_intel_signals",
        AsyncMock(return_value=signals),
    )

    kpi = await compose_social_intel_roadmap_refresh_kpi(
        session,
        tenant_id=tenant_id,
        tenant=MagicMock(operator_settings={}),
    )
    assert kpi.due is True
    assert kpi.status == "due"
    assert kpi.signal_count == 2


@pytest.mark.asyncio
async def test_kpi_insufficient_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "social_intel_roadmap_refresh_enabled", True)
    monkeypatch.setattr(settings, "social_intel_roadmap_refresh_min_signals", 3)

    session = AsyncMock()
    monkeypatch.setattr(
        "app.application.services.social_intel_roadmap_refresh_service._load_social_intel_signals",
        AsyncMock(return_value=[_knowledge_row(tags=["social-intel"])]),
    )

    kpi = await compose_social_intel_roadmap_refresh_kpi(
        session,
        tenant_id=uuid.uuid4(),
        tenant=MagicMock(operator_settings={}),
    )
    assert kpi.due is False
    assert kpi.status == "insufficient_signals"


@pytest.mark.asyncio
async def test_kpi_recent_when_refreshed_recently(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "social_intel_roadmap_refresh_enabled", True)
    monkeypatch.setattr(settings, "social_intel_roadmap_refresh_min_signals", 2)
    monkeypatch.setattr(settings, "social_intel_roadmap_refresh_interval_days", 90)

    last = datetime.now(tz=UTC) - timedelta(days=10)
    tenant = MagicMock(
        operator_settings={
            "social_intel_roadmap_refresh": {
                "last_refresh_at": last.isoformat(),
                "last_task_id": str(uuid.uuid4()),
            },
        },
    )
    session = AsyncMock()
    monkeypatch.setattr(
        "app.application.services.social_intel_roadmap_refresh_service._load_social_intel_signals",
        AsyncMock(
            return_value=[
                _knowledge_row(tags=["social-intel"]),
                _knowledge_row(tags=["intel"]),
            ],
        ),
    )

    kpi = await compose_social_intel_roadmap_refresh_kpi(
        session,
        tenant_id=uuid.uuid4(),
        tenant=tenant,
    )
    assert kpi.due is False
    assert kpi.status == "recent"


@pytest.mark.asyncio
async def test_run_refresh_creates_triage_task(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "social_intel_roadmap_refresh_enabled", True)
    monkeypatch.setattr(settings, "social_intel_roadmap_refresh_min_signals", 2)

    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.id = tenant_id
    tenant.operator_settings = {}
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.flush = AsyncMock()

    signals = [
        _knowledge_row(tags=["social-intel"], content="Agent loop hype"),
        _knowledge_row(tags=["hivemind-candidate"], content="Memory beats Hermes"),
    ]
    monkeypatch.setattr(
        "app.application.services.social_intel_roadmap_refresh_service._load_social_intel_signals",
        AsyncMock(return_value=signals),
    )

    task_id = uuid.uuid4()
    triage = MagicMock()
    triage.task.id = task_id
    monkeypatch.setattr(
        "app.application.services.social_intel_roadmap_refresh_service.create_mission_triage_task",
        AsyncMock(return_value=triage),
    )

    result = await run_social_intel_roadmap_refresh(
        session,
        tenant_id=tenant_id,
        tenant=tenant,
        created_by_subject="operator",
        force=True,
    )
    assert result.ok is True
    assert result.task_id == str(task_id)
    assert tenant.operator_settings["social_intel_roadmap_refresh"]["last_task_id"] == str(task_id)
