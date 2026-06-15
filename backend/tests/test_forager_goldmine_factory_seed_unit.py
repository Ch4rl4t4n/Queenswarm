"""Unit tests for DG8 goldmine → Skill Factory seed."""

from __future__ import annotations

import uuid

import pytest

from app.application.services.forager_goldmine_factory_seed_service import (
    compose_goldmine_factory_seed_snapshot,
    derive_goldmine_factory_niche,
    preview_goldmine_factory_seed,
)
from app.core import config
from app.infrastructure.persistence.models.forager import ForagerORM


def test_derive_goldmine_factory_niche_from_intent() -> None:
    forager = ForagerORM(
        tenant_id=uuid.uuid4(),
        name="EU Python Jobs",
        description="",
        source_type="rss",
        source_config={},
        filter_config={"intent": "Track senior Python remote jobs in EU", "monitor_niche": "jobs"},
        prompt_template="",
        tools=[],
    )
    niche = derive_goldmine_factory_niche(forager)
    assert niche == "Track senior Python remote jobs in EU"


def test_derive_goldmine_factory_niche_from_monitor_niche() -> None:
    forager = ForagerORM(
        tenant_id=uuid.uuid4(),
        name="Price watch",
        description="",
        source_type="rss",
        source_config={},
        filter_config={"monitor_niche": "prices"},
        prompt_template="",
        tools=[],
    )
    niche = derive_goldmine_factory_niche(forager)
    assert "Prices" in niche
    assert "skill pack" in niche.lower()


def test_compose_goldmine_factory_seed_snapshot_enabled() -> None:
    snap = compose_goldmine_factory_seed_snapshot()
    assert snap.enabled is True


@pytest.mark.asyncio
async def test_preview_goldmine_factory_seed_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "forager_goldmine_factory_seed_enabled", False)

    class _Session:
        pass

    with pytest.raises(ValueError, match="goldmine_factory_seed_disabled"):
        await preview_goldmine_factory_seed(
            _Session(),  # type: ignore[arg-type]
            tenant_id=uuid.uuid4(),
            forager_id=uuid.uuid4(),
        )
