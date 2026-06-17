"""Unit tests for MK11 catalog wave seed batch."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.catalog_wave_seed_batch_service import run_catalog_wave_seed_batch
from app.application.services.skill_factory_service import SkillFactoryPolicyOut
from app.core.config import settings


@pytest.mark.asyncio
async def test_seed_batch_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """When MK11 flag is off, batch returns disabled message."""

    monkeypatch.setattr(settings, "catalog_wave_seed_batch_enabled", False)

    result = await run_catalog_wave_seed_batch(
        AsyncMock(),
        tenant_id=uuid.uuid4(),
        created_by_subject="operator",
    )
    assert result.ok is False
    assert "disabled" in result.message.lower()


@pytest.mark.asyncio
async def test_seed_batch_no_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no pending seeds, batch is a no-op."""

    monkeypatch.setattr(settings, "catalog_wave_seed_batch_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.catalog_wave_seed_batch_service.pending_vertical_seeds",
        lambda: [],
    )

    result = await run_catalog_wave_seed_batch(
        AsyncMock(),
        tenant_id=uuid.uuid4(),
        created_by_subject="operator",
    )
    assert result.ok is False
    assert result.pending_before == 0


@pytest.mark.asyncio
async def test_seed_batch_researches_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    """Batch researches pending seeds and reports created rows."""

    monkeypatch.setattr(settings, "catalog_wave_seed_batch_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.catalog_wave_seed_batch_service.pending_vertical_seeds",
        lambda: ["newsletter growth loop", "seo pipeline"],
    )

    policy = SkillFactoryPolicyOut(enabled=True, niche_seeds=[], auto_build_enabled=False)
    opp = MagicMock()
    opp.id = uuid.uuid4()
    opp.niche = "newsletter growth loop"
    opp.status = "pending"

    monkeypatch.setattr(
        "app.application.services.catalog_wave_seed_batch_service.get_skill_factory_policy",
        AsyncMock(return_value=policy),
    )
    monkeypatch.setattr(
        "app.application.services.catalog_wave_seed_batch_service.run_skill_market_research",
        AsyncMock(return_value=[opp]),
    )

    result = await run_catalog_wave_seed_batch(
        AsyncMock(),
        tenant_id=uuid.uuid4(),
        created_by_subject="operator",
        limit=2,
    )
    assert result.ok is True
    assert result.researched_count == 1
    assert result.seeds == ["newsletter growth loop", "seo pipeline"]
    assert result.rows[0].status == "pending"


@pytest.mark.asyncio
async def test_seed_batch_auto_build_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auto-build starts when tenant policy has auto_build_enabled."""

    monkeypatch.setattr(settings, "catalog_wave_seed_batch_enabled", True)
    monkeypatch.setattr(settings, "skill_factory_enabled", True)
    monkeypatch.setattr(
        "app.application.services.catalog_wave_seed_batch_service.pending_vertical_seeds",
        lambda: ["cursor skill packs"],
    )

    policy = SkillFactoryPolicyOut(enabled=True, niche_seeds=[], auto_build_enabled=True)
    opp = MagicMock()
    opp.id = uuid.uuid4()
    opp.niche = "cursor skill packs"
    opp.status = "queued"

    monkeypatch.setattr(
        "app.application.services.catalog_wave_seed_batch_service.get_skill_factory_policy",
        AsyncMock(return_value=policy),
    )
    monkeypatch.setattr(
        "app.application.services.catalog_wave_seed_batch_service.run_skill_market_research",
        AsyncMock(return_value=[opp]),
    )
    monkeypatch.setattr(
        "app.application.services.catalog_wave_seed_batch_service.auto_queue_factory_builds",
        AsyncMock(return_value=1),
    )

    result = await run_catalog_wave_seed_batch(
        AsyncMock(),
        tenant_id=uuid.uuid4(),
        created_by_subject="operator",
    )
    assert result.ok is True
    assert result.builds_started == 1
