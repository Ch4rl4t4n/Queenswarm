"""Side effects: Postgres rows, Markdown archives, optional Chroma vectors."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import aiofiles
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chroma_client import TASK_DELIVERABLES_COLLECTION, embed_and_store
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

logger = get_logger(__name__)


def slugify_fragment(text: str, *, max_len: int = 54) -> str:
    """Folder-safe lowercase slug."""

    lowered = text.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = lowered.strip("-")[:max_len]
    return lowered or "deliverable"


def derive_title(markdown_body: str, fallback: str) -> str:
    """Prefer first Markdown ``# `` heading."""

    for line in markdown_body.splitlines():
        strip = line.strip()
        if strip.startswith("# "):
            return strip.removeprefix("# ").strip()[:500]
        if strip.startswith("#"):
            cand = strip.removeprefix("#").strip()
            if cand:
                return cand[:500]
    return fallback[:500]


async def allocate_next_version(session: AsyncSession, lineage_id: uuid.UUID) -> int:
    """Monotonic versioning per Ballroom lineage."""

    stmt = select(func.coalesce(func.max(TaskFinalDeliverable.version), 0)).where(
        TaskFinalDeliverable.lineage_id == lineage_id,
    )
    current = await session.scalar(stmt)
    return int(current or 0) + 1


async def _write_archive_bundle(
    *,
    settings: Settings,
    slug: str,
    version: int,
    payload: TaskFinalDeliverable,
) -> str:
    """Persist ``deliverable.md`` + ``metadata.json`` under dated folder."""

    root = Path(settings.output_archive_root).resolve()
    folder_name = f"{date.today().isoformat()}_{slug}"
    archive_dir = root / folder_name / f"v{version}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    md_path = archive_dir / "deliverable.md"
    meta_path = archive_dir / "metadata.json"

    async with aiofiles.open(md_path, "w", encoding="utf-8") as fh:
        await fh.write(payload.markdown_body)

    stamp = payload.created_at.isoformat() if payload.created_at else datetime.now(tz=UTC).isoformat()
    meta_blob = {
        "id": str(payload.id),
        "lineage_id": str(payload.lineage_id),
        "version": payload.version,
        "title": payload.title,
        "slug": payload.slug,
        "created_at": stamp,
        "tags": payload.tags,
        "dashboard_user_id": str(payload.dashboard_user_id) if payload.dashboard_user_id else None,
        "ballroom_session_id": str(payload.ballroom_session_id) if payload.ballroom_session_id else None,
        "mission_id": str(payload.mission_id) if payload.mission_id else None,
        "chroma_embedding_id": payload.chroma_embedding_id,
    }
    async with aiofiles.open(meta_path, "w", encoding="utf-8") as fh:
        await fh.write(json.dumps(meta_blob, indent=2, default=str))

    return f"{folder_name}/v{version}"


async def persist_final_deliverable(
    session: AsyncSession,
    *,
    lineage_id: uuid.UUID,
    dashboard_user_id: uuid.UUID | None,
    ballroom_session_id: uuid.UUID | None,
    mission_id: uuid.UUID | None,
    source_task_id: uuid.UUID | None,
    slug_hint: str,
    title_hint: str,
    markdown_body: str,
    structured: dict[str, Any],
    tags: Sequence[str],
    voice_script: str | None,
    settings: Settings | None = None,
) -> TaskFinalDeliverable:
    """Persist ORM row, filesystem mirror, optional Chroma."""

    cfg = settings or get_settings()
    markdown_stripped = markdown_body.strip()
    title = derive_title(markdown_stripped, title_hint)
    slug_base = slugify_fragment(slug_hint or title)
    version = await allocate_next_version(session, lineage_id)
    normalized_tags = [str(item).strip() for item in tags if str(item).strip()][:32]

    row = TaskFinalDeliverable(
        id=uuid.uuid4(),
        lineage_id=lineage_id,
        version=version,
        dashboard_user_id=dashboard_user_id,
        source_task_id=source_task_id,
        ballroom_session_id=ballroom_session_id,
        mission_id=mission_id,
        slug=slug_base,
        title=title,
        markdown_body=markdown_stripped,
        structured_json=dict(structured),
        tags=list(dict.fromkeys(normalized_tags)),
        voice_script=(voice_script.strip()[:12_000] if voice_script else None),
        chroma_embedding_id=None,
        archive_relpath=None,
    )
    session.add(row)
    await session.flush()

    try:
        rel = await _write_archive_bundle(settings=cfg, slug=slug_base, version=version, payload=row)
        row.archive_relpath = rel
        await session.flush()
    except OSError as exc:
        logger.warning(
            "output_archive.fs_write_failed",
            agent_id=str(dashboard_user_id or ""),
            swarm_id=str(ballroom_session_id or ""),
            task_id=str(mission_id or ""),
            error=str(exc),
        )

    if cfg.output_archive_chroma_enabled:
        cap = cfg.output_archive_embed_max_chars
        embed_text_parts = [
            f"# {title}\n",
            markdown_stripped[:cap],
            "\n--- JSON ---\n",
            json.dumps(structured, default=str, sort_keys=True)[:8000],
        ]
        chroma_plain = "".join(embed_text_parts)
        meta_flat: dict[str, Any] = {
            "deliverable_id": str(row.id),
            "lineage_id": str(lineage_id),
            "version": version,
            "slug": slug_base,
            "dashboard_user_id": str(dashboard_user_id) if dashboard_user_id else "",
            "tags_csv": ",".join(row.tags[:12]),
        }
        try:
            row.chroma_embedding_id = await embed_and_store(
                chroma_plain,
                meta_flat,
                TASK_DELIVERABLES_COLLECTION,
            )
            await session.flush()
        except Exception as exc:
            logger.warning(
                "output_archive.chroma_failed",
                agent_id=str(dashboard_user_id or ""),
                swarm_id=str(ballroom_session_id or ""),
                task_id=str(mission_id or ""),
                error=str(exc),
            )

    logger.info(
        "output_archive.persisted",
        agent_id=str(dashboard_user_id or ""),
        swarm_id=str(ballroom_session_id or ""),
        task_id=str(mission_id or ""),
        lineage=str(lineage_id),
        version=version,
        deliverable_id=str(row.id),
    )
    return row


async def fetch_owned_deliverable(
    session: AsyncSession,
    *,
    deliverable_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> TaskFinalDeliverable | None:
    """Return deliverable scoped to cockpit owner."""

    row = await session.get(TaskFinalDeliverable, deliverable_id)
    if row is None:
        return None
    if row.dashboard_user_id != dashboard_user_id:
        return None
    return row


async def list_owned_deliverables(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    limit: int,
) -> list[TaskFinalDeliverable]:
    """Recent rows newest-first."""

    cap = max(1, min(limit, 120))
    stmt = (
        select(TaskFinalDeliverable)
        .where(TaskFinalDeliverable.dashboard_user_id == dashboard_user_id)
        .order_by(TaskFinalDeliverable.created_at.desc())
        .limit(cap)
    )
    res = await session.scalars(stmt)
    return list(res.all())


async def latest_for_lineage(
    session: AsyncSession,
    *,
    lineage_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> TaskFinalDeliverable | None:
    """Highest version row respecting ownership."""

    stmt = (
        select(TaskFinalDeliverable)
        .where(
            TaskFinalDeliverable.lineage_id == lineage_id,
            TaskFinalDeliverable.dashboard_user_id == dashboard_user_id,
        )
        .order_by(TaskFinalDeliverable.version.desc())
        .limit(1)
    )
    res = await session.scalar(stmt)
    return res


__all__ = [
    "derive_title",
    "fetch_owned_deliverable",
    "latest_for_lineage",
    "list_owned_deliverables",
    "persist_final_deliverable",
    "slugify_fragment",
]
