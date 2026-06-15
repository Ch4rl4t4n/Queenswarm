"""Unit tests for NP3 Brand Context Pack."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.application.services.brand_context_pack_service import (
    compose_brand_context_pack_snapshot,
    is_brand_pack_ready,
    load_marketing_brand_injection,
    parse_brand_sections,
    render_marketing_brand_injection,
    should_inject_brand_for_session,
)
from app.application.services.brain_pack_starters import BRAIN_PACK_STARTERS
from app.domain.memory.curated import CuratedFileKind


def _sample_brand_md() -> str:
    return BRAIN_PACK_STARTERS[CuratedFileKind.BRAND]


def test_parse_brand_sections_finds_voice_and_forbidden() -> None:
    sections = parse_brand_sections(_sample_brand_md())
    assert "voice" in sections
    assert "forbidden" in sections
    assert "examples" in sections
    assert len(sections["voice"]) >= 20


def test_is_brand_pack_ready_with_starter_template() -> None:
    assert is_brand_pack_ready(_sample_brand_md()) is True


def test_is_brand_pack_ready_rejects_empty() -> None:
    assert is_brand_pack_ready("") is False


def test_render_marketing_brand_injection_caps_length(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "brand_context_max_injection_chars", 80)
    block = render_marketing_brand_injection("x" * 200)
    assert "=== BRAND CONTEXT PACK" in block
    assert "=== END BRAND CONTEXT ===" in block
    assert "…" in block


@pytest.mark.asyncio
async def test_compose_brand_context_pack_snapshot_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "brand_context_pack_enabled", True)
    tenant_id = uuid.uuid4()

    async def _fake_get_bundle(self, _tenant_id: uuid.UUID) -> dict[CuratedFileKind, str]:  # noqa: ANN001
        return {CuratedFileKind.BRAND: _sample_brand_md()}

    monkeypatch.setattr(
        "app.application.services.brand_context_pack_service.CuratedMemoryService.get_bundle",
        _fake_get_bundle,
    )
    snap = await compose_brand_context_pack_snapshot(AsyncMock(), tenant_id=tenant_id)

    assert snap.enabled is True
    assert snap.ready is True
    assert snap.char_count > 0
    assert any(row.id == "voice" and row.filled for row in snap.sections)


@pytest.mark.asyncio
async def test_should_inject_brand_for_marketing_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config
    from types import SimpleNamespace

    monkeypatch.setattr(config.settings, "brand_context_pack_enabled", True)
    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        operator_settings={"harness_profiles": {"active_profile_id": "marketing"}},
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=tenant)

    assert await should_inject_brand_for_session(
        db,
        tenant_id=tenant_id,
        context_seed=None,
    )


@pytest.mark.asyncio
async def test_load_marketing_brand_injection_skips_trading_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config
    from types import SimpleNamespace

    monkeypatch.setattr(config.settings, "brand_context_pack_enabled", True)
    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        operator_settings={"harness_profiles": {"active_profile_id": "trading"}},
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=tenant)

    block = await load_marketing_brand_injection(db, tenant_id=tenant_id, context_seed=None)
    assert block == ""
