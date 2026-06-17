"""Unit tests for Marketing Team unified snapshot."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.marketing_team_service import compose_marketing_team_snapshot
from app.core.config import settings


@pytest.mark.asyncio
async def test_marketing_team_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "marketing_team_enabled", False)
    snapshot = await compose_marketing_team_snapshot(
        AsyncMock(),
        dashboard_user_id=uuid.uuid4(),
    )
    assert snapshot.enabled is False


@pytest.mark.asyncio
async def test_marketing_team_compose_with_queue_and_channels(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "marketing_team_enabled", True)
    monkeypatch.setattr(settings, "social_publish_live_enabled", False)
    monkeypatch.setattr(settings, "scheduled_publish_enabled", True)

    deliverable_id = uuid.uuid4()
    row = type(
        "Row",
        (),
        {
            "id": deliverable_id,
            "title": "Launch post",
            "tags": ["publish-pack-verified", "simulate_only", "publish-queue-approved"],
            "structured_json": {
                "channel": "instagram",
                "body": "Hello hive",
                "scheduled_at": "2026-06-20T09:00:00Z",
            },
            "markdown_body": "Hello hive",
            "created_at": datetime.now(tz=UTC),
        },
    )()

    from app.application.services.publish_queue import PublishQueueSnapshotOut

    queue_snapshot = PublishQueueSnapshotOut(
        pending_count=1,
        approved_count=2,
        rejected_count=0,
        count=3,
    )
    social_snapshot = type(
        "SocialSnap",
        (),
        {
            "channels": [
                type(
                    "Ch",
                    (),
                    {
                        "channel": "instagram",
                        "label": "Instagram",
                        "active": True,
                        "live_allowed": False,
                    },
                )(),
            ],
        },
    )()

    with patch(
        "app.application.services.marketing_team_service.list_owned_deliverables",
        AsyncMock(return_value=[row]),
    ):
        with patch(
            "app.application.services.marketing_team_service.build_publish_queue_snapshot",
            AsyncMock(return_value=queue_snapshot),
        ):
            with patch(
                "app.application.services.marketing_team_service.build_social_publish_snapshot",
                AsyncMock(return_value=social_snapshot),
            ):
                snapshot = await compose_marketing_team_snapshot(
                    AsyncMock(),
                    dashboard_user_id=uuid.uuid4(),
                )

    assert snapshot.enabled is True
    assert snapshot.queue_pending_count == 1
    assert snapshot.channels_ready_count == 1
    assert len(snapshot.calendar_entries) == 1
    assert snapshot.calendar_entries[0].status == "scheduled"
    assert snapshot.calendar_entries[0].channel == "instagram"
