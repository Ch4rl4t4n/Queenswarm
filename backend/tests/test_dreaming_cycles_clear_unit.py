"""Unit tests for tenant dream cycle clear API."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.presentation.api.routers.dreaming import clear_dream_cycles


@pytest.mark.asyncio
async def test_clear_dream_cycles_returns_deleted_count() -> None:
    tenant_id = uuid.uuid4()
    db = AsyncMock()
    db.scalars = AsyncMock(
        return_value=MagicMock(
            all=MagicMock(return_value=[uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]),
        ),
    )
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    result = await clear_dream_cycles(
        db=db,  # type: ignore[arg-type]
        principal={"tenant_id": tenant_id, "tenant_role": "owner", "user": MagicMock(id=uuid.uuid4())},
    )

    assert result == {"cleared": 3}
    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_clear_dream_cycles_skips_commit_when_empty() -> None:
    tenant_id = uuid.uuid4()
    db = AsyncMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    result = await clear_dream_cycles(
        db=db,  # type: ignore[arg-type]
        principal={"tenant_id": tenant_id, "tenant_role": "admin", "user": MagicMock(id=uuid.uuid4())},
    )

    assert result == {"cleared": 0}
    db.execute.assert_not_awaited()
    db.commit.assert_not_awaited()
