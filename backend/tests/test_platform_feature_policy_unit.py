"""Unit coverage for platform feature policy persistence helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.platform_feature_policy import (
    delete_policy_override,
    load_policy_overrides,
    upsert_policy_overrides,
)


@pytest.mark.asyncio
async def test_load_policy_overrides_maps_rows() -> None:
    row = MagicMock(feature_key="voice", profile_key="prod", enabled=True)
    db = AsyncMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[row])))

    out = await load_policy_overrides(db)

    assert out == {("voice", "prod"): True}


@pytest.mark.asyncio
async def test_upsert_policy_overrides_skips_blank_keys() -> None:
    db = AsyncMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    db.execute = AsyncMock()
    db.flush = AsyncMock()

    merged = await upsert_policy_overrides(
        db,
        updates=[{"feature_key": "", "profile_key": "prod", "enabled": True}],
    )

    assert merged == {}
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_upsert_policy_overrides_executes_insert() -> None:
    db = AsyncMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    db.execute = AsyncMock()
    db.flush = AsyncMock()

    merged = await upsert_policy_overrides(
        db,
        updates=[{"feature_key": "agents", "profile_key": "prod", "enabled": False}],
    )

    assert merged == {("agents", "prod"): False}
    db.execute.assert_awaited_once()
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_policy_override_noop_when_missing() -> None:
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=None)
    db.delete = AsyncMock()
    db.flush = AsyncMock()

    await delete_policy_override(db, feature_key="x", profile_key="y")

    db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_policy_override_removes_row() -> None:
    row = object()
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=row)
    db.delete = AsyncMock()
    db.flush = AsyncMock()

    await delete_policy_override(db, feature_key=" agents ", profile_key=" prod ")

    db.delete.assert_awaited_once_with(row)
    db.flush.assert_awaited_once()
