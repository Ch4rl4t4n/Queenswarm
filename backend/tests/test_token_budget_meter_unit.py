"""Unit tests for MEM4 token budget meter service."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.token_budget_meter_service import (
    compose_token_budget_meter,
    derive_token_budget_meter,
    estimate_tokens,
)
from app.domain.memory.curated import CuratedFileKind


def _bundle(*, mission: str = "Mission", instructions: str = "Be concise") -> dict[CuratedFileKind, str]:
    return {
        CuratedFileKind.MISSION: mission,
        CuratedFileKind.IDEAL_STATE: "Ideal",
        CuratedFileKind.SOUL: "Soul",
        CuratedFileKind.SKILLS_HIERARCHY: "Skills",
        CuratedFileKind.INSTRUCTIONS: instructions,
        CuratedFileKind.BRAND: "",
    }


def test_estimate_tokens_uses_four_chars_per_token() -> None:
    assert estimate_tokens(400) == 100
    assert estimate_tokens(0) == 0


def test_derive_token_budget_meter_selective_defaults() -> None:
    meter = derive_token_budget_meter(
        bundle=_bundle(),
        recall_mode="selective",
        tenant_token_budget=0,
    )

    assert meter.enabled is True
    assert meter.prompt_prefix_chars > 0
    assert meter.estimated_tokens == estimate_tokens(meter.prompt_prefix_chars)
    assert meter.recall_mode == "selective"
    assert meter.recall_char_budget > 0
    assert meter.max_prompt_chars > 0
    assert len(meter.layers) == 4
    assert meter.layers[0].layer_id == "soul"
    assert meter.status in {"ok", "warn", "critical"}


def test_derive_token_budget_meter_critical_when_brain_pack_huge(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "hive_mind_max_prompt_chars", 500)
    huge = "x" * 2000
    meter = derive_token_budget_meter(
        bundle=_bundle(mission=huge, instructions=huge),
        recall_mode="selective",
        tenant_token_budget=0,
    )

    assert meter.status == "critical"
    assert "Trim SOUL" in meter.operator_hint or "tokens" in meter.operator_hint


def test_derive_token_budget_meter_full_recall_uses_max_prompt_cap() -> None:
    meter = derive_token_budget_meter(
        bundle=_bundle(),
        recall_mode="full",
        tenant_token_budget=0,
    )

    assert meter.recall_mode == "full"
    assert meter.recall_char_budget == meter.max_prompt_chars
    assert meter.recall_usage_pct == 100


@pytest.mark.asyncio
async def test_compose_token_budget_meter_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "token_budget_meter_enabled", False)
    db = AsyncMock()

    result = await compose_token_budget_meter(db, tenant_id=uuid.uuid4())

    assert result.enabled is False


@pytest.mark.asyncio
async def test_compose_token_budget_meter_loads_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.curated_memory_service import CuratedMemoryService

    tenant_id = uuid.uuid4()
    db = AsyncMock()
    bundle = _bundle()

    async def fake_get_bundle(_self: CuratedMemoryService, _tenant_id: uuid.UUID) -> dict[CuratedFileKind, str]:
        return bundle

    monkeypatch.setattr(CuratedMemoryService, "get_bundle", fake_get_bundle)
    monkeypatch.setattr(
        "app.application.services.token_budget_meter_service.load_recall_config",
        AsyncMock(return_value={"recall_mode": "selective", "token_budget_chars": 1200}),
    )

    result = await compose_token_budget_meter(db, tenant_id=tenant_id)

    assert result.enabled is True
    assert result.recall_char_budget == 1200
