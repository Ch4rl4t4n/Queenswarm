"""Mirror external integration audit lines into the Hive Mind Markdown vault (fail-open)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _write_vault_append(path: Path, lines: list[str]) -> None:
    """Blocking append of UTF-8 lines ensuring parent dirs exist."""

    path.parent.mkdir(parents=True, exist_ok=True)
    blob = "\n".join(lines) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(blob)


async def mirror_external_audit_to_vault(
    *,
    project_slug: str,
    action_slug: str,
    ok: bool,
    latency_ms: int,
    summary: dict[str, Any],
    agent_id: str,
    swarm_id: str,
    task_id: str,
    settings: Settings | None = None,
) -> None:
    """Append a short Markdown audit stitch under ``external_integrations/``.

    Args:
        project_slug: Stable slug for the remote integration surface.
        action_slug: Invoked capability identifier.
        ok: Whether the guarded invocation succeeded.
        latency_ms: Wall-clock latency for observability.
        summary: JSON-safe preview dictionary stored beside narrative headers.
        agent_id: Structured logging / Hive lineage anchor (often API key id prefix).
        swarm_id: Hive lineage grouping (project slug recommended).
        task_id: Idempotency / correlation anchor (often audit row UUID).
        settings: Optional settings override for tests.
    """

    cfg = settings or get_settings()
    if not cfg.hive_mind_enabled or not cfg.external_integration_audit_to_vault:
        return

    root = Path(cfg.hive_mind_vault_root).expanduser()
    day = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    path = root / "external_integrations" / project_slug / f"{day}.md"
    stamp = datetime.now(tz=UTC).isoformat()
    lines = [
        f"## external:{project_slug} @ {stamp}",
        f"- action: `{action_slug}`",
        f"- ok: `{ok}`",
        f"- latency_ms: `{latency_ms}`",
        f"- agent_id: `{agent_id}`",
        f"- swarm_id: `{swarm_id}`",
        f"- task_id: `{task_id}`",
        f"- summary: `{summary!r}`",
        "",
    ]
    try:
        await asyncio.to_thread(_write_vault_append, path, lines)
    except OSError as exc:
        logger.warning(
            "external.hive_audit.vault_append_failed",
            agent_id=agent_id,
            swarm_id=swarm_id,
            task_id=task_id,
            error=str(exc),
        )


__all__ = ["mirror_external_audit_to_vault"]
