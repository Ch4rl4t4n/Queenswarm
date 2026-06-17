"""Unit tests for POS-I2 Jarvis proactive nudge service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.jarvis_advisor_service import MissionJarvisStepOut
from app.application.services.jarvis_proactive_nudge_service import push_jarvis_proactive_nudge


@pytest.mark.asyncio
async def test_push_jarvis_nudge_disabled() -> None:
    session = AsyncMock()
    step = MissionJarvisStepOut(
        order=1,
        title="Review digest",
        detail="Two digests waiting.",
        href="/cockpit#four-lanes",
        kind="verify",
    )
    with patch("app.application.services.jarvis_proactive_nudge_service.settings") as mock_settings:
        mock_settings.jarvis_proactive_nudge_enabled = False
        pushed = await push_jarvis_proactive_nudge(session, tenant_id=uuid.uuid4(), step=step)
    assert pushed is False


@pytest.mark.asyncio
async def test_push_jarvis_nudge_dedup_blocks_repeat(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    step = MissionJarvisStepOut(
        order=1,
        title="Fill Brain Pack",
        detail="SOUL empty.",
        href="/knowledge?tab=memory#brain-pack",
        kind="setup",
    )

    with patch("app.application.services.jarvis_proactive_nudge_service.settings") as mock_settings:
        mock_settings.jarvis_proactive_nudge_enabled = True
        mock_settings.jarvis_proactive_nudge_web_push_enabled = False
        with patch(
            "app.application.services.jarvis_proactive_nudge_service._dedup_claim",
            AsyncMock(side_effect=[True, False]),
        ):
            with patch(
                "app.application.services.jarvis_proactive_nudge_service.push_mission_feed_event",
                AsyncMock(),
            ) as push_mock:
                first = await push_jarvis_proactive_nudge(session, tenant_id=tenant_id, step=step)
                second = await push_jarvis_proactive_nudge(session, tenant_id=tenant_id, step=step)

    assert first is True
    assert second is False
    push_mock.assert_awaited_once()
