"""Unit tests for POS-I3 Jarvis weekly reflection strip."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.jarvis_weekly_reflection_service import (
    compose_jarvis_weekly_reflection_strip,
)


def _scalar_side_effect(*values: object):
    """Return async scalars in sequence."""

    queue = list(values)

    async def _scalar(_stmt):
        if not queue:
            return None
        return queue.pop(0)

    return _scalar


@pytest.mark.asyncio
async def test_weekly_reflection_disabled_when_flag_off() -> None:
    session = AsyncMock()
    with patch(
        "app.application.services.jarvis_weekly_reflection_service.settings",
    ) as mock_settings:
        mock_settings.jarvis_weekly_reflection_enabled = False
        strip = await compose_jarvis_weekly_reflection_strip(
            session,
            tenant_id=uuid.uuid4(),
            first_run_complete=True,
        )
    assert strip.enabled is False


@pytest.mark.asyncio
async def test_weekly_reflection_disabled_before_first_run() -> None:
    session = AsyncMock()
    with patch(
        "app.application.services.jarvis_weekly_reflection_service.settings",
    ) as mock_settings:
        mock_settings.jarvis_weekly_reflection_enabled = True
        strip = await compose_jarvis_weekly_reflection_strip(
            session,
            tenant_id=uuid.uuid4(),
            first_run_complete=False,
        )
    assert strip.enabled is False


@pytest.mark.asyncio
async def test_weekly_reflection_empty_when_no_activity() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=_scalar_side_effect(0, 0))
    session.scalars = AsyncMock(return_value=MagicMock(all=lambda: []))
    tenant = MagicMock()
    tenant.operator_settings = {"episodic_captures": {"captures": []}}
    session.get = AsyncMock(return_value=tenant)

    with patch(
        "app.application.services.jarvis_weekly_reflection_service.settings",
    ) as mock_settings:
        mock_settings.jarvis_weekly_reflection_enabled = True
        strip = await compose_jarvis_weekly_reflection_strip(
            session,
            tenant_id=uuid.uuid4(),
            first_run_complete=True,
        )

    assert strip.enabled is False
    assert "No Ballroom" in strip.message


@pytest.mark.asyncio
async def test_weekly_reflection_surfaces_ballroom_and_episodic() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=_scalar_side_effect(2, 1, None))
    now = datetime.now(tz=UTC)
    recipe = MagicMock()
    recipe.name = "Ballroom post-mortem abc"
    recipe.description = "Highlights: shipped verify loop. Risks: LLM latency."
    recipe.workflow_template = {"kind": "ballroom_post_mortem"}
    session.scalars = AsyncMock(return_value=MagicMock(all=lambda: [recipe]))
    tenant = MagicMock()
    tenant.operator_settings = {
        "episodic_captures": {
            "captures": [
                {
                    "session_id": str(uuid.uuid4()),
                    "goal": "Research brief",
                    "summary": "Verified weak-signal digest with simulate-first gate.",
                    "captured_at": now.isoformat(),
                    "href": "/agents#sessions",
                },
            ],
        },
    }
    session.get = AsyncMock(return_value=tenant)

    with patch(
        "app.application.services.jarvis_weekly_reflection_service.settings",
    ) as mock_settings:
        mock_settings.jarvis_weekly_reflection_enabled = True
        strip = await compose_jarvis_weekly_reflection_strip(
            session,
            tenant_id=uuid.uuid4(),
            first_run_complete=True,
        )

    assert strip.enabled is True
    assert strip.ballroom_post_mortems_7d == 1
    assert strip.episodic_captures_7d == 1
    assert strip.sessions_completed_7d == 2
    assert len(strip.highlights) >= 2
    assert strip.highlights[0].source == "ballroom"
    assert "Hive Mind" in strip.message


@pytest.mark.asyncio
async def test_weekly_reflection_ignores_stale_episodic_captures() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=_scalar_side_effect(1, 0))
    session.scalars = AsyncMock(return_value=MagicMock(all=lambda: []))
    stale = datetime.now(tz=UTC) - timedelta(days=14)
    tenant = MagicMock()
    tenant.operator_settings = {
        "episodic_captures": {
            "captures": [
                {
                    "session_id": str(uuid.uuid4()),
                    "goal": "Old session",
                    "summary": "Should not appear.",
                    "captured_at": stale.isoformat(),
                },
            ],
        },
    }
    session.get = AsyncMock(return_value=tenant)

    with patch(
        "app.application.services.jarvis_weekly_reflection_service.settings",
    ) as mock_settings:
        mock_settings.jarvis_weekly_reflection_enabled = True
        strip = await compose_jarvis_weekly_reflection_strip(
            session,
            tenant_id=uuid.uuid4(),
            first_run_complete=True,
        )

    assert strip.enabled is True
    assert strip.episodic_captures_7d == 0
    assert all(item.source != "episodic" for item in strip.highlights)
