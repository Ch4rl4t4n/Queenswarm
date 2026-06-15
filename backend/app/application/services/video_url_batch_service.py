"""NP8 — Video URL batch wizard: paste 1–20 URLs → intel digest → kanban + wiki."""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import UTC, datetime
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.mission_kanban import create_mission_triage_task
from app.application.services.research_bee import fetch_url_text
from app.application.services.youtube_transcript_bee import (
    fetch_youtube_oembed_title,
    fetch_youtube_transcript,
    is_youtube_url,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.outputs.engine import OutputEngine
from app.infrastructure.persistence.models.knowledge import KnowledgeItem

_logger = get_logger(__name__)

_URL_RE = re.compile(r"https?://[^\s<>\"')\],]+", re.IGNORECASE)

VideoIntelStatus = Literal["ok", "partial", "error"]
VideoIntelPlatform = Literal["youtube", "web"]


class VideoUrlIntelItemOut(BaseModel):
    """One resolved URL row in the batch digest."""

    model_config = ConfigDict(extra="ignore")

    url: str
    title: str
    platform: VideoIntelPlatform
    status: VideoIntelStatus
    excerpt: str = ""
    transcript_available: bool = False
    transcript_language: str | None = None
    video_id: str | None = None
    error: str | None = None


class VideoUrlBatchWizardOut(BaseModel):
    """Static wizard snapshot for UI."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    max_urls: int = 20
    min_urls: int = 1
    excerpt_chars: int = 1200
    knowledge_href: str = "/knowledge?tab=wiki"
    tasks_href: str = "/tasks"


class VideoUrlBatchSubmitIn(BaseModel):
    """Operator pasted URL list."""

    model_config = ConfigDict(extra="forbid")

    urls_text: str = Field(min_length=8, max_length=24_000)
    title: str | None = Field(default=None, min_length=3, max_length=500)
    wiki_capture: bool = True
    trigger_gardener: bool = True


class VideoUrlBatchSubmitOut(BaseModel):
    """Triage task + workspace deliverable (+ optional wiki raw items)."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    task_id: str
    deliverable_id: str
    title: str
    digest_markdown: str
    href: str = "/tasks"
    url_count: int = 0
    ok_count: int = 0
    partial_count: int = 0
    error_count: int = 0
    knowledge_item_ids: list[str] = Field(default_factory=list)
    gardener_triggered: bool = False
    message: str = ""


def parse_url_batch(raw: str, *, max_urls: int | None = None) -> list[str]:
    """Extract unique HTTP(S) URLs from pasted text (newline, comma, or space separated)."""

    cap = max_urls if max_urls is not None else int(settings.video_url_batch_max_urls)
    cap = max(1, min(cap, 20))
    seen: set[str] = set()
    ordered: list[str] = []
    for match in _URL_RE.finditer(raw or ""):
        url = match.group(0).rstrip(".,;")
        key = url.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(url)
        if len(ordered) >= cap:
            break
    return ordered


def compose_video_url_batch_wizard_snapshot() -> VideoUrlBatchWizardOut:
    """Return static wizard config."""

    if not settings.video_url_batch_wizard_enabled:
        return VideoUrlBatchWizardOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            max_urls=0,
        )
    return VideoUrlBatchWizardOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        max_urls=int(settings.video_url_batch_max_urls),
        min_urls=1,
        excerpt_chars=int(settings.video_url_batch_excerpt_chars),
    )


def _excerpt(text: str, *, max_chars: int) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[: max_chars - 1].rstrip()}…"


async def _fetch_youtube_intel(url: str, *, excerpt_chars: int) -> VideoUrlIntelItemOut:
    """Resolve YouTube URL via oEmbed + optional transcript bee."""

    title = url[:120]
    async with httpx.AsyncClient() as client:
        try:
            title = (await fetch_youtube_oembed_title(client, url)).strip() or title
        except httpx.HTTPError:
            title = url[:120]

    if settings.youtube_transcript_bee_enabled:
        try:
            yt = await fetch_youtube_transcript(url, max_chars=excerpt_chars)
            return VideoUrlIntelItemOut(
                url=url,
                title=yt.title or title,
                platform="youtube",
                status="ok",
                excerpt=_excerpt(yt.transcript_text, max_chars=excerpt_chars),
                transcript_available=True,
                transcript_language=yt.language,
                video_id=yt.video_id,
            )
        except ValueError as exc:
            return VideoUrlIntelItemOut(
                url=url,
                title=title,
                platform="youtube",
                status="partial",
                excerpt="",
                transcript_available=False,
                error=str(exc)[:240],
            )

    return VideoUrlIntelItemOut(
        url=url,
        title=title,
        platform="youtube",
        status="partial",
        excerpt="",
        transcript_available=False,
        error="Transcript bee disabled — title only via oEmbed.",
    )


async def _fetch_web_intel(url: str, *, excerpt_chars: int) -> VideoUrlIntelItemOut:
    """Resolve generic URL via Research Bee fetch (title + text excerpt)."""

    try:
        raw = await fetch_url_text(url, max_chars=excerpt_chars)
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        title = lines[0][:200] if lines else url[:120]
        return VideoUrlIntelItemOut(
            url=url,
            title=title,
            platform="web",
            status="ok" if raw.strip() else "partial",
            excerpt=_excerpt(raw, max_chars=excerpt_chars),
            transcript_available=False,
        )
    except (ValueError, httpx.HTTPError) as exc:
        return VideoUrlIntelItemOut(
            url=url,
            title=url[:120],
            platform="web",
            status="error",
            excerpt="",
            error=str(exc)[:240],
        )


async def fetch_url_intel(url: str, *, excerpt_chars: int | None = None) -> VideoUrlIntelItemOut:
    """Fetch one URL intel row (YouTube transcript path or web excerpt)."""

    cap = excerpt_chars if excerpt_chars is not None else int(settings.video_url_batch_excerpt_chars)
    cleaned = url.strip()
    if not cleaned.lower().startswith(("http://", "https://")):
        return VideoUrlIntelItemOut(
            url=cleaned,
            title=cleaned[:120],
            platform="web",
            status="error",
            excerpt="",
            error="URL must start with http:// or https://",
        )
    if is_youtube_url(cleaned):
        return await _fetch_youtube_intel(cleaned, excerpt_chars=cap)
    return await _fetch_web_intel(cleaned, excerpt_chars=cap)


async def fetch_url_batch_intel(
    urls: list[str],
    *,
    excerpt_chars: int | None = None,
) -> list[VideoUrlIntelItemOut]:
    """Fetch intel for many URLs concurrently with per-URL isolation."""

    cap = excerpt_chars if excerpt_chars is not None else int(settings.video_url_batch_excerpt_chars)

    async def _one(link: str) -> VideoUrlIntelItemOut:
        try:
            return await fetch_url_intel(link, excerpt_chars=cap)
        except Exception as exc:  # noqa: BLE001 — batch must not fail whole run
            _logger.warning(
                "video_url_batch.fetch_failed",
                agent_id="video_url_batch",
                url=link[:120],
                error=str(exc)[:200],
            )
            return VideoUrlIntelItemOut(
                url=link,
                title=link[:120],
                platform="youtube" if is_youtube_url(link) else "web",
                status="error",
                excerpt="",
                error=str(exc)[:240],
            )

    return list(await asyncio.gather(*(_one(u) for u in urls)))


def compose_batch_digest_markdown(
    items: list[VideoUrlIntelItemOut],
    *,
    title: str | None = None,
) -> tuple[str, str]:
    """Build markdown digest and resolved title."""

    resolved_title = (title or "").strip() or f"Video intel batch ({len(items)} URLs)"
    ok = sum(1 for row in items if row.status == "ok")
    partial = sum(1 for row in items if row.status == "partial")
    errors = sum(1 for row in items if row.status == "error")

    lines = [
        f"# {resolved_title}",
        "",
        "_Generated by NP8 Video URL batch wizard — operator review digest, simulate-first._",
        "",
        "## Batch summary",
        "",
        f"- URLs: **{len(items)}** · OK: **{ok}** · Partial: **{partial}** · Failed: **{errors}**",
        "",
        "## Sources",
        "",
    ]

    for index, row in enumerate(items, start=1):
        lines.extend(
            [
                f"### {index}. {row.title}",
                "",
                f"- URL: {row.url}",
                f"- Platform: `{row.platform}` · Status: `{row.status}`",
            ],
        )
        if row.transcript_available and row.transcript_language:
            lines.append(f"- Transcript: `{row.transcript_language}`")
        if row.error:
            lines.append(f"- Note: {row.error}")
        if row.excerpt:
            lines.extend(["", "> " + row.excerpt.replace("\n", "\n> "), ""])
        else:
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend(
        [
            "## Operator next steps",
            "",
            "1. Review excerpts — no raw transcript in Queen prompt without triage.",
            "2. Dispatch research session on highest-signal URLs.",
            "3. Wiki Gardener compiles hot tier when wiki capture enabled.",
            "",
        ],
    )
    return resolved_title, "\n".join(lines).strip() + "\n"


async def _persist_wiki_raw_items(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    items: list[VideoUrlIntelItemOut],
    digest_markdown: str,
) -> list[str]:
    """Persist digest + per-URL rows to knowledge_items raw tier."""

    ids: list[str] = []
    now = datetime.now(tz=UTC)
    digest_row = KnowledgeItem(
        tenant_id=tenant_id,
        source_type="video_url_batch",
        source_url=None,
        content_text=digest_markdown,
        confidence_score=0.85,
        topic_tags=["np8", "video_url_batch", "wiki_layer:raw", "forager:youtube"],
        decay_factor=1.0,
        scraped_at=now,
        verified_at=now,
    )
    session.add(digest_row)
    await session.flush()
    ids.append(str(digest_row.id))

    for row in items:
        if row.status == "error" and not row.excerpt:
            continue
        body = (
            f"# {row.title}\n\n"
            f"URL: {row.url}\n\n"
            f"Status: {row.status}\n\n"
            f"{row.excerpt or row.error or ''}"
        ).strip()
        ki = KnowledgeItem(
            tenant_id=tenant_id,
            source_type="youtube_transcript" if row.platform == "youtube" else "url",
            source_url=row.url[:2048],
            content_text=body[:12_000],
            confidence_score=0.8 if row.status == "ok" else 0.6,
            topic_tags=list(
                dict.fromkeys(
                    [
                        "np8",
                        "video_url_batch",
                        "wiki_layer:raw",
                        "forager:youtube" if row.platform == "youtube" else "research_bee",
                    ],
                ),
            )[:16],
            decay_factor=1.0,
            scraped_at=now,
            verified_at=now,
        )
        session.add(ki)
        await session.flush()
        ids.append(str(ki.id))

    return ids


async def submit_video_url_batch_wizard(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    body: VideoUrlBatchSubmitIn,
) -> VideoUrlBatchSubmitOut:
    """Process URL batch → markdown digest → triage task + deliverable."""

    if not settings.video_url_batch_wizard_enabled:
        raise ValueError("Video URL batch wizard is disabled.")

    urls = parse_url_batch(body.urls_text)
    if not urls:
        raise ValueError("Paste at least one valid http(s) URL.")
    if len(urls) > int(settings.video_url_batch_max_urls):
        raise ValueError(f"Maximum {settings.video_url_batch_max_urls} URLs per batch.")

    items = await fetch_url_batch_intel(urls)
    title, markdown = compose_batch_digest_markdown(items, title=body.title)

    triage = await create_mission_triage_task(
        session,
        task_text=markdown,
        title=title,
        priority=6,
        swarm_id=None,
        skills=["social-intel-evaluator", "context", "decision-frameworks"],
        extra_payload={
            "video_url_batch_wizard": True,
            "url_count": len(items),
            "urls": [row.url for row in items[:20]],
        },
    )
    task_id = triage.task.id
    lineage_id = uuid.uuid4()

    deliverable = await OutputEngine.create_final_deliverable(
        session,
        lineage_id=lineage_id,
        markdown_body=markdown,
        structured={
            "format": "queenswarm.video_url_batch.v1",
            "url_count": len(items),
            "items": [row.model_dump(mode="json") for row in items],
            "task_id": str(task_id),
        },
        title_hint=title,
        slug_hint="video-url-batch-digest",
        tags=["video-url-batch", "np8", "intel-digest"],
        voice_script=None,
        dashboard_user_id=dashboard_user_id,
        ballroom_session_id=None,
        mission_id=task_id,
        source_task_id=task_id,
    )

    knowledge_ids: list[str] = []
    gardener_triggered = False
    if body.wiki_capture and settings.wiki_layer_enabled:
        knowledge_ids = await _persist_wiki_raw_items(
            session,
            tenant_id=tenant_id,
            items=items,
            digest_markdown=markdown,
        )
        if body.trigger_gardener:
            from app.application.services.wiki_layer_service import WikiLayerService

            wiki = WikiLayerService(db=session)
            await wiki.run_gardener(tenant_id, agent_id="video_url_batch")
            gardener_triggered = True

    ok_count = sum(1 for row in items if row.status == "ok")
    partial_count = sum(1 for row in items if row.status == "partial")
    error_count = sum(1 for row in items if row.status == "error")

    _logger.info(
        "video_url_batch.submitted",
        agent_id="video_url_batch",
        swarm_id=str(tenant_id),
        task_id=str(task_id),
        url_count=len(items),
        ok_count=ok_count,
    )

    message = f"Digest saved for {len(items)} URLs — {ok_count} OK, {partial_count} partial, {error_count} failed."
    if gardener_triggered:
        message = f"{message} Wiki Gardener triggered."

    return VideoUrlBatchSubmitOut(
        ok=True,
        task_id=str(task_id),
        deliverable_id=str(deliverable.id),
        title=title,
        digest_markdown=markdown,
        href=f"/tasks?task={task_id}",
        url_count=len(items),
        ok_count=ok_count,
        partial_count=partial_count,
        error_count=error_count,
        knowledge_item_ids=knowledge_ids,
        gardener_triggered=gardener_triggered,
        message=message,
    )


__all__ = [
    "VideoUrlBatchSubmitIn",
    "VideoUrlBatchSubmitOut",
    "VideoUrlBatchWizardOut",
    "VideoUrlIntelItemOut",
    "compose_batch_digest_markdown",
    "compose_video_url_batch_wizard_snapshot",
    "fetch_url_batch_intel",
    "fetch_url_intel",
    "parse_url_batch",
    "submit_video_url_batch_wizard",
]
