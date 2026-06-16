"""Unit tests for Track L DA9 analytics weekly routine."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.analytics_weekly_routine_service import (
    ROUTINE_NAME,
    compose_analytics_routine_kpi,
    ensure_analytics_weekly_routine,
    run_analytics_weekly_routine_bootstrap_tick,
)
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine


def _routine_row(*, tenant_id: uuid.UUID) -> SupervisorRoutine:
    return SupervisorRoutine(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=ROUTINE_NAME,
        goal_template="Weekly deck",
        schedule_kind="cron",
        cron_expr="0 7 * * 1",
        interval_seconds=None,
        runtime_mode="durable",
        roles=["orchestrator"],
        retrieval_contract="default_v2",
        skills=["business-analytics-playbook"],
        context_payload={"lane": "analytics_weekly"},
        status="scheduled",
        is_active=True,
        created_by_subject="test",
        next_run_at=datetime.now(tz=UTC),
        last_run_at=None,
    )


@pytest.mark.asyncio
async def test_ensure_analytics_weekly_routine_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_weekly_routine_enabled", False)
    result = await ensure_analytics_weekly_routine(AsyncMock(), tenant_id=uuid.uuid4())
    assert result["status"] == "disabled"


@pytest.mark.asyncio
async def test_ensure_analytics_weekly_routine_creates(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_weekly_routine_enabled", True)
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    created = _routine_row(tenant_id=tenant_id)

    with patch(
        "app.application.services.analytics_weekly_routine_service.create_supervisor_routine",
        new=AsyncMock(return_value=created),
    ):
        result = await ensure_analytics_weekly_routine(session, tenant_id=tenant_id)

    assert result["status"] == "created"
    assert result["routine_id"] == str(created.id)


@pytest.mark.asyncio
async def test_compose_analytics_routine_kpi_missing_routine(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_weekly_routine_enabled", True)
    monkeypatch.setattr(config.settings, "analytics_connector_profile_enabled", False)
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)

    with patch(
        "app.application.services.analytics_weekly_routine_service.list_owned_deliverables",
        new=AsyncMock(return_value=[]),
    ):
        kpi = await compose_analytics_routine_kpi(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
        )

    assert kpi.enabled is True
    assert kpi.routine_status == "missing"
    assert "not scheduled" in kpi.morning_brief_line.lower()


@pytest.mark.asyncio
async def test_compose_analytics_routine_kpi_with_routine(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_weekly_routine_enabled", True)
    monkeypatch.setattr(config.settings, "analytics_connector_profile_enabled", False)
    tenant_id = uuid.uuid4()
    routine = _routine_row(tenant_id=tenant_id)
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=[routine, None])

    with patch(
        "app.application.services.analytics_weekly_routine_service.list_owned_deliverables",
        new=AsyncMock(return_value=[]),
    ):
        kpi = await compose_analytics_routine_kpi(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=uuid.uuid4(),
        )

    assert kpi.routine_status == "scheduled"
    assert kpi.routine_id == str(routine.id)


@pytest.mark.asyncio
async def test_run_analytics_weekly_routine_bootstrap_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_weekly_routine_enabled", True)
    tenant = MagicMock()
    tenant.id = uuid.uuid4()
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[tenant])))

    with patch(
        "app.application.services.analytics_weekly_routine_service.ensure_analytics_weekly_routine",
        new=AsyncMock(return_value={"status": "created", "routine_id": "x"}),
    ):
        payload = await run_analytics_weekly_routine_bootstrap_tick(session)

    assert payload["tenants"] == 1
    assert payload["created"] == 1
