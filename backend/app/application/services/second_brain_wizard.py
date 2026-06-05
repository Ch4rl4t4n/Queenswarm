"""Second Brain Pack wizard — Brain Pack → My 3 Bees → Obsidian / first cycle."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.brain_pack_starters import starter_kinds
from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.publish_operator_onboarding import _brain_pack_filled_count
from app.application.services.solo_operator_trio import get_solo_trio_status
from app.core.config import settings
from app.domain.memory.curated import CuratedFileKind
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService

SecondBrainStepId = Literal["brain_pack", "trio_bound", "vault_or_cycle"]


class SecondBrainStepOut(BaseModel):
    """One step in the Second Brain Pack wizard."""

    model_config = ConfigDict(extra="ignore")

    id: SecondBrainStepId
    label: str
    detail: str
    done: bool
    href: str
    link_label: str
    progress_note: str | None = None


class SecondBrainWizardOut(BaseModel):
    """Operator wizard for Hermes-style second brain setup."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    complete: bool
    progress_pct: int = Field(ge=0, le=100)
    generated_at: datetime
    brain_pack_filled: int = 0
    brain_pack_total: int = 5
    trio_bound: int = 0
    trio_total: int = 3
    steps: list[SecondBrainStepOut] = Field(default_factory=list)


async def compose_second_brain_wizard(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> SecondBrainWizardOut:
    """Build 3-step second brain checklist for solo operators."""

    if not settings.solo_mode_enabled and not settings.operator_loop_enabled:
        return SecondBrainWizardOut(
            enabled=False,
            complete=True,
            progress_pct=100,
            generated_at=datetime.now(tz=UTC),
            steps=[],
        )

    svc = CuratedMemoryService(db=session)
    bundle = await svc.get_bundle(tenant_id)
    filled = _brain_pack_filled_count(bundle)
    total = len(starter_kinds())
    brain_done = filled >= 3

    trio = await get_solo_trio_status(session, tenant_id=tenant_id)
    bound = int(trio.get("lanes_bound") or 0)
    trio_done = bound >= 2

    obsidian_row = await DynamicConnectorService().fetch_by_slug(session, slug="obsidian_store")
    obsidian_ready = obsidian_row is not None and obsidian_row.is_active
    any_lane_ran = any(
        bool(lane.get("last_run_at") or lane.get("last_session_id"))
        for lane in list(trio.get("lanes") or [])
        if isinstance(lane, dict)
    )
    vault_done = obsidian_ready or any_lane_ran

    steps: list[SecondBrainStepOut] = [
        SecondBrainStepOut(
            id="brain_pack",
            label="Brain Pack (SOUL · MEMORY · USER)",
            detail="Seed curated memory so Queen knows who you are, what matters, and how you work.",
            done=brain_done,
            href="/knowledge?tab=memory#brain-pack",
            link_label="Open Brain Pack",
            progress_note=f"{filled}/{total} slots filled",
        ),
        SecondBrainStepOut(
            id="trio_bound",
            label="My 3 Bees — bind routines",
            detail="Hive Learner, SCV Maintainer, Life OS — specialist agents that hand off without you micromanaging.",
            done=trio_done,
            href="/settings/harness#solo-trio",
            link_label="Bind trio lanes",
            progress_note=f"{bound}/3 lanes bound",
        ),
        SecondBrainStepOut(
            id="vault_or_cycle",
            label="Obsidian vault or first cycle",
            detail="Export Brain Pack to Obsidian, enable vault sync, or run today's trio cycle once.",
            done=vault_done,
            href="/knowledge?tab=wiki#wiki-obsidian" if not obsidian_ready else "/integrations#obsidian",
            link_label="Obsidian export" if not obsidian_ready else "Vault sync",
            progress_note="Obsidian connected" if obsidian_ready else ("Cycle ran" if any_lane_ran else "Not started"),
        ),
    ]

    done_count = sum(1 for step in steps if step.done)
    progress = int(round(100 * done_count / max(len(steps), 1)))
    complete = done_count == len(steps)

    return SecondBrainWizardOut(
        enabled=True,
        complete=complete,
        progress_pct=progress,
        generated_at=datetime.now(tz=UTC),
        brain_pack_filled=filled,
        brain_pack_total=total,
        trio_bound=bound,
        trio_total=3,
        steps=steps,
    )


__all__ = ["SecondBrainWizardOut", "compose_second_brain_wizard"]
