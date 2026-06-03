"""RSS feed scraping for tenant foragers (Pleva, JaHan, …)."""

from __future__ import annotations

import html as html_lib
import re
from typing import Any
from urllib.parse import urlparse

import feedparser
import httpx

from app.core.logging import get_logger
from app.infrastructure.persistence.models.forager import ForagerORM

logger = get_logger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")


def _rss_feed_urls(forager: ForagerORM) -> list[str]:
    """Extract feed URLs from forager ``source_config``."""

    cfg = dict(forager.source_config or {})
    raw = cfg.get("feeds") or cfg.get("urls") or cfg.get("rss_feeds") or []
    if isinstance(raw, str):
        raw = [line.strip() for line in raw.splitlines() if line.strip()]
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _strip_html(text: str) -> str:
    """Remove HTML tags from RSS summary/content."""

    without_tags = _TAG_RE.sub(" ", text)
    return html_lib.unescape(without_tags).strip()


def _entry_external_id(feed_url: str, entry: Any) -> str:
    """Stable id for dedupe within one feed."""

    for attr in ("id", "guid", "link"):
        value = getattr(entry, attr, None) or (entry.get(attr) if isinstance(entry, dict) else None)
        if value:
            return str(value).strip()[:512]
    title = str(getattr(entry, "title", None) or entry.get("title") or "").strip()
    return f"{feed_url}::{title}"[:512]


def rss_item_to_ingest_record(
    *,
    feed_url: str,
    title: str,
    summary: str,
    link: str | None,
    published: str | None,
    default_tags: list[str],
) -> dict[str, Any]:
    """Map one RSS entry to ``ForagerService.ingest_records`` payload."""

    host = urlparse(feed_url).netloc or feed_url
    body = (
        f"# {title}\n\n"
        f"Feed: {feed_url}\n"
        f"Source host: {host}\n"
        f"Published: {published or 'unknown'}\n"
    )
    if link:
        body += f"URL: {link}\n"
    body += f"\n{summary}\n"
    tags = list(dict.fromkeys([*default_tags, "rss", f"feed:{host}", "forager-rss"]))[:32]
    return {
        "source_url": link or feed_url,
        "content_text": body.strip(),
        "confidence_score": 0.7,
        "topic_tags": tags,
        "external_id": f"{feed_url}::{title}"[:512],
    }


async def fetch_rss_feed_records(
    feed_url: str,
    *,
    default_tags: list[str],
    item_limit: int = 12,
    timeout_sec: float = 20.0,
) -> list[dict[str, Any]]:
    """Fetch and parse one RSS/Atom feed into ingest records."""

    try:
        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
            response = await client.get(
                feed_url,
                headers={"User-Agent": "Queenswarm-Forager/1.0 (+https://queenswarm.love)"},
            )
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
    except Exception as exc:
        logger.warning(
            "forager.rss_feed_fetch_failed",
            agent_id="forager_rss",
            feed_url=feed_url,
            error=str(exc)[:300],
        )
        return []

    records: list[dict[str, Any]] = []
    for entry in list(parsed.entries or [])[: max(1, min(item_limit, 30))]:
        title = str(getattr(entry, "title", None) or "").strip() or "RSS item"
        summary_raw = (
            str(getattr(entry, "summary", None) or "")
            or str(getattr(entry, "description", None) or "")
            or title
        )
        summary = _strip_html(summary_raw)[:4000]
        link = str(getattr(entry, "link", None) or "").strip() or None
        published = str(getattr(entry, "published", None) or getattr(entry, "updated", None) or "").strip() or None
        records.append(
            rss_item_to_ingest_record(
                feed_url=feed_url,
                title=title[:500],
                summary=summary,
                link=link,
                published=published,
                default_tags=default_tags,
            ),
        )
    return records


async def scrape_rss_forager_feeds(
    forager: ForagerORM,
    *,
    feeds_per_run: int | None = None,
    items_per_feed: int = 12,
) -> list[dict[str, Any]]:
    """Scrape all configured RSS feeds for one forager."""

    feed_urls = _rss_feed_urls(forager)
    if not feed_urls:
        return []

    cfg = dict(forager.filter_config or {})
    default_tags = [str(tag).strip() for tag in list(cfg.get("default_tags") or cfg.get("topic_tags") or []) if str(tag).strip()]
    limit_feeds = feeds_per_run or int(dict(forager.source_config or {}).get("feeds_per_run") or len(feed_urls))
    limit_feeds = max(1, min(limit_feeds, len(feed_urls)))

    records: list[dict[str, Any]] = []
    for feed_url in feed_urls[:limit_feeds]:
        batch = await fetch_rss_feed_records(
            feed_url,
            default_tags=default_tags,
            item_limit=items_per_feed,
        )
        records.extend(batch)
        if not batch:
            site_guess = _feed_url_to_site_guess(feed_url)
            if site_guess:
                records.extend(await fetch_site_snapshot_records(site_guess, default_tags=default_tags))

    if not records:
        fallback_urls = _fallback_site_urls(forager)
        for site_url in fallback_urls:
            records.extend(await fetch_site_snapshot_records(site_url, default_tags=default_tags))
    return records


def _feed_url_to_site_guess(feed_url: str) -> str | None:
    """Derive shop homepage from a broken RSS URL."""

    parsed = urlparse(feed_url.strip())
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/"


def _fallback_site_urls(forager: ForagerORM) -> list[str]:
    """Optional explicit homepage list when RSS feeds are unavailable."""

    cfg = dict(forager.source_config or {})
    raw = cfg.get("fallback_site_urls") or cfg.get("site_urls") or []
    if isinstance(raw, str):
        raw = [line.strip() for line in raw.splitlines() if line.strip()]
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


async def fetch_site_snapshot_records(
    site_url: str,
    *,
    default_tags: list[str],
    timeout_sec: float = 20.0,
) -> list[dict[str, Any]]:
    """Fetch one e-shop homepage snapshot when RSS is missing or empty."""

    try:
        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
            response = await client.get(
                site_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; Queenswarm-Forager/1.0)"},
            )
            response.raise_for_status()
            html_text = response.text
    except Exception as exc:
        logger.warning(
            "forager.site_snapshot_failed",
            agent_id="forager_rss",
            site_url=site_url,
            error=str(exc)[:300],
        )
        return []

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    title = _strip_html(title_match.group(1)) if title_match else urlparse(site_url).netloc
    body = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html_text)
    body = _strip_html(body)
    body = re.sub(r"\s+", " ", body).strip()[:5000]
    if not body:
        return []

    host = urlparse(site_url).netloc or site_url
    summary = body[:4000]
    record = rss_item_to_ingest_record(
        feed_url=site_url,
        title=f"Site snapshot · {title[:200]}",
        summary=summary,
        link=site_url,
        published=None,
        default_tags=[*default_tags, "site-snapshot"],
    )
    record["confidence_score"] = 0.55
    record["topic_tags"] = list(dict.fromkeys([*record.get("topic_tags", []), f"site:{host}"]))[:32]
    return [record]


__all__ = [
    "fetch_rss_feed_records",
    "fetch_site_snapshot_records",
    "rss_item_to_ingest_record",
    "scrape_rss_forager_feeds",
]
