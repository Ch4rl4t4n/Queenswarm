"""Unit tests for Hive Oracle v2 heuristics."""

from __future__ import annotations

import pytest

from app.application.services.hive_oracle import (
    derive_heuristic_predictions,
    derive_heuristic_warnings,
)
from app.application.services.operator_control_plane import OperatorLoopActionOut


class _FleetStub:
    def __init__(
        self,
        *,
        immune_status: str = "healthy",
        autopilot: bool = False,
        active: bool = True,
        next_run_at: str | None = None,
    ) -> None:
        self.immune_status = immune_status
        self.autopilot = autopilot
        self.active = active
        self.next_run_at = next_run_at


def test_oracle_trio_unbound_warning() -> None:
    warnings = derive_heuristic_warnings(
        loop_actions=[],
        fleet=[],
        trio={"lanes_bound": 1},
    )
    assert any(w.id == "trio_unbound" for w in warnings)


def test_oracle_publish_backlog_warning() -> None:
    actions = [
        OperatorLoopActionOut(
            id="approve_publish",
            label="Approve 2 publish pack(s)",
            detail="",
            priority="high",
            href="/integrations?tab=studio&section=publish#publish-queue",
        ),
    ]
    warnings = derive_heuristic_warnings(
        loop_actions=actions,
        fleet=[],
        trio={"lanes_bound": 3},
    )
    assert any(w.id == "publish_backlog" for w in warnings)


def test_oracle_quarantine_prediction() -> None:
    fleet = [_FleetStub(immune_status="quarantine", autopilot=True, active=True)]
    warnings = derive_heuristic_warnings(
        loop_actions=[],
        fleet=fleet,
        trio={"lanes_bound": 3},
    )
    predictions = derive_heuristic_predictions(warnings=warnings, fleet=fleet)
    assert any(p.id == "routine_miss_cron" for p in predictions)


@pytest.mark.asyncio
async def test_compose_oracle_disabled() -> None:
    from unittest.mock import patch

    from app.application.services.hive_oracle import compose_hive_oracle_snapshot

    with patch("app.application.services.hive_oracle.settings") as mock_settings:
        mock_settings.hive_oracle_enabled = False
        mock_settings.hive_oracle_llm_synthesis_enabled = False
        snap = await compose_hive_oracle_snapshot(
            None,  # type: ignore[arg-type]
            tenant_id=__import__("uuid").uuid4(),
            dashboard_user_id=__import__("uuid").uuid4(),
            loop_actions=[],
            fleet=[],
            trio={},
        )
    assert snap.enabled is False
