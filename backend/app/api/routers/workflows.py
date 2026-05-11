"""Workflow breaker HTTP surface guarded by swarm JWT issuance."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession, JwtSubject
from app.schemas.workflow_breaker import (
    DecomposeWorkflowRequest,
    DecomposeWorkflowResponse,
)
from app.services.workflow_breaker.breaker import WorkflowBreakerService

router = APIRouter()


@router.post(
    "/decompose",
    response_model=DecomposeWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run Auto Workflow Breaker",
)
async def decompose_workflow(
    body: DecomposeWorkflowRequest,
    db: DbSession,
    _subject: JwtSubject,
) -> DecomposeWorkflowResponse:
    """Kick off GPT-style decomposition persisted for LangGraph supervisors."""

    service = WorkflowBreakerService()
    try:
        result = await service.build_workflow_plan(
            db,
            task_text=body.task_text,
            matching_recipe_id=body.matching_recipe_id,
            enrich_from_chroma_recipes=body.enrich_from_chroma_recipes,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence layer rejected workflow insert.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    await db.commit()
    return result
