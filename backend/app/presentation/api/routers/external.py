"""Pull-only generic external connector (dashboard API keys, no vendor-specific adapters)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.presentation.api.deps import DbSession
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.core.logging import get_logger
from app.domain.external.gateway import integration_router
from app.application.services.dashboard_api_keys import resolve_api_key_principal
from app.application.services.external_output_feed import (
    list_external_results,
    normalize_tag_filter,
    parse_since_iso,
)

router = APIRouter(prefix="/external", tags=["External"])
logger = get_logger(__name__)

router.include_router(integration_router)


class ExternalResultItem(BaseModel):
    """One orchestrator payload visible to external pull clients."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    created_at: datetime
    text_report: str
    voice_script: str | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Mission routing context (ids, brief excerpt, status).",
    )
    simulation_outcome: dict[str, Any] | None = None
    tags: list[str] = Field(default_factory=list)


async def require_external_api_user(
    db: DbSession,
    api_key: Annotated[str | None, Query(description="Dashboard API key (qs_kw_…).")] = None,
) -> UUID:
    """Resolve ``api_key`` to the owning dashboard user id."""

    if api_key is None or not api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing api_key query parameter.",
        )
    subject = await resolve_api_key_principal(db, api_key.strip())
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )
    user_id = parse_dashboard_user_subject(subject)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key subject is not a dashboard user.",
        )
    return user_id


@router.get(
    "/results",
    response_model=list[ExternalResultItem],
    summary="List orchestrator-delivered payloads (pull feed)",
)
async def list_orchestrator_results(
    db: DbSession,
    user_id: Annotated[UUID, Depends(require_external_api_user)],
    since: Annotated[str | None, Query(description="ISO-8601 created_at lower bound")] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="Max rows")] = 50,
    tags: Annotated[str | None, Query(description="Comma-separated; row must overlap any")] = None,
) -> list[ExternalResultItem]:
    """Return finished Orchestrator outputs for the authenticated API key holder."""

    try:
        since_dt = parse_since_iso(since)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    tag_filter = normalize_tag_filter(tags)
    rows = await list_external_results(
        db,
        dashboard_user_id=user_id,
        since=since_dt,
        limit=limit,
        tag_filter=tag_filter,
    )
    logger.info(
        "external.feed_query",
        agent_id=str(user_id),
        swarm_id=str(len(rows)),
        task_id="external.results",
    )

    out: list[ExternalResultItem] = []
    for row in rows:
        out.append(
            ExternalResultItem(
                id=row.id,
                created_at=row.created_at,
                text_report=row.text_report,
                voice_script=row.voice_script,
                metadata=dict(row.output_metadata),
                simulation_outcome=dict(row.simulation_outcome) if row.simulation_outcome else None,
                tags=list(row.tags or []),
            ),
        )
    return out


__all__ = ["router"]
