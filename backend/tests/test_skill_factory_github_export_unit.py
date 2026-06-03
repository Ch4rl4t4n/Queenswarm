"""Unit tests for Skill Factory GitHub PR export."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.application.services.skill_factory_github_export import (
    build_skill_export_branch_name,
    github_pr_export_ready,
    push_skill_export_github_pr,
)


def test_build_skill_export_branch_name_format() -> None:
    branch = build_skill_export_branch_name(slug="Newsletter Growth Pack")
    assert branch.startswith("skill-factory/")
    assert "newsletter-growth-pack" in branch


@pytest.mark.asyncio
async def test_github_pr_export_ready_false_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.application.services.skill_factory_github_export.settings",
        SimpleNamespace(
            skill_factory_github_pr_enabled=False,
            skill_factory_github_owner="acme",
            skill_factory_github_repo="skills",
            skill_factory_github_connector_slug="github_rest",
            skill_factory_github_base_branch="main",
        ),
    )
    assert await github_pr_export_ready(AsyncMock()) is False


@pytest.mark.asyncio
async def test_push_skill_export_github_pr_happy_path(monkeypatch) -> None:
    tenant_id = uuid4()
    skill_id = uuid4()
    skill = SimpleNamespace(
        id=skill_id,
        tenant_id=tenant_id,
        slug="test-skill",
        title="Test Skill",
        description="Desc",
        markdown_body="# Test\n",
        version="1.0.0",
        roles=["coder"],
        keywords=["test"],
        source="verified_skill_forge",
        verified_at=None,
    )

    monkeypatch.setattr(
        "app.application.services.skill_factory_github_export.settings",
        SimpleNamespace(
            skill_factory_github_pr_enabled=True,
            skill_factory_github_owner="acme",
            skill_factory_github_repo="skill-packs",
            skill_factory_github_connector_slug="github_rest",
            skill_factory_github_base_branch="main",
        ),
    )

    session = AsyncMock()
    session.get = AsyncMock(return_value=skill)
    session.scalar = AsyncMock(return_value=None)

    ref_response = '{"object":{"sha":"abc123"}}'
    pr_response = '{"html_url":"https://github.com/acme/skill-packs/pull/1"}'

    async def fake_invoke(_session, *, connector_slug, tool_name, arguments):  # noqa: ANN001
        if tool_name == "git_ref_get":
            return True, ref_response
        if tool_name == "git_ref_create":
            return True, "{}"
        if tool_name == "repos_contents_put":
            return True, "{}"
        if tool_name == "pulls_create":
            return True, pr_response
        return False, "unknown"

    with (
        patch(
            "app.application.services.skill_factory_github_export.github_pr_export_ready",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.application.services.skill_factory_github_export._github_invoke",
            side_effect=fake_invoke,
        ),
        patch(
            "app.application.services.skill_factory_github_export.mark_skill_github_exported",
            new_callable=AsyncMock,
        ) as mock_mark,
    ):
        out = await push_skill_export_github_pr(session, tenant_id=tenant_id, skill_id=skill_id)

    assert out["ok"] is True
    assert out["branch"].startswith("skill-factory/")
    assert out["files_committed"] >= 1
    assert out["pr"]["status"] == "created"
    mock_mark.assert_awaited_once()
