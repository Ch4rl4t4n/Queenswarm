"""Obsidian Markdown vault → HiveMind Chroma embedding bridge (Phase 3)."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.chroma_client import HIVE_MIND_COLLECTION, embed_and_store
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_LAST_SYNC_STATE: dict[str, Any] = {
    "last_run_at": None,
    "files_scanned": 0,
    "chunks_embedded": 0,
    "errors": [],
}


async def run_obsidian_vault_sync_once(
    settings: Settings | None = None,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Walk ``hive_mind_vault_root`` for Markdown and embed snippets into ``hive_mind``."""

    cfg = settings or get_settings()
    errors: list[str] = []
    embedded = 0
    scanned = 0

    if not cfg.phase3_obsidian_watch_enabled and not force:
        return {"skipped": True, "reason": "phase3_obsidian_watch_disabled"}

    if not cfg.hive_mind_enabled or not cfg.hive_mind_chroma_enabled:
        msg = "hive_mind chroma disabled — skipping Obsidian sync."
        logger.info(
            "phase3.obsidian_sync.skipped",
            agent_id="phase3-obsidian",
            swarm_id="vault",
            task_id="sync-once",
            reason=msg,
        )
        return {"skipped": True, "reason": msg}

    root = Path(cfg.hive_mind_vault_root).expanduser()
    if not root.is_dir():
        msg = f"vault root missing:{root}"
        errors.append(msg)
        _publish_state(scanned, embedded, errors)
        return {"ok": False, "errors": errors}

    max_files = cfg.phase3_obsidian_max_files_per_sync
    max_chars = cfg.hive_mind_embed_max_chars
    skip_prefixes = tuple(cfg.phase3_obsidian_ignore_dir_prefixes)

    def _walk() -> list[Path]:
        files: list[Path] = []
        for path in sorted(root.rglob("*.md")):
            if any(part.startswith(".") for part in path.parts):
                continue
            rel = path.relative_to(root)
            if any(str(rel).startswith(pfx.strip("/")) for pfx in skip_prefixes if pfx.strip()):
                continue
            files.append(path)
            if len(files) >= max_files:
                break
        return files

    candidates = await asyncio.to_thread(_walk)
    scanned = len(candidates)

    for md_path in candidates:
        try:
            text = await asyncio.to_thread(md_path.read_text, encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"{md_path}:{exc!s}")
            continue

        trimmed = text.strip()
        if not trimmed:
            continue
        if len(trimmed) > max_chars:
            trimmed = trimmed[: max_chars - 1] + "…"

        rel_key = str(md_path.relative_to(root))
        stable = hashlib.sha256(rel_key.encode("utf-8")).hexdigest()
        doc_blob = f"# {md_path.name}\npath:{rel_key}\n\n{trimmed}"
        meta = {
            "source": "obsidian_phase3",
            "vault_rel_path": rel_key,
            "vault_digest": stable[:24],
        }
        try:
            await embed_and_store(doc_blob, meta, HIVE_MIND_COLLECTION)
            embedded += 1
        except (RuntimeError, ValueError, TypeError) as exc:
            errors.append(f"chroma:{rel_key}:{exc!s}")

    logger.info(
        "phase3.obsidian_sync.completed",
        agent_id="phase3-obsidian",
        swarm_id="vault",
        task_id="sync-once",
        scanned=scanned,
        embedded=embedded,
        errors=len(errors),
    )
    _publish_state(scanned, embedded, errors)
    return {
        "ok": not errors,
        "files_scanned": scanned,
        "chunks_embedded": embedded,
        "errors": errors,
    }


def obsidian_sync_snapshot() -> dict[str, Any]:
    """Return last published telemetry for dashboards."""

    return dict(_LAST_SYNC_STATE)


def _publish_state(scanned: int, embedded: int, errors: list[str]) -> None:
    """Update module-level snapshot consumed by HTTP handlers."""

    global _LAST_SYNC_STATE
    _LAST_SYNC_STATE = {
        "last_run_at": datetime.now(tz=UTC).isoformat(),
        "files_scanned": scanned,
        "chunks_embedded": embedded,
        "errors": errors[:12],
    }


async def obsidian_poll_loop() -> None:
    """Background cadence aligned with ~16 GB single-node deployments."""

    cfg = get_settings()
    interval = float(cfg.phase3_obsidian_poll_interval_sec)
    log = get_logger(__name__)
    while True:
        try:
            await run_obsidian_vault_sync_once(cfg)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — watchdog loop must survive
            log.warning(
                "phase3.obsidian_sync.loop_error",
                agent_id="phase3-obsidian",
                swarm_id="vault",
                task_id="poll-loop",
                error=str(exc),
            )
        await asyncio.sleep(max(30.0, interval))


__all__ = [
    "obsidian_poll_loop",
    "obsidian_sync_snapshot",
    "run_obsidian_vault_sync_once",
]
