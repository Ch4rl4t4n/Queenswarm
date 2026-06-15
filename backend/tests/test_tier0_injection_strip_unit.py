"""Unit tests for MEM3 tier-0 injection strip service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.tier0_injection_strip_service import (
    compose_tier0_injection_strip,
    derive_tier0_injection_strip,
)
from app.domain.memory.curated import CuratedFileKind


def _bundle(*, mission: str = "Ship Queenswarm", instructions: str = "Be concise") -> dict[CuratedFileKind, str]:
    return {
        CuratedFileKind.MISSION: mission,
        CuratedFileKind.IDEAL_STATE: "Ideal daily ops",
        CuratedFileKind.SOUL: "Verify-first tone",
        CuratedFileKind.SKILLS_HIERARCHY: "execution-studio first",
        CuratedFileKind.INSTRUCTIONS: instructions,
        CuratedFileKind.BRAND: "",
    }


def test_derive_tier0_injection_strip_orders_tiers() -> None:
    strip = derive_tier0_injection_strip(
        bundle=_bundle(),
        wiki_prompt_block="=== WIKI LAYER (hot tier) ===\n## Notes\nHello\n=== END WIKI LAYER ===",
        recall_mode="selective",
        tenant_token_budget=0,
        wiki_enabled=True,
        chroma_enabled=True,
    )

    assert strip.visible is True
    assert len(strip.tiers) == 3
    assert strip.tiers[0].tier_id == "tier0"
    assert strip.tiers[0].active is True
    assert strip.tiers[0].char_count > 0
    assert len(strip.tiers[0].sections) == 5
    assert strip.tiers[1].tier_id == "tier1"
    assert strip.tiers[1].active is True
    assert strip.tiers[2].tier_id == "tier2"
    assert strip.tiers[2].active is True
    assert strip.deep_recall_budget_chars > 0


def test_derive_tier0_injection_strip_empty_brain_pack_hint() -> None:
    empty = {
        CuratedFileKind.MISSION: "",
        CuratedFileKind.IDEAL_STATE: "",
        CuratedFileKind.SOUL: "",
        CuratedFileKind.SKILLS_HIERARCHY: "",
        CuratedFileKind.INSTRUCTIONS: "",
        CuratedFileKind.BRAND: "",
    }
    strip = derive_tier0_injection_strip(
        bundle=empty,
        wiki_prompt_block="",
        recall_mode="selective",
        tenant_token_budget=0,
        wiki_enabled=True,
        chroma_enabled=False,
    )

    assert strip.tiers[0].active is False
    assert "Seed Brain Pack" in strip.operator_hint
    assert strip.tiers[2].active is False


def test_derive_tier0_injection_strip_full_recall_budget() -> None:
    strip = derive_tier0_injection_strip(
        bundle=_bundle(),
        wiki_prompt_block="",
        recall_mode="full",
        tenant_token_budget=0,
        wiki_enabled=False,
        chroma_enabled=True,
    )

    assert strip.recall_mode == "full"
    assert strip.deep_recall_budget_chars == strip.tiers[2].char_count


@pytest.mark.asyncio
async def test_compose_tier0_injection_strip_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "tier0_injection_strip_enabled", False)
    db = AsyncMock()

    result = await compose_tier0_injection_strip(db, tenant_id=uuid.uuid4())

    assert result.enabled is False
    assert result.visible is False


@pytest.mark.asyncio
async def test_compose_tier0_injection_strip_loads_bundle_and_wiki(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.curated_memory_service import CuratedMemoryService
    from app.core import config

    tenant_id = uuid.uuid4()
    db = AsyncMock()
    bundle = _bundle()

    async def fake_get_bundle(_self: CuratedMemoryService, _tenant_id: uuid.UUID) -> dict[CuratedFileKind, str]:
        return bundle

    monkeypatch.setattr(CuratedMemoryService, "get_bundle", fake_get_bundle)
    monkeypatch.setattr(config.settings, "wiki_layer_enabled", True)
    monkeypatch.setattr(
        "app.application.services.tier0_injection_strip_service.load_recall_config",
        AsyncMock(return_value={"recall_mode": "selective", "token_budget_chars": 0}),
    )

    with patch(
        "app.application.services.wiki_layer_service.WikiLayerService.render_wiki_prompt_block",
        AsyncMock(return_value="=== WIKI LAYER (hot tier) ===\n## Ops\nDaily\n=== END WIKI LAYER ==="),
    ):
        result = await compose_tier0_injection_strip(db, tenant_id=tenant_id)

    assert result.enabled is True
    assert result.tiers[1].active is True
