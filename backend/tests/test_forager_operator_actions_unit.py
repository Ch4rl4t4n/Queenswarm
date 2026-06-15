"""Unit tests for forager digest → task promotion."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.forager_operator_actions import promote_forager_digest_to_task


@pytest.mark.asyncio
async def test_promote_forager_digest_when_missing_forager() -> None:
    session = AsyncMock()
    with patch(
        "app.application.services.forager_operator_actions.promote_forager_goldmine_dispatch",
        AsyncMock(return_value={"ok": False, "error": "forager_not_found"}),
    ):
        out = await promote_forager_digest_to_task(
            session,
            tenant_id=uuid.uuid4(),
            forager_id=uuid.uuid4(),
        )
    assert out["ok"] is False
    assert out["error"] == "forager_not_found"


@pytest.mark.asyncio
async def test_promote_forager_digest_delegates_to_goldmine_dispatch() -> None:
    tenant_id = uuid.uuid4()
    forager_id = uuid.uuid4()
    task_id = uuid.uuid4()
    session = AsyncMock()

    with patch(
        "app.application.services.forager_operator_actions.promote_forager_goldmine_dispatch",
        AsyncMock(
            return_value={
                "ok": True,
                "task_id": str(task_id),
                "forager_id": str(forager_id),
                "title": "Forager digest · X Intel",
                "mode": "digest",
                "new_item_count": 2,
                "skill_slugs": ["competitor-scrape-analyze", "context"],
            },
        ),
    ) as dispatch_mock:
        out = await promote_forager_digest_to_task(
            session,
            tenant_id=tenant_id,
            forager_id=forager_id,
            mode="alert",
            include_skill_bundle=True,
        )

    dispatch_mock.assert_awaited_once()
    assert out["ok"] is True
    assert out["task_id"] == str(task_id)
    assert out["skill_slugs"] == ["competitor-scrape-analyze", "context"]
