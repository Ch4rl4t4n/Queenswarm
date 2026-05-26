"""GitHub post-merge webhook → Queen Maintainer supervisor trigger."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.queen_maintainer.service import (
    build_maintainer_goal,
    build_post_merge_maintainer_goal,
    ensure_queen_maintainer_routine,
    queue_maintainer_run,
)
from app.core.config import settings

logger = structlog.get_logger(__name__)

DEFAULT_BRANCH_REFS = frozenset({"refs/heads/main", "refs/heads/master"})


class PostMergeWebhookConfigError(ValueError):
    """Webhook ingress misconfigured."""


class PostMergeWebhookDisabledError(ValueError):
    """Post-merge webhook feature flag is off."""


def verify_github_webhook_signature(
    *,
    secret: str,
    body: bytes,
    signature_header: str,
) -> bool:
    """Validate ``X-Hub-Signature-256`` or legacy ``X-Hub-Signature`` HMAC."""

    trimmed_secret = secret.strip()
    trimmed_sig = signature_header.strip()
    if not trimmed_secret or not trimmed_sig:
        return False

    if trimmed_sig.startswith("sha256="):
        digest = hmac.new(trimmed_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        expected = f"sha256={digest}"
        return hmac.compare_digest(expected, trimmed_sig)

    if trimmed_sig.startswith("sha1="):
        digest = hmac.new(trimmed_secret.encode("utf-8"), body, hashlib.sha1).hexdigest()
        expected = f"sha1={digest}"
        return hmac.compare_digest(expected, trimmed_sig)

    return False


def parse_post_merge_context(event: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return merge metadata when GitHub event should trigger Maintainer, else None."""

    event_key = event.strip().lower()
    if event_key == "ping":
        return {"kind": "ping"}

    if event_key == "pull_request":
        action = str(payload.get("action") or "").strip().lower()
        pull_request = payload.get("pull_request")
        if not isinstance(pull_request, dict):
            return None
        if action != "closed" or not bool(pull_request.get("merged")):
            return None
        base = pull_request.get("base") if isinstance(pull_request.get("base"), dict) else {}
        user = pull_request.get("user") if isinstance(pull_request.get("user"), dict) else {}
        return {
            "kind": "pull_request_merged",
            "title": str(pull_request.get("title") or "").strip(),
            "merge_commit_sha": str(pull_request.get("merge_commit_sha") or "").strip(),
            "base_ref": str(base.get("ref") or "").strip(),
            "merged_by": str(user.get("login") or "").strip(),
            "html_url": str(pull_request.get("html_url") or "").strip(),
            "repo_full_name": _repo_full_name(payload),
        }

    if event_key == "push":
        ref = str(payload.get("ref") or "").strip()
        if ref not in DEFAULT_BRANCH_REFS:
            return None
        head_commit = payload.get("head_commit") if isinstance(payload.get("head_commit"), dict) else {}
        return {
            "kind": "push_default_branch",
            "ref": ref,
            "head_commit_sha": str(head_commit.get("id") or "").strip(),
            "commit_message": str(head_commit.get("message") or "").strip(),
            "repo_full_name": _repo_full_name(payload),
        }

    return None


def _repo_full_name(payload: dict[str, Any]) -> str:
    repository = payload.get("repository")
    if isinstance(repository, dict):
        return str(repository.get("full_name") or "").strip()
    return ""


def repository_matches_config(payload: dict[str, Any]) -> bool:
    """Return True when webhook repo matches configured owner/repo (or config unset)."""

    owner = settings.queen_maintainer_github_owner.strip().lower()
    repo = settings.queen_maintainer_github_repo.strip().lower()
    if not owner or not repo:
        return True

    repository = payload.get("repository")
    if not isinstance(repository, dict):
        return False
    repo_owner = repository.get("owner")
    owner_login = ""
    if isinstance(repo_owner, dict):
        owner_login = str(repo_owner.get("login") or "").strip().lower()
    repo_name = str(repository.get("name") or "").strip().lower()
    return owner_login == owner and repo_name == repo


def resolve_post_merge_tenant_id() -> uuid.UUID:
    """Return tenant id configured for Maintainer webhook triggers."""

    raw = (settings.queen_maintainer_post_merge_tenant_id or "").strip()
    if not raw:
        msg = "QUEEN_MAINTAINER_POST_MERGE_TENANT_ID is not configured."
        raise PostMergeWebhookConfigError(msg)
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        msg = "QUEEN_MAINTAINER_POST_MERGE_TENANT_ID must be a valid UUID."
        raise PostMergeWebhookConfigError(msg) from exc


def webhook_status_payload() -> dict[str, Any]:
    """Non-secret webhook deployment status for dashboards."""

    return {
        "enabled": bool(settings.queen_maintainer_post_merge_webhook_enabled),
        "secret_configured": bool((settings.queen_maintainer_github_webhook_secret or "").strip()),
        "tenant_id_configured": bool((settings.queen_maintainer_post_merge_tenant_id or "").strip()),
        "github_owner": settings.queen_maintainer_github_owner,
        "github_repo": settings.queen_maintainer_github_repo,
        "webhook_path": "/api/v1/queen-maintainer/github-webhook",
        "accepted_events": ["ping", "pull_request", "push"],
    }


async def handle_github_post_merge_webhook(
    db: AsyncSession,
    *,
    event: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify-ready handler: parse merge event and spawn Maintainer session."""

    if not settings.queen_maintainer_enabled:
        msg = "Queen Maintainer feature flag disabled."
        raise PostMergeWebhookDisabledError(msg)
    if not settings.queen_maintainer_post_merge_webhook_enabled:
        msg = "Post-merge webhook disabled."
        raise PostMergeWebhookDisabledError(msg)

    merge_ctx = parse_post_merge_context(event, payload)
    if merge_ctx is None:
        return {"triggered": False, "reason": "ignored_event", "event": event}

    if merge_ctx.get("kind") == "ping":
        return {"triggered": False, "reason": "ping", "hook_id": payload.get("hook_id")}

    if not repository_matches_config(payload):
        return {
            "triggered": False,
            "reason": "repo_mismatch",
            "repo_full_name": _repo_full_name(payload),
        }

    tenant_id = resolve_post_merge_tenant_id()
    subject = "github:post-merge-webhook"
    routine = await ensure_queen_maintainer_routine(
        db,
        tenant_id=tenant_id,
        created_by_subject=subject,
        enabled=True,
    )

    if merge_ctx.get("kind") == "pull_request_merged":
        routine.goal_template = build_post_merge_maintainer_goal(merge_meta=merge_ctx)
    else:
        routine.goal_template = build_post_merge_maintainer_goal(merge_meta=merge_ctx)

    payload_ctx = dict(routine.context_payload or {})
    payload_ctx["post_merge_trigger"] = merge_ctx
    payload_ctx["post_merge_event"] = event
    routine.context_payload = payload_ctx
    await db.flush()

    result = await queue_maintainer_run(
        db,
        routine=routine,
        trigger_source="post_merge_webhook",
        goal_override=routine.goal_template,
    )
    if not result.get("ok"):
        return {
            "triggered": False,
            "reason": str(result.get("error") or "blocked"),
            "budget": result,
        }

    session_id = uuid.UUID(str(result["session_id"]))
    logger.info(
        "queen_maintainer.post_merge_triggered",
        agent_id="queen_maintainer",
        swarm_id=str(tenant_id),
        task_id=str(session_id),
        github_event=event,
        merge_kind=merge_ctx.get("kind"),
    )
    return {
        "triggered": True,
        "session_id": str(session_id),
        "routine_id": str(routine.id),
        "merge_kind": merge_ctx.get("kind"),
        "repo_full_name": merge_ctx.get("repo_full_name"),
    }


def decode_github_webhook_payload(body: bytes) -> dict[str, Any]:
    """Parse JSON body from GitHub webhook delivery."""

    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        msg = "Invalid GitHub webhook JSON body."
        raise ValueError(msg) from exc
    if not isinstance(parsed, dict):
        msg = "GitHub webhook payload must be a JSON object."
        raise ValueError(msg)
    return parsed


__all__ = [
    "PostMergeWebhookConfigError",
    "PostMergeWebhookDisabledError",
    "decode_github_webhook_payload",
    "handle_github_post_merge_webhook",
    "parse_post_merge_context",
    "repository_matches_config",
    "verify_github_webhook_signature",
    "webhook_status_payload",
]
