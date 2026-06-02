"""Unit tests for Four Cs harness audit."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.harness_four_cs_audit import compose_four_cs_audit


@pytest.mark.asyncio
async def test_compose_four_cs_audit_returns_four_dimensions() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    with (
        patch("app.application.services.harness_four_cs_audit.settings") as mock_settings,
        patch(
            "app.application.services.harness_four_cs_audit.CuratedMemoryService",
        ) as mock_memory_cls,
        patch(
            "app.application.services.harness_four_cs_audit.MCPAdapter.dynamic_tool_catalog",
            new_callable=AsyncMock,
            return_value=[{"id": "a"}, {"id": "b"}],
        ),
        patch(
            "app.application.services.harness_four_cs_audit._collect_skills_summary",
            return_value=["s1", "s2", "s3"],
        ),
        patch(
            "app.application.services.harness_four_cs_audit.count_maintainer_runs_today",
            new_callable=AsyncMock,
            return_value=0,
        ),
        patch(
            "app.application.services.harness_four_cs_audit.maintainer_daily_run_limit",
            return_value=3,
        ),
    ):
        mock_settings.wiki_layer_enabled = True
        mock_settings.skill_hot_tier_enabled = True
        mock_settings.routines_enabled = True
        mock_settings.supervisor_routine_webhook_enabled = False
        mock_settings.hive_innovation_lab_enabled = True
        mock_settings.recipes_enabled = True
        mock_settings.queen_maintainer_enabled = True
        mock_settings.supervisor_pattern_router_enabled = True
        mock_settings.autonomous_routines_enabled = False

        memory = MagicMock()
        memory.get_bundle = AsyncMock(return_value={"instructions": "x" * 250})
        mock_memory_cls.return_value = memory

        session.scalar = AsyncMock(side_effect=[0, 0])

        out = await compose_four_cs_audit(session, tenant_id=tenant_id)

    assert len(out.dimensions) == 4
    assert out.overall_score >= 0
    assert len(out.maintainer_safety) >= 8
