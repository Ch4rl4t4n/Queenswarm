"""Unit tests for GitHub post-merge webhook → Queen Maintainer."""

from __future__ import annotations

import hashlib
import hmac
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.queen_maintainer.post_merge_webhook import (
    decode_github_webhook_payload,
    parse_post_merge_context,
    repository_matches_config,
    verify_github_webhook_signature,
)


def test_verify_github_webhook_signature_accepts_sha256() -> None:
    """Valid HMAC sha256 signature should pass verification."""

    secret = "super-secret"
    body = b'{"action":"closed"}'
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    assert verify_github_webhook_signature(
        secret=secret,
        body=body,
        signature_header=f"sha256={digest}",
    )


def test_parse_post_merge_context_when_pr_merged_then_returns_metadata() -> None:
    """Merged pull_request closed events should produce trigger context."""

    payload = {
        "action": "closed",
        "pull_request": {
            "merged": True,
            "title": "feat: ship rubrics",
            "merge_commit_sha": "abc123",
            "html_url": "https://github.com/org/repo/pull/1",
            "base": {"ref": "main"},
            "user": {"login": "bee-operator"},
        },
        "repository": {"full_name": "org/repo", "name": "repo", "owner": {"login": "org"}},
    }
    ctx = parse_post_merge_context("pull_request", payload)
    assert ctx is not None
    assert ctx["kind"] == "pull_request_merged"
    assert ctx["title"] == "feat: ship rubrics"


def test_parse_post_merge_context_when_push_to_feature_branch_then_ignored() -> None:
    """Non-default branch pushes should not trigger Maintainer."""

    payload = {"ref": "refs/heads/feature/foo", "repository": {"full_name": "org/repo"}}
    assert parse_post_merge_context("push", payload) is None


def test_decode_github_webhook_payload_rejects_invalid_json() -> None:
    """Malformed webhook bodies should raise ValueError."""

    with pytest.raises(ValueError, match="Invalid GitHub webhook JSON"):
        decode_github_webhook_payload(b"not-json")


@pytest.mark.asyncio
async def test_handle_github_post_merge_webhook_triggers_session() -> None:
    """Merged PR webhook should spawn Maintainer supervisor session."""

    from app.core import config as config_module

    config_module.get_settings.cache_clear()
    db = AsyncMock()
    payload = {
        "action": "closed",
        "pull_request": {
            "merged": True,
            "title": "merge maintainer",
            "merge_commit_sha": "deadbeef",
            "base": {"ref": "main"},
            "user": {"login": "operator"},
        },
        "repository": {"full_name": "org/repo", "name": "repo", "owner": {"login": "org"}},
    }
    with patch.object(config_module.settings, "queen_maintainer_enabled", True):
        with patch.object(config_module.settings, "queen_maintainer_post_merge_webhook_enabled", True):
            with patch.object(
                config_module.settings,
                "queen_maintainer_post_merge_tenant_id",
                "11111111-1111-1111-1111-111111111111",
            ):
                with patch.object(config_module.settings, "queen_maintainer_github_owner", "org"):
                    with patch.object(config_module.settings, "queen_maintainer_github_repo", "repo"):
                        with patch(
                            "app.application.services.queen_maintainer.post_merge_webhook.ensure_queen_maintainer_routine",
                            new_callable=AsyncMock,
                        ) as ensure_mock:
                            routine = AsyncMock()
                            routine.id = "routine-1"
                            routine.context_payload = {}
                            ensure_mock.return_value = routine
                            with patch(
                                "app.application.services.queen_maintainer.post_merge_webhook.queue_maintainer_run",
                                new_callable=AsyncMock,
                                return_value={
                                    "ok": True,
                                    "session_id": "11111111-1111-1111-1111-111111111111",
                                },
                            ):
                                from app.application.services.queen_maintainer.post_merge_webhook import (
                                    handle_github_post_merge_webhook,
                                )

                                result = await handle_github_post_merge_webhook(
                                    db,
                                    event="pull_request",
                                    payload=payload,
                                )

    assert result["triggered"] is True
    assert result["session_id"] == "11111111-1111-1111-1111-111111111111"


def test_repository_matches_config_when_owner_repo_set() -> None:
    """Configured owner/repo should filter unrelated repositories."""

    with patch("app.application.services.queen_maintainer.post_merge_webhook.settings") as mock_settings:
        mock_settings.queen_maintainer_github_owner = "Queenswarm"
        mock_settings.queen_maintainer_github_repo = "Queenswarm"
        payload = {
            "repository": {
                "name": "Queenswarm",
                "owner": {"login": "Queenswarm"},
            },
        }
        assert repository_matches_config(payload) is True
