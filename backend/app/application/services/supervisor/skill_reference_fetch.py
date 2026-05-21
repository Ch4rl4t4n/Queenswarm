"""Lazy fetch for skill reference pointers (Langfuse-style reference mode)."""

from __future__ import annotations

from pathlib import Path
import re

import httpx

from app.core.logging import get_logger
from app.core.repo_root import resolve_repo_root

logger = get_logger(__name__)

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _safe_repo_path(repo_root: Path, reference: str) -> Path | None:
    """Resolve a repo-relative reference without path traversal."""

    raw = (reference or "").strip()
    if not raw or _URL_RE.match(raw):
        return None
    candidate = (repo_root / raw).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


async def fetch_skill_reference(
    reference: str,
    *,
    repo_root: Path | None = None,
    max_chars: int = 3000,
) -> str:
    """Fetch one skill reference (HTTPS URL or repo-relative doc path).

    Args:
        reference: URL or path like ``docs/harness/QUEEN_MAINTAINER_INSTRUCTIONS.md``.
        repo_root: Repository root for local paths; defaults to ``resolve_repo_root()``.
        max_chars: Maximum returned characters per reference.

    Returns:
        Trimmed text content, or empty string on failure.
    """

    ref = (reference or "").strip()
    if not ref:
        return ""

    cap = max(256, min(int(max_chars), 12000))
    root = repo_root or resolve_repo_root()

    if _URL_RE.match(ref):
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                response = await client.get(ref)
            if response.status_code >= 400:
                logger.warning(
                    "skill_reference.fetch_http_failed",
                    agent_id="skill_library",
                    swarm_id="",
                    task_id="",
                    reference=ref[:240],
                    status=response.status_code,
                )
                return ""
            text = (response.text or "").strip()
            return text[:cap]
        except httpx.HTTPError as exc:
            logger.warning(
                "skill_reference.fetch_http_error",
                agent_id="skill_library",
                swarm_id="",
                task_id="",
                reference=ref[:240],
                error=str(exc)[:240],
            )
            return ""

    local = _safe_repo_path(root, ref)
    if local is None:
        return ""
    try:
        text = local.read_text(encoding="utf-8").strip()
        return text[:cap]
    except OSError as exc:
        logger.warning(
            "skill_reference.fetch_local_failed",
            agent_id="skill_library",
            swarm_id="",
            task_id="",
            reference=ref[:240],
            error=str(exc)[:240],
        )
        return ""


__all__ = ["fetch_skill_reference"]
