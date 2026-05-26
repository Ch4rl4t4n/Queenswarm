"""Unit tests for Control Plane planned modules."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.ambient_forager import compose_ambient_forager_snapshot
from app.application.services.context_teleport import compose_context_teleport_snapshot
from app.application.services.evolutionary_recipes import compose_evolutionary_recipes_snapshot
from app.application.services.parallel_hive_view import compose_parallel_hive_view_snapshot
from app.application.services.regret_simulator import compose_regret_simulator_snapshot
from app.application.services.swarm_immune_system import compose_swarm_immune_snapshot


@pytest.mark.asyncio
async def test_context_teleport_disabled_when_flags_off() -> None:
    session = AsyncMock()
    with patch("app.application.services.context_teleport.settings") as mock_settings:
        mock_settings.cross_swarm_knowledge_enabled = False
        mock_settings.operator_control_plane_enabled = False
        snap = await compose_context_teleport_snapshot(session, tenant=None)
    assert snap.enabled is False


@pytest.mark.asyncio
async def test_regret_simulator_returns_score() -> None:
    session = AsyncMock()
    tenant = MagicMock()
    tenant.operator_settings = {}
    with patch("app.application.services.regret_simulator.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        with patch(
            "app.application.services.regret_simulator.compose_publish_performance_snapshot",
            new=AsyncMock(
                return_value=MagicMock(
                    simulate_success_rate_pct=50.0,
                    live_posts=0,
                    totals={"queue_approved": 2, "social_simulate": 0},
                ),
            ),
        ):
            snap = await compose_regret_simulator_snapshot(
                session,
                tenant_id=uuid.uuid4(),
                dashboard_user_id=uuid.uuid4(),
                tenant=tenant,
            )
    assert snap.enabled is True
    assert 0 <= snap.regret_score <= 100


@pytest.mark.asyncio
async def test_ambient_forager_compose_when_enabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.ambient_forager.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        mock_settings.forager_intelligence_v2_enabled = False
        mock_settings.dump_sleep_enabled = False
        snap = await compose_ambient_forager_snapshot(
            session,
            tenant=None,
            dashboard_user_id=uuid.uuid4(),
        )
    assert snap.enabled is True


@pytest.mark.asyncio
async def test_parallel_hive_view_empty_sessions() -> None:
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    with patch("app.application.services.parallel_hive_view.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        snap = await compose_parallel_hive_view_snapshot(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
        )
    assert snap.enabled is True
    assert snap.sessions == []


def test_swarm_immune_from_fleet() -> None:
    from types import SimpleNamespace

    fleet = [
        SimpleNamespace(routine_id="a", name="Alpha", immune_status="quarantine"),
        SimpleNamespace(routine_id="b", name="Beta", immune_status="healthy"),
    ]
    with patch("app.application.services.swarm_immune_system.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        snap = compose_swarm_immune_snapshot(fleet=fleet)
    assert snap.enabled is True
    assert snap.quarantine_count == 1
    assert snap.healthy_count == 1


@pytest.mark.asyncio
async def test_evolutionary_recipes_disabled_when_flags_off() -> None:
    session = AsyncMock()
    with patch("app.application.services.evolutionary_recipes.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = False
        mock_settings.imitation_v2_enabled = False
        snap = await compose_evolutionary_recipes_snapshot(session, tenant_id=uuid.uuid4())
    assert snap.enabled is False
