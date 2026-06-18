"""Unit tests for POS-J3 email draft outer loop."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.email_draft_outer_loop_service import (
    EmailDraftReviewIn,
    compose_email_draft_outer_loop_snapshot,
    review_email_draft,
    run_email_draft_outer_loop_for_tenant,
)
from app.core.config import settings


@pytest.mark.asyncio
async def test_compose_email_draft_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "email_draft_outer_loop_enabled", False)
    snap = await compose_email_draft_outer_loop_snapshot(
        AsyncMock(),
        tenant_id=uuid.uuid4(),
        dashboard_user_id=uuid.uuid4(),
    )
    assert snap.enabled is False


@pytest.mark.asyncio
async def test_run_email_draft_outer_loop_no_connector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "email_draft_outer_loop_enabled", True)

    with patch(
        "app.application.services.email_draft_outer_loop_service.DynamicConnectorService",
    ) as mock_svc:
        instance = mock_svc.return_value
        instance.fetch_by_slug = AsyncMock(return_value=None)
        created = await run_email_draft_outer_loop_for_tenant(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
        )
    assert created == 0


@pytest.mark.asyncio
async def test_review_email_draft_reject(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "email_draft_outer_loop_enabled", True)
    tenant_id = uuid.uuid4()
    draft_id = "email-draft-1"

    tenant = MagicMock()
    tenant.operator_settings = {
        "email_draft_outer_loop": {
            "drafts": [
                {
                    "id": draft_id,
                    "status": "pending",
                    "created_at": datetime.now(tz=UTC).isoformat(),
                },
            ],
        },
    }

    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.flush = AsyncMock()

    result = await review_email_draft(
        session,
        tenant_id=tenant_id,
        draft_id=draft_id,
        body=EmailDraftReviewIn(decision="reject", note="not now"),
    )
    assert result.status == "rejected"
