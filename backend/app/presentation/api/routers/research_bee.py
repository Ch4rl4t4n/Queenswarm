"""Research Bee API — URL/PDF text → structured HiveMind brief."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.research_bee import ResearchBriefOut, compose_research_brief
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


def _require_enabled() -> None:
    if not settings.research_bee_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research bee disabled.")


@router.get("/status", summary="Research bee feature status")
async def research_bee_status() -> dict[str, bool | int]:
    """Return whether research bee is enabled and content limits."""

    return {
        "enabled": bool(settings.research_bee_enabled),
        "max_chars": int(settings.research_bee_max_chars),
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


__all__ = ["router"]
