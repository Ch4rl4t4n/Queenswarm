"""Unit tests for BA7 cross-lane learning."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.business_cross_lane_learning import compose_business_cross_lane_learning
from app.application.services.cross_swarm_knowledge import (
    CrossSwarmKnowledgeSnapshotOut,
    CrossSwarmRecipeSuggestionOut,
)


@pytest.mark.asyncio
async def test_cross_lane_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.business_cross_lane_learning.settings") as mock_settings:
        mock_settings.cross_swarm_knowledge_enabled = False
        mock_settings.business_cross_lane_learning_enabled = True
        out = await compose_business_cross_lane_learning(session, tenant_id=uuid.uuid4())
    assert out.enabled is False


@pytest.mark.asyncio
async def test_cross_lane_collects_suggestions() -> None:
    session = AsyncMock()
    from datetime import UTC, datetime

    snap = CrossSwarmKnowledgeSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        source_domain="trading",
        suggestions=[
            CrossSwarmRecipeSuggestionOut(
                recipe_id="r1",
                name="Paper discipline",
                source_domain="trading",
                target_domain="marketing",
                similarity=0.82,
                rationale="test",
            ),
        ],
    )
    with (
        patch("app.application.services.business_cross_lane_learning.settings") as mock_settings,
        patch(
            "app.application.services.business_cross_lane_learning.compose_cross_swarm_knowledge_snapshot",
            new=AsyncMock(return_value=snap),
        ),
    ):
        mock_settings.cross_swarm_knowledge_enabled = True
        mock_settings.business_cross_lane_learning_enabled = True
        out = await compose_business_cross_lane_learning(session, tenant_id=uuid.uuid4(), limit=3)
    assert out.enabled is True
    assert len(out.suggestions) >= 1
