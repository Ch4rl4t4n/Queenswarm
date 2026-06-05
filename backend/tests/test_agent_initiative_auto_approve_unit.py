"""Unit tests for agent initiative auto-approve drain."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.agent_initiative_auto_approve import (
    auto_approve_pending_agent_initiative_suggestions,
    maybe_auto_approve_agent_initiative_pending,
)


@pytest.mark.asyncio
async def test_auto_approve_pending_drains_batches_until_empty() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    bulk = AsyncMock(side_effect=[{"processed": 2, "skipped": 0, "errors": []}, {"processed": 0, "skipped": 0, "errors": []}])

    with patch(
        "app.application.services.agent_initiative_auto_approve.bulk_review_agent_suggestions",
        bulk,
    ):
        result = await auto_approve_pending_agent_initiative_suggestions(
            session,
            tenant_id=tenant_id,
            reviewer_subject="test-reviewer",
            include_high_risk=False,
            batch_limit=10,
            max_rounds=3,
        )

    assert result["processed"] == 2
    assert bulk.await_count == 2


@pytest.mark.asyncio
async def test_maybe_auto_approve_when_tenant_missing_then_noop() -> None:
    result = await maybe_auto_approve_agent_initiative_pending(AsyncMock(), tenant=None)
    assert result["drained"] is False


@pytest.mark.asyncio
async def test_maybe_auto_approve_when_policy_off_then_noop() -> None:
    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    result = await maybe_auto_approve_agent_initiative_pending(AsyncMock(), tenant=tenant)
    assert result["drained"] is False
    assert result["processed"] == 0


@pytest.mark.asyncio
async def test_maybe_auto_approve_when_enabled_then_flushes() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        operator_settings={"agent_initiative": {"auto_approve_enabled": True, "include_high_risk": False}},
    )

    with patch(
        "app.application.services.agent_initiative_auto_approve.auto_approve_pending_agent_initiative_suggestions",
        AsyncMock(return_value={"processed": 1, "skipped": 0, "errors": []}),
    ):
        result = await maybe_auto_approve_agent_initiative_pending(session, tenant=tenant)

    assert result["drained"] is True
    session.flush.assert_awaited_once()
