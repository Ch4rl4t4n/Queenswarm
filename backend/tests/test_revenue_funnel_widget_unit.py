"""Unit tests for MK10 unified revenue funnel widget."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.application.services.catalog_wave_widget_service import CatalogWaveWidgetOut
from app.application.services.factory_launch_widget_service import FactoryLaunchWidgetOut
from app.application.services.revenue_funnel_widget_service import compose_revenue_funnel_widget_snapshot
from app.core.config import settings


@pytest.mark.asyncio
async def test_revenue_funnel_widget_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """When MK10 flag is off, snapshot is disabled."""

    monkeypatch.setattr(settings, "revenue_funnel_mission_home_enabled", False)

    class _Session:
        pass

    snapshot = await compose_revenue_funnel_widget_snapshot(_Session(), tenant_id=uuid.uuid4())
    assert snapshot.enabled is False
    assert "disabled" in snapshot.operator_hint.lower()


@pytest.mark.asyncio
async def test_revenue_funnel_prefers_launch_and_verify(monkeypatch: pytest.MonkeyPatch) -> None:
    """Primary CTA is Launch & verify when REV12 is available."""

    monkeypatch.setattr(settings, "revenue_funnel_mission_home_enabled", True)
    monkeypatch.setattr(settings, "catalog_wave_mission_home_enabled", True)
    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)

    now = datetime.now(tz=UTC)
    monkeypatch.setattr(
        "app.application.services.revenue_funnel_widget_service.compose_catalog_wave_widget_snapshot",
        lambda: CatalogWaveWidgetOut(
            enabled=True,
            generated_at=now,
            scorecard_clean_count=18,
            mk6_target=50,
            gap_to_mk6=32,
            seed_pending_count=2,
            wave_complete=False,
            operator_hint="Scale catalog.",
            catalog_href="https://letagentscook.org/skills",
        ),
    )

    async def _launch(_session: object, *, tenant_id: uuid.UUID) -> FactoryLaunchWidgetOut:
        return FactoryLaunchWidgetOut(
            enabled=True,
            generated_at=now,
            sellable_count=2,
            launch_and_verify_available=True,
            full_funnel_available=True,
            operator_hint="Ready to launch.",
        )

    monkeypatch.setattr(
        "app.application.services.revenue_funnel_widget_service.compose_factory_launch_widget_snapshot",
        _launch,
    )

    snapshot = await compose_revenue_funnel_widget_snapshot(object(), tenant_id=uuid.uuid4())
    assert snapshot.enabled is True
    assert snapshot.primary_action is not None
    assert snapshot.primary_action.id == "launch_and_verify"
    assert snapshot.sellable_count == 2
    assert snapshot.funnel_complete is False


@pytest.mark.asyncio
async def test_revenue_funnel_complete_when_loop_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Funnel complete when all four steps are satisfied."""

    monkeypatch.setattr(settings, "revenue_funnel_mission_home_enabled", True)
    monkeypatch.setattr(settings, "catalog_wave_mission_home_enabled", True)
    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)

    now = datetime.now(tz=UTC)
    monkeypatch.setattr(
        "app.application.services.revenue_funnel_widget_service.compose_catalog_wave_widget_snapshot",
        lambda: CatalogWaveWidgetOut(
            enabled=True,
            generated_at=now,
            scorecard_clean_count=52,
            mk6_target=50,
            gap_to_mk6=0,
            wave_complete=True,
            operator_hint="MK6 met.",
        ),
    )

    async def _launch(_session: object, *, tenant_id: uuid.UUID) -> FactoryLaunchWidgetOut:
        return FactoryLaunchWidgetOut(
            enabled=True,
            generated_at=now,
            sellable_count=3,
            published_gumroad_count=2,
            revenue_loop_ready=True,
        )

    monkeypatch.setattr(
        "app.application.services.revenue_funnel_widget_service.compose_factory_launch_widget_snapshot",
        _launch,
    )

    snapshot = await compose_revenue_funnel_widget_snapshot(object(), tenant_id=uuid.uuid4())
    assert snapshot.funnel_complete is True
    assert snapshot.primary_action is None
    assert all(step.done for step in snapshot.steps)


@pytest.mark.asyncio
async def test_revenue_funnel_scale_when_no_sellable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without sellable harness, CTA points to factory seeds or scale."""

    monkeypatch.setattr(settings, "revenue_funnel_mission_home_enabled", True)
    monkeypatch.setattr(settings, "catalog_wave_mission_home_enabled", True)
    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "catalog_wave_seed_batch_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)

    now = datetime.now(tz=UTC)
    monkeypatch.setattr(
        "app.application.services.revenue_funnel_widget_service.compose_catalog_wave_widget_snapshot",
        lambda: CatalogWaveWidgetOut(
            enabled=True,
            generated_at=now,
            scorecard_clean_count=5,
            mk6_target=50,
            gap_to_mk6=45,
            seed_pending_count=4,
            wave_complete=False,
            factory_href="/apps-tools/skill-factory",
        ),
    )

    async def _launch(_session: object, *, tenant_id: uuid.UUID) -> FactoryLaunchWidgetOut:
        return FactoryLaunchWidgetOut(
            enabled=True,
            generated_at=now,
            sellable_count=0,
            launch_and_verify_available=False,
            full_funnel_available=False,
            prepare_available=False,
        )

    monkeypatch.setattr(
        "app.application.services.revenue_funnel_widget_service.compose_factory_launch_widget_snapshot",
        _launch,
    )

    snapshot = await compose_revenue_funnel_widget_snapshot(object(), tenant_id=uuid.uuid4())
    assert snapshot.primary_action is not None
    assert snapshot.primary_action.id == "factory_seeds"
    assert snapshot.primary_action.post_path == "dashboard/catalog-wave/seed-batch"
