"""YouTubeTranscriptBee — on-demand video URL → transcript text (no Data API quota)."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx
import structlog
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

logger = structlog.get_logger(__name__)

_PREFERRED_LANGS = ("en", "en-US", "sk", "cs", "de", "pl")


@dataclass(slots=True)
class YouTubeTranscriptResult:
    """Fetched transcript + metadata for Research Bee."""

    video_id: str
    title: str
    transcript_text: str
    language: str
    source_url: str


def extract_youtube_video_id(url: str) -> str | None:
    """Parse YouTube watch, shorts, or youtu.be URLs into an 11-char video id."""

    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
        return candidate if len(candidate) >= 8 else None
    if host.endswith("youtube.com"):
        if parsed.path == "/watch":
            values = parse_qs(parsed.query).get("v") or []
            return str(values[0]).strip() if values else None
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
            return parts[1]
    return None


def is_youtube_url(url: str) -> bool:
    """Return True when URL resolves to a YouTube video id."""

    return extract_youtube_video_id(url) is not None


def _join_transcript(entries: list[dict[str, object]]) -> str:
    parts: list[str] = []
    for row in entries:
        text = str(row.get("text") or "").strip()
        if text:
            parts.append(text)
    merged = re.sub(r"\s+", " ", " ".join(parts)).strip()
    return merged


def _fetch_transcript_sync(video_id: str) -> tuple[str, str]:
    """Blocking transcript fetch — run via asyncio.to_thread."""

    try:
        listing = YouTubeTranscriptApi.list_transcripts(video_id)
    except (TranscriptsDisabled, VideoUnavailable, NoTranscriptFound) as exc:
        msg = f"YouTube transcript unavailable: {exc}"
        raise ValueError(msg) from exc

    transcript = None
    language = "en"
    for lang in _PREFERRED_LANGS:
        try:
            transcript = listing.find_transcript([lang])
            language = lang
            break
        except NoTranscriptFound:
            continue
    if transcript is None:
        try:
            transcript = listing.find_generated_transcript(["en"])
            language = "auto-en"
        except NoTranscriptFound as exc:
            msg = "No captions or auto-transcript for this video."
            raise ValueError(msg) from exc

    entries = transcript.fetch()
    text = _join_transcript(entries)
    if not text:
        msg = "Transcript was empty."
        raise ValueError(msg)
    return text, language


async def fetch_youtube_oembed_title(client: httpx.AsyncClient, url: str) -> str:
    """Best-effort title via YouTube oEmbed (no API key)."""

    response = await client.get(
        "https://www.youtube.com/oembed",
        params={"url": url, "format": "json"},
        timeout=10.0,
    )
    response.raise_for_status()
    payload = response.json()
    title = str(payload.get("title") or "").strip()
    return title


async def fetch_youtube_transcript(
    url: str,
    *,
    max_chars: int,
) -> YouTubeTranscriptResult:
    """Fetch transcript for a public YouTube URL."""

    video_id = extract_youtube_video_id(url)
    if not video_id:
        msg = "Invalid YouTube URL."
        raise ValueError(msg)

    cap = max(512, min(max_chars, 120_000))
    transcript_text, language = await asyncio.to_thread(_fetch_transcript_sync, video_id)
    transcript_text = transcript_text[:cap]

    title = video_id
    async with httpx.AsyncClient() as client:
        try:
            title = await fetch_youtube_oembed_title(client, url) or video_id
        except httpx.HTTPError:
            logger.warning(
                "youtube_transcript.oembed_failed",
                agent_id="youtube_transcript_bee",
                swarm_id=video_id,
                task_id="",
            )

    logger.info(
        "youtube_transcript.fetched",
        agent_id="youtube_transcript_bee",
        swarm_id=video_id,
        task_id="",
        language=language,
        char_count=len(transcript_text),
    )
    return YouTubeTranscriptResult(
        video_id=video_id,
        title=title[:200],
        transcript_text=transcript_text,
        language=language,
        source_url=url.strip()[:2048],
    )


__all__ = [
    "YouTubeTranscriptResult",
    "extract_youtube_video_id",
    "fetch_youtube_transcript",
    "is_youtube_url",
]
