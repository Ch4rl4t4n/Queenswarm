"""GitHub PR-only workflow helpers for Queen Maintainer (never write to main)."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.connectors.dynamic.service import invoke_dynamic_tool

logger = get_logger(__name__)

MAINTAINER_DENYLIST_PREFIXES: tuple[str, ...] = (
    ".env",
    ".env.",
    "backend/app/presentation/api/routers/billing",
    "backend/app/core/config.py",
    "docker-compose.prod",
    "nginx/",
    "scripts/deploy-prod.sh",
)

MAINTAINER_DENYLIST_EXACT: frozenset[str] = frozenset(
    {
        ".env.prod",
        ".env.stg",
        "docker-compose.prod.yml",
    },
)


def validate_changed_paths(paths: list[str]) -> tuple[bool, list[str]]:
    """Return whether all paths are allowed for Maintainer PRs.

    Args:
        paths: Repository-relative POSIX paths.

    Returns:
        Tuple of (all_allowed, blocked_paths).
    """
    blocked: list[str] = []
    for raw in paths:
        normalized = str(PurePosixPath(raw.replace("\\", "/")))
        if normalized.startswith("./"):
            normalized = normalized[2:]
        if normalized in MAINTAINER_DENYLIST_EXACT:
            blocked.append(normalized)
            continue
        if any(normalized.startswith(prefix) for prefix in MAINTAINER_DENYLIST_PREFIXES):
            blocked.append(normalized)
    return (len(blocked) == 0, blocked)


def build_branch_name(*, slug: str) -> str:
    """Build ``queen-maintainer/YYYYMMDD-slug`` branch name."""

    stamp = datetime.now(tz=UTC).strftime("%Y%m%d")
    safe = re.sub(r"[^a-z0-9\-]+", "-", slug.strip().lower())[:48].strip("-") or "maint"
    return f"queen-maintainer/{stamp}-{safe}"


def build_pr_payload(
    *,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str = "main",
) -> dict[str, Any]:
    """Build GitHub REST pull request create body."""

    return {
        "title": title[:256],
        "body": body[:65_000],
        "head": head_branch,
        "base": base_branch,
    }


async def create_github_pr_if_configured(
    session: AsyncSession,
    *,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str = "main",
) -> dict[str, Any]:
    """Attempt PR creation via dynamic ``github_rest`` connector when configured.

    Never merges — operator review required.
    """
    owner = settings.queen_maintainer_github_owner.strip()
    repo = settings.queen_maintainer_github_repo.strip()
    slug = settings.queen_maintainer_github_connector_slug.strip().lower() or "github_rest"

    payload = build_pr_payload(title=title, body=body, head_branch=head_branch, base_branch=base_branch)

    if not owner or not repo:
        return {
            "status": "manual_required",
            "reason": "QUEEN_MAINTAINER_GITHUB_OWNER/REPO not configured",
            "branch": head_branch,
            "pr_payload": payload,
        }

    result = await invoke_dynamic_tool(
        session,
        connector_slug=slug,
        tool_name="pulls_create",
        arguments={
            "owner": owner,
            "repo": repo,
            **payload,
        },
        manager_slug="execution_operations",
        agent_task_id="queen_maintainer",
        granted_permissions=frozenset({"tool:write"}),
    )

    if str(result).startswith("dynamic_invoke_error"):
        logger.warning(
            "queen_maintainer.pr_create_failed",
            agent_id="queen_maintainer",
            swarm_id="maintainer",
            task_id="",
            error=result[:500],
        )
        return {
            "status": "connector_error",
            "reason": result,
            "branch": head_branch,
            "pr_payload": payload,
        }

    return {
        "status": "created",
        "branch": head_branch,
        "github_response_preview": str(result)[:2000],
        "pr_payload": payload,
    }


__all__ = [
    "MAINTAINER_DENYLIST_EXACT",
    "MAINTAINER_DENYLIST_PREFIXES",
    "build_branch_name",
    "build_pr_payload",
    "create_github_pr_if_configured",
    "validate_changed_paths",
]
