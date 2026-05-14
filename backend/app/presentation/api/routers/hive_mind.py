"""Dashboard JWT routes for Hive Mind explorer (Neo4j + vault + semantic lane)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from app.presentation.api.deps import DashboardSession, DbSession
from app.core.chroma_client import HIVE_MIND_COLLECTION, semantic_search
from app.core.config import Settings, get_settings
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.domain.hive_mind.graph import bounded_operator_graph_snapshot
from app.domain.hive_mind.service import HiveMindService
from app.domain.outputs.service import fetch_owned_deliverable

router = APIRouter(prefix="/hive-mind", tags=["hive-mind"])

SettingsDep = Annotated[Settings, Depends(get_settings)]

__all__ = ["router"]


class HiveMindRecallBody(BaseModel):
    """Debug / cockpit-triggered retrieval payload."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    relevance_to_current_task: str = Field(min_length=3, max_length=8000)


def _dashboard_principal(session_payload: DashboardSession) -> uuid.UUID:
    raw = session_payload.get("sub")
    if not isinstance(raw, str) or not raw.strip():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing dashboard subject.")
    resolved = parse_dashboard_user_subject(raw.strip())
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Malformed dashboard subject.")
    return resolved


@router.get("/graph")
async def hive_graph(
    sess: DashboardSession,
    settings: SettingsDep,
    limit_nodes: int = Query(default=64, ge=8, le=260),
) -> dict[str, Any]:
    """Neo4j constellation snapshot for dashboards (Deliverable-owner scoped)."""

    pid = _dashboard_principal(sess)
    cap = min(limit_nodes, settings.hive_mind_max_graph_export_nodes)
    return await bounded_operator_graph_snapshot(
        dashboard_user_id=str(pid),
        limit_nodes=cap,
    )


@router.get("/search")
async def hive_search_semantic(
    _sess: DashboardSession,
    settings: SettingsDep,
    q: str = Query(min_length=2, max_length=2400),
    limit: int = Query(default=8, ge=1, le=32),
) -> dict[str, Any]:
    """Chroma cosine search over HiveMind embeddings."""

    del _sess  # dependency-only session — forces JWT validation gate
    clipped = q.strip()
    capped = min(limit, settings.hive_mind_max_query_hits_vector + 6)
    hits = await semantic_search(clipped, HIVE_MIND_COLLECTION, n_results=capped)
    sanitized: list[dict[str, Any]] = []
    for row in hits:
        meta = dict(row.get("metadata") or {})
        if meta.get("dashboard_user_id"):
            meta["dashboard_user_id"] = "***"
        sanitized.append(
            {
                "id": row.get("id"),
                "document": (row.get("document") or "")[:4096],
                "metadata": meta,
                "distance": row.get("distance"),
            },
        )
    return {"items": sanitized, "query": clipped}


@router.post("/query")
async def hive_query_debug(
    body: HiveMindRecallBody,
    sess: DashboardSession,
    settings: SettingsDep,
) -> dict[str, Any]:
    """Operator parity with Ballroom HiveMind appendix — inspect clip lengths."""

    uid = _dashboard_principal(sess)
    text = await HiveMindService.query_for_prompt(
        relevance_to_current_task=body.relevance_to_current_task.strip(),
        settings=settings,
        swarm_id="dashboard",
        task_id=f"hive-mind-debug:{uid}",
        agent_id=str(uid),
    )
    return {"hive_mind_prompt_block": text, "characters": len(text)}


@router.get("/deliverables/{deliverable_id}")
async def hive_deliverable_detail(
    deliverable_id: uuid.UUID,
    db: DbSession,
    sess: DashboardSession,
) -> dict[str, Any]:
    """Hydrate Postgres deliverable mirrored by ingestion."""

    uid = _dashboard_principal(sess)
    row = await fetch_owned_deliverable(db, deliverable_id=deliverable_id, dashboard_user_id=uid)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable unavailable.")
    return {
        "id": str(row.id),
        "title": row.title,
        "lineage_id": str(row.lineage_id),
        "version": row.version,
        "markdown_body": row.markdown_body,
        "structured_json": dict(row.structured_json) if isinstance(row.structured_json, dict) else {},
        "tags": list(row.tags or []),
        "voice_script": row.voice_script,
        "mission_id": str(row.mission_id) if row.mission_id else None,
        "ballroom_session_id": str(row.ballroom_session_id) if row.ballroom_session_id else None,
    }


@router.get("/export")
async def hive_export_zip(
    db: DbSession,
    sess: DashboardSession,
    settings: SettingsDep,
) -> Response:
    """ZIP bundle: deliverable Markdown snapshots + mirrored vault manifests + graph JSON."""

    uid = _dashboard_principal(sess)
    blob = await HiveMindService.export_zip_bytes(session=db, dashboard_user_id=uid, settings=settings)

    fname = "queenswarm-hive-mind-export.zip"
    return Response(
        content=blob,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
