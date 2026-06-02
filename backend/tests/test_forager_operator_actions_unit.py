"""Unit tests for forager digest → task promotion."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.forager_operator_actions import promote_forager_digest_to_task


@pytest.mark.asyncio
async def test_promote_forager_digest_when_missing_forager() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    out = await promote_forager_digest_to_task(
        session,
        tenant_id=uuid.uuid4(),
        forager_id=uuid.uuid4(),
    )
    assert out["ok"] is False
    assert out["error"] == "forager_not_found"


@pytest.mark.asyncio
async def test_promote_forager_digest_creates_triage_task() -> None:
    tenant_id = uuid.uuid4()
    forager_id = uuid.uuid4()
    forager = MagicMock()
    forager.id = forager_id
    forager.name = "X Intel"
    forager.source_type = "twitter"

    session = AsyncMock()
    session.scalar = AsyncMock(return_value=forager)

    task_row = MagicMock()
    task_row.id = uuid.uuid4()

    with patch(
        "app.application.services.forager_operator_actions._latest_forager_knowledge_excerpt",
        AsyncMock(return_value=(2, "sample intel excerpt")),
    ), patch(
        "app.application.services.forager_operator_actions.create_task_record",
        AsyncMock(return_value=task_row),
    ):
        out = await promote_forager_digest_to_task(
            session,
            tenant_id=tenant_id,
            forager_id=forager_id,
        )

    assert out["ok"] is True
    assert out["task_id"] == str(task_row.id)
