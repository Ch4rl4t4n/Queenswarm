"""YouTube + X scraping helpers for social intel foragers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_YOUTUBE_CHANNEL_ID_RE = re.compile(r"^UC[\w-]{10,}$")
_YOUTUBE_HANDLE_RE = re.compile(r"^@?[\w.-]{2,}$")


@dataclass(slots=True)
class ScrapedIntelItem:
    """One normalized social post for HiveMind ingest."""

    platform: str
    source_key: str
    external_id: str
    title: str
    summary: str
    source_url: str
    published_at: str | None = None
    raw: dict[str, Any] | None = None


def normalize_youtube_source_key(raw: str) -> str:
    """Normalize channel handle, id, or URL to a stable source key."""

    text = raw.strip()
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        path = urlparse(text).path.strip("/")
        if path.startswith("@"):
            return path.split("/")[0].lower()
        if path.startswith("channel/"):
            return path.split("/")[1]
        return path.split("/")[0] if path else text
    if _YOUTUBE_CHANNEL_ID_RE.match(text):
        return text
    if text.startswith("@"):
        return text.lower()
    if _YOUTUBE_HANDLE_RE.match(text):
        return f"@{text.lstrip('@').lower()}"
    return text.lower()


def normalize_x_source_key(raw: str) -> str:
    """Normalize X handle or profile URL."""

    text = raw.strip()
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        path = urlparse(text).path.strip("/")
        handle = path.split("/")[0] if path else text
        return handle.lstrip("@").lower()
    return text.lstrip("@").lower()


async def resolve_youtube_channel_id(
    client: httpx.AsyncClient,
    *,
    api_key: str,
    source_key: str,
) -> str | None:
    """Resolve UC… channel id from handle, id, or URL fragment."""

    key = normalize_youtube_source_key(source_key)
    if not key:
        return None
    if _YOUTUBE_CHANNEL_ID_RE.match(key):
        return key
    handle = key.lstrip("@")
    params: dict[str, str] = {"part": "id", "key": api_key}
    if key.startswith("@"):
        params["forHandle"] = handle
    else:
        params["forUsername"] = handle
    try:
        response = await client.get("https://www.googleapis.com/youtube/v3/channels", params=params, timeout=30.0)
        response.raise_for_status()
        items = response.json().get("items") or []
        if items:
            return str(items[0].get("id") or "").strip() or None
    except httpx.HTTPError as exc:
        logger.warning(
            "social_intel.youtube.resolve_failed",
            agent_id="youtube_scraper",
            swarm_id=source_key,
            error=str(exc)[:200],
        )
    return None


async def fetch_youtube_channel_items(
    client: httpx.AsyncClient,
    *,
    api_key: str,
    source_key: str,
    last_external_id: str | None,
    backfill_limit: int,
    delta_limit: int,
) -> list[ScrapedIntelItem]:
    """Fetch uploads from one YouTube channel (backfill or delta)."""

    channel_id = await resolve_youtube_channel_id(client, api_key=api_key, source_key=source_key)
    if not channel_id:
        return []

    try:
        ch_resp = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "contentDetails,snippet", "id": channel_id, "key": api_key},
            timeout=30.0,
        )
        ch_resp.raise_for_status()
        ch_items = ch_resp.json().get("items") or []
        if not ch_items:
            return []
        uploads_playlist = (
            ch_items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads") or ""
        ).strip()
        channel_title = str(ch_items[0].get("snippet", {}).get("title") or source_key)
        if not uploads_playlist:
            return []
    except httpx.HTTPError as exc:
        logger.warning(
            "social_intel.youtube.channel_failed",
            agent_id="youtube_scraper",
            swarm_id=source_key,
            error=str(exc)[:200],
        )
        return []

    max_items = backfill_limit if not last_external_id else delta_limit
    collected: list[ScrapedIntelItem] = []
    page_token: str | None = None

    while len(collected) < max_items:
        params = {
            "part": "snippet,contentDetails",
            "playlistId": uploads_playlist,
            "maxResults": min(50, max_items - len(collected)),
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token
        try:
            pl_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/playlistItems",
                params=params,
                timeout=30.0,
            )
            pl_resp.raise_for_status()
            payload = pl_resp.json()
        except httpx.HTTPError as exc:
            logger.warning(
                "social_intel.youtube.playlist_failed",
                agent_id="youtube_scraper",
                swarm_id=source_key,
                error=str(exc)[:200],
            )
            break

        for row in payload.get("items") or []:
            video_id = str(row.get("contentDetails", {}).get("videoId") or "").strip()
            if not video_id:
                continue
            if last_external_id and video_id == last_external_id:
                return collected
            snippet = row.get("snippet") or {}
            title = str(snippet.get("title") or "").strip() or video_id
            description = str(snippet.get("description") or "").strip()
            published = str(snippet.get("publishedAt") or "") or None
            summary = description[:1200] if description else title
            collected.append(
                ScrapedIntelItem(
                    platform="youtube",
                    source_key=normalize_youtube_source_key(source_key),
                    external_id=video_id,
                    title=title,
                    summary=summary,
                    source_url=f"https://www.youtube.com/watch?v={video_id}",
                    published_at=published,
                    raw={"channel_title": channel_title, "channel_id": channel_id},
                ),
            )
            if len(collected) >= max_items:
                break

        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    return collected


async def fetch_x_user_items(
    client: httpx.AsyncClient,
    *,
    access_token: str,
    source_key: str,
    last_external_id: str | None,
    backfill_limit: int,
    delta_limit: int,
) -> list[ScrapedIntelItem]:
    """Fetch tweets from one public X account using OAuth user context."""

    handle = normalize_x_source_key(source_key)
    if not handle:
        return []

    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        user_resp = await client.get(
            f"https://api.twitter.com/2/users/by/username/{handle}",
            params={"user.fields": "name,username,description"},
            headers=headers,
            timeout=30.0,
        )
        user_resp.raise_for_status()
        user_data = user_resp.json().get("data") or {}
        user_id = str(user_data.get("id") or "").strip()
        if not user_id:
            return []
    except httpx.HTTPError as exc:
        logger.warning(
            "social_intel.x.user_lookup_failed",
            agent_id="x_scraper",
            swarm_id=handle,
            error=str(exc)[:200],
        )
        return []

    max_items = backfill_limit if not last_external_id else delta_limit
    params: dict[str, str | int] = {
        "max_results": min(100, max_items),
        "tweet.fields": "created_at,public_metrics,entities",
        "exclude": "retweets,replies",
    }
    if last_external_id:
        params["since_id"] = last_external_id

    collected: list[ScrapedIntelItem] = []
    pagination_token: str | None = None

    while len(collected) < max_items:
        if pagination_token:
            params["pagination_token"] = pagination_token
        try:
            tw_resp = await client.get(
                f"https://api.twitter.com/2/users/{user_id}/tweets",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            tw_resp.raise_for_status()
            payload = tw_resp.json()
        except httpx.HTTPError as exc:
            logger.warning(
                "social_intel.x.timeline_failed",
                agent_id="x_scraper",
                swarm_id=handle,
                error=str(exc)[:200],
            )
            break

        rows = payload.get("data") or []
        if not rows:
            break
        for row in rows:
            tweet_id = str(row.get("id") or "").strip()
            if not tweet_id:
                continue
            if last_external_id and tweet_id == last_external_id:
                return collected
            text = str(row.get("text") or "").strip()
            created = str(row.get("created_at") or "") or None
            collected.append(
                ScrapedIntelItem(
                    platform="x",
                    source_key=handle,
                    external_id=tweet_id,
                    title=f"@{handle}: {text[:120]}",
                    summary=text[:2000],
                    source_url=f"https://x.com/{handle}/status/{tweet_id}",
                    published_at=created,
                    raw={"username": handle, "user_id": user_id},
                ),
            )
            if len(collected) >= max_items:
                break

        pagination_token = (payload.get("meta") or {}).get("next_token")
        if not pagination_token or len(collected) >= max_items:
            break
        if last_external_id:
            break

    return collected


def scraped_item_to_ingest_record(item: ScrapedIntelItem, *, default_tags: list[str]) -> dict[str, Any]:
    """Map scraped item to ForagerService.ingest_records payload."""

    tags = list(
        dict.fromkeys(
            [
                *default_tags,
                f"platform:{item.platform}",
                f"source:{item.source_key}",
                "social-intel",
                "pending-grok-verification",
            ],
        ),
    )[:32]
    body = (
        f"# {item.title}\n\n"
        f"Platform: {item.platform}\n"
        f"Source: {item.source_key}\n"
        f"URL: {item.source_url}\n"
        f"Published: {item.published_at or 'unknown'}\n\n"
        f"{item.summary}\n"
    )
    return {
        "source_url": item.source_url,
        "content_text": body,
        "confidence_score": 0.72,
        "topic_tags": tags,
        "external_id": item.external_id,
    }


__all__ = [
    "ScrapedIntelItem",
    "fetch_x_user_items",
    "fetch_youtube_channel_items",
    "normalize_x_source_key",
    "normalize_youtube_source_key",
    "scraped_item_to_ingest_record",
]
