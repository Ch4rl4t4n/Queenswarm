"""Unit tests for TJ7 journal studio presets."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.journal_studio_preset_catalog import (
    normalize_studio_preset,
    preset_field_toggles,
    preset_meta,
)
from app.application.services.journal_studio_settings_service import (
    JournalStudioSettingsPatchIn,
    get_journal_studio_settings,
    save_journal_studio_settings,
)


def test_normalize_studio_preset_defaults_trading() -> None:
    assert normalize_studio_preset(None) == "trading"
    assert normalize_studio_preset("business_brain") == "business_brain"


def test_business_brain_preset_disables_trade_fields() -> None:
    toggles = preset_field_toggles("business_brain")
    assert toggles["thesis"] is True
    assert toggles["entry_price"] is False
    assert toggles["pnl"] is False


def test_preset_meta_includes_np4_and_wiki_links() -> None:
    meta = preset_meta("business_brain")
    assert meta["module_title"] == "Business Brain"
    assert "investment-product-brief" in meta["brief_dispatch_href"]
    assert meta["wiki_capture_href"].startswith("/knowledge")


@pytest.mark.asyncio
async def test_save_studio_preset_applies_business_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "journal_studio_business_brain_preset_enabled", True)

    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.id = tenant_id
    tenant.operator_settings = {}

    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.flush = AsyncMock()

    saved = await save_journal_studio_settings(
        session,
        tenant_id=tenant_id,
        patch=JournalStudioSettingsPatchIn(studio_preset="business_brain"),
    )
    assert saved.studio_preset == "business_brain"
    assert saved.obsidian_subfolder == "Business/Brain"
    assert "scope_creep" in saved.mistake_tags
    assert saved.field_toggles["entry_price"] is False


@pytest.mark.asyncio
async def test_get_settings_includes_preset_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {
        "journal_studio": {
            "studio_preset": "business_brain",
            "mistake_tags": ["scope_creep"],
            "field_toggles": {"thesis": True, "entry_price": False},
        },
    }
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)

    out = await get_journal_studio_settings(session, tenant_id=tenant_id)
    assert out.studio_preset == "business_brain"
    assert out.field_labels["thesis"] == "Hypothesis"
    assert out.pattern_tags_label == "Pattern tags"
