"""POS-H3 — Research project: batch URLs → merged Hive Mind brief."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.research_bee import ResearchBriefOut, build_structured_brief, fetch_url_text
from app.core.config import settings
from app.infrastructure.persistence.models.knowledge import KnowledgeItem

logger = structlog.get_logger(__name__)

MAX_PROJECT_URLS = 8


class ResearchProjectSourceOut(BaseModel):
    """One source in a research project run."""

    model_config = ConfigDict(extra="ignore")

    url: str
    ok: bool = True
    title: str = ""
    error: str | None = None


class ResearchProjectBriefOut(BaseModel):
    """Merged research project brief — structured, never raw dump."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    project_title: str
    source_count: int = 0
    sources: list[ResearchProjectSourceOut] = Field(default_factory=list)
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    topic_tags: list[str] = Field(default_factory=list)
    markdown: str = ""
    persisted: bool = False
    knowledge_item_id: str | None = None


async def compose_research_project_brief(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    source_urls: list[str],
    project_title: str | None = None,
    persist: bool = False,
) -> ResearchProjectBriefOut:
    """Fetch multiple URLs, merge into one structured research project brief."""

    if not settings.research_bee_enabled or not settings.research_project_enabled:
        return ResearchProjectBriefOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            project_title=project_title or "Research project",
        )

    urls = [url.strip() for url in source_urls if url.strip()][:MAX_PROJECT_URLS]
    if not urls:
        raise ValueError("At least one source URL is required.")

    max_chars = int(settings.research_bee_max_chars)
    per_url_cap = max(512, max_chars // max(len(urls), 1))
    sources: list[ResearchProjectSourceOut] = []
    merged_parts: list[str] = []
    all_tags: list[str] = []

    for url in urls:
        try:
            text = await fetch_url_text(url, max_chars=per_url_cap)
            mini = build_structured_brief(
                raw_text=text,
                source_type="url",
                source_label=url,
            )
            sources.append(
                ResearchProjectSourceOut(
                    url=url,
                    ok=True,
                    title=mini.title,
                ),
            )
            merged_parts.append(f"## {mini.title}\n\n{mini.summary}\n\n" + "\n".join(f"- {p}" for p in mini.key_points))
            all_tags.extend(mini.topic_tags)
        except (ValueError, OSError) as exc:
            sources.append(
                ResearchProjectSourceOut(
                    url=url,
                    ok=False,
                    error=str(exc)[:200],
                ),
            )

    ok_count = sum(1 for row in sources if row.ok)
    if ok_count == 0:
        raise ValueError("No sources could be fetched — check URLs are public http(s).")

    title = (project_title or "").strip() or f"Research project ({ok_count} sources)"
    merged_text = "\n\n".join(merged_parts)
    merged = build_structured_brief(
        raw_text=merged_text,
        source_type="research_project",
        source_label=f"{ok_count} URLs",
        title_hint=title,
    )
    tags = list(dict.fromkeys(["research_project", "research_bee", *all_tags, *merged.topic_tags]))[:16]

    markdown_lines = [
        f"# {title}",
        "",
        f"**Sources:** {ok_count}/{len(urls)} fetched",
        "",
        merged.markdown,
        "",
        "## Sources",
    ]
    for row in sources:
        status = "OK" if row.ok else f"FAIL: {row.error}"
        markdown_lines.append(f"- [{row.url}]({row.url}) — {status}")

    markdown = "\n".join(markdown_lines)

    out = ResearchProjectBriefOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        project_title=title[:200],
        source_count=ok_count,
        sources=sources,
        summary=merged.summary,
        key_points=merged.key_points,
        topic_tags=tags,
        markdown=markdown,
    )

    if persist and merged.summary:
        row = KnowledgeItem(
            tenant_id=tenant_id,
            source_type="research_project",
            content_text=markdown,
            confidence_score=0.85,
            topic_tags=tags,
            decay_factor=1.0,
            scraped_at=datetime.now(tz=UTC),
            verified_at=datetime.now(tz=UTC),
        )
        session.add(row)
        await session.flush()
        out = out.model_copy(update={"persisted": True, "knowledge_item_id": str(row.id)})
        logger.info(
            "research_project.persisted",
            agent_id="research_bee",
            swarm_id=str(tenant_id),
            task_id=str(row.id),
            source_count=ok_count,
        )

    return out


__all__ = [
    "ResearchProjectBriefOut",
    "ResearchProjectSourceOut",
    "compose_research_project_brief",
]
