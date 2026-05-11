"""Unit tests for agent / sub-swarm catalog services (async session mocks)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.enums import AgentRole, AgentStatus, SwarmPurpose
from app.services.agent_catalog import (
    AgentCatalogError,
    apply_agent_updates,
    create_agent_record,
)
from app.services.sub_swarm_catalog import (
    SubSwarmCatalogError,
    apply_sub_swarm_updates,
    create_sub_swarm,
    validate_queen_agent,
)


@pytest.mark.asyncio
async def test_create_agent_unknown_swarm_raises() -> None:
    swarm_id = uuid.uuid4()
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)

    with pytest.raises(AgentCatalogError):
        await create_agent_record(
            session,
            name="bee-one",
            role=AgentRole.SCRAPER,
            status=AgentStatus.IDLE,
            swarm_id=swarm_id,
            config={},
        )


@pytest.mark.asyncio
async def test_create_agent_with_swarm_increments_member_count() -> None:
    swarm_id = uuid.uuid4()
    swarm = SimpleNamespace(member_count=1)
    session = AsyncMock()
    session.get = AsyncMock(return_value=swarm)
    session.add = lambda row: None
    session.flush = AsyncMock()

    await create_agent_record(
        session,
        name="bee-two",
        role=AgentRole.SCRAPER,
        status=AgentStatus.IDLE,
        swarm_id=swarm_id,
        config={},
    )

    assert swarm.member_count == 2


@pytest.mark.asyncio
async def test_create_agent_record_without_swarm_persists_agent() -> None:
    session = AsyncMock()
    session.add = lambda row: None
    session.flush = AsyncMock()

    agent = await create_agent_record(
        session,
        name="bee-one",
        role=AgentRole.SCRAPER,
        status=AgentStatus.IDLE,
        swarm_id=None,
        config={},
    )

    session.flush.assert_awaited()
    assert agent.name == "bee-one"


@pytest.mark.asyncio
async def test_apply_agent_updates_moves_swarm() -> None:
    old_id, new_id = uuid.uuid4(), uuid.uuid4()
    old_swarm = SimpleNamespace(member_count=2)
    new_swarm = SimpleNamespace(member_count=1)
    agent = SimpleNamespace(
        swarm_id=old_id,
        status=AgentStatus.IDLE,
        config={},
        pollen_points=0.0,
        performance_score=0.0,
    )

    async def fake_get(_model: object, pid: uuid.UUID) -> object | None:
        if pid == old_id:
            return old_swarm
        if pid == new_id:
            return new_swarm
        return None

    session = AsyncMock()
    session.get = AsyncMock(side_effect=fake_get)
    session.flush = AsyncMock()

    await apply_agent_updates(
        session,
        agent,
        status=None,
        swarm_move=True,
        new_swarm_id=new_id,
        config=None,
        performance_score=None,
        pollen_points=None,
    )

    assert agent.swarm_id == new_id
    assert old_swarm.member_count == 1
    assert new_swarm.member_count == 2


@pytest.mark.asyncio
async def test_validate_queen_agent_raises_when_missing() -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    qid = uuid.uuid4()
    with pytest.raises(SubSwarmCatalogError):
        await validate_queen_agent(session, qid)


@pytest.mark.asyncio
async def test_create_sub_swarm_persists_row() -> None:
    session = AsyncMock()
    session.add = lambda row: None
    session.flush = AsyncMock()

    row = await create_sub_swarm(
        session,
        name="colony-a",
        purpose=SwarmPurpose.SCOUT,
        local_memory={"k": 1},
        queen_agent_id=None,
        is_active=True,
    )
    session.flush.assert_awaited()
    assert row.name == "colony-a"


@pytest.mark.asyncio
async def test_apply_sub_swarm_updates_clears_queen() -> None:
    swarm = SimpleNamespace(queen_agent_id=uuid.uuid4())
    session = AsyncMock()
    session.flush = AsyncMock()

    await apply_sub_swarm_updates(
        session,
        swarm,
        name=None,
        local_memory=None,
        queen_agent_id=None,
        clear_queen=True,
        is_active=None,
        total_pollen=None,
    )

    assert swarm.queen_agent_id is None
