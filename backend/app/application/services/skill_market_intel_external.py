"""External Skill Market Intel — Tavily/Serper live search + optional Apify scrape."""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.research_runtime_credentials import resolve_research_keys
from app.core.config import settings

logger = structlog.get_logger(__name__)

_DEFAULT_APIFY_SEARCH_ACTOR = "apify~google-search-scraper"

_EXTERNAL_QUERY_SUFFIXES: tuple[str, ...] = (
    "cursor agent skill gumroad marketplace",
    "n8n workflow template sell",
    "AI skill pack github agents",
)

_MARKET_SIGNAL_RE = re.compile(
    r"\b(gumroad|github|marketplace|template|workflow|skill|pack|€|\$|price|buyers?|demand)\b",
    re.IGNORECASE,
)


def _parse_serper_lines(raw: str) -> list[dict[str, Any]]:
    """Extract structured refs from serper tool output."""

    refs: list[dict[str, Any]] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        if not _MARKET_SIGNAL_RE.search(stripped):
            continue
        refs.append(
            {
                "kind": "external_serper",
                "excerpt": stripped[:180],
                "keyword_hits": len(_MARKET_SIGNAL_RE.findall(stripped)),
            },
        )
    return refs


def _parse_tavily_blob(raw: str) -> list[dict[str, Any]]:
    """Extract structured refs from tavily tool output."""

    refs: list[dict[str, Any]] = []
    for chunk in raw.split("\n"):
        stripped = chunk.strip()
        if len(stripped) < 24:
            continue
        if not _MARKET_SIGNAL_RE.search(stripped):
            continue
        refs.append(
            {
                "kind": "external_tavily",
                "excerpt": stripped[:180],
                "keyword_hits": len(_MARKET_SIGNAL_RE.findall(stripped)),
            },
        )
    return refs


async def _search_serper(*, client: httpx.AsyncClient, query: str, api_key: str) -> list[dict[str, Any]]:
    """Run one Serper query and normalize hits."""

    try:
        response = await client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": 5},
            timeout=12.0,
        )
        response.raise_for_status()
        data = response.json()
        organic = data.get("organic") if isinstance(data, dict) else None
        lines: list[str] = []
        if isinstance(organic, list):
            for hit in organic[:5]:
                if isinstance(hit, dict):
                    title = str(hit.get("title", ""))
                    link = str(hit.get("link", ""))
                    snippet = str(hit.get("snippet", ""))[:200]
                    lines.append(f"- {title} :: {snippet} ({link})")
        return _parse_serper_lines("\n".join(lines))
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.debug(
            "skill_market_intel_external.serper_failed",
            agent_id="skill_market_intel_external",
            query=query[:80],
            reason=str(exc),
        )
        return []


async def _search_tavily(*, client: httpx.AsyncClient, query: str, api_key: str) -> list[dict[str, Any]]:
    """Run one Tavily query and normalize hits."""

    try:
        response = await client.post(
            "https://api.tavily.com/search",
            json={"api_key": api_key, "query": query, "search_depth": "basic", "max_results": 5},
            timeout=12.0,
        )
        response.raise_for_status()
        blob = response.json()
        results = blob.get("results") if isinstance(blob, dict) else None
        lines: list[str] = []
        if isinstance(results, list):
            for row in results[:5]:
                if isinstance(row, dict):
                    lines.append(str(row.get("content") or row.get("url") or row))
        return _parse_tavily_blob("\n".join(lines))
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.debug(
            "skill_market_intel_external.tavily_failed",
            agent_id="skill_market_intel_external",
            query=query[:80],
            reason=str(exc),
        )
        return []


def _parse_apify_search_results(raw: str) -> list[dict[str, Any]]:
    """Normalize Apify Google Search Scraper run-sync output."""

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        if not _MARKET_SIGNAL_RE.search(raw):
            return []
        return [
            {
                "kind": "external_apify_scrape",
                "excerpt": raw.strip()[:180],
                "keyword_hits": len(_MARKET_SIGNAL_RE.findall(raw)),
            },
        ]

    rows: list[Any] = []
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        for key in ("organicResults", "results", "items", "data"):
            block = payload.get(key)
            if isinstance(block, list):
                rows = block
                break

    refs: list[dict[str, Any]] = []
    for row in rows[:10]:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or row.get("name") or "")
        desc = str(row.get("description") or row.get("snippet") or row.get("text") or "")
        url = str(row.get("url") or row.get("link") or "")
        blob = f"{title} {desc} {url}".strip()
        if len(blob) < 20:
            continue
        if not _MARKET_SIGNAL_RE.search(blob):
            continue
        refs.append(
            {
                "kind": "external_apify_scrape",
                "excerpt": f"{title[:72]} — {desc[:72]}".strip(" —"),
                "url": url[:240] or None,
                "keyword_hits": len(_MARKET_SIGNAL_RE.findall(blob)),
            },
        )
    return refs


async def apify_connector_ready(session: AsyncSession | None) -> bool:
    """Return True when tenant Apify store connector is active."""

    if session is None:
        return False
    from app.infrastructure.connectors.dynamic.service import DynamicConnectorService

    row = await DynamicConnectorService().fetch_by_slug(session, slug="apify_store")
    return row is not None and row.is_active


async def _persist_apify_intel_rows(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    niche: str,
    refs: list[dict[str, Any]],
) -> None:
    """Persist Apify scrape excerpts into Knowledge for HiveMind embed."""

    if not refs:
        return
    from app.infrastructure.persistence.models.knowledge import KnowledgeItem

    lines = [f"- {item.get('excerpt', '')}" for item in refs[:6] if item.get("excerpt")]
    if not lines:
        return
    blob = f"Skill market Apify intel — niche: {niche[:120]}\n\n" + "\n".join(lines)
    session.add(
        KnowledgeItem(
            tenant_id=tenant_id,
            source_type="skill_market_apify",
            source_url=f"apify://skill-factory/{niche[:80]}",
            content_text=blob[:12_000],
            confidence_score=0.74,
            topic_tags=["skill-market", "skill-market-intel", "apify"],
            decay_factor=1.0,
            scraped_at=datetime.now(tz=UTC),
        ),
    )
    await session.flush()


async def _apify_deep_market_scrape(
    session: AsyncSession,
    *,
    niche: str,
    tenant_id: uuid.UUID | None,
) -> list[dict[str, Any]]:
    """Run Apify Google Search Scraper for Gumroad/GitHub marketplace signals."""

    if not await apify_connector_ready(session):
        return []

    from app.infrastructure.connectors.dynamic.service import invoke_dynamic_tool

    query = f"{niche.strip()} gumroad OR github AI skill pack marketplace"
    raw = await invoke_dynamic_tool(
        session,
        connector_slug="apify_store",
        tool_name="actor_run_sync",
        arguments={
            "actorId": _DEFAULT_APIFY_SEARCH_ACTOR,
            "queries": query[:240],
            "maxPagesPerQuery": 1,
            "resultsPerPage": 6,
            "languageCode": "en",
        },
        manager_slug="research_intelligence",
        agent_task_id="skill_factory_apify_deep",
        granted_permissions=frozenset({"tool:read", "tool:write"}),
    )
    if raw.startswith("dynamic_invoke_error") or raw.startswith("dynamic_invoke_http"):
        logger.warning(
            "skill_market_intel_external.apify_deep_failed",
            agent_id="skill_market_intel_external",
            swarm_id=str(tenant_id or ""),
            reason=raw[:120],
        )
        return []

    refs = _parse_apify_search_results(raw)
    if refs and tenant_id is not None:
        await _persist_apify_intel_rows(session, tenant_id=tenant_id, niche=niche, refs=refs)
        logger.info(
            "skill_market_intel_external.apify_deep_complete",
            agent_id="skill_market_intel_external",
            swarm_id=str(tenant_id),
            niche=niche[:80],
            hits=len(refs),
        )
    return refs


async def _apify_market_probe(session: AsyncSession | None) -> list[dict[str, Any]]:
    """Light Apify actors_list probe when connector is configured."""

    if session is None or not settings.skill_factory_apify_probe_enabled:
        return []

    from app.infrastructure.connectors.dynamic.service import DynamicConnectorService, invoke_dynamic_tool

    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug="apify_store")
    if row is None or not row.is_active:
        return []

    raw = await invoke_dynamic_tool(
        session,
        connector_slug="apify_store",
        tool_name="actors_list",
        arguments={"search": "gumroad scraper", "limit": 3},
        manager_slug="research_intelligence",
        agent_task_id="skill_factory_research",
    )
    if raw.startswith("dynamic_invoke_error"):
        return []

    try:
        payload = json.loads(raw) if raw.strip().startswith("{") or raw.strip().startswith("[") else None
    except json.JSONDecodeError:
        payload = None

    count = 0
    if isinstance(payload, dict):
        items = payload.get("data") or payload.get("items") or []
        if isinstance(items, list):
            count = len(items)
    elif isinstance(payload, list):
        count = len(payload)

    if count <= 0 and "actor" not in raw.lower():
        return []

    return [
        {
            "kind": "external_apify",
            "excerpt": f"Apify store reachable — {count or 'multiple'} scraper actors for market intel",
            "keyword_hits": 2,
        },
    ]


async def gather_external_skill_market_intel(
    *,
    niche: str,
    session: AsyncSession | None = None,
    tenant_id: uuid.UUID | None = None,
    apify_deep_scrape_enabled: bool = False,
    apify_deep_budget: list[int] | None = None,
) -> dict[str, Any]:
    """Collect live web market signals via Tavily/Serper (+ optional Apify scrape).

    Args:
        niche: Operator niche seed.
        session: DB session for Apify connector + Knowledge persist.
        tenant_id: Tenant scope for Knowledge rows.
        apify_deep_scrape_enabled: Tenant policy — run actor_run_sync (costs Apify credits).
        apify_deep_budget: Mutable single-element list counter shared across one research run.

    Returns:
        Dict with ``intel_hits``, ``demand_boost``, ``source_refs``, ``providers_used``.
    """

    if not settings.skill_factory_external_intel_enabled:
        return {"intel_hits": 0, "demand_boost": 0.0, "source_refs": [], "providers_used": []}

    niche_clean = niche.strip()
    if len(niche_clean) < 3:
        return {"intel_hits": 0, "demand_boost": 0.0, "source_refs": [], "providers_used": []}

    keys: dict[str, str] = {}
    if session is not None:
        keys = await resolve_research_keys(session)
    if not keys:
        for provider, env_name in (("tavily", "TAVILY_API_KEY"), ("serper", "SERPER_API_KEY")):
            val = os.getenv(env_name, "").strip()
            if val:
                keys[provider] = val

    queries = [niche_clean, *[f"{niche_clean} {suffix}" for suffix in _EXTERNAL_QUERY_SUFFIXES]]
    refs: list[dict[str, Any]] = []
    providers_used: list[str] = []

    if keys:
        async with httpx.AsyncClient() as client:
            for query in queries[:3]:
                serper_key = keys.get("serper", "").strip()
                if serper_key:
                    batch = await _search_serper(client=client, query=query, api_key=serper_key)
                    if batch:
                        providers_used.append("serper")
                        refs.extend(batch)
                tavily_key = keys.get("tavily", "").strip()
                if tavily_key:
                    batch = await _search_tavily(client=client, query=query, api_key=tavily_key)
                    if batch:
                        providers_used.append("tavily")
                        refs.extend(batch)

    budget = apify_deep_budget if apify_deep_budget is not None else [0]
    max_deep = settings.skill_factory_apify_deep_scrape_max_per_run
    if (
        apify_deep_scrape_enabled
        and max_deep > 0
        and budget[0] < max_deep
        and session is not None
    ):
        deep_refs = await _apify_deep_market_scrape(session, niche=niche_clean, tenant_id=tenant_id)
        if deep_refs:
            budget[0] += 1
            providers_used.append("apify_deep")
            refs.extend(deep_refs)
    elif settings.skill_factory_apify_probe_enabled:
        apify_refs = await _apify_market_probe(session)
        if apify_refs:
            providers_used.append("apify")
            refs.extend(apify_refs)

    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for row in refs:
        key = str(row.get("excerpt", ""))[:100]
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    intel_hits = len(deduped)
    keyword_score = sum(int(item.get("keyword_hits") or 0) for item in deduped)
    demand_boost = min(0.50, intel_hits * 0.07 + keyword_score * 0.012)

    if intel_hits:
        logger.info(
            "skill_market_intel_external.complete",
            agent_id="skill_market_intel_external",
            niche=niche_clean[:80],
            intel_hits=intel_hits,
            providers=providers_used,
        )

    return {
        "intel_hits": intel_hits,
        "demand_boost": demand_boost,
        "source_refs": deduped[:8],
        "providers_used": list(dict.fromkeys(providers_used)),
    }


__all__ = ["apify_connector_ready", "gather_external_skill_market_intel", "_parse_apify_search_results"]
