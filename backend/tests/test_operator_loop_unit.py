"""Operator Loop — action derivation and snapshot assembly."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.operator_loop import (
    OperatorLoopActionOut,
    _derive_actions,
    compose_operator_loop_snapshot,
)


def test_derive_actions_prioritizes_pending_publish() -> None:
    actions = _derive_actions(
        overnight={"available": False},
        publish_pipeline={"pending_publish_count": 3},
        publish_onboarding={"progress_pct": 100},
        trading={"performance": {"is_halted": False}, "config": {"default_mode": "paper"}},
    )
    assert actions[0].id == "approve_publish"
    assert actions[0].priority == "high"


def test_derive_actions_trading_halted() -> None:
    actions = _derive_actions(
        overnight={"available": True, "stalled_signals": 0},
        publish_pipeline={"pending_publish_count": 0},
        publish_onboarding={"progress_pct": 100},
        trading={
            "performance": {"is_halted": True, "halt_reason": "Daily loss limit"},
            "config": {"default_mode": "paper"},
        },
    )
    ids = [a.id for a in actions]
    assert "trading_halted" in ids


@pytest.mark.asyncio
async def test_compose_operator_loop_snapshot_disabled_flag() -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()

    with (
        patch("app.application.services.operator_loop.settings") as mock_settings,
        patch(
            "app.application.services.operator_loop._load_overnight_summary",
            new_callable=AsyncMock,
            return_value={"available": False},
        ),
        patch(
            "app.application.services.operator_loop.compose_morning_hive_brief",
            new_callable=AsyncMock,
            return_value={"markdown": "# Brief"},
        ),
        patch(
            "app.application.services.operator_loop.compose_morning_publish_pipeline_snapshot",
            new_callable=AsyncMock,
        ) as pipeline_mock,
        patch(
            "app.application.services.operator_loop.compose_publish_onboarding_snapshot",
            new_callable=AsyncMock,
        ) as onboard_mock,
        patch(
            "app.application.services.operator_loop.compose_trading_cockpit_snapshot",
            new_callable=AsyncMock,
        ) as trading_mock,
    ):
        mock_settings.operator_loop_enabled = True
        mock_settings.dump_sleep_enabled = True

        pipeline_snap = SimpleNamespace(
            model_dump=lambda: {"pending_publish_count": 1, "approved_publish_count": 0},
        )
        pipeline_mock.return_value = pipeline_snap
        onboard_snap = SimpleNamespace(model_dump=lambda: {"progress_pct": 50})
        onboard_mock.return_value = onboard_snap
        trading_snap = SimpleNamespace(
            model_dump=lambda: {
                "performance": {"total_pnl_usd": 12.5, "is_halted": False},
                "funding": {},
                "config": {"default_mode": "paper"},
            },
        )
        trading_mock.return_value = trading_snap

        snap = await compose_operator_loop_snapshot(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            tenant=None,
        )

    assert snap.enabled is True
    assert snap.publish_pipeline["pending_publish_count"] == 1
    assert any(a.id == "approve_publish" for a in snap.actions)
    assert isinstance(snap.actions[0], OperatorLoopActionOut)
