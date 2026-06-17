"""Second-brain capture convention — IDEA / CONNECTS TO / MIGHT USE FOR / Key Tension."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.knowledge import KnowledgeItem

logger = get_logger(__name__)

_CAPTURE_TAG = "second_brain:capture"
_PENDING_TAG = "second_brain:pending"
_APPROVED_TAG = "second_brain:approved"
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
    status: str = "pending"


class SecondBrainCapturePendingOut(BaseModel):
    """Pending capture awaiting operator approval (SB3)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    idea: str
    connects_to: list[str] = Field(default_factory=list)
    might_use_for: str = ""
    key_tension: str = ""
    captured_at: str | None = None


class SecondBrainCaptureApproveOut(BaseModel):
    """Verified capture with Obsidian wikilink targets (SB3)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    status: str = "approved"
    obsidian_filename: str
    wiki_slug: str
    wikilinks: list[str] = Field(default_factory=list)
    approved_at: str


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


def obsidian_safe_filename(*, idea: str, capture_id: uuid.UUID) -> str:
    """Derive Obsidian-safe capture filename stem."""

    slug = re.sub(r"[^\w\-]+", "-", idea.strip().lower())[:48].strip("-") or "idea"
    return f"{slug}-{str(capture_id)[:8]}"


def capture_wiki_slug(*, idea: str, capture_id: uuid.UUID) -> str:
    """Derive compiled wiki page slug for an approved capture."""

    base = re.sub(r"[^\w\-]+", "-", idea.strip().lower())[:40].strip("-") or "capture"
    return f"capture-{base}-{str(capture_id)[:8]}"


def resolve_obsidian_wikilink(target: str, *, wiki_slug_stems: set[str]) -> str:
    """Map CONNECTS TO target to an Obsidian wikilink stem when possible."""

    cleaned = target.strip()
    normalized = re.sub(r"[^\w\-]+", "-", cleaned.lower()).strip("-")
    if normalized in wiki_slug_stems:
        return normalized
    for stem in wiki_slug_stems:
        if stem.replace("-", "") == normalized.replace("-", ""):
            return stem
    return re.sub(r"[^\w\-]+", "-", cleaned).strip("-") or cleaned


def build_obsidian_export_markdown(
    *,
    content_md: str,
    obsidian_filename: str,
    connects_to: list[str],
    wiki_slug_stems: set[str] | None = None,
) -> str:
    """Append auto wikilinks for approved capture Obsidian export (SB3)."""

    stems = wiki_slug_stems or set()
    wikilinks = [resolve_obsidian_wikilink(item, wiki_slug_stems=stems) for item in connects_to if item.strip()]
    lines = [content_md.rstrip(), "", "## Vault links"]
    if wikilinks:
        lines.extend(f"- [[{link}]]" for link in wikilinks)
    else:
        lines.append("- _(no CONNECTS TO targets yet)_")
    lines.extend(["", "---", f"Backlinks: [[Vault-MOC]] · [[{obsidian_filename}]]"])
    return "\n".join(lines) + "\n"


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
    tags = [_CAPTURE_TAG, _PENDING_TAG, "wiki_layer:raw"]
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
        verified_at=None,
    )
    session.add(row)
    await session.flush()
    logger.info(
        "second_brain.capture_persisted",
        agent_id="wiki_layer",
        swarm_id=str(tenant_id),
        task_id=str(row.id),
    )
    return SecondBrainCaptureOut(
        id=str(row.id),
        markdown=markdown,
        topic_tags=tags,
        status="pending",
    )


async def list_pending_capture_notes(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 40,
) -> list[SecondBrainCapturePendingOut]:
    """Return capture notes awaiting operator approval."""

    rows = list(
        (
            await session.scalars(
                select(KnowledgeItem)
                .where(
                    KnowledgeItem.tenant_id == tenant_id,
                    KnowledgeItem.source_type == "second_brain_capture",
                    KnowledgeItem.verified_at.is_(None),
                )
                .order_by(desc(KnowledgeItem.scraped_at))
                .limit(limit),
            )
        ).all(),
    )
    out: list[SecondBrainCapturePendingOut] = []
    for row in rows:
        fields = parse_capture_fields(row.content_text)
        out.append(
            SecondBrainCapturePendingOut(
                id=str(row.id),
                idea=fields["idea"],
                connects_to=list(fields["connects_to"]),
                might_use_for=str(fields["might_use_for"]),
                key_tension=str(fields["key_tension"]),
                captured_at=row.scraped_at.isoformat() if row.scraped_at else None,
            ),
        )
    return out


async def approve_capture_note(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    capture_id: uuid.UUID,
) -> SecondBrainCaptureApproveOut:
    """Approve capture — compile wiki page and enable Obsidian wikilink export (SB3)."""

    if not settings.second_brain_capture_approve_enabled:
        raise ValueError("capture_approve_disabled")

    row = await session.get(KnowledgeItem, capture_id)
    if row is None or row.tenant_id != tenant_id or row.source_type != "second_brain_capture":
        raise ValueError("capture_not_found")
    if row.verified_at is not None:
        raise ValueError("capture_already_approved")

    fields = parse_capture_fields(row.content_text)
    idea = str(fields["idea"]).strip() or "Untitled capture"
    obsidian_filename = obsidian_safe_filename(idea=idea, capture_id=row.id)
    wiki_slug = capture_wiki_slug(idea=idea, capture_id=row.id)
    wikilinks = [
        resolve_obsidian_wikilink(item, wiki_slug_stems=set())
        for item in fields["connects_to"]
        if str(item).strip()
    ]

    now = datetime.now(tz=UTC)
    tags = [tag for tag in list(row.topic_tags or []) if tag not in {_PENDING_TAG, _APPROVED_TAG}]
    tags.extend(
        [
            _CAPTURE_TAG,
            _APPROVED_TAG,
            "wiki_layer:raw",
            f"obsidian:captures/{obsidian_filename}",
        ],
    )
    row.topic_tags = list(dict.fromkeys(tags))[:24]
    row.verified_at = now

    if settings.wiki_layer_enabled:
        from app.application.services.wiki_layer_service import WikiLayerService

        wiki = WikiLayerService(db=session)
        title = f"Capture · {idea[:80]}"
        await wiki.upsert_custom_page(
            tenant_id,
            slug=wiki_slug,
            title=title,
            content_md=row.content_text,
            source_refs=[{"type": "second_brain_capture", "id": str(row.id)}],
        )

    logger.info(
        "second_brain.capture_approved",
        agent_id="wiki_layer",
        swarm_id=str(tenant_id),
        task_id=str(row.id),
        obsidian_filename=obsidian_filename,
        wiki_slug=wiki_slug,
    )
    return SecondBrainCaptureApproveOut(
        id=str(row.id),
        obsidian_filename=obsidian_filename,
        wiki_slug=wiki_slug,
        wikilinks=wikilinks,
        approved_at=now.isoformat(),
    )


__all__ = [
    "SecondBrainCaptureApproveOut",
    "SecondBrainCaptureIn",
    "SecondBrainCaptureOut",
    "SecondBrainCapturePendingOut",
    "approve_capture_note",
    "build_capture_markdown",
    "build_obsidian_export_markdown",
    "capture_wiki_slug",
    "empty_capture_template",
    "is_capture_note",
    "list_pending_capture_notes",
    "obsidian_safe_filename",
    "parse_capture_fields",
    "persist_capture_note",
    "resolve_obsidian_wikilink",
]
