"""Agent OS snapshot unit tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.agent_os import compose_agent_os_snapshot


@pytest.mark.asyncio
async def test_compose_agent_os_snapshot_enabled() -> None:
    tenant_id = uuid.uuid4()
    session = AsyncMock()

    with (
        patch("app.application.services.agent_os.settings") as mock_settings,
        patch(
            "app.application.services.agent_os.compose_cross_swarm_knowledge_snapshot",
            new_callable=AsyncMock,
        ) as cross_mock,
        patch(
            "app.application.services.agent_os.compose_imitation_v2_snapshot",
            new_callable=AsyncMock,
        ) as imit_mock,
        patch(
            "app.application.services.agent_os.compose_dreaming_behavioral_snapshot",
            new_callable=AsyncMock,
        ) as dream_mock,
        patch(
            "app.application.services.agent_os.run_analysis_consensus",
            new_callable=AsyncMock,
        ) as analysis_mock,
    ):
        mock_settings.agent_os_enabled = True
        mock_settings.analysis_swarm_enabled = True

        from app.application.services.cross_swarm_knowledge import CrossSwarmKnowledgeSnapshotOut
        from app.application.services.dreaming_behavioral_proposals import DreamingBehavioralSnapshotOut
        from app.application.services.imitation_v2 import ImitationV2SnapshotOut
        from app.application.services.analysis_swarm import AnalysisConsensusOut
        from datetime import UTC, datetime

        now = datetime.now(tz=UTC)
        cross_mock.return_value = CrossSwarmKnowledgeSnapshotOut(
            enabled=True, generated_at=now, source_domain="trading", suggestions=[],
        )
        imit_mock.return_value = ImitationV2SnapshotOut(
            enabled=True, generated_at=now, verified_outcomes=1, ready=False, suggestions=[],
        )
        dream_mock.return_value = DreamingBehavioralSnapshotOut(enabled=True, generated_at=now, proposals=[])
        analysis_mock.return_value = AnalysisConsensusOut(
            enabled=True,
            generated_at=now,
            task="t",
            symbol="BTC",
            consensus="neutral",
            consensus_strength=0.33,
            recommend_execute=False,
        )

        snap = await compose_agent_os_snapshot(session, tenant_id=tenant_id, tenant=None)

    assert snap.enabled is True
    assert snap.imitation_v2.verified_outcomes == 1
