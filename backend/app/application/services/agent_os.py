"""Agent OS — unified P8 autonomy snapshot (cross-swarm, imitation, behavioral, analysis)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.analysis_swarm import AnalysisConsensusOut, run_analysis_consensus
from app.application.services.cross_swarm_knowledge import (
    CrossSwarmKnowledgeSnapshotOut,
    compose_cross_swarm_knowledge_snapshot,
)
from app.application.services.dreaming_behavioral_proposals import (
    DreamingBehavioralSnapshotOut,
    compose_dreaming_behavioral_snapshot,
)
from app.application.services.imitation_v2 import ImitationV2SnapshotOut, compose_imitation_v2_snapshot
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant


class AgentOsActionOut(BaseModel):
    """Prioritized autonomy action."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    detail: str
    priority: str
    href: str | None = None


class AgentOsSnapshotOut(BaseModel):
    """Single snapshot for Agent OS panel — P8 autonomy layer."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    cross_swarm: CrossSwarmKnowledgeSnapshotOut
    imitation_v2: ImitationV2SnapshotOut
    behavioral_proposals: DreamingBehavioralSnapshotOut
    last_analysis: AnalysisConsensusOut | None = None
    actions: list[AgentOsActionOut] = Field(default_factory=list)
    links: dict[str, str] = Field(default_factory=dict)


def _derive_actions(
    *,
    cross_swarm: CrossSwarmKnowledgeSnapshotOut,
    imitation: ImitationV2SnapshotOut,
    behavioral: DreamingBehavioralSnapshotOut,
) -> list[AgentOsActionOut]:
    actions: list[AgentOsActionOut] = []

    if behavioral.proposals:
        actions.append(
            AgentOsActionOut(
                id="behavioral_proposal",
                label=f"{len(behavioral.proposals)} overnight instruction proposal(s)",
                detail="Review and merge into Settings → harness behavioral memory.",
                priority="high",
                href="/settings/harness",
            ),
        )

    if imitation.ready and imitation.suggestions:
        top = imitation.suggestions[0]
        actions.append(
            AgentOsActionOut(
                id="imitation_v2",
                label=f"Copy top recipe: {top.name[:60]}",
                detail=top.detail,
                priority="medium",
                href="/recipes",
            ),
        )

    if cross_swarm.suggestions:
        sug = cross_swarm.suggestions[0]
        actions.append(
            AgentOsActionOut(
                id="cross_swarm",
                label=f"Apply {cross_swarm.source_domain} → {sug.target_domain}",
                detail=sug.rationale,
                priority="medium",
                href="/recipes",
            ),
        )

    if not imitation.ready:
        actions.append(
            AgentOsActionOut(
                id="imitation_warming",
                label=f"Imitation v2: {imitation.verified_outcomes}/{3} verified outcomes",
                detail="Keep running simulate-first workflows to unlock auto-suggestions.",
                priority="low",
                href="/integrations?tab=studio",
            ),
        )

    return actions[:6]


async def compose_agent_os_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant | None,
) -> AgentOsSnapshotOut:
    """Assemble P8 autonomy snapshot from verified subsystems."""

    cross = await compose_cross_swarm_knowledge_snapshot(
        session,
        source_domain="trading",
        target_domain="marketing",
    )
    imitation = await compose_imitation_v2_snapshot(session, tenant_id=tenant_id)
    behavioral = await compose_dreaming_behavioral_snapshot(session, tenant_id=tenant_id)

    last_analysis: AnalysisConsensusOut | None = None
    if settings.analysis_swarm_enabled:
        last_analysis = await run_analysis_consensus(
            task="agent_os_health_check",
            symbol="BTC",
            side_hint="neutral",
            signal_confidence=0.0,
        )

    actions = _derive_actions(cross_swarm=cross, imitation=imitation, behavioral=behavioral)

    return AgentOsSnapshotOut(
        enabled=bool(settings.agent_os_enabled),
        generated_at=datetime.now(tz=UTC),
        cross_swarm=cross,
        imitation_v2=imitation,
        behavioral_proposals=behavioral,
        last_analysis=last_analysis,
        actions=actions,
        links={
            "recipes": "/recipes",
            "harness": "/settings/harness",
            "publish_queue": "/integrations?tab=studio#publish-queue",
            "trading_cockpit": "/integrations?tab=studio#trading-cockpit",
            "knowledge": "/knowledge",
        },
    )


__all__ = ["AgentOsSnapshotOut", "compose_agent_os_snapshot"]
