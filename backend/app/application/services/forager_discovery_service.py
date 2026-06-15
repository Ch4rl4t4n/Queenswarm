"""DG6 — Discovery-first scrape: Serper/Tavily URL find → bind forager."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.data_monitor_wizard_service import (
    DataMonitorSubmitIn,
    submit_data_monitor_wizard,
)
from app.application.services.forager_service import ForagerService
from app.application.services.research_runtime_credentials import resolve_research_keys, research_key_status
from app.application.services.social_intel_runner import append_forager_sources
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)

UrlKind = Literal["rss", "youtube", "twitter", "web"]

_YOUTUBE_HOSTS = frozenset({"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"})
_TWITTER_HOSTS = frozenset({"twitter.com", "www.twitter.com", "x.com", "www.x.com"})
_RSS_HINT_RE = re.compile(r"(/feed|/rss|\.xml$|/atom)", re.IGNORECASE)


class ForagerDiscoveryUrlHit(BaseModel):
    """One discovered URL row."""

    model_config = ConfigDict(extra="forbid")

    url: str
    title: str
    snippet: str = ""
    provider: str
    url_kind: UrlKind


class ForagerDiscoveryWizardOut(BaseModel):
    """Wizard snapshot for Foragers discovery panel."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    generated_at: datetime
    keys_configured: bool = False
    tavily_configured: bool = False
    serper_configured: bool = False
    max_urls: int = 12
    operator_hint: str = "Search with Tavily or Serper, then bind URLs to a forager."


class ForagerDiscoverySearchOut(BaseModel):
    """Discovery search results."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    query: str
    hits: list[ForagerDiscoveryUrlHit] = Field(default_factory=list)
    providers_used: list[str] = Field(default_factory=list)
    keys_configured: bool = False
    operator_hint: str = ""


class ForagerDiscoveryBindIn(BaseModel):
    """Bind discovered URLs to an existing or new forager."""

    model_config = ConfigDict(extra="forbid")

    forager_id: uuid.UUID | None = None
    urls: list[str] = Field(min_length=1, max_length=24)
    intent: str | None = Field(default=None, max_length=2000)
    schedule_preset: Literal["6h", "12h", "24h", "daily_6utc"] = Field(default="24h")
    trigger_first_run: bool = Field(default=True)


class ForagerDiscoveryBindOut(BaseModel):
    """Bind acknowledgement."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    forager_id: str
    forager_name: str
    bound_count: int = 0
    skipped_count: int = 0
    created: bool = False
    message: str = ""


def classify_discovery_url(url: str) -> UrlKind:
    """Classify URL for forager source_config binding."""

    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    if host in _YOUTUBE_HOSTS:
        return "youtube"
    if host in _TWITTER_HOSTS:
        return "twitter"
    if _RSS_HINT_RE.search(path) or url.lower().endswith(".xml"):
        return "rss"
    return "web"


def _normalize_url(url: str) -> str:
    cleaned = url.strip()
    if cleaned and not cleaned.startswith(("http://", "https://")):
        return f"https://{cleaned}"
    return cleaned


async def compose_forager_discovery_wizard_snapshot(session: AsyncSession) -> ForagerDiscoveryWizardOut:
    """Return discovery wizard metadata and key status."""

    if not settings.forager_discovery_enabled:
        return ForagerDiscoveryWizardOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )
    status = await research_key_status(session)
    tavily = bool(status.get("tavily", {}).get("configured"))
    serper = bool(status.get("serper", {}).get("configured"))
    return ForagerDiscoveryWizardOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        keys_configured=tavily or serper,
        tavily_configured=tavily,
        serper_configured=serper,
        max_urls=int(settings.forager_discovery_max_urls),
        operator_hint="Discover public URLs via Serper/Tavily, then bind feeds or channels to a forager.",
    )


async def _search_serper_hits(
    *,
    client: httpx.AsyncClient,
    query: str,
    api_key: str,
    limit: int,
) -> list[ForagerDiscoveryUrlHit]:
    """Return Serper organic hits as discovery rows."""

    try:
        response = await client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": min(limit, 10)},
            timeout=12.0,
        )
        response.raise_for_status()
        data = response.json()
        organic = data.get("organic") if isinstance(data, dict) else None
        hits: list[ForagerDiscoveryUrlHit] = []
        if isinstance(organic, list):
            for row in organic[:limit]:
                if not isinstance(row, dict):
                    continue
                link = _normalize_url(str(row.get("link") or ""))
                if not link:
                    continue
                hits.append(
                    ForagerDiscoveryUrlHit(
                        url=link,
                        title=str(row.get("title") or link)[:200],
                        snippet=str(row.get("snippet") or "")[:280],
                        provider="serper",
                        url_kind=classify_discovery_url(link),
                    ),
                )
        return hits
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        _logger.debug("forager.discovery.serper_failed", reason=str(exc))
        return []


async def _search_tavily_hits(
    *,
    client: httpx.AsyncClient,
    query: str,
    api_key: str,
    limit: int,
) -> list[ForagerDiscoveryUrlHit]:
    """Return Tavily hits as discovery rows."""

    try:
        response = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": min(limit, 10),
            },
            timeout=12.0,
        )
        response.raise_for_status()
        blob = response.json()
        results = blob.get("results") if isinstance(blob, dict) else None
        hits: list[ForagerDiscoveryUrlHit] = []
        if isinstance(results, list):
            for row in results[:limit]:
                if not isinstance(row, dict):
                    continue
                link = _normalize_url(str(row.get("url") or ""))
                if not link:
                    continue
                hits.append(
                    ForagerDiscoveryUrlHit(
                        url=link,
                        title=str(row.get("title") or link)[:200],
                        snippet=str(row.get("content") or "")[:280],
                        provider="tavily",
                        url_kind=classify_discovery_url(link),
                    ),
                )
        return hits
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        _logger.debug("forager.discovery.tavily_failed", reason=str(exc))
        return []


async def search_forager_discovery_urls(
    session: AsyncSession,
    *,
    query: str,
    limit: int = 8,
) -> ForagerDiscoverySearchOut:
    """Discover candidate monitor URLs via Serper/Tavily."""

    trimmed = query.strip()
    cap = max(1, min(limit, int(settings.forager_discovery_max_urls)))
    if not settings.forager_discovery_enabled:
        return ForagerDiscoverySearchOut(enabled=False, query=trimmed, operator_hint="Discovery disabled.")
    if len(trimmed) < 4:
        return ForagerDiscoverySearchOut(
            enabled=True,
            query=trimmed,
            operator_hint="Enter at least 4 characters to search.",
        )

    keys = await resolve_research_keys(session)
    keys_configured = bool(keys)
    if not keys_configured:
        return ForagerDiscoverySearchOut(
            enabled=True,
            query=trimmed,
            keys_configured=False,
            operator_hint="Add Tavily or Serper keys in Settings → Integrations → Research keys.",
        )

    providers_used: list[str] = []
    merged: list[ForagerDiscoveryUrlHit] = []
    seen: set[str] = set()

    async with httpx.AsyncClient() as client:
        serper_key = keys.get("serper", "").strip()
        if serper_key:
            for hit in await _search_serper_hits(client=client, query=trimmed, api_key=serper_key, limit=cap):
                key = hit.url.lower()
                if key in seen:
                    continue
                seen.add(key)
                merged.append(hit)
                providers_used.append("serper")
        tavily_key = keys.get("tavily", "").strip()
        if tavily_key and len(merged) < cap:
            for hit in await _search_tavily_hits(
                client=client,
                query=trimmed,
                api_key=tavily_key,
                limit=cap - len(merged),
            ):
                key = hit.url.lower()
                if key in seen:
                    continue
                seen.add(key)
                merged.append(hit)
                providers_used.append("tavily")

    _logger.info(
        "forager.discovery_search",
        agent_id="forager_hub",
        query_chars=len(trimmed),
        hit_count=len(merged),
        providers=list(dict.fromkeys(providers_used)),
    )
    return ForagerDiscoverySearchOut(
        enabled=True,
        query=trimmed,
        hits=merged[:cap],
        providers_used=list(dict.fromkeys(providers_used)),
        keys_configured=True,
        operator_hint="Select URLs and bind to an existing forager or create a new monitor.",
    )


def _merge_feed_urls(source_config: dict[str, Any], urls: list[str]) -> tuple[dict[str, Any], int]:
    """Append unique feed/web URLs to RSS forager config."""

    cfg = dict(source_config or {})
    feeds_raw = cfg.get("feeds") or []
    if isinstance(feeds_raw, str):
        feeds = [line.strip() for line in feeds_raw.splitlines() if line.strip()]
    else:
        feeds = [str(item).strip() for item in list(feeds_raw) if str(item).strip()]
    seen = {item.lower() for item in feeds}
    bound = 0
    for raw in urls:
        url = _normalize_url(raw)
        if not url or url.lower() in seen:
            continue
        seen.add(url.lower())
        feeds.append(url)
        bound += 1
    cfg["feeds"] = feeds
    return cfg, bound


async def bind_discovery_urls_to_forager(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    urls: list[str],
) -> tuple[int, int]:
    """Merge discovered URLs into one forager source_config."""

    service = ForagerService(db=session)
    row = await service.get_by_id(tenant_id, forager_id)
    if row is None:
        raise ValueError("forager_not_found")

    youtube_urls: list[str] = []
    twitter_urls: list[str] = []
    feed_urls: list[str] = []
    for raw in urls:
        url = _normalize_url(raw)
        if not url:
            continue
        kind = classify_discovery_url(url)
        if kind == "youtube":
            youtube_urls.append(url)
        elif kind == "twitter":
            twitter_urls.append(url)
        else:
            feed_urls.append(url)

    bound = 0
    skipped = 0

    if youtube_urls and row.source_type in {"youtube", "rss", "free_api", "custom"}:
        updated = await append_forager_sources(
            session,
            tenant_id=tenant_id,
            forager_id=forager_id,
            platform="youtube",
            sources=youtube_urls,
        )
        if updated is not None:
            bound += len(youtube_urls)
            row = updated
    if twitter_urls and row.source_type in {"twitter", "x", "rss", "free_api", "custom"}:
        updated = await append_forager_sources(
            session,
            tenant_id=tenant_id,
            forager_id=forager_id,
            platform="x",
            sources=twitter_urls,
        )
        if updated is not None:
            bound += len(twitter_urls)
            row = updated

    if feed_urls:
        cfg, feed_bound = _merge_feed_urls(dict(row.source_config or {}), feed_urls)
        row.source_config = cfg
        bound += feed_bound
        await session.flush()

    filter_cfg = dict(row.filter_config or {})
    filter_cfg["discovery_bound_urls"] = list(dict.fromkeys(urls))[:24]
    row.filter_config = filter_cfg
    await session.flush()
    skipped = max(0, len(urls) - bound)
    return bound, skipped


async def submit_forager_discovery_bind(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    body: ForagerDiscoveryBindIn,
    created_by_subject: str | None,
) -> ForagerDiscoveryBindOut:
    """Bind URLs to existing forager or create one via Data Monitor wizard."""

    if not settings.forager_discovery_enabled:
        raise ValueError("forager_discovery_disabled")

    cleaned_urls = [_normalize_url(url) for url in body.urls if str(url).strip()]
    cleaned_urls = [url for url in cleaned_urls if url]
    if not cleaned_urls:
        raise ValueError("urls_empty")

    created = False
    forager_id = body.forager_id
    forager_name = ""

    if forager_id is None:
        intent = (body.intent or f"Monitor discovered sources for: {cleaned_urls[0]}").strip()
        if len(intent) < 12:
            intent = f"Monitor discovered URLs — {intent}"
        create_out = await submit_data_monitor_wizard(
            session,
            tenant_id=tenant_id,
            body=DataMonitorSubmitIn(
                intent=intent[:2000],
                schedule_preset=body.schedule_preset,
                trigger_first_run=False,
            ),
            created_by_subject=created_by_subject,
        )
        forager_id = uuid.UUID(create_out.forager_id)
        forager_name = create_out.forager_name
        created = True
    else:
        service = ForagerService(db=session)
        row = await service.get_by_id(tenant_id, forager_id)
        if row is None:
            raise ValueError("forager_not_found")
        forager_name = row.name

    bound, skipped = await bind_discovery_urls_to_forager(
        session,
        tenant_id=tenant_id,
        forager_id=forager_id,
        urls=cleaned_urls,
    )

    if body.trigger_first_run:
        service = ForagerService(db=session)
        await service.trigger_manual_run(
            tenant_id=tenant_id,
            forager_id=forager_id,
            records=[],
        )

    _logger.info(
        "forager.discovery_bind",
        agent_id="forager_hub",
        swarm_id=str(tenant_id),
        forager_id=str(forager_id),
        bound=bound,
        created=created,
    )
    action = "Created monitor and bound" if created else "Bound"
    return ForagerDiscoveryBindOut(
        ok=True,
        forager_id=str(forager_id),
        forager_name=forager_name,
        bound_count=bound,
        skipped_count=skipped,
        created=created,
        message=f"{action} {bound} URL{'s' if bound != 1 else ''} — tune schedule in Forager Edit if needed.",
    )


__all__ = [
    "bind_discovery_urls_to_forager",
    "classify_discovery_url",
    "compose_forager_discovery_wizard_snapshot",
    "ForagerDiscoveryBindIn",
    "ForagerDiscoveryBindOut",
    "ForagerDiscoverySearchOut",
    "ForagerDiscoveryUrlHit",
    "ForagerDiscoveryWizardOut",
    "search_forager_discovery_urls",
    "submit_forager_discovery_bind",
]
