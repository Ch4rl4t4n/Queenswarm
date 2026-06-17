"""SB4 — Wiki Layer hits for ⌘K mission search (lexical + Chroma re-rank)."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import Text, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.second_brain_capture import parse_capture_fields
from app.core.chroma_client import HIVE_MIND_COLLECTION, semantic_search
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.wiki_layer import WikiLayerPageORM

_logger = get_logger(__name__)

_LEXICAL_RELEVANCE_SCORE = 0.72
_SEMANTIC_MATCH_THRESHOLD = 0.52
_SNIPPET_CAP = 320


def _truncate(text: str, cap: int = _SNIPPET_CAP) -> str:
    if len(text) <= cap:
        return text
    return text[: cap - 1] + "…"


def _wiki_href(*, kind: str, slug: str) -> str:
    if kind == "capture":
        return f"/knowledge?tab=wiki#capture-{slug}"
    return f"/knowledge?tab=wiki#wiki-{slug}"


async def search_mission_wiki_hits(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    query: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Search compiled wiki pages and approved captures for Mission Control ⌘K."""

    if not settings.wiki_layer_enabled or not settings.wiki_layer_mission_search_enabled:
        return []

    needle = (query or "").strip()
    if len(needle) < 2:
        return []

    cap = max(1, min(limit, 20))
    lexical_pages = await _lexical_wiki_page_hits(db, tenant_id=tenant_id, query=needle, limit=cap)
    lexical_captures = await _lexical_capture_hits(db, tenant_id=tenant_id, query=needle, limit=cap)
    lexical = lexical_pages + lexical_captures

    semantic = await _semantic_wiki_hits(db, tenant_id=tenant_id, query=needle, limit=cap)
    merged = _rank_merged_wiki_hits(lexical, semantic, cap=cap)
    return merged


async def _lexical_wiki_page_hits(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Match compiled wiki pages by title, slug, and body."""

    pattern = f"%{query}%"
    rows = list(
        (
            await db.scalars(
                select(WikiLayerPageORM)
                .where(
                    WikiLayerPageORM.tenant_id == tenant_id,
                    or_(
                        WikiLayerPageORM.title.ilike(pattern),
                        WikiLayerPageORM.slug.ilike(pattern),
                        WikiLayerPageORM.content_md.ilike(pattern),
                    ),
                )
                .order_by(desc(WikiLayerPageORM.updated_at))
                .limit(max(1, min(limit, 20))),
            )
        ).all(),
    )
    return [
        {
            "wiki_hit_id": row.slug,
            "kind": "wiki_page",
            "title": row.title,
            "slug": row.slug,
            "snippet": _truncate((row.content_md or "").replace("\n", " ")),
            "href": _wiki_href(kind="wiki_page", slug=row.slug),
            "match_source": "lexical",
            "relevance_score": _LEXICAL_RELEVANCE_SCORE,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]


async def _lexical_capture_hits(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Match approved second-brain captures in raw tier."""

    pattern = f"%{query}%"
    rows = list(
        (
            await db.scalars(
                select(KnowledgeItem)
                .where(
                    KnowledgeItem.tenant_id == tenant_id,
                    KnowledgeItem.source_type == "second_brain_capture",
                    KnowledgeItem.verified_at.isnot(None),
                    or_(
                        KnowledgeItem.content_text.ilike(pattern),
                        KnowledgeItem.topic_tags.cast(Text).ilike(pattern),
                    ),
                )
                .order_by(desc(KnowledgeItem.verified_at))
                .limit(max(1, min(limit, 20))),
            )
        ).all(),
    )
    hits: list[dict[str, Any]] = []
    for row in rows:
        fields = parse_capture_fields(row.content_text)
        idea = str(fields.get("idea") or "Capture").strip() or "Capture"
        slug = str(row.id)
        hits.append(
            {
                "wiki_hit_id": slug,
                "kind": "capture",
                "title": f"Capture · {_truncate(idea, 96)}",
                "slug": slug,
                "snippet": _truncate(idea),
                "href": _wiki_href(kind="capture", slug=slug),
                "match_source": "lexical",
                "relevance_score": _LEXICAL_RELEVANCE_SCORE,
                "updated_at": row.verified_at.isoformat() if row.verified_at else None,
            },
        )
    return hits


async def _semantic_wiki_hits(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Best-effort vector recall over Hive Mind rows tagged for wiki layer."""

    needle = (query or "").strip()
    if len(needle) < 2:
        return []

    cap = max(1, min(limit, 12))
    try:
        raw_hits = await semantic_search(needle, HIVE_MIND_COLLECTION, n_results=cap * 4)
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "mission_wiki_search.semantic_failed",
            agent_id="mission_wiki_search",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return []

    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in raw_hits:
        meta = dict(row.get("metadata") or {})
        if str(meta.get("tenant_id") or "") != str(tenant_id):
            continue

        tags_raw = str(meta.get("tags") or "")
        source = str(meta.get("source") or meta.get("kind") or "")
        is_wiki_tagged = "wiki_layer" in tags_raw or "second_brain" in tags_raw
        knowledge_id_raw = meta.get("knowledge_item_id")
        if not is_wiki_tagged and not knowledge_id_raw:
            continue

        distance = row.get("distance")
        similarity = max(0.0, min(1.0, 1.0 - float(distance))) if distance is not None else 0.0
        if similarity < _SEMANTIC_MATCH_THRESHOLD:
            continue

        if knowledge_id_raw:
            try:
                knowledge_id = uuid.UUID(str(knowledge_id_raw))
            except ValueError:
                continue
            item = await db.get(KnowledgeItem, knowledge_id)
            if item is None or item.tenant_id != tenant_id:
                continue
            if item.source_type == "second_brain_capture":
                if item.verified_at is None:
                    continue
                fields = parse_capture_fields(item.content_text)
                idea = str(fields.get("idea") or "Capture").strip() or "Capture"
                hit_id = str(item.id)
                title = f"Capture · {_truncate(idea, 96)}"
                kind = "capture"
                slug = hit_id
                snippet = str(row.get("document") or idea)[: _SNIPPET_CAP]
            elif "wiki_layer" in tags_raw or item.source_type.endswith("_capture"):
                hit_id = str(item.id)
                title = _truncate(str(row.get("document") or item.content_text).split("\n", 1)[0], 96)
                kind = "capture"
                slug = hit_id
                snippet = _truncate(str(row.get("document") or item.content_text))
            else:
                continue
        else:
            doc = str(row.get("document") or "").strip()
            if not doc:
                continue
            hit_id = f"semantic-{hash(doc) & 0xFFFF_FFFF:x}"
            title = _truncate(doc.split("\n", 1)[0].removeprefix("# ").strip(), 96)
            kind = "wiki_page"
            slug = re.sub(r"[^\w\-]+", "-", title.lower()).strip("-") or hit_id
            snippet = _truncate(doc)

        if hit_id in seen:
            continue
        seen.add(hit_id)
        hits.append(
            {
                "wiki_hit_id": hit_id,
                "kind": kind,
                "title": title,
                "slug": slug,
                "snippet": snippet,
                "href": _wiki_href(kind=kind, slug=slug),
                "match_source": "semantic",
                "similarity": round(similarity, 3),
                "relevance_score": round(similarity, 3),
                "updated_at": None,
            },
        )
        if len(hits) >= cap:
            break
    return hits


def _rank_merged_wiki_hits(
    lexical: list[dict[str, Any]],
    semantic: list[dict[str, Any]],
    *,
    cap: int,
) -> list[dict[str, Any]]:
    """Merge lexical + semantic wiki hits by relevance score."""

    ranked: dict[str, dict[str, Any]] = {}
    for row in lexical:
        entity_id = str(row.get("wiki_hit_id") or "")
        if not entity_id:
            continue
        score = float(row.get("relevance_score") or _LEXICAL_RELEVANCE_SCORE)
        ranked[entity_id] = {**row, "relevance_score": round(score, 3)}

    for row in semantic:
        entity_id = str(row.get("wiki_hit_id") or "")
        if not entity_id:
            continue
        score = float(row.get("relevance_score") or row.get("similarity") or 0.0)
        if entity_id in ranked:
            merged_score = max(float(ranked[entity_id]["relevance_score"]), score)
            ranked[entity_id]["relevance_score"] = round(merged_score, 3)
            ranked[entity_id]["match_source"] = "lexical+semantic"
            if row.get("snippet") and not ranked[entity_id].get("snippet"):
                ranked[entity_id]["snippet"] = row["snippet"]
        else:
            ranked[entity_id] = {**row, "relevance_score": round(score, 3)}

    ordered = sorted(
        ranked.values(),
        key=lambda item: (float(item.get("relevance_score") or 0.0), str(item.get("updated_at") or "")),
        reverse=True,
    )
    return ordered[: max(1, cap)]


__all__ = ["search_mission_wiki_hits"]
