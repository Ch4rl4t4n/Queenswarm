"""Unit tests for LR3 worker crash auto-resume."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.supervisor.checkpoint_resume import SessionCheckpointSnapshot
from app.application.services.worker_crash_auto_resume_service import (
    derive_worker_crash_stale_cutoff,
    sweep_stale_durable_sub_agents_for_auto_resume,
)


def test_derive_worker_crash_stale_cutoff_uses_timeout() -> None:
    now = datetime(2026, 6, 5, 12, 0, 0, tzinfo=UTC)
    cutoff = derive_worker_crash_stale_cutoff(now=now, timeout_sec=240)
    assert cutoff == now - timedelta(seconds=240)


def test_derive_worker_crash_stale_cutoff_minimum_window() -> None:
    now = datetime(2026, 6, 5, 12, 0, 0, tzinfo=UTC)
    cutoff = derive_worker_crash_stale_cutoff(now=now, timeout_sec=10)
    assert cutoff == now - timedelta(seconds=30)


@pytest.mark.asyncio
async def test_sweep_disabled_returns_zero() -> None:
    with patch("app.application.services.worker_crash_auto_resume_service.settings") as mock_settings:
        mock_settings.worker_crash_auto_resume_enabled = False
        result = await sweep_stale_durable_sub_agents_for_auto_resume(AsyncMock())
    assert result.resumed == 0
    assert result.scanned == 0


@pytest.mark.asyncio
async def test_sweep_marks_stale_running_and_notifies() -> None:
    tenant_id = uuid.uuid4()
    session_id = uuid.uuid4()
    sub_id = uuid.uuid4()
    stale_started = datetime.now(tz=UTC) - timedelta(seconds=900)

    sub = SimpleNamespace(
        id=sub_id,
        role="reporter",
        status="running",
        started_at=stale_started,
        completed_at=None,
        error_text=None,
    )
    sup = SimpleNamespace(
        id=session_id,
        tenant_id=tenant_id,
        goal="Ship Gumroad listing",
        status="running",
        runtime_mode="durable",
        context_summary={"raw_goal": "Ship Gumroad listing"},
    )

    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.all.return_value = [(sub, sup)]
    db.execute = AsyncMock(return_value=execute_result)
    db.flush = AsyncMock()

    snapshot = SessionCheckpointSnapshot(
        session_id=session_id,
        session_status="running",
        runtime_mode="durable",
        can_resume_from_checkpoint=True,
        resume_hint="Resume reporter from checkpoint.",
        last_verified_role="researcher",
        next_resumable_role="reporter",
    )

    with (
        patch("app.application.services.worker_crash_auto_resume_service.settings") as mock_settings,
        patch(
            "app.application.services.worker_crash_auto_resume_service.resume_session_from_last_checkpoint",
            new_callable=AsyncMock,
        ) as mock_resume,
        patch(
            "app.application.services.worker_crash_auto_resume_service.append_event",
            new_callable=AsyncMock,
        ),
        patch(
            "app.application.services.worker_crash_auto_resume_service.push_mission_feed_event",
            new_callable=AsyncMock,
        ) as mock_feed,
    ):
        mock_settings.worker_crash_auto_resume_enabled = True
        mock_settings.worker_crash_stale_timeout_sec = 240
        mock_settings.worker_crash_resume_cooldown_sec = 600
        mock_resume.return_value = (sup, snapshot, 1)

        result = await sweep_stale_durable_sub_agents_for_auto_resume(db)

    assert result.scanned == 1
    assert result.resumed == 1
    assert result.notified == 1
    assert sub.status == "failed"
    assert "Worker lease expired" in str(sub.error_text)
    mock_feed.assert_awaited_once()
    assert sup.context_summary.get("last_worker_crash_resume_requeued") == 1


@pytest.mark.asyncio
async def test_sweep_skips_recent_cooldown() -> None:
    tenant_id = uuid.uuid4()
    sub = SimpleNamespace(
        id=uuid.uuid4(),
        role="coder",
        status="running",
        started_at=datetime.now(tz=UTC) - timedelta(seconds=900),
        completed_at=None,
        error_text=None,
    )
    sup = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        goal="Retry after crash",
        status="running",
        runtime_mode="durable",
        context_summary={
            "last_worker_crash_resume_at": datetime.now(tz=UTC).isoformat(),
        },
    )

    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.all.return_value = [(sub, sup)]
    db.execute = AsyncMock(return_value=execute_result)

    with patch("app.application.services.worker_crash_auto_resume_service.settings") as mock_settings:
        mock_settings.worker_crash_auto_resume_enabled = True
        mock_settings.worker_crash_stale_timeout_sec = 240
        mock_settings.worker_crash_resume_cooldown_sec = 600
        result = await sweep_stale_durable_sub_agents_for_auto_resume(db)

    assert result.scanned == 1
    assert result.skipped_cooldown == 1
    assert result.resumed == 0
    assert sub.status == "running"
