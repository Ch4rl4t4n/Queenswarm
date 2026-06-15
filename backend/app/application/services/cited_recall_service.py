"""MEM2 — Cited recall panel: answer + source citations or explicit not-in-memory."""

from __future__ import annotations

import re
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.hive_session_search import search_supervisor_sessions
from app.application.services.selective_recall import query_tokens, score_vector_similarity
from app.core.chroma_client import HIVE_MIND_COLLECTION, semantic_search
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.hive_mind.graph import vault_document_recall_for_prompt
from app.domain.memory.curated import CuratedFileKind

_logger = get_logger(__name__)

RecallStatus = Literal["found", "partial", "not_in_memory"]
SourceType = Literal["curated_memory", "hive_mind", "session", "vault"]

_CURATED_LABELS: dict[CuratedFileKind, str] = {
    CuratedFileKind.MISSION: "Brain Pack · Mission",
    CuratedFileKind.IDEAL_STATE: "Brain Pack · Ideal state",
    CuratedFileKind.SOUL: "Brain Pack · Soul",
    CuratedFileKind.SKILLS_HIERARCHY: "Brain Pack · Skills hierarchy",
    CuratedFileKind.INSTRUCTIONS: "Brain Pack · Behavioral instructions",
    CuratedFileKind.BRAND: "Brain Pack · Brand",
}

_MIN_QUERY_LEN = 3
_FOUND_SIMILARITY = 0.62
_PARTIAL_SIMILARITY = 0.35


class CitedRecallSourceOut(BaseModel):
    """One cited memory source for operator drill-down."""

    model_config = ConfigDict(extra="ignore")

    source_id: str
    source_type: SourceType
    label: str
    snippet: str
    similarity: float | None = None
    href: str | None = None


class CitedRecallOut(BaseModel):
    """GBrain-style cited recall answer for operator grill Q&A."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    query: str = ""
    in_memory: bool = False
    status: RecallStatus = "not_in_memory"
    answer: str = ""
    citations: list[CitedRecallSourceOut] = Field(default_factory=list)
    citation_count: int = 0
    operator_hint: str = "Ask a question — cited answer pulls Brain Pack, HiveMind vectors, sessions, and vault."


def _clip(text: str, limit: int = 280) -> str:
    cleaned = " ".join((text or "").strip().split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1]}…"


def _keyword_overlap(query: str, haystack: str) -> float:
    tokens = query_tokens(query)
    if not tokens:
        return 0.0
    blob = haystack.lower()
    hits = sum(1 for token in tokens if token in blob)
    return hits / len(tokens)


def _extract_snippet(text: str, query: str, *, limit: int = 240) -> str:
    lowered = text.lower()
    for token in query_tokens(query):
        idx = lowered.find(token)
        if idx >= 0:
            start = max(0, idx - 60)
            chunk = text[start:start + limit]
            return _clip(chunk, limit)
    return _clip(text, limit)


def _resolve_status(citations: list[CitedRecallSourceOut]) -> RecallStatus:
    if not citations:
        return "not_in_memory"
    top_sim = max((c.similarity or 0.0) for c in citations)
    if top_sim >= _FOUND_SIMILARITY:
        return "found"
    if top_sim >= _PARTIAL_SIMILARITY or len(citations) >= 2:
        return "partial"
    return "partial" if citations else "not_in_memory"


def _build_answer(query: str, citations: list[CitedRecallSourceOut], status: RecallStatus) -> str:
    if status == "not_in_memory":
        return (
            f"Not in memory — no curated Brain Pack, HiveMind vector, session archive, or vault "
            f"entry supports a cited answer for “{query}”."
        )
    lead = citations[0]
    answer = f"{_clip(lead.snippet, 260)}"
    if len(citations) > 1:
        others = ", ".join(c.label for c in citations[1:3])
        suffix = f" (also: {others})" if others else ""
        answer = f"{answer}{suffix}"
    if status == "partial":
        answer = f"Partial recall — verify before acting. {answer}"
    return answer


def _curated_citations(query: str, bundle: dict[CuratedFileKind, str]) -> list[CitedRecallSourceOut]:
    rows: list[CitedRecallSourceOut] = []
    for kind, label in _CURATED_LABELS.items():
        content = str(bundle.get(kind) or "").strip()
        if len(content) < 8:
            continue
        overlap = _keyword_overlap(query, content)
        if overlap <= 0:
            continue
        rows.append(
            CitedRecallSourceOut(
                source_id=f"curated:{kind.value}",
                source_type="curated_memory",
                label=label,
                snippet=_extract_snippet(content, query),
                similarity=round(min(1.0, overlap), 3),
                href="/knowledge?tab=memory#brain-pack",
            ),
        )
    rows.sort(key=lambda row: row.similarity or 0.0, reverse=True)
    return rows[:4]


def _hive_mind_citations(query: str, hits: list[dict]) -> list[CitedRecallSourceOut]:  # noqa: ANN001
    rows: list[CitedRecallSourceOut] = []
    for hit in hits:
        document = str(hit.get("document") or "").strip()
        if len(document) < 8:
            continue
        meta = dict(hit.get("metadata") or {})
        deliverable_id = str(meta.get("deliverable_id") or meta.get("id") or hit.get("id") or "").strip()
        title = str(meta.get("title") or meta.get("slug") or "HiveMind vector").strip()
        sim = score_vector_similarity(hit.get("distance"))
        href = "/knowledge?tab=outputs"
        if deliverable_id:
            href = f"/knowledge?tab=outputs&deliverable={deliverable_id}"
        rows.append(
            CitedRecallSourceOut(
                source_id=f"hive:{deliverable_id or title}",
                source_type="hive_mind",
                label=f"HiveMind · {title}",
                snippet=_extract_snippet(document, query),
                similarity=round(sim, 3),
                href=href,
            ),
        )
    rows.sort(key=lambda row: row.similarity or 0.0, reverse=True)
    return rows[:5]


def _session_citations(query: str, session_hits: list[dict]) -> list[CitedRecallSourceOut]:  # noqa: ANN001
    rows: list[CitedRecallSourceOut] = []
    for hit in session_hits:
        session_id = str(hit.get("session_id") or "").strip()
        if not session_id:
            continue
        snippet = str(hit.get("snippet") or hit.get("goal_excerpt") or "").strip()
        goal = str(hit.get("goal_excerpt") or "").strip()
        overlap = _keyword_overlap(query, f"{goal} {snippet}")
        if overlap <= 0 and not snippet:
            continue
        rows.append(
            CitedRecallSourceOut(
                source_id=f"session:{session_id}",
                source_type="session",
                label=f"Session · {goal[:72] or session_id[:8]}",
                snippet=_clip(snippet or goal, 240),
                similarity=round(min(1.0, max(overlap, 0.4)), 3),
                href=f"/agents?session={session_id}",
            ),
        )
    return rows[:4]


def _vault_citations(query: str, vault_lines: list[str]) -> list[CitedRecallSourceOut]:
    rows: list[CitedRecallSourceOut] = []
    for line in vault_lines:
        cleaned = line.strip().lstrip("-").strip()
        if not cleaned:
            continue
        overlap = _keyword_overlap(query, cleaned)
        if overlap <= 0:
            continue
        rel_match = re.search(r"([\w./-]+\.md)", cleaned)
        rel_path = rel_match.group(1) if rel_match else ""
        label = cleaned.split(":")[0].strip() if ":" in cleaned else "Vault document"
        snippet = cleaned.split(":", 1)[-1].strip() if ":" in cleaned else cleaned
        rows.append(
            CitedRecallSourceOut(
                source_id=f"vault:{rel_path or label}",
                source_type="vault",
                label=label[:80],
                snippet=_clip(snippet, 240),
                similarity=round(min(1.0, overlap), 3),
                href="/knowledge?tab=hivemind#explorer",
            ),
        )
    return rows[:3]


def _merge_citations(candidates: list[CitedRecallSourceOut], *, limit: int = 8) -> list[CitedRecallSourceOut]:
    merged: list[CitedRecallSourceOut] = []
    seen: set[str] = set()
    for row in sorted(candidates, key=lambda item: item.similarity or 0.0, reverse=True):
        if row.source_id in seen:
            continue
        seen.add(row.source_id)
        merged.append(row)
        if len(merged) >= limit:
            break
    return merged


def derive_cited_recall(
    *,
    query: str,
    curated_hits: list[CitedRecallSourceOut],
    hive_hits: list[CitedRecallSourceOut],
    session_hits: list[CitedRecallSourceOut],
    vault_hits: list[CitedRecallSourceOut],
) -> CitedRecallOut:
    """Pure MEM2 cited recall assembly."""

    trimmed = query.strip()
    if len(trimmed) < _MIN_QUERY_LEN:
        return CitedRecallOut(
            enabled=True,
            query=trimmed,
            in_memory=False,
            status="not_in_memory",
            answer="Enter at least 3 characters to search hive memory with citations.",
            operator_hint="Type a question about goals, copy, sessions, or vault notes.",
        )

    citations = _merge_citations([*curated_hits, *hive_hits, *session_hits, *vault_hits])
    status = _resolve_status(citations)
    in_memory = status != "not_in_memory"
    answer = _build_answer(trimmed, citations, status)

    if status == "found":
        hint = "Cited answer ready — open source links to verify before supervisor approve."
    elif status == "partial":
        hint = "Weak or sparse hits — cross-check Brain Pack and session report before trusting answer."
    else:
        hint = "Not in memory — ingest URL, update Brain Pack, or complete a session to capture this topic."

    return CitedRecallOut(
        enabled=True,
        query=trimmed,
        in_memory=in_memory,
        status=status,
        answer=answer,
        citations=citations,
        citation_count=len(citations),
        operator_hint=hint,
    )


async def compose_cited_recall(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    query: str,
) -> CitedRecallOut:
    """Compose MEM2 cited recall from Brain Pack, HiveMind, sessions, and vault."""

    if not settings.cited_recall_panel_enabled:
        return CitedRecallOut(enabled=False)

    trimmed = query.strip()
    if len(trimmed) < _MIN_QUERY_LEN:
        return derive_cited_recall(
            query=trimmed,
            curated_hits=[],
            hive_hits=[],
            session_hits=[],
            vault_hits=[],
        )

    memory_service = CuratedMemoryService(db=session)
    bundle = await memory_service.get_bundle(tenant_id)
    curated_hits = _curated_citations(trimmed, bundle)

    hive_hits: list[CitedRecallSourceOut] = []
    if settings.hive_mind_enabled and settings.hive_mind_chroma_enabled:
        try:
            raw_hits = await semantic_search(
                trimmed[:4000],
                HIVE_MIND_COLLECTION,
                n_results=min(settings.hive_mind_max_query_hits_vector, 8),
            )
            hive_hits = _hive_mind_citations(trimmed, raw_hits)
        except Exception as exc:
            _logger.warning(
                "cited_recall.hive_search_failed",
                agent_id="cited_recall",
                swarm_id=str(tenant_id),
                error=str(exc),
            )

    session_rows = await search_supervisor_sessions(session, tenant_id=tenant_id, query=trimmed, limit=6)
    session_hits = _session_citations(trimmed, session_rows)

    vault_hits: list[CitedRecallSourceOut] = []
    if settings.hive_mind_enabled:
        try:
            vault_lines = await vault_document_recall_for_prompt(
                tenant_id=tenant_id,
                query=trimmed,
                limit=4,
            )
            vault_hits = _vault_citations(trimmed, vault_lines)
        except Exception as exc:
            _logger.warning(
                "cited_recall.vault_failed",
                agent_id="cited_recall",
                swarm_id=str(tenant_id),
                error=str(exc),
            )

    result = derive_cited_recall(
        query=trimmed,
        curated_hits=curated_hits,
        hive_hits=hive_hits,
        session_hits=session_hits,
        vault_hits=vault_hits,
    )
    _logger.info(
        "cited_recall.composed",
        agent_id="cited_recall",
        swarm_id=str(tenant_id),
        status=result.status,
        citation_count=result.citation_count,
    )
    return result


__all__ = [
    "CitedRecallOut",
    "CitedRecallSourceOut",
    "compose_cited_recall",
    "derive_cited_recall",
]
