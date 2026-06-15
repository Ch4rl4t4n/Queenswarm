"""Unit tests for MEM1 auto episodic capture."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.episodic_capture_service import (
    build_capture_record,
    capture_episodic_session,
    derive_episodic_daily_log,
)
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession


def _session(**overrides: object) -> SupervisorSession:
    row = SupervisorSession(
        tenant_id=uuid.uuid4(),
        goal="Ship Gumroad hero pack listing",
        status="completed",
        runtime_mode="inprocess",
        context_summary={"raw_goal": "Ship Gumroad hero pack listing"},
    )
    row.id = uuid.uuid4()
    row.completed_at = datetime.now(tz=UTC)
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def test_build_capture_record_includes_goal_and_day() -> None:
    session = _session()
    record = build_capture_record(session, summary="Verified CTA and headline draft ready for upload.")
    assert record["session_id"] == str(session.id)
    assert record["day"]
    assert "Gumroad" in record["goal"]
    assert len(record["summary"]) >= 48


def test_derive_episodic_daily_log_groups_by_day() -> None:
    today = datetime.now(tz=UTC).date().isoformat()
    captures = [
        {
            "capture_id": "capture:1",
            "session_id": "00000000-0000-4000-8000-000000000001",
            "captured_at": f"{today}T12:00:00+00:00",
            "day": today,
            "goal": "Gumroad hero pack",
            "summary": "Listing draft with CTA.",
            "status": "completed",
            "href": "/agents?session=1",
        },
    ]
    log = derive_episodic_daily_log(captures, days=3)
    assert log.enabled is True
    assert log.total_captures == 1
    assert any(day.session_count == 1 for day in log.days)


@pytest.mark.asyncio
async def test_capture_episodic_session_persists_to_tenant_settings() -> None:
    db = AsyncMock()
    session_row = _session()
    tenant = SimpleNamespace(operator_settings={})
    sub = SimpleNamespace(
        role="reporter",
        status="completed",
        last_output="Verified Gumroad listing copy with clear CTA and scorecard references for operator approve.",
        short_memory={},
    )
    db.get = AsyncMock(return_value=tenant)
    db.scalars = AsyncMock(return_value=AsyncMock(all=lambda: [sub]))
    db.flush = AsyncMock()

    with patch("app.application.services.episodic_capture_service.settings") as mock_settings:
        mock_settings.auto_episodic_capture_enabled = True
        mock_settings.episodic_memory_enabled = True
        ok = await capture_episodic_session(db, session=session_row)

    assert ok is True
    bucket = tenant.operator_settings.get("episodic_captures", {})
    assert len(bucket.get("captures") or []) == 1
    assert session_row.context_summary.get("episodic_captured") is True


@pytest.mark.asyncio
async def test_capture_episodic_session_skips_when_disabled() -> None:
    db = AsyncMock()
    with patch("app.application.services.episodic_capture_service.settings") as mock_settings:
        mock_settings.auto_episodic_capture_enabled = False
        ok = await capture_episodic_session(db, session=_session())
    assert ok is False
