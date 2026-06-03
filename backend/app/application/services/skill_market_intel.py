"""Skill Market Intel — HiveMind demand signals for Skill Factory research."""

from __future__ import annotations

import re
from typing import Any

import structlog

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


async def gather_skill_market_intel(*, niche: str) -> dict[str, Any]:
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
    demand_boost = min(0.35, intel_hits * 0.06 + keyword_score * 0.015)
    return {
        "intel_hits": intel_hits,
        "demand_boost": demand_boost,
        "source_refs": refs[:6],
    }


__all__ = ["gather_skill_market_intel"]
