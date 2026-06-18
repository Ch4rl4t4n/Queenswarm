"""POS-V — Mission Home Skill Factory verified harness strip (Personal OS lite)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.factory_llm_readiness_service import resolve_factory_llm_readiness
from app.application.services.personal_os_mode import personal_os_skill_factory_commercial_enabled
from app.application.services.skill_factory_sellable import assess_tenant_skill_sellable
from app.application.services.skill_factory_service import (
    _forge_quality_by_skill_id,
    count_skill_opportunity_statuses,
    list_tenant_skills,
)
from app.core.config import settings


class MissionSkillFactoryHarnessStripOut(BaseModel):
    """Skill Factory harness pipeline visibility on Mission Home (POS-V)."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    headline: str = "Verified harness · Skill Factory"
    message: str = ""
    personal_os_lite: bool = True
    llm_ready: bool = False
    llm_smoke_ok: bool | None = None
    queue_actionable: int = 0
    building_count: int = 0
    failed_count: int = 0
    verified_count: int = 0
    library_count: int = 0
    research_href: str = "/apps-tools/skill-factory#research"
    queue_href: str = "/apps-tools/skill-factory#queue"
    library_href: str = "/apps-tools/skill-factory#library"
    guide_href: str = "/apps-tools/skill-factory#guide"


async def compose_mission_skill_factory_harness_strip(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    first_run_complete: bool,
) -> MissionSkillFactoryHarnessStripOut:
    """Lightweight Skill Factory strip — queue → verified library (no Gumroad UI)."""

    if not settings.skill_factory_enabled or not first_run_complete:
        return MissionSkillFactoryHarnessStripOut(enabled=False)

    personal_os_lite = not personal_os_skill_factory_commercial_enabled()
    llm = await resolve_factory_llm_readiness(session)
    status_counts = await count_skill_opportunity_statuses(session, tenant_id=tenant_id)
    library_rows = await list_tenant_skills(session, tenant_id=tenant_id, limit=80)
    forge_quality = await _forge_quality_by_skill_id(
        session,
        tenant_id=tenant_id,
        skill_ids=[row.id for row in library_rows],
    )

    verified_count = 0
    for row in library_rows:
        assessment = assess_tenant_skill_sellable(
            row,
            forge_quality=forge_quality.get(row.id),
        )
        if assessment.tier == "sellable":
            verified_count += 1

    llm_ready = bool(llm.build_allowed)
    llm_smoke_ok = llm.smoke_ok
    queue_actionable = int(status_counts.actionable)
    building_count = int(status_counts.building)
    failed_count = int(status_counts.failed)
    library_count = len(library_rows)

    if not llm_ready:
        message = "Factory builds blocked — configure LLM keys and run smoke test in Skill Factory."
    elif llm_smoke_ok is False:
        message = "LLM smoke failed — fix decomposition chain before queue drain or builds."
    elif queue_actionable > 0:
        message = (
            f"{queue_actionable} build(s) in pipeline"
            + (f" · {failed_count} failed" if failed_count else "")
            + " — review queue and approve forges."
        )
    elif verified_count == 0:
        message = (
            "No verified harness yet — Research → Queue → Library "
            "(Personal OS lite — export skills to your agent OS, no Gumroad tab)."
            if personal_os_lite
            else "No sellable harness yet — run research → build → approve forge."
        )
    else:
        message = (
            f"{verified_count} verified harness skill(s) in library — export or attach via skill picker."
            if personal_os_lite
            else f"{verified_count} sellable harness(s) ready — open Launch tab or export bundle."
        )

    return MissionSkillFactoryHarnessStripOut(
        enabled=True,
        headline="Verified harness · Skill Factory",
        message=message,
        personal_os_lite=personal_os_lite,
        llm_ready=llm_ready,
        llm_smoke_ok=llm_smoke_ok,
        queue_actionable=queue_actionable,
        building_count=building_count,
        failed_count=failed_count,
        verified_count=verified_count,
        library_count=library_count,
    )
