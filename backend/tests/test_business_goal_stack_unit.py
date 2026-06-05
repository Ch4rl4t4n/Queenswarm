"""Unit tests for BA2 Business Goal Stack."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.business_goal_stack import (
    BusinessGoalIn,
    BusinessGoalStackPatchIn,
    compose_business_goal_stack,
    load_goal_definitions,
    mission_goal_payload,
    persist_goal_definitions,
)
from app.application.services.business_operator import (
    BusinessCatalogSummaryOut,
    BusinessMissionSummaryOut,
    BusinessRevenueSummaryOut,
)


def test_load_goal_definitions_defaults_when_empty() -> None:
    tenant = SimpleNamespace(operator_settings={})
    goals = load_goal_definitions(tenant)
    assert len(goals) >= 2
    assert any(goal.kind == "gumroad_listings" for goal in goals)


def test_persist_goal_definitions_roundtrip() -> None:
    tenant = SimpleNamespace(operator_settings={})
    patch = BusinessGoalStackPatchIn(
        goals=[
            BusinessGoalIn(
                id="custom_1",
                kind="custom",
                label="First sale",
                target_value=1,
                unit="sales",
            ),
        ],
    )
    persist_goal_definitions(tenant, patch.goals)
    loaded = load_goal_definitions(tenant)
    assert loaded[0].id == "custom_1"


def test_mission_goal_payload_maps_lane() -> None:
    payload = mission_goal_payload("revenue")
    assert payload.get("business_goal_id") == "gumroad_live"


@pytest.mark.asyncio
async def test_compose_goal_stack_detects_triage_drift() -> None:
    session = AsyncMock()
    tenant = SimpleNamespace(operator_settings={})
    stack = await compose_business_goal_stack(
        session,
        tenant_id=uuid.uuid4(),
        tenant=tenant,
        catalog=BusinessCatalogSummaryOut(product_count=5, gumroad_linked_count=0),
        missions=BusinessMissionSummaryOut(triage_count=4),
        revenue=BusinessRevenueSummaryOut(),
    )
    triage_goal = next(g for g in stack.goals if g.kind == "mission_triage_clear")
    assert triage_goal.drift_severity == "critical"
    assert stack.critical_drift_count >= 1
