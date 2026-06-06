"""Second-brain capture convention — IDEA / CONNECTS TO / MIGHT USE FOR / Key Tension."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.persistence.models.knowledge import KnowledgeItem

logger = get_logger(__name__)

_CAPTURE_TAG = "second_brain:capture"
_IDEA_RE = re.compile(r"(?im)^##\s*IDEA\s*\n(.+?)(?=\n##\s|\Z)", re.DOTALL)
_CONNECTS_RE = re.compile(r"(?im)^##\s*CONNECTS TO\s*\n(.+?)(?=\n##\s|\Z)", re.DOTALL)
_MIGHT_USE_RE = re.compile(r"(?im)^##\s*MIGHT USE FOR\s*\n(.+?)(?=\n##\s|\Z)", re.DOTALL)
_TENSION_RE = re.compile(r"(?im)^##\s*Key Tension\s*\n(.+?)(?=\n##\s|\Z)", re.DOTALL)


class SecondBrainCaptureIn(BaseModel):
    """Operator quick-capture payload."""

    model_config = ConfigDict(extra="forbid")

    idea: str = Field(min_length=3, max_length=4000)
    connects_to: list[str] = Field(default_factory=list, max_length=12)
    might_use_for: str = Field(default="", max_length=2000)
    key_tension: str = Field(default="", max_length=2000)
    body: str = Field(default="", max_length=12000)


class SecondBrainCaptureOut(BaseModel):
    """Persisted capture note."""

    model_config = ConfigDict(extra="ignore")

    id: str
    markdown: str
    topic_tags: list[str] = Field(default_factory=list)


def empty_capture_template() -> str:
    """Markdown skeleton for Obsidian-compatible capture notes."""

    return build_capture_markdown(
        idea="",
        connects_to=[],
        might_use_for="",
        key_tension="",
        body="",
    )


def build_capture_markdown(
    *,
    idea: str,
    connects_to: list[str],
    might_use_for: str,
    key_tension: str,
    body: str = "",
) -> str:
    """Render capture note with second-brain linking convention."""

    links = "\n".join(f"- [[{item.strip()}]]" if not item.strip().startswith("-") else item.strip() for item in connects_to if item.strip())
    if not links:
        links = "- _(add wikilinks or topic names)_"
    tension = key_tension.strip() or "_(what trade-off or open question does this idea create?)_"
    use_for = might_use_for.strip() or "_(project, swarm, or decision this might inform)_"
    idea_text = idea.strip() or "_(one sentence core idea)_"
    extra = body.strip()
    parts = [
        "---",
        "capture: second_brain",
        f"captured_at: {datetime.now(tz=UTC).isoformat()}",
        "---",
        "",
        "## IDEA",
        idea_text,
        "",
        "## CONNECTS TO",
        links,
        "",
        "## MIGHT USE FOR",
        use_for,
        "",
        "## Key Tension",
        tension,
    ]
    if extra:
        parts.extend(["", "## Notes", extra])
    return "\n".join(parts).strip() + "\n"


def parse_capture_fields(markdown: str) -> dict[str, Any]:
    """Extract structured capture fields from persisted markdown."""

    def _section(pattern: re.Pattern[str]) -> str:
        match = pattern.search(markdown)
        return match.group(1).strip() if match else ""

    connects_raw = _section(_CONNECTS_RE)
    connects: list[str] = []
    for line in connects_raw.splitlines():
        cleaned = line.strip().lstrip("-").strip()
        cleaned = cleaned.removeprefix("[[").removesuffix("]]").strip()
        if cleaned and not cleaned.startswith("_("):
            connects.append(cleaned)

    return {
        "idea": _section(_IDEA_RE),
        "connects_to": connects,
        "might_use_for": _section(_MIGHT_USE_RE),
        "key_tension": _section(_TENSION_RE),
    }


def is_capture_note(markdown: str) -> bool:
    """Return True when content follows capture convention."""

    lower = markdown.lower()
    return "capture: second_brain" in lower or ("## idea" in lower and "## connects to" in lower)


async def persist_capture_note(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    payload: SecondBrainCaptureIn,
) -> SecondBrainCaptureOut:
    """Store one capture note in raw knowledge tier."""

    markdown = build_capture_markdown(
        idea=payload.idea,
        connects_to=payload.connects_to,
        might_use_for=payload.might_use_for,
        key_tension=payload.key_tension,
        body=payload.body,
    )
    tags = [_CAPTURE_TAG, "wiki_layer:raw"]
    for link in payload.connects_to[:8]:
        slug = re.sub(r"[^\w\-]+", "-", link.strip().lower()).strip("-")
        if slug:
            tags.append(f"connects:{slug[:48]}")
    tags = list(dict.fromkeys(tags))[:24]

    row = KnowledgeItem(
        tenant_id=tenant_id,
        source_type="second_brain_capture",
        source_url=None,
        content_text=markdown,
        confidence_score=0.9,
        topic_tags=tags,
        decay_factor=1.0,
        scraped_at=datetime.now(tz=UTC),
        verified_at=datetime.now(tz=UTC),
    )
    session.add(row)
    await session.flush()
    logger.info(
        "second_brain.capture_persisted",
        agent_id="wiki_layer",
        swarm_id=str(tenant_id),
        task_id=str(row.id),
    )
    return SecondBrainCaptureOut(id=str(row.id), markdown=markdown, topic_tags=tags)


__all__ = [
    "SecondBrainCaptureIn",
    "SecondBrainCaptureOut",
    "build_capture_markdown",
    "empty_capture_template",
    "is_capture_note",
    "parse_capture_fields",
    "persist_capture_note",
]
