"""Unit tests for skill picker usage service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.skill_picker_usage import (
    get_skill_picker_usage_map,
    increment_skill_picker_usage,
    sync_skill_picker_usage_counts,
)


@pytest.mark.asyncio
async def test_get_skill_picker_usage_map_returns_lowercase_keys() -> None:
    tenant_id = uuid.uuid4()
    row_a = SimpleNamespace(skill_slug="Context", usage_count=3)
    row_b = SimpleNamespace(skill_slug="DECIDE", usage_count=0)

    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[row_a, row_b])))

    result = await get_skill_picker_usage_map(session, tenant_id=tenant_id)

    assert result == {"context": 3}


@pytest.mark.asyncio
async def test_increment_skill_picker_usage_creates_new_row() -> None:
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=None)))
    session.add = MagicMock()

    await increment_skill_picker_usage(session, tenant_id=tenant_id, slugs=["context", "CONTEXT"])

    session.add.assert_called_once()
    added = session.add.call_args.args[0]
    assert added.skill_slug == "context"
    assert added.usage_count == 1
    assert added.tenant_id == tenant_id


@pytest.mark.asyncio
async def test_increment_skill_picker_usage_updates_existing_row() -> None:
    tenant_id = uuid.uuid4()
    existing = SimpleNamespace(skill_slug="decide", usage_count=2, last_used_at=datetime(2020, 1, 1, tzinfo=UTC))

    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=existing)))

    await increment_skill_picker_usage(session, tenant_id=tenant_id, slugs=["decide"])

    assert existing.usage_count == 3
    assert existing.last_used_at.year >= 2020


@pytest.mark.asyncio
async def test_sync_skill_picker_usage_counts_adds_delta() -> None:
    tenant_id = uuid.uuid4()
    existing = SimpleNamespace(skill_slug="lead-gen-lane", usage_count=1, last_used_at=datetime(2020, 1, 1, tzinfo=UTC))

    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=existing)))
    session.add = MagicMock()

    await sync_skill_picker_usage_counts(
        session,
        tenant_id=tenant_id,
        counts={"lead-gen-lane": 4, "": 0, "invalid-negative": -1},
    )

    assert existing.usage_count == 5
