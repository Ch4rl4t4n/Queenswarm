"""Dashboard JWT routes for Hive Mind explorer (Neo4j + vault + semantic lane)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.presentation.api.deps import (
    DashboardSession,
    DbSession,
    require_dashboard_user_with_tenant_role,
    require_tenant_permission,
)
from app.core.chroma_client import HIVE_MIND_COLLECTION, semantic_search
from app.core.config import Settings, get_settings, settings
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.core.logging import get_logger
from app.core.redis_client import get_json, set_json
from app.domain.hive_mind.graph import bounded_operator_graph_snapshot, bounded_tenant_project_shape_snapshot
from app.domain.hive_mind.service import HiveMindService
from app.domain.outputs.service import fetch_owned_deliverable
from app.application.services.selective_recall import (
    effective_prompt_char_budget,
    load_recall_config,
    merge_recall_patch,
    normalize_recall_mode,
)
from app.application.services.billing import ensure_tenant_subscription
from app.application.services.platform_features import resolve_platform_features_for_subscription
from app.application.services.supervisor.memory_evolution import (
    approve_memory_evolution_proposal,
    list_memory_evolution_proposals,
    reject_memory_evolution_proposal,
    run_memory_evolution_for_tenant,
)
from app.infrastructure.persistence.models.memory_evolution import MemoryEvolutionProposal
from app.infrastructure.persistence.models.tenant import Tenant

router = APIRouter(prefix="/hive-mind", tags=["hive-mind"])
logger = get_logger(__name__)

SettingsDep = Annotated[Settings, Depends(get_settings)]

__all__ = ["router"]


class HiveMindRecallBody(BaseModel):
    """Debug / cockpit-triggered retrieval payload."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    relevance_to_current_task: str = Field(min_length=3, max_length=8000)


class HiveMindRecallSettingsResponse(BaseModel):
    """Tenant recall mode + token budget."""

    recall_mode: str
    token_budget_chars: int
    feature_enabled: bool
    max_prompt_chars: int
    selective_max_chars: int


class HiveMindRecallSettingsUpdateBody(BaseModel):
    """Partial recall settings patch."""

    model_config = ConfigDict(extra="forbid")

    recall_mode: str | None = None
    token_budget_chars: int | None = Field(default=None, ge=0, le=16_000)


class MemoryEvolutionRunResponse(BaseModel):
    """Summary returned after one memory evolution cycle."""

    tenant_id: str
    generated_lessons: int
    pending_approval: int
    auto_applied: int
    swarm_learning_entries: int
    history_consolidations: int


class MemoryEvolutionProposalView(BaseModel):
    """Public view of one memory evolution proposal."""

    id: str
    proposal_kind: str
    title: str
    summary: str
    payload: dict[str, Any]
    status: str
    importance_score: float
    requires_manual_approval: bool
    proposed_by_user_id: str | None
    approved_by_user_id: str | None
    approved_at: str | None
    created_at: str


def _serialize_proposal(row: MemoryEvolutionProposal) -> MemoryEvolutionProposalView:
    return MemoryEvolutionProposalView(
        id=str(row.id),
        proposal_kind=row.proposal_kind,
        title=row.title,
        summary=row.summary,
        payload=dict(row.payload or {}),
        status=row.status,
        importance_score=float(row.importance_score),
        requires_manual_approval=bool(row.requires_manual_approval),
        proposed_by_user_id=str(row.proposed_by_user_id) if row.proposed_by_user_id else None,
        approved_by_user_id=str(row.approved_by_user_id) if row.approved_by_user_id else None,
        approved_at=row.approved_at.isoformat() if row.approved_at else None,
        created_at=row.created_at.isoformat(),
    )


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
    cache_ttl = max(0, int(settings.hive_mind_graph_cache_ttl_sec))
    cache_key = f"hive_mind:graph:{pid}:{cap}"
    if cache_ttl > 0:
        try:
            cached = await get_json(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass
    try:
        payload = await bounded_operator_graph_snapshot(
            dashboard_user_id=str(pid),
            limit_nodes=cap,
        )
    except Exception as exc:  # noqa: BLE001 - route intentionally degrades to vector recall
        logger.warning(
            "hive_mind.graph.degraded_to_vector_fallback",
            agent_id="hive_mind_graph",
            swarm_id="dashboard",
            task_id=f"hive_graph:{pid}",
            error=str(exc),
        )
        fallback_hits = await semantic_search(
            "hive mind",
            HIVE_MIND_COLLECTION,
            n_results=min(6, settings.hive_mind_max_query_hits_vector),
        )
        payload = {
            "nodes": [],
            "edges": [],
            "degraded": True,
            "fallback_backend": "vector_store",
            "fallback_items": [
                {
                    "id": row.get("id"),
                    "document": str(row.get("document") or "")[:320],
                    "distance": row.get("distance"),
                }
                for row in fallback_hits
            ],
        }
    if cache_ttl > 0:
        try:
            await set_json(cache_key, payload, ttl=cache_ttl)
        except Exception:
            pass
    return payload


@router.get("/project-shape")
async def hive_project_shape(
    settings: SettingsDep,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    limit_nodes: int = Query(default=96, ge=8, le=260),
) -> dict[str, Any]:
    """Tenant-scoped folder tree from Auto-Graphify vault ingest (VaultFolder → VaultDocument)."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    cap = min(limit_nodes, settings.hive_mind_max_graph_export_nodes)
    cache_ttl = max(0, int(settings.hive_mind_graph_cache_ttl_sec))
    cache_key = f"hive_mind:project_shape:{tenant_id}:{cap}"
    if cache_ttl > 0:
        try:
            cached = await get_json(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass
    try:
        payload = await bounded_tenant_project_shape_snapshot(tenant_id=tenant_id, limit_nodes=cap)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "hive_mind.project_shape.degraded",
            agent_id="hive_mind_graph",
            swarm_id=str(tenant_id),
            task_id=f"project_shape:{tenant_id}",
            error=str(exc),
        )
        payload = {"nodes": [], "edges": [], "degraded": True, "tenant_id": str(tenant_id), "shape": "project"}
    if cache_ttl > 0:
        try:
            await set_json(cache_key, payload, ttl=cache_ttl)
        except Exception:
            pass
    return payload


async def _assert_selective_recall_feature(db: DbSession, principal: dict[str, Any]) -> uuid.UUID:
    """Gate selective recall settings behind platform feature."""

    if not settings.hive_mind_selective_recall_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Selective recall is disabled on this deployment.",
        )
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant not found.")
    subscription = await ensure_tenant_subscription(db, tenant_id=tenant_id)
    role = str(principal.get("tenant_role") or "guest")
    features = resolve_platform_features_for_subscription(
        platform_mode=str(tenant.platform_mode or "internal"),
        is_admin=role in {"owner", "admin"},
        subscription=subscription,
    )
    if not features.get("selective_recall"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Selective recall requires Pro tier or internal operator mode.",
        )
    return tenant_id


@router.get("/recall-settings", response_model=HiveMindRecallSettingsResponse, summary="HiveMind recall mode settings")
async def get_recall_settings(
    db: DbSession,
    settings: SettingsDep,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> HiveMindRecallSettingsResponse:
    """Return tenant selective recall mode and token budget."""

    tenant_id = await _assert_selective_recall_feature(db, principal)
    cfg = await load_recall_config(db, tenant_id=tenant_id)
    return HiveMindRecallSettingsResponse(
        recall_mode=str(cfg.get("recall_mode") or "selective"),
        token_budget_chars=int(cfg.get("token_budget_chars") or 0),
        feature_enabled=bool(cfg.get("feature_enabled", True)),
        max_prompt_chars=settings.hive_mind_max_prompt_chars,
        selective_max_chars=settings.hive_mind_selective_recall_max_chars,
    )


@router.put("/recall-settings", response_model=HiveMindRecallSettingsResponse, summary="Update HiveMind recall settings")
async def update_recall_settings(
    body: HiveMindRecallSettingsUpdateBody,
    db: DbSession,
    settings: SettingsDep,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> HiveMindRecallSettingsResponse:
    """Patch recall mode / token budget for active tenant."""

    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin tenant role required.")
    tenant_id = await _assert_selective_recall_feature(db, principal)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

    patch: dict[str, Any] = {}
    if body.recall_mode is not None:
        patch["recall_mode"] = normalize_recall_mode(body.recall_mode)
    if body.token_budget_chars is not None:
        patch["token_budget_chars"] = int(body.token_budget_chars)

    tenant.operator_settings = merge_recall_patch(tenant.operator_settings, patch)
    await db.commit()
    await db.refresh(tenant)
    cfg = await load_recall_config(db, tenant_id=tenant_id)
    return HiveMindRecallSettingsResponse(
        recall_mode=str(cfg["recall_mode"]),
        token_budget_chars=int(cfg.get("token_budget_chars") or 0),
        feature_enabled=True,
        max_prompt_chars=settings.hive_mind_max_prompt_chars,
        selective_max_chars=settings.hive_mind_selective_recall_max_chars,
    )


@router.get("/recall-preview", summary="Preview selective recall block for a query")
async def recall_preview(
    db: DbSession,
    settings: SettingsDep,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    q: str = Query(min_length=2, max_length=2400),
) -> dict[str, Any]:
    """Return assembled recall markdown + char count for operator QA."""

    tenant_id = await _assert_selective_recall_feature(db, principal)
    cfg = await load_recall_config(db, tenant_id=tenant_id)
    budget = effective_prompt_char_budget(
        recall_mode=normalize_recall_mode(cfg.get("recall_mode")),
        tenant_budget=int(cfg.get("token_budget_chars") or 0),
        settings_max_prompt=settings.hive_mind_max_prompt_chars,
        selective_max_chars=settings.hive_mind_selective_recall_max_chars,
    )
    text = await HiveMindService.query_for_prompt(
        relevance_to_current_task=q.strip(),
        settings=settings,
        swarm_id="dashboard",
        task_id=f"recall-preview:{tenant_id}",
        agent_id="hive-mind-preview",
        tenant_id=tenant_id,
        recall_mode=str(cfg.get("recall_mode") or "selective"),
        token_budget_chars=int(cfg.get("token_budget_chars") or 0),
    )
    return {
        "recall_mode": str(cfg.get("recall_mode") or "selective"),
        "characters": len(text),
        "char_budget": budget,
        "hive_mind_prompt_block": text,
    }


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
    capped = min(limit, settings.hive_mind_max_query_hits_vector)
    cache_ttl = max(0, int(settings.hive_mind_search_cache_ttl_sec))
    cache_key = f"hive_mind:search:{capped}:{clipped.lower()}"
    if cache_ttl > 0:
        try:
            cached = await get_json(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass
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
    payload = {"items": sanitized, "query": clipped}
    if cache_ttl > 0:
        try:
            await set_json(cache_key, payload, ttl=cache_ttl)
        except Exception:
            pass
    return payload


@router.post("/query")
async def hive_query_debug(
    body: HiveMindRecallBody,
    db: DbSession,
    sess: DashboardSession,
    settings: SettingsDep,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Operator parity with Ballroom HiveMind appendix — inspect clip lengths."""

    uid = _dashboard_principal(sess)
    tenant_id = principal.get("tenant_id")
    recall_mode = None
    cfg: dict[str, Any] = {}
    if tenant_id is not None and settings.hive_mind_selective_recall_enabled:
        cfg = await load_recall_config(db, tenant_id=tenant_id)
        recall_mode = str(cfg.get("recall_mode") or settings.hive_mind_default_recall_mode)
    text = await HiveMindService.query_for_prompt(
        relevance_to_current_task=body.relevance_to_current_task.strip(),
        settings=settings,
        swarm_id="dashboard",
        task_id=f"hive-mind-debug:{uid}",
        agent_id=str(uid),
        tenant_id=tenant_id,
        recall_mode=recall_mode,
        token_budget_chars=int(cfg.get("token_budget_chars") or 0),
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


@router.post(
    "/memory-evolution/run",
    response_model=MemoryEvolutionRunResponse,
    summary="Run long-term memory consolidation + swarm learning cycle",
)
async def run_memory_evolution(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    _: bool = Depends(require_tenant_permission("team:manage")),
) -> MemoryEvolutionRunResponse:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    user_id = principal.get("user").id if principal.get("user") is not None else None
    result = await run_memory_evolution_for_tenant(
        db,
        tenant_id=tenant_id,
        proposed_by_user_id=user_id,
    )
    await db.commit()
    return MemoryEvolutionRunResponse(
        tenant_id=str(result.tenant_id),
        generated_lessons=result.generated_lessons,
        pending_approval=result.pending_approval,
        auto_applied=result.auto_applied,
        swarm_learning_entries=result.swarm_learning_entries,
        history_consolidations=result.history_consolidations,
    )


@router.get(
    "/memory-evolution/proposals",
    response_model=list[MemoryEvolutionProposalView],
    summary="List memory evolution proposals for active tenant",
)
async def list_memory_evolution_changes(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    _: bool = Depends(require_tenant_permission("team:manage")),
    status_filter: str | None = Query(default=None, max_length=24),
    limit: int = Query(default=60, ge=1, le=200),
) -> list[MemoryEvolutionProposalView]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    rows = await list_memory_evolution_proposals(
        db,
        tenant_id=tenant_id,
        status_filter=status_filter,
        limit=limit,
    )
    return [_serialize_proposal(row) for row in rows]


@router.post(
    "/memory-evolution/proposals/{proposal_id}/approve",
    response_model=MemoryEvolutionProposalView,
    summary="Approve memory evolution proposal",
)
async def approve_memory_evolution_change(
    proposal_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    _: bool = Depends(require_tenant_permission("team:manage")),
) -> MemoryEvolutionProposalView:
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    proposal = await db.scalar(
        select(MemoryEvolutionProposal).where(
            MemoryEvolutionProposal.id == proposal_id,
            MemoryEvolutionProposal.tenant_id == tenant_id,
        ),
    )
    if proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found.")
    await approve_memory_evolution_proposal(db, proposal=proposal, approver_user_id=user.id)
    await db.commit()
    await db.refresh(proposal)
    return _serialize_proposal(proposal)


@router.post(
    "/memory-evolution/proposals/{proposal_id}/reject",
    response_model=MemoryEvolutionProposalView,
    summary="Reject memory evolution proposal",
)
async def reject_memory_evolution_change(
    proposal_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    _: bool = Depends(require_tenant_permission("team:manage")),
) -> MemoryEvolutionProposalView:
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    proposal = await db.scalar(
        select(MemoryEvolutionProposal).where(
            MemoryEvolutionProposal.id == proposal_id,
            MemoryEvolutionProposal.tenant_id == tenant_id,
        ),
    )
    if proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found.")
    await reject_memory_evolution_proposal(db, proposal=proposal, approver_user_id=user.id)
    await db.commit()
    await db.refresh(proposal)
    return _serialize_proposal(proposal)
