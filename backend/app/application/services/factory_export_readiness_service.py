"""Factory export readiness — Gumroad, GitHub, manual bundle paths."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession


class FactoryExportReadinessOut(BaseModel):
    """Export channel readiness for factory library items."""

    model_config = ConfigDict(extra="ignore")

    manual_export_ready: bool = True
    github_pr_ready: bool = False
    gumroad_draft_ready: bool = False
    gumroad_publish_ready: bool = False
    gumroad_setup_hint: str = ""
    github_setup_hint: str = ""


async def resolve_factory_export_readiness(session: AsyncSession) -> FactoryExportReadinessOut:
    """Summarize automated vs manual export paths."""

    from app.application.services.skill_factory_github_export import github_pr_export_ready
    from app.application.services.skill_factory_gumroad_listing import (
        gumroad_listing_ready,
        gumroad_publish_ready,
    )

    github_ready = await github_pr_export_ready(session)
    gumroad_draft = await gumroad_listing_ready(session)
    gumroad_live = await gumroad_publish_ready(session)

    gumroad_hint = ""
    if not gumroad_draft:
        gumroad_hint = (
            "Manual upload: exports/gumroad-upload/*.tar.gz + LISTING.md. "
            "For API: SKILL_FACTORY_GUMROAD_LISTING_ENABLED=true + Gumroad token or gumroad_rest connector."
        )
    elif not gumroad_live:
        gumroad_hint = "Gumroad draft API ready. Enable SKILL_FACTORY_GUMROAD_PUBLISH_ENABLED for one-click publish."
    else:
        gumroad_hint = "Gumroad draft + publish API ready."

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
        gumroad_draft_ready=gumroad_draft,
        gumroad_publish_ready=gumroad_live,
        gumroad_setup_hint=gumroad_hint,
        github_setup_hint=github_hint,
    )


__all__ = ["FactoryExportReadinessOut", "resolve_factory_export_readiness"]
