"""Dashboard paper trading P&L and manual tick controls."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.paper_trading_service import (
    build_dashboard_paper_summary,
    build_portfolio_snapshot,
    run_paper_trading_tick_all,
    run_paper_trading_tick_for_project,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.external_project import ExternalProject
from app.presentation.api.deps import DbSession, JwtSubject

logger = get_logger(__name__)

router = APIRouter(prefix="/paper-trading", tags=["Paper Trading"])


def _ensure_paper_trading_enabled() -> None:
    if not settings.paper_trading_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Paper trading module is disabled.",
        )


@router.get("/summary", summary="Paper trading P&L dashboard aggregate")
async def paper_trading_summary(db: DbSession, _subject: JwtSubject) -> dict[str, object]:
    """Return simulated equity and P&L across paper trading projects."""

    _ensure_paper_trading_enabled()
    try:
        return await build_dashboard_paper_summary(db)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected paper trading summary.",
        )


@router.get("/projects/{project_id}", summary="Paper trading project snapshot")
async def paper_trading_project_snapshot(
    project_id: uuid.UUID,
    db: DbSession,
    _subject: JwtSubject,
) -> dict[str, object]:
    """Return positions, fills, and P&L for one paper project."""

    _ensure_paper_trading_enabled()
    try:
        project = await db.get(ExternalProject, project_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected project lookup.",
        )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    try:
        return await build_portfolio_snapshot(db, project=project)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected paper snapshot.",
        )


@router.post("/tick", summary="Run paper trading bee tick (all auto projects)")
async def paper_trading_tick_all(
    db: DbSession,
    subject: JwtSubject,
) -> dict[str, object]:
    """Manually trigger paper trading evaluation (same as Celery beat)."""

    _ensure_paper_trading_enabled()
    try:
        payload = await run_paper_trading_tick_all(db)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected paper trading tick.",
        )
    logger.info("paper_trading.manual_tick", operator_subject=subject, projects=payload.get("projects"))
    return payload


@router.post("/projects/{project_id}/tick", summary="Run paper tick for one project")
async def paper_trading_tick_one(
    project_id: uuid.UUID,
    db: DbSession,
    subject: JwtSubject,
) -> dict[str, object]:
    """Evaluate signals and maybe fill for a single paper project."""

    _ensure_paper_trading_enabled()
    try:
        project = await db.get(ExternalProject, project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        result = await run_paper_trading_tick_for_project(db, project=project)
        await db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected paper trading tick.",
        )
    logger.info("paper_trading.manual_project_tick", operator_subject=subject, project_id=str(project_id))
    return result


__all__ = ["router"]
