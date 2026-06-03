"""Push Skill Factory export bundles to GitHub via PR (never direct main write)."""

from __future__ import annotations

import base64
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.queen_maintainer.pr_workflow import build_pr_payload
from app.application.services.skill_export import build_export_bundle_from_tenant_skill
from app.application.services.skill_factory_service import mark_skill_github_exported
from app.common.schemas.skill_export import SkillExportFile, SkillExportResponse
from app.core.config import settings
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService, invoke_dynamic_tool
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

logger = structlog.get_logger(__name__)

_GITHUB_SLUG_DEFAULT = "github_rest"


def _github_target() -> tuple[str, str, str, str]:
    """Return owner, repo, base branch, connector slug from settings."""

    owner = settings.skill_factory_github_owner.strip()
    repo = settings.skill_factory_github_repo.strip()
    base = settings.skill_factory_github_base_branch.strip() or "main"
    slug = settings.skill_factory_github_connector_slug.strip().lower() or _GITHUB_SLUG_DEFAULT
    return owner, repo, base, slug


async def github_pr_export_ready(session: AsyncSession) -> bool:
    """True when env target repo + active GitHub connector are configured."""

    if not settings.skill_factory_github_pr_enabled:
        return False
    owner, repo, _, slug = _github_target()
    if not owner or not repo:
        return False
    row = await DynamicConnectorService().fetch_by_slug(session, slug=slug)
    if row is None or not row.is_active:
        return False
    svc = DynamicConnectorService()
    secrets = svc._secrets_dict(row)  # noqa: SLF001
    token = str(secrets.get("bearer_token") or secrets.get("api_key") or "").strip()
    return bool(token)


def _parse_json_response(raw: str) -> dict[str, Any]:
    """Parse dynamic connector JSON snippet."""

    text = raw.strip()
    if not text or text.startswith("dynamic_invoke"):
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_skill_export_branch_name(*, slug: str) -> str:
    """Build ``skill-factory/YYYYMMDD-slug`` branch name."""

    stamp = datetime.now(tz=UTC).strftime("%Y%m%d")
    safe = re.sub(r"[^a-z0-9\-]+", "-", slug.strip().lower())[:48].strip("-") or "skill"
    return f"skill-factory/{stamp}-{safe}"


async def _github_invoke(
    session: AsyncSession,
    *,
    connector_slug: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> tuple[bool, str]:
    """Invoke GitHub REST tool; return (ok, raw response)."""

    raw = await invoke_dynamic_tool(
        session,
        connector_slug=connector_slug,
        tool_name=tool_name,
        arguments=arguments,
        manager_slug="execution_operations",
        agent_task_id="skill_factory_github_export",
        granted_permissions=frozenset({"tool:write"}),
    )
    if raw.startswith("dynamic_invoke_error") or raw.startswith("dynamic_invoke_http"):
        return False, raw
    return True, raw


async def _resolve_base_sha(
    session: AsyncSession,
    *,
    owner: str,
    repo: str,
    base_branch: str,
    connector_slug: str,
) -> str | None:
    """Fetch commit SHA for base branch tip."""

    ok, raw = await _github_invoke(
        session,
        connector_slug=connector_slug,
        tool_name="git_ref_get",
        arguments={"owner": owner, "repo": repo, "ref": f"heads/{base_branch}"},
    )
    if not ok:
        logger.warning(
            "skill_factory.github_ref_get_failed",
            agent_id="skill_factory",
            reason=raw[:200],
        )
        return None
    payload = _parse_json_response(raw)
    obj = payload.get("object") if isinstance(payload.get("object"), dict) else {}
    sha = str(obj.get("sha") or "").strip()
    return sha or None


async def _create_branch(
    session: AsyncSession,
    *,
    owner: str,
    repo: str,
    branch: str,
    sha: str,
    connector_slug: str,
) -> bool:
    """Create branch ref from base SHA."""

    ok, raw = await _github_invoke(
        session,
        connector_slug=connector_slug,
        tool_name="git_ref_create",
        arguments={"owner": owner, "repo": repo, "ref": f"refs/heads/{branch}", "sha": sha},
    )
    if not ok and "422" in raw:
        # Branch may already exist — continue (idempotent re-export).
        return True
    if not ok:
        logger.warning(
            "skill_factory.github_ref_create_failed",
            agent_id="skill_factory",
            reason=raw[:200],
        )
        return False
    return True


async def _put_file(
    session: AsyncSession,
    *,
    owner: str,
    repo: str,
    branch: str,
    file_path: str,
    content: str,
    message: str,
    connector_slug: str,
) -> bool:
    """Create or update one file on branch via Contents API."""

    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    ok, raw = await _github_invoke(
        session,
        connector_slug=connector_slug,
        tool_name="repos_contents_put",
        arguments={
            "owner": owner,
            "repo": repo,
            "path": file_path,
            "message": message[:240],
            "content": encoded,
            "branch": branch,
        },
    )
    if ok:
        return True

    if "422" not in raw:
        logger.warning(
            "skill_factory.github_contents_put_failed",
            agent_id="skill_factory",
            path=file_path[:120],
            reason=raw[:200],
        )
        return False

    get_ok, get_raw = await _github_invoke(
        session,
        connector_slug=connector_slug,
        tool_name="repos_contents_get",
        arguments={"owner": owner, "repo": repo, "path": file_path, "ref": branch},
    )
    if not get_ok:
        return False
    existing = _parse_json_response(get_raw)
    file_sha = str(existing.get("sha") or "").strip()
    if not file_sha:
        return False

    ok, raw = await _github_invoke(
        session,
        connector_slug=connector_slug,
        tool_name="repos_contents_put",
        arguments={
            "owner": owner,
            "repo": repo,
            "path": file_path,
            "message": message[:240],
            "content": encoded,
            "branch": branch,
            "sha": file_sha,
        },
    )
    if not ok:
        logger.warning(
            "skill_factory.github_contents_update_failed",
            agent_id="skill_factory",
            path=file_path[:120],
            reason=raw[:200],
        )
    return ok


async def _commit_export_files(
    session: AsyncSession,
    *,
    owner: str,
    repo: str,
    branch: str,
    files: list[SkillExportFile],
    commit_prefix: str,
    connector_slug: str,
) -> tuple[int, list[str]]:
    """Upload all bundle files; return (success_count, failed_paths)."""

    ok_count = 0
    failed: list[str] = []
    for item in files:
        message = f"{commit_prefix}: {item.path}"
        if await _put_file(
            session,
            owner=owner,
            repo=repo,
            branch=branch,
            file_path=item.path,
            content=item.content,
            message=message,
            connector_slug=connector_slug,
        ):
            ok_count += 1
        else:
            failed.append(item.path)
    return ok_count, failed


def _pr_body(bundle: SkillExportResponse, *, branch: str) -> str:
    """PR description for operator review."""

    meta = bundle.meta
    lines = [
        "## Skill Factory export",
        "",
        f"- **Skill:** {meta.recipe_name}",
        f"- **Slug:** `{meta.slug}`",
        f"- **Branch:** `{branch}`",
        f"- **Verified:** {'yes' if meta.verified else 'pending'}",
        "",
        "### Files",
        "",
    ]
    for item in bundle.files:
        lines.append(f"- `{item.path}`")
    lines.extend(
        [
            "",
            "### Operator checklist",
            "",
            "- [ ] Review SKILL.md guardrails + evaluation criteria",
            "- [ ] Copy LISTING.md to Gumroad if selling externally",
            "- [ ] Merge when ready — **never** auto-merge from factory",
            "",
            bundle.install_hint,
        ],
    )
    return "\n".join(lines)


async def push_skill_export_github_pr(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    skill_id: uuid.UUID,
) -> dict[str, Any]:
    """Build export bundle, commit to branch, open GitHub PR for operator review."""

    if not settings.skill_factory_github_pr_enabled:
        return {"ok": False, "error": "github_pr_disabled"}

    owner, repo, base_branch, connector_slug = _github_target()
    if not owner or not repo:
        return {"ok": False, "error": "github_target_not_configured"}
    if not await github_pr_export_ready(session):
        return {"ok": False, "error": "github_connector_not_ready"}

    from sqlalchemy import select

    row = await session.get(TenantSkillORM, skill_id)
    if row is None or row.tenant_id != tenant_id:
        return {"ok": False, "error": "skill_not_found"}

    opportunity = await session.scalar(
        select(SkillOpportunityORM).where(
            SkillOpportunityORM.tenant_id == tenant_id,
            SkillOpportunityORM.tenant_skill_id == skill_id,
        ),
    )
    bundle = build_export_bundle_from_tenant_skill(row, opportunity=opportunity)
    branch = build_skill_export_branch_name(slug=bundle.meta.slug)

    base_sha = await _resolve_base_sha(
        session,
        owner=owner,
        repo=repo,
        base_branch=base_branch,
        connector_slug=connector_slug,
    )
    if not base_sha:
        return {"ok": False, "error": "base_ref_unresolved"}

    if not await _create_branch(
        session,
        owner=owner,
        repo=repo,
        branch=branch,
        sha=base_sha,
        connector_slug=connector_slug,
    ):
        return {"ok": False, "error": "branch_create_failed"}

    ok_count, failed = await _commit_export_files(
        session,
        owner=owner,
        repo=repo,
        branch=branch,
        files=bundle.files,
        commit_prefix=f"skill-factory: {bundle.meta.slug}",
        connector_slug=connector_slug,
    )
    if ok_count == 0:
        return {"ok": False, "error": "file_commit_failed", "failed_paths": failed}

    pr_title = f"skill-factory: {bundle.meta.recipe_name}"[:256]
    pr_body = _pr_body(bundle, branch=branch)
    pr_payload = build_pr_payload(title=pr_title, body=pr_body, head_branch=branch, base_branch=base_branch)
    pr_ok, pr_raw = await _github_invoke(
        session,
        connector_slug=connector_slug,
        tool_name="pulls_create",
        arguments={"owner": owner, "repo": repo, **pr_payload},
    )
    pr_result: dict[str, Any]
    if pr_ok:
        pr_result = {
            "status": "created",
            "branch": branch,
            "github_response_preview": pr_raw[:2000],
            "pr_payload": pr_payload,
        }
    else:
        pr_result = {
            "status": "connector_error",
            "reason": pr_raw[:500],
            "branch": branch,
            "pr_payload": pr_payload,
        }

    await mark_skill_github_exported(session, tenant_id=tenant_id, skill_id=skill_id)

    logger.info(
        "skill_factory.github_pr_pushed",
        agent_id="skill_factory",
        swarm_id=str(tenant_id),
        task_id=str(skill_id),
        branch=branch,
        files_ok=ok_count,
        pr_status=pr_result.get("status"),
    )

    return {
        "ok": True,
        "branch": branch,
        "files_committed": ok_count,
        "files_failed": failed,
        "pr": pr_result,
        "owner": owner,
        "repo": repo,
    }


__all__ = [
    "build_skill_export_branch_name",
    "github_pr_export_ready",
    "push_skill_export_github_pr",
]
