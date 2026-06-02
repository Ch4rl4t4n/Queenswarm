"""IngestRouterBee — route public URLs to the correct ingest bee (YouTube vs web)."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.services.research_bee import SOURCE_PASTE, SOURCE_PDF_TEXT, SOURCE_URL, fetch_url_text
from app.application.services.youtube_transcript_bee import (
    fetch_youtube_transcript,
    is_youtube_url,
)
from app.core.config import settings

SOURCE_YOUTUBE = "youtube_transcript"


@dataclass(slots=True)
class IngestResolvedSource:
    """Normalized ingest payload for Research Bee."""

    raw_text: str
    source_type: str
    source_label: str
    title_hint: str | None = None
    ingest_route: str = "paste"
    video_id: str | None = None
    transcript_language: str | None = None


async def resolve_ingest_source(
    *,
    source_url: str | None = None,
    content_text: str | None = None,
    title_hint: str | None = None,
    max_chars: int | None = None,
) -> IngestResolvedSource:
    """Resolve URL or pasted text into raw content + metadata."""

    cap = max_chars if max_chars is not None else int(settings.research_bee_max_chars)
    url = (source_url or "").strip()
    pasted = (content_text or "").strip()

    if url and pasted:
        msg = "Provide either source_url or content_text, not both."
        raise ValueError(msg)
    if not url and not pasted:
        msg = "Provide source_url or content_text."
        raise ValueError(msg)

    if url:
        if is_youtube_url(url) and settings.youtube_transcript_bee_enabled:
            yt = await fetch_youtube_transcript(url, max_chars=cap)
            return IngestResolvedSource(
                raw_text=yt.transcript_text,
                source_type=SOURCE_YOUTUBE,
                source_label=yt.source_url,
                title_hint=title_hint or yt.title,
                ingest_route="youtube",
                video_id=yt.video_id,
                transcript_language=yt.language,
            )
        raw = await fetch_url_text(url, max_chars=cap)
        return IngestResolvedSource(
            raw_text=raw,
            source_type=SOURCE_URL,
            source_label=url[:500],
            title_hint=title_hint,
            ingest_route="web_url",
        )

    raw = pasted[:cap]
    source_type = SOURCE_PDF_TEXT if pasted.lower().startswith("%pdf") else SOURCE_PASTE
    return IngestResolvedSource(
        raw_text=raw,
        source_type=source_type,
        source_label=title_hint or ("Pasted document" if source_type == SOURCE_PASTE else "PDF text"),
        title_hint=title_hint,
        ingest_route="paste",
    )


__all__ = ["IngestResolvedSource", "resolve_ingest_source", "SOURCE_YOUTUBE"]
