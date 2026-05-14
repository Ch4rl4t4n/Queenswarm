"""Dashboard JWT-scoped archived deliverables (Phase 0.51)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, Response

from app.presentation.api.deps import DashboardSession, DbSession
from app.core.chroma_client import TASK_DELIVERABLES_COLLECTION, semantic_search
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable
from app.domain.outputs.engine import OutputEngine
from app.domain.outputs.models import (
    FinalDeliverableDetailOut,
    FinalDeliverableSummaryOut,
    RegenerateDeliverableBody,
)
from app.domain.outputs.service import fetch_owned_deliverable, latest_for_lineage, list_owned_deliverables

router = APIRouter(prefix="/outputs", tags=["Outputs"])


def _dashboard_principal(session_payload: DashboardSession) -> uuid.UUID:
    """Resolve cockpit UUID embedded in prefixed ``sub`` claims."""

    raw = session_payload.get("sub")
    if not isinstance(raw, str) or not raw.strip():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing dashboard subject.")
    resolved = parse_dashboard_user_subject(raw.strip())
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Malformed dashboard subject.")
    return resolved


def _summary(row: TaskFinalDeliverable) -> FinalDeliverableSummaryOut:
    preview = row.markdown_body.replace("\n", " ").strip()
    tags = row.tags if isinstance(row.tags, list) else []
    safe_tags = [str(t) for t in tags][:32]
    return FinalDeliverableSummaryOut(
        id=row.id,
        lineage_id=row.lineage_id,
        version=row.version,
        title=row.title,
        slug=row.slug,
        created_at=row.created_at,
        tags=safe_tags,
        preview=preview[:280],
    )


def _detail(row: TaskFinalDeliverable) -> FinalDeliverableDetailOut:
    base = _summary(row)
    tags = row.tags if isinstance(row.tags, list) else []
    safe_tags = [str(t) for t in tags][:32]
    structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
    return FinalDeliverableDetailOut(
        **base.model_dump(),
        markdown_body=row.markdown_body,
        structured_json=structured,
        voice_script=row.voice_script,
        archive_relpath=row.archive_relpath,
        chroma_embedding_id=row.chroma_embedding_id,
        ballroom_session_id=row.ballroom_session_id,
        mission_id=row.mission_id,
        tags=safe_tags,
    )


@router.get("", response_model=list[FinalDeliverableSummaryOut])
async def list_my_outputs(
    db: DbSession,
    sess: DashboardSession,
    limit: int = Query(default=40, ge=1, le=120),
) -> list[FinalDeliverableSummaryOut]:
    """List recent archival rows for authenticated dashboard operators."""

    user_id = _dashboard_principal(sess)
    rows = await list_owned_deliverables(db, dashboard_user_id=user_id, limit=limit)
    return [_summary(row) for row in rows]


@router.get("/search", response_model=dict[str, Any])
async def search_my_outputs_semantic(
    db: DbSession,
    sess: DashboardSession,
    q: str = Query(min_length=2, max_length=2000),
    limit: int = Query(default=8, ge=1, le=24),
) -> dict[str, Any]:
    """Chroma cosine search narrowed to embeddings owned by the caller."""

    user_id = _dashboard_principal(sess)
    trimmed = q.strip()
    hits = await semantic_search(trimmed, TASK_DELIVERABLES_COLLECTION, n_results=limit)
    summaries: list[FinalDeliverableSummaryOut] = []
    for row in hits:
        meta_raw = dict(row.get("metadata") or {})
        did = meta_raw.get("deliverable_id")
        if not did:
            continue
        if str(meta_raw.get("dashboard_user_id", "")).strip() != str(user_id):
            continue

        pk = uuid.UUID(str(did))
        record = await fetch_owned_deliverable(db, deliverable_id=pk, dashboard_user_id=user_id)
        if record is None:
            continue
        summaries.append(_summary(record))

    return {
        "items": [model.model_dump() for model in summaries],
        "query": trimmed,
    }


@router.post("/by-lineage/{lineage_id}/regenerate", response_model=FinalDeliverableDetailOut)
async def regenerate_output_revision(
    lineage_id: uuid.UUID,
    db: DbSession,
    sess: DashboardSession,
    body: RegenerateDeliverableBody,
) -> FinalDeliverableDetailOut:
    """Produce version N+1 with LiteLLM assist."""

    user_id = _dashboard_principal(sess)
    newest = await latest_for_lineage(db, lineage_id=lineage_id, dashboard_user_id=user_id)
    if newest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown lineage.")
    merged_tags = list(newest.tags) if isinstance(newest.tags, list) else []

    try:
        created = await OutputEngine.regenerate_via_llm(
            db,
            lineage_id=lineage_id,
            dashboard_user_id=user_id,
            instruction=body.instruction,
            prior_markdown=newest.markdown_body,
            prior_structured=dict(newest.structured_json),
            ballroom_session_id=newest.ballroom_session_id,
            mission_id=newest.mission_id,
            tags=merged_tags,
            swarm_id_label=f"outputs-regenerate-{newest.ballroom_session_id or newest.id}",
            task_slug=f"output-regenerate-{newest.lineage_id}",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return _detail(created)


@router.get("/{deliverable_id}", response_model=FinalDeliverableDetailOut)
async def get_output_detail(
    deliverable_id: uuid.UUID,
    db: DbSession,
    sess: DashboardSession,
) -> FinalDeliverableDetailOut:
    """Full artefact."""

    user_id = _dashboard_principal(sess)
    row = await fetch_owned_deliverable(db, deliverable_id=deliverable_id, dashboard_user_id=user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable unavailable.")
    return _detail(row)


@router.get(
    "/{deliverable_id}/markdown.md",
    response_class=PlainTextResponse,
    summary="Download canonical Markdown artefact",
)
async def download_output_markdown(
    deliverable_id: uuid.UUID,
    db: DbSession,
    sess: DashboardSession,
) -> PlainTextResponse:
    """Expose ``text/markdown`` download for archiving."""

    user_id = _dashboard_principal(sess)
    row = await fetch_owned_deliverable(db, deliverable_id=deliverable_id, dashboard_user_id=user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable unavailable.")
    ascii_slug = row.slug.encode("ascii", "ignore").decode("ascii").replace("/", "-") or "deliverable"
    headers = {"Content-Disposition": f'attachment; filename="{ascii_slug}_v{row.version}.md"'}

    class _MarkedPlain(PlainTextResponse):
        media_type = "text/markdown"

    return _MarkedPlain(row.markdown_body, headers=headers)


@router.get("/{deliverable_id}/pdf")
async def download_pdf_stub(_deliverable_id: uuid.UUID) -> Response:
    """PDF export intentionally disabled to keep deps + RAM footprint low."""

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="PDF export not enabled — download Markdown instead.",
    )


__all__ = ["router"]
