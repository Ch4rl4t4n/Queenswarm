from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.billing import assert_agent_hard_limit, assert_supervisor_session_hard_limit, assert_swarm_hard_limit


@pytest.mark.asyncio
async def test_assert_agent_hard_limit_when_internal_tenant_then_skips() -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    db.get = AsyncMock(return_value=SimpleNamespace(platform_mode="internal"))
    await assert_agent_hard_limit(db, tenant_id=tenant_id)
    db.scalar.assert_not_called()


@pytest.mark.asyncio
async def test_assert_agent_hard_limit_when_commercial_free_at_cap_then_raises() -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    db.get = AsyncMock(return_value=SimpleNamespace(platform_mode="commercial"))
    subscription = SimpleNamespace(tier="free", limits_override={}, feature_overrides={})
    db.scalar = AsyncMock(side_effect=[subscription, 2])
    with pytest.raises(ValueError, match="billing_limit_exceeded:max_agents"):
        await assert_agent_hard_limit(db, tenant_id=tenant_id)


@pytest.mark.asyncio
async def test_assert_supervisor_session_hard_limit_when_internal_tenant_then_skips() -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    db.get = AsyncMock(return_value=SimpleNamespace(platform_mode="internal"))
    await assert_supervisor_session_hard_limit(db, tenant_id=tenant_id)
    db.scalar.assert_not_called()


@pytest.mark.asyncio
async def test_assert_supervisor_session_hard_limit_when_commercial_at_cap_then_raises() -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    db.get = AsyncMock(return_value=SimpleNamespace(platform_mode="commercial"))
    subscription = SimpleNamespace(tier="free", limits_override={}, feature_overrides={})
    # ensure_tenant_subscription + usage aggregation scalars
    db.scalar = AsyncMock(
        side_effect=[
            subscription,
            0,  # token_total
            0.0,  # total_spend
            80,  # supervisor session count
            0.0,  # supervisor_runtime_seconds
            0,  # external_calls
            0,  # knowledge_chars
            0,  # output_chars
        ],
    )
    with pytest.raises(ValueError, match="billing_limit_exceeded:monthly_supervisor_sessions"):
        await assert_supervisor_session_hard_limit(db, tenant_id=tenant_id)


@pytest.mark.asyncio
async def test_assert_swarm_hard_limit_when_commercial_free_at_cap_then_raises() -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    db.get = AsyncMock(return_value=SimpleNamespace(platform_mode="commercial"))
    subscription = SimpleNamespace(tier="free", limits_override={}, feature_overrides={})
    db.scalar = AsyncMock(side_effect=[subscription, 1])
    with pytest.raises(ValueError, match="billing_limit_exceeded:max_swarms"):
        await assert_swarm_hard_limit(db, tenant_id=tenant_id)
