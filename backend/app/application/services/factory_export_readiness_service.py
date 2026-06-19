"""Factory export readiness — GitHub PR and manual bundle paths."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession


class FactoryExportReadinessOut(BaseModel):
    """Export channel readiness for factory library items."""

    model_config = ConfigDict(extra="ignore")

    manual_export_ready: bool = True
    github_pr_ready: bool = False
    github_setup_hint: str = ""


async def resolve_factory_export_readiness(session: AsyncSession) -> FactoryExportReadinessOut:
    """Summarize automated vs manual export paths."""

    from app.application.services.skill_factory_github_export import github_pr_export_ready

    github_ready = await github_pr_export_ready(session)

    github_hint = ""
    if not github_ready:
        github_hint = (
            "Manual: Library → Export bundle. "
            "For auto PR: github_rest connector + SKILL_FACTORY_GITHUB_PR_ENABLED + owner/repo env."
        )
    else:
        github_hint = "GitHub PR export ready from Library."

    return FactoryExportReadinessOut(
        manual_export_ready=True,
        github_pr_ready=github_ready,
        github_setup_hint=github_hint,
    )


__all__ = ["FactoryExportReadinessOut", "resolve_factory_export_readiness"]
