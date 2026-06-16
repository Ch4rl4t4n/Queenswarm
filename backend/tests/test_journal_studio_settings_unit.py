"""Unit tests for Track O TJ4 journal studio settings service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.journal_studio_settings_service import (
    DEFAULT_FIELD_TOGGLES,
    JournalStudioSettingsPatchIn,
    compose_journal_studio_routine_kpi,
    enabled_field_keys,
    merge_field_toggles,
    resolve_review_cron,
    save_journal_studio_settings,
    validate_cron_expr,
)


def test_validate_cron_expr_accepts_daily() -> None:
    assert validate_cron_expr("0 6 * * *") == "0 6 * * *"


def test_validate_cron_expr_rejects_bad_field_count() -> None:
    with pytest.raises(ValueError, match="5 fields"):
        validate_cron_expr("0 6 * *")


def test_resolve_review_cron_preset_daily_0600() -> None:
    assert resolve_review_cron("daily_0600", None) == "0 6 * * *"


def test_resolve_review_cron_custom() -> None:
    assert resolve_review_cron("custom", "15 8 * * 2") == "15 8 * * 2"


def test_merge_field_toggles_keeps_defaults() -> None:
    merged = merge_field_toggles({"screenshot": True, "unknown": True})
    assert merged["screenshot"] is True
    assert merged["thesis"] is DEFAULT_FIELD_TOGGLES["thesis"]
    assert "unknown" not in merged


def test_enabled_field_keys_filters_off() -> None:
    toggles = dict(DEFAULT_FIELD_TOGGLES)
    toggles["emotion"] = False
    keys = enabled_field_keys(toggles)
    assert "emotion" not in keys
    assert "thesis" in keys


@pytest.mark.asyncio
async def test_save_journal_studio_settings_persists_tenant_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {}
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.flush = AsyncMock()
    session.scalar = AsyncMock(return_value=None)

    saved = await save_journal_studio_settings(
        session,
        tenant_id=tenant_id,
        patch=JournalStudioSettingsPatchIn(
            obsidian_subfolder="Vault/Trades",
            review_cron_preset="weekly_monday",
            mistake_tags=["fomo", "no_stop"],
        ),
    )
    assert saved.obsidian_subfolder == "Vault/Trades"
    assert saved.review_cron == "0 7 * * 1"
    assert saved.mistake_tags == ["fomo", "no_stop"]
    assert saved.source == "tenant"
    bucket = tenant.operator_settings["journal_studio"]
    assert bucket["obsidian_subfolder"] == "Vault/Trades"
    assert bucket["review_cron_preset"] == "weekly_monday"


@pytest.mark.asyncio
async def test_save_journal_studio_settings_rejects_bad_subfolder() -> None:
    with pytest.raises(ValueError, match="parent path"):
        JournalStudioSettingsPatchIn(obsidian_subfolder="../escape")


@pytest.mark.asyncio
async def test_compose_journal_studio_routine_kpi_disabled_when_off(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {"journal_studio": {"enabled": False}}
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)

    kpi = await compose_journal_studio_routine_kpi(session, tenant_id=tenant_id)
    assert kpi.enabled is False
    assert kpi.routine_status == "disabled"


@pytest.mark.asyncio
async def test_compose_journal_studio_routine_kpi_missing_routine(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {}
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.scalar = AsyncMock(return_value=None)

    kpi = await compose_journal_studio_routine_kpi(session, tenant_id=tenant_id)
    assert kpi.enabled is True
    assert kpi.routine_status == "missing"
    assert kpi.enabled_field_count == len(enabled_field_keys(DEFAULT_FIELD_TOGGLES))


@pytest.mark.asyncio
async def test_ensure_journal_review_routine_creates_row(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.journal_studio_settings_service import ensure_journal_review_routine

    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {}
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.scalar = AsyncMock(return_value=None)
    session.flush = AsyncMock()

    routine = MagicMock()
    routine.id = uuid.uuid4()
    routine.next_run_at = None

    monkeypatch.setattr(
        "app.application.services.journal_studio_settings_service.create_supervisor_routine",
        AsyncMock(return_value=routine),
    )

    result = await ensure_journal_review_routine(session, tenant_id=tenant_id)
    assert result["status"] == "created"
    assert result["routine_id"] == str(routine.id)

