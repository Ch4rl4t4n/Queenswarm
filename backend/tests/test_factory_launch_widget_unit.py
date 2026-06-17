"""Unit tests for REV4 Factory Launch Mission Home widget."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.application.services.factory_launch_widget_service import compose_factory_launch_widget_snapshot
from app.application.services.skill_factory_service import (
    LaunchReadinessOut,
    SkillFactorySnapshotOut,
    SkillFactoryPolicyOut,
    TenantSkillOut,
)


def _skill(*, slug: str, title: str) -> TenantSkillOut:
    return TenantSkillOut(
        id=str(uuid.uuid4()),
        slug=slug,
        title=title,
        description="Harness pack",
        version="1.0.0",
        priority=1,
        roles=["operator"],
        keywords=["harness"],
        source="factory",
        recipe_id=None,
        verified_at=datetime.now(tz=UTC),
        github_exported_at=None,
        is_active=True,
    )


def _factory_snapshot(
    *,
    sellable: int = 0,
    launch_queue: list[TenantSkillOut] | None = None,
    gumroad_listing_ready: bool = False,
) -> SkillFactorySnapshotOut:
    return SkillFactorySnapshotOut(
        policy=SkillFactoryPolicyOut(),
        opportunities=[],
        library=[],
        queue_count=0,
        building_count=2,
        launch_readiness=LaunchReadinessOut(
            sellable_count=sellable,
            draft_count=1,
            rejected_count=0,
            gumroad_token_configured=gumroad_listing_ready,
        ),
        launch_queue=launch_queue or [],
        gumroad_listing_ready=gumroad_listing_ready,
    )


@pytest.mark.asyncio
async def test_factory_launch_widget_disabled_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", False)
    session = AsyncMock()

    snapshot = await compose_factory_launch_widget_snapshot(session, tenant_id=uuid.uuid4())

    assert snapshot.enabled is False
    assert "disabled" in snapshot.operator_hint.lower()


@pytest.mark.asyncio
async def test_factory_launch_widget_no_sellable_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.skill_factory_service.compose_skill_factory_snapshot",
        AsyncMock(return_value=_factory_snapshot(sellable=0)),
    )
    session = AsyncMock()

    snapshot = await compose_factory_launch_widget_snapshot(session, tenant_id=uuid.uuid4())

    assert snapshot.enabled is True
    assert snapshot.sellable_count == 0
    assert snapshot.funnel_ready is False
    assert "sellable" in snapshot.operator_hint.lower()


@pytest.mark.asyncio
async def test_factory_launch_widget_funnel_ready_with_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    queue = [_skill(slug="harness-pack", title="Queenswarm Harness Pack")]
    monkeypatch.setattr(settings, "factory_launch_mission_home_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.skill_factory_service.compose_skill_factory_snapshot",
        AsyncMock(return_value=_factory_snapshot(sellable=1, launch_queue=queue, gumroad_listing_ready=True)),
    )
    session = AsyncMock()

    snapshot = await compose_factory_launch_widget_snapshot(session, tenant_id=uuid.uuid4())

    assert snapshot.funnel_ready is True
    assert snapshot.gumroad_ready is True
    assert snapshot.launch_queue_count == 1
    assert snapshot.top_launch_titles == ["Queenswarm Harness Pack"]
    assert "revenue funnel ready" in snapshot.operator_hint.lower()
