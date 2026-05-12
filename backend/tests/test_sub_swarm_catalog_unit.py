"""Unit tests for sub-swarm catalog boundary helpers."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.enums import SwarmPurpose
from app.services.sub_swarm_catalog import (
    SubSwarmCatalogError,
    validate_queen_agent,
    list_sub_swarms,
)


@pytest.mark.asyncio
async def test_validate_queen_agent_skips_none() -> None:
    session = AsyncMock(get=AsyncMock())
    await validate_queen_agent(session, None)
    session.get.assert_not_called()


@pytest.mark.asyncio
async def test_validate_queen_agent_raises_when_missing() -> None:
    bee = uuid.uuid4()
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)

    with pytest.raises(SubSwarmCatalogError, match=str(bee)):
        await validate_queen_agent(session, bee)

    session.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_queen_agent_passes_when_row_exists() -> None:
    bee = uuid.uuid4()
    session = AsyncMock()
    session.get = AsyncMock(return_value=object())

    await validate_queen_agent(session, bee)


@pytest.mark.asyncio
async def test_list_sub_swarms_returns_scalar_rows() -> None:
    swarm = MagicMock(name="dummy_swarm")

    scalar_result = MagicMock()
    scalar_result.all.return_value = [swarm]

    executed = MagicMock()
    executed.scalars.return_value = scalar_result

    session = AsyncMock()
    session.execute = AsyncMock(return_value=executed)

    rows = await list_sub_swarms(session, purpose=SwarmPurpose.SCOUT, is_active=True, limit=5)

    assert rows == [swarm]
