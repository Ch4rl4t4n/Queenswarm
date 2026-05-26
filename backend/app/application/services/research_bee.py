"""NotebookLM-style Research Bee — URL/text → structured HiveMind brief (P2 #78)."""

from __future__ import annotations

import ipaddress
import re
import uuid
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.persistence.models.knowledge import KnowledgeItem

logger = structlog.get_logger(__name__)

_TAG_STOPWORDS = frozenset(
    {
        "about",
        "after",
        "also",
        "been",
        "being",
        "could",
        "from",
        "have",
        "into",
        "more",
        "other",
        "should",
        "that",
        "their",
        "there",
        "these",
        "they",
        "this",
        "through",
        "were",
        "what",
        "when",
        "which",
        "with",
        "would",
        "your",
    },
)

SOURCE_URL = "url"
SOURCE_PDF_TEXT = "pdf_text"
SOURCE_PASTE = "paste"


class ResearchBriefOut(BaseModel):
    """Structured research brief — never raw dump."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    source_type: str
    source_label: str
    title: str
    summary: str
    key_points: list[str] = Field(default_factory=list)
    notable_quotes: list[str] = Field(default_factory=list)
    topic_tags: list[str] = Field(default_factory=list)
    word_count: int = 0
    persisted: bool = False
    knowledge_item_id: str | None = None
    markdown: str = ""


class _HtmlTextExtractor(HTMLParser):
    """Strip scripts/styles and concatenate visible text snippets."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: ARG002
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self._parts.append(data.strip())

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._parts)).strip()


def _is_safe_public_url(url: str) -> bool:
    """Reject local/private targets for SSRF safety."""

    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    if not host or host in {"localhost", "127.0.0.1", "0.0.0.0"}:
        return False
    if host.endswith(".local") or host.endswith(".internal"):
        return False
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    except ValueError:
        pass
    blocked_prefixes = ("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.2", "172.30.", "172.31.")
    if any(host.startswith(prefix) for prefix in blocked_prefixes):
        return False
    return True


async def fetch_url_text(url: str, *, max_chars: int) -> str:
    """Fetch and extract readable text from a public URL."""

    if not _is_safe_public_url(url):
        raise ValueError("URL must be a public http(s) address.")

    cap = max(512, min(max_chars, 120_000))
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "Queenswarm-ResearchBee/1.0"})
        response.raise_for_status()
        content_type = (response.headers.get("content-type") or "").lower()
        raw = response.text or ""
        if "html" in content_type or raw.lstrip().startswith("<"):
            parser = _HtmlTextExtractor()
            parser.feed(raw[: cap + 50_000])
            text = parser.text()
        else:
            text = raw.strip()
    if not text:
        raise ValueError("No extractable text at URL.")
    return text[:cap]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if len(part.strip()) >= 20]


def _extract_tags(text: str, *, limit: int = 8) -> list[str]:
    words = re.findall(r"[a-zA-Z]{5,}", text.lower())
    freq: dict[str, int] = {}
    for word in words:
        if word in _TAG_STOPWORDS:
            continue
        freq[word] = freq.get(word, 0) + 1
    ranked = sorted(freq.items(), key=lambda row: (-row[1], row[0]))
    return [word for word, _ in ranked[:limit]]


def _extract_quotes(text: str, *, limit: int = 4) -> list[str]:
    quoted = re.findall(r'"([^"]{20,220})"', text)
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith('"')]
    merged = [*quoted, *[line.strip('"') for line in lines]]
    unique: list[str] = []
    for item in merged:
        if item not in unique:
            unique.append(item)
        if len(unique) >= limit:
            break
    return unique


def build_structured_brief(
    *,
    raw_text: str,
    source_type: str,
    source_label: str,
    title_hint: str | None = None,
) -> ResearchBriefOut:
    """Transform raw text into a structured brief without LLM."""

    text = re.sub(r"\s+", " ", raw_text.strip())
    cap = max(512, min(int(settings.research_bee_max_chars), 120_000))
    text = text[:cap]
    sentences = _split_sentences(text)
    title = (title_hint or "").strip()
    if not title:
        title = sentences[0][:120] if sentences else source_label[:120]
    summary = " ".join(sentences[:3])[:600] if sentences else text[:600]
    key_points = [sent[:280] for sent in sentences[1:9] if 40 <= len(sent) <= 280][:8]
    if not key_points and len(sentences) > 1:
        key_points = [sent[:280] for sent in sentences[1:6]]

    tags = _extract_tags(text)
    quotes = _extract_quotes(text)
    word_count = len(text.split())

    markdown_lines = [
        f"# {title}",
        "",
        f"**Source:** {source_label}",
        "",
        "## Summary",
        summary,
        "",
        "## Key points",
    ]
    markdown_lines.extend(f"- {point}" for point in key_points)
    if quotes:
        markdown_lines.extend(["", "## Notable quotes"])
        markdown_lines.extend(f"> {quote}" for quote in quotes)
    markdown_lines.extend(["", "## Tags", ", ".join(tags) if tags else "_none_"])
    markdown = "\n".join(markdown_lines)

    return ResearchBriefOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        source_type=source_type,
        source_label=source_label,
        title=title[:200],
        summary=summary,
        key_points=key_points,
        notable_quotes=quotes,
        topic_tags=tags,
        word_count=word_count,
        markdown=markdown,
    )


async def compose_research_brief(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    source_url: str | None = None,
    content_text: str | None = None,
    title_hint: str | None = None,
    persist: bool = False,
) -> ResearchBriefOut:
    """Fetch or accept text, structure brief, optionally persist to HiveMind."""

    if not settings.research_bee_enabled:
        return ResearchBriefOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            source_type="disabled",
            source_label="",
            title="",
            summary="",
        )

    url = (source_url or "").strip()
    pasted = (content_text or "").strip()
    max_chars = int(settings.research_bee_max_chars)

    if url and pasted:
        raise ValueError("Provide either source_url or content_text, not both.")
    if not url and not pasted:
        raise ValueError("Provide source_url or content_text.")

    if url:
        raw = await fetch_url_text(url, max_chars=max_chars)
        source_type = SOURCE_URL
        source_label = url[:500]
    else:
        raw = pasted[:max_chars]
        source_type = SOURCE_PDF_TEXT if pasted.lower().startswith("%pdf") else SOURCE_PASTE
        source_label = title_hint or ("Pasted document" if source_type == SOURCE_PASTE else "PDF text")

    brief = build_structured_brief(
        raw_text=raw,
        source_type=source_type,
        source_label=source_label,
        title_hint=title_hint,
    )

    if persist and brief.summary:
        tags = list(dict.fromkeys(["research_bee", *brief.topic_tags]))[:16]
        row = KnowledgeItem(
            tenant_id=tenant_id,
            source_url=url or None,
            source_type="research_bee",
            content_text=brief.markdown,
            confidence_score=0.82,
            topic_tags=tags,
            decay_factor=1.0,
            scraped_at=datetime.now(tz=UTC),
            verified_at=datetime.now(tz=UTC),
        )
        session.add(row)
        await session.flush()
        brief = brief.model_copy(update={"persisted": True, "knowledge_item_id": str(row.id)})
        logger.info(
            "research_bee.persisted",
            agent_id="research_bee",
            swarm_id=str(tenant_id),
            task_id=str(row.id),
            source_type=source_type,
        )

    return brief


__all__ = [
    "ResearchBriefOut",
    "build_structured_brief",
    "compose_research_brief",
    "fetch_url_text",
]
