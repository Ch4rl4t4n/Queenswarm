"""Markdown vault mirroring ingest — Obsidian-compatible plain Markdown + JSON sidecar."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import aiofiles


def _vault_slug(text: str, *, max_len: int = 48) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = lowered.strip("-")[:max_len]
    return lowered or "hive-mind"


def vault_day_folder_slug(title: str, slug_hint: str) -> str:
    """Return `{iso_date}_{slug}` directory name rooted under the vault."""

    base = _vault_slug(slug_hint or title or "hive-mind", max_len=48)
    return f"{date.today().isoformat()}_{base}"


async def write_hive_mind_bundle(
    *,
    vault_root: Path,
    folder_name: str,
    deliverable_md: str,
    manifest: dict[str, Any],
    reflection_md: str | None,
    insight_note: str | None,
    version: int,
) -> str:
    """Persist Markdown + manifest JSON + optional artefacts; returns relative folder path."""

    root = vault_root.resolve()
    target = root / folder_name / f"v{version}"
    target.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(target / "memory.md", "w", encoding="utf-8") as fh:
        await fh.write(deliverable_md)

    async with aiofiles.open(target / "manifest.json", "w", encoding="utf-8") as fh:
        await fh.write(json.dumps(manifest, indent=2, default=str))

    if reflection_md and reflection_md.strip():
        async with aiofiles.open(target / "reflection.md", "w", encoding="utf-8") as fh:
            await fh.write(reflection_md.strip())

    if insight_note and insight_note.strip():
        async with aiofiles.open(target / "insight.md", "w", encoding="utf-8") as fh:
            await fh.write(insight_note.strip())

    return f"{folder_name}/v{version}"


__all__ = ["vault_day_folder_slug", "write_hive_mind_bundle"]
