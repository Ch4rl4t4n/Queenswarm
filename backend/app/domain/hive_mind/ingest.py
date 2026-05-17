"""Ingest ballroom deliverables — summarisation helpers + stitching."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.hive_mind import vault as vault_ops
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

_TOKEN_RE = re.compile(r"#\s+([^\n]{2,140})")


def extract_auto_tags(markdown_body: str, existing: list[str]) -> list[str]:
    """Merge heading-derived tags without exploding cardinality."""

    found: list[str] = []
    for m in _TOKEN_RE.finditer(markdown_body[:8000]):
        slug = re.sub(r"[^a-z0-9_-]+", "-", m.group(1).lower()).strip("-")
        if len(slug) > 32 or len(slug) < 2:
            continue
        found.append(slug)
        if len(found) >= 12:
            break
    merged = list(dict.fromkeys([*(t.strip().lower().replace(" ", "_") for t in existing), *found]))
    return merged[:48]


class HiveMindExtras(BaseModel):
    """Optional mission metadata carried through OutputEngine ingestion."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    reflection_excerpt: str | None = None
    manager_template_slugs: list[str] = Field(default_factory=list)


def summarise_deliverable(structured: dict[str, Any], markdown_body: str) -> tuple[str, str]:
    """Return `(summary, insight_body)` derived heuristically (no LLM by default — RAM-safe)."""

    summary = ""
    cand = structured.get("summary") or structured.get("brief_excerpt")
    if isinstance(cand, str) and cand.strip():
        summary = cand.strip()
    elif isinstance(structured.get("reflection"), dict):
        refl = structured.get("reflection") or {}
        pm = refl.get("post_mortem")
        if isinstance(pm, dict):
            rex = pm.get("reflection_excerpt")
            if isinstance(rex, str) and rex.strip():
                summary = rex.strip()
            else:
                for key in ("lessons_learned", "rationale", "summary"):
                    val = pm.get(key)
                    if isinstance(val, str) and val.strip():
                        summary = val.strip()
                        break

    lines = markdown_body.strip().splitlines()
    if not summary and lines:
        summary = lines[0].lstrip("#").strip()[:400]

    insight_lines: list[str] = []
    for line in markdown_body.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ", "• ")):
            insight_lines.append(stripped[:240])
        if len("\n".join(insight_lines)) > 1200:
            break
    fallback_insight = "\n".join(insight_lines)
    insight_body = summary if len(summary) > 240 else (fallback_insight if fallback_insight else summary)
    return summary[:2000], insight_body[:4800]


async def persist_vault_projection(
    *,
    row: TaskFinalDeliverable,
    summary: str,
    reflection_excerpt: str | None,
    insight_note: str,
    vault_root_str: str,
    folder_slug_hint: str,
) -> str | None:
    """Write Markdown mirror; returns relative vault path when filesystem succeeds."""

    folder = vault_ops.vault_day_folder_slug(row.title, folder_slug_hint or row.slug)
    manifest: dict[str, Any] = {
        "phase": "0.6",
        "deliverable_id": str(row.id),
        "lineage_id": str(row.lineage_id),
        "version": row.version,
        "title": row.title,
        "slug": row.slug,
        "summary": summary,
        "dashboard_user_id": str(row.dashboard_user_id) if row.dashboard_user_id else "",
        "mission_id": str(row.mission_id) if row.mission_id else "",
        "ballroom_session_id": str(row.ballroom_session_id) if row.ballroom_session_id else "",
        "tags": row.tags,
        "reflection_excerpt_preview": (reflection_excerpt or "")[:4000],
    }

    refl_md = reflection_excerpt.strip() if reflection_excerpt else None
    try:
        return await vault_ops.write_hive_mind_bundle(
            vault_root=Path(vault_root_str),
            folder_name=folder,
            deliverable_md=row.markdown_body,
            manifest=manifest,
            reflection_md=refl_md,
            insight_note=insight_note,
            version=int(row.version),
        )
    except OSError:
        return None


__all__ = [
    "HiveMindExtras",
    "extract_auto_tags",
    "persist_vault_projection",
    "summarise_deliverable",
]
