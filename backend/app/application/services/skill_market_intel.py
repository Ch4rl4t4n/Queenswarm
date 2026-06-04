"""Skill Market Intel — HiveMind demand signals for Skill Factory research."""

from __future__ import annotations

import re
import uuid
from typing import Any

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = structlog.get_logger(__name__)

_DEMAND_KEYWORDS: frozenset[str] = frozenset(
    {
        "cursor",
        "skill",
        "skills",
        "agent",
        "workflow",
        "automation",
        "template",
        "n8n",
        "claude",
        "gumroad",
        "marketplace",
        "saas",
        "newsletter",
        "seo",
    },
)

_INTEL_QUERY_SUFFIXES: tuple[str, ...] = (
    "cursor agent skill demand",
    "automation workflow template market",
    "AI skill pack opportunity",
)

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}", re.IGNORECASE)


def _normalize_hits(raw_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate semantic search rows by document id or content prefix."""

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in raw_hits:
        doc_id = str(row.get("id") or row.get("document_id") or "").strip()
        doc = str(row.get("document") or row.get("text") or row.get("content") or "").strip()
        key = doc_id or doc[:120]
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _demand_keyword_hits(text: str) -> int:
    """Count skill-market demand tokens present in a HiveMind excerpt."""

    tokens = {tok.lower() for tok in _TOKEN_RE.findall(text)}
    return sum(1 for keyword in _DEMAND_KEYWORDS if keyword in tokens)


async def _postgres_skill_market_refs(
    session: AsyncSession | None,
    *,
    tenant_id: uuid.UUID | None,
    niche: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Supplement vector intel with tenant Knowledge rows tagged skill-market."""

    if session is None or tenant_id is None:
        return []

    from app.infrastructure.persistence.models.knowledge import KnowledgeItem

    niche_tokens = {tok.lower() for tok in _TOKEN_RE.findall(niche)}
    tag_filters = [
        KnowledgeItem.topic_tags.contains(["skill-market"]),
        KnowledgeItem.topic_tags.contains(["skill_market"]),
    ]
    rows = list(
        (
            await session.scalars(
                select(KnowledgeItem)
                .where(
                    KnowledgeItem.tenant_id == tenant_id,
                    or_(*tag_filters),
                )
                .order_by(KnowledgeItem.scraped_at.desc())
                .limit(max(limit * 3, 12)),
            )
        ).all(),
    )
    refs: list[dict[str, Any]] = []
    for row in rows:
        doc = row.content_text.strip()
        if not doc:
            continue
        doc_tokens = {tok.lower() for tok in _TOKEN_RE.findall(doc)}
        overlap = niche_tokens & doc_tokens if niche_tokens else set()
        if niche_tokens and not overlap:
            continue
        hits = _demand_keyword_hits(doc)
        refs.append(
            {
                "kind": "knowledge_item",
                "keyword_hits": hits,
                "excerpt": doc[:160],
                "tags": [str(tag) for tag in list(row.topic_tags or [])[:6]],
                "source_type": row.source_type,
            },
        )
        if len(refs) >= limit:
            break
    return refs


async def gather_skill_market_intel(
    *,
    niche: str,
    session: AsyncSession | None = None,
    tenant_id: uuid.UUID | None = None,
    apify_deep_scrape_enabled: bool = False,
    apify_deep_budget: list[int] | None = None,
    monid_listing_signals_enabled: bool = False,
    monid_budget: list[int] | None = None,
) -> dict[str, Any]:
    """Collect demand signals for a niche via HiveMind vector probes.

    Args:
        niche: Operator niche seed or auto-generated opportunity label.

    Returns:
        Dict with ``intel_hits``, ``demand_boost``, and ``source_refs`` for scoring.
    """

    niche_clean = niche.strip()
    if len(niche_clean) < 3:
        return {"intel_hits": 0, "demand_boost": 0.0, "source_refs": []}

    try:
        from app.core.chroma_client import HIVE_MIND_COLLECTION, semantic_search
    except Exception:
        return {"intel_hits": 0, "demand_boost": 0.0, "source_refs": []}

    queries = [niche_clean, *[f"{niche_clean} {suffix}" for suffix in _INTEL_QUERY_SUFFIXES]]
    merged: list[dict[str, Any]] = []
    for query in queries[:4]:
        try:
            hits = await semantic_search(query, HIVE_MIND_COLLECTION, n_results=6)
            merged.extend(hits)
        except Exception as exc:
            logger.debug(
                "skill_market_intel.search_failed",
                agent_id="skill_market_intel",
                query=query[:80],
                reason=str(exc),
            )

    rows = _normalize_hits(merged)
    keyword_score = 0
    refs: list[dict[str, Any]] = []
    for row in rows[:12]:
        doc = str(row.get("document") or row.get("text") or row.get("content") or "")
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        tags = meta.get("tags") if isinstance(meta.get("tags"), list) else []
        tag_text = " ".join(str(tag) for tag in tags)
        hits = _demand_keyword_hits(f"{doc} {tag_text}")
        if hits <= 0:
            continue
        keyword_score += hits
        refs.append(
            {
                "kind": "skill_market_intel",
                "keyword_hits": hits,
                "excerpt": doc[:160],
                "tags": [str(tag) for tag in tags[:6]],
            },
        )

    intel_hits = len(refs)
    pg_refs = await _postgres_skill_market_refs(session, tenant_id=tenant_id, niche=niche_clean)
    for item in pg_refs:
        if item not in refs:
            refs.append(item)
    intel_hits = len(refs)

    from app.application.services.skill_market_intel_external import gather_external_skill_market_intel

    external = await gather_external_skill_market_intel(
        niche=niche_clean,
        session=session,
        tenant_id=tenant_id,
        apify_deep_scrape_enabled=apify_deep_scrape_enabled,
        apify_deep_budget=apify_deep_budget,
    )
    ext_refs = external.get("source_refs")
    if isinstance(ext_refs, list):
        for item in ext_refs:
            if isinstance(item, dict) and item not in refs:
                refs.append(item)
    ext_boost = float(external.get("demand_boost") or 0.0)
    intel_hits = len(refs)

    monid_budget = monid_budget if monid_budget is not None else [0]
    max_monid = settings.skill_factory_monid_max_per_run
    if (
        monid_listing_signals_enabled
        and settings.skill_factory_monid_intel_enabled
        and max_monid > 0
        and monid_budget[0] < max_monid
        and session is not None
    ):
        from app.application.services.skill_market_intel_monid import gather_monid_listing_signals

        monid_refs = await gather_monid_listing_signals(session, tenant_id=tenant_id, niche=niche_clean)
        if monid_refs:
            monid_budget[0] += 1
            for item in monid_refs:
                if item not in refs:
                    refs.append(item)

    intel_hits = len(refs)
    monid_boost = min(0.12, sum(int(item.get("keyword_hits") or 0) for item in refs if item.get("kind") == "external_monid_discover") * 0.02)
    demand_boost = min(0.50, intel_hits * 0.06 + keyword_score * 0.015 + ext_boost + monid_boost)
    return {
        "intel_hits": intel_hits,
        "demand_boost": demand_boost,
        "source_refs": refs[:6],
    }


__all__ = ["gather_skill_market_intel"]
