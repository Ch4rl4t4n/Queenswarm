"""Unit tests for BA5 Proactive Pulse."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.proactive_pulse import compose_proactive_pulse


@pytest.mark.asyncio
async def test_compose_proactive_pulse_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.proactive_pulse.settings") as mock_settings:
        mock_settings.proactive_pulse_enabled = False
        mock_settings.operator_control_plane_enabled = True
        out = await compose_proactive_pulse(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            tenant=MagicMock(),
        )
    assert out.enabled is False


@pytest.mark.asyncio
async def test_compose_proactive_pulse_surfaces_inbox_changes() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=0)
    tenant = SimpleNamespace(operator_settings={})
    inbox = SimpleNamespace(
        counts=SimpleNamespace(total=2),
        items=[],
    )
    loop = SimpleNamespace(
        publish_pipeline={"pending_publish_count": 0},
        trading={},
        overnight={"available": False},
    )

    with (
        patch("app.application.services.proactive_pulse.settings") as mock_settings,
        patch(
            "app.application.services.proactive_pulse.compose_operator_loop_lite",
            new=AsyncMock(return_value=loop),
        ),
        patch(
            "app.application.services.proactive_pulse.compose_approval_inbox_snapshot",
            new=AsyncMock(return_value=inbox),
        ),
        patch(
            "app.application.services.proactive_pulse.compose_background_business_team",
            new=AsyncMock(
                return_value=SimpleNamespace(enabled=False, bees=[]),
            ),
        ),
    ):
        mock_settings.proactive_pulse_enabled = True
        mock_settings.operator_control_plane_enabled = True
        out = await compose_proactive_pulse(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            tenant=tenant,
            phase="midday",
        )

    assert out.enabled is True
    assert any(change.id == "approval_inbox" for change in out.changes)
