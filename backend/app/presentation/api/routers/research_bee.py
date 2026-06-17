"""Research Bee API — URL/PDF text → structured HiveMind brief."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.research_bee import ResearchBriefOut, compose_research_brief
from app.application.services.research_brief_export import (
    build_research_brief_export_bundle,
    export_response_to_dict,
)
from app.core.config import settings
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/research-bee", tags=["Research Bee"])


class ResearchBriefRequest(BaseModel):
    """Request body for research brief generation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_url: str | None = Field(default=None, max_length=2048)
    content_text: str | None = Field(default=None, max_length=120_000)
    title_hint: str | None = Field(default=None, max_length=200)
    persist: bool = False
    trigger_gardener: bool = Field(
        default=False,
        description="After persist, run Wiki Gardener sweep so forager-insights wiki updates immediately.",
    )


def _require_enabled() -> None:
    if not settings.research_bee_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research bee disabled.")


@router.get("/status", summary="Research bee feature status")
async def research_bee_status() -> dict[str, bool | int]:
    """Return whether research bee is enabled and content limits."""

    return {
        "enabled": bool(settings.research_bee_enabled),
        "max_chars": int(settings.research_bee_max_chars),
        "youtube_transcript_bee_enabled": bool(settings.youtube_transcript_bee_enabled),
        "skill_hot_tier_enabled": bool(settings.skill_hot_tier_enabled),
    }


@router.post("/brief", response_model=ResearchBriefOut, summary="Generate structured research brief")
async def create_research_brief(
    body: ResearchBriefRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> ResearchBriefOut:
    """Fetch URL or accept pasted text → structured brief; optional HiveMind persist."""

    _require_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    try:
        brief = await compose_research_brief(
            db,
            tenant_id=tenant_id,
            source_url=body.source_url,
            content_text=body.content_text,
            title_hint=body.title_hint,
            persist=body.persist,
            trigger_gardener=body.trigger_gardener,
        )
        await db.commit()
        return brief
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch source URL: {exc}",
        ) from exc


@router.post("/brief/export", summary="Generate brief + B2B export bundle")
async def export_research_brief_bundle(
    body: ResearchBriefRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Fetch URL or pasted text → structured brief → Gumroad-ready export files."""

    _require_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    try:
        brief = await compose_research_brief(
            db,
            tenant_id=tenant_id,
            source_url=body.source_url,
            content_text=body.content_text,
            title_hint=body.title_hint,
            persist=body.persist,
            trigger_gardener=body.trigger_gardener,
        )
        if not brief.summary:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="empty_brief")
        bundle = build_research_brief_export_bundle(brief)
        await db.commit()
        return export_response_to_dict(bundle)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch source URL: {exc}",
        ) from exc


class ResearchProjectRequest(BaseModel):
    """Batch URL research project (POS-H3)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_urls: list[str] = Field(..., min_length=1, max_length=8)
    project_title: str | None = Field(default=None, max_length=200)
    persist: bool = False


@router.post("/project", summary="Batch URLs → merged research project brief")
async def create_research_project(
    body: ResearchProjectRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Fetch multiple public URLs → one structured Hive Mind brief."""

    _require_enabled()
    if not settings.research_project_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research project disabled.")

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    from app.application.services.research_project_service import compose_research_project_brief

    try:
        brief = await compose_research_project_brief(
            db,
            tenant_id=tenant_id,
            source_urls=body.source_urls,
            project_title=body.project_title,
            persist=body.persist,
        )
        await db.commit()
        return brief.model_dump(mode="json")
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


__all__ = ["router"]
