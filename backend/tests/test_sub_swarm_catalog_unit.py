"""Unit tests for sub-swarm catalog boundary helpers."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.enums import SwarmPurpose
from app.models.swarm import SubSwarm
from app.services.sub_swarm_catalog import (
    SubSwarmCatalogError,
    apply_sub_swarm_updates,
    create_sub_swarm,
    fetch_sub_swarm,
    list_sub_swarms,
    validate_queen_agent,
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


@pytest.mark.asyncio
async def test_create_sub_swarm_flushes_row() -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=object())
    session.add = MagicMock()
    session.flush = AsyncMock()

    row = await create_sub_swarm(
        session,
        name="Scout hive",
        purpose=SwarmPurpose.SCOUT,
        local_memory={"peers": []},
        queen_agent_id=uuid.uuid4(),
        is_active=True,
    )

    assert isinstance(row, SubSwarm)
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_sub_swarm_returns_row() -> None:
    swarm_id = uuid.uuid4()
    row = SubSwarm(name="n", purpose=SwarmPurpose.SCOUT, local_memory={}, is_active=True)
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)

    found = await fetch_sub_swarm(session, swarm_id)

    assert found is row


@pytest.mark.asyncio
async def test_apply_sub_swarm_updates_patches_fields() -> None:
    queen = uuid.uuid4()
    session = AsyncMock()
    session.get = AsyncMock(return_value=object())
    session.flush = AsyncMock()
    row = SubSwarm(name="old", purpose=SwarmPurpose.SCOUT, local_memory={}, is_active=False)

    updated = await apply_sub_swarm_updates(
        session,
        row,
        name="new",
        local_memory={"synced": True},
        queen_agent_id=queen,
        clear_queen=False,
        is_active=True,
        total_pollen=12.5,
    )

    assert updated.name == "new"
    assert updated.local_memory == {"synced": True}
    assert updated.queen_agent_id == queen
    assert updated.is_active is True
    assert updated.total_pollen == 12.5


@pytest.mark.asyncio
async def test_apply_sub_swarm_updates_clear_queen() -> None:
    session = AsyncMock()
    session.flush = AsyncMock()
    row = SubSwarm(name="n", purpose=SwarmPurpose.SCOUT, local_memory={}, is_active=True)
    row.queen_agent_id = uuid.uuid4()

    await apply_sub_swarm_updates(
        session,
        row,
        name=None,
        local_memory=None,
        queen_agent_id=uuid.uuid4(),
        clear_queen=True,
        is_active=None,
        total_pollen=None,
    )

    assert row.queen_agent_id is None
