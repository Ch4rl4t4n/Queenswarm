"""Verify tenant skill overlays load for durable worker and routines."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.supervisor.skills import SkillLibrary
from app.application.services.tenant_skill_loader import build_skill_library_for_tenant


@pytest.mark.asyncio
async def test_build_skill_library_for_tenant_merges_overlays() -> None:
    session = AsyncMock()
    row = SimpleNamespace(
        slug="verified-skill-forge",
        title="Verified Skill",
        markdown_body="# Verified Skill\n\nBody",
        description="desc",
        version="1.0.0",
        priority=80,
        roles=["researcher"],
        keywords=["forge"],
        is_active=True,
    )
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[row])))
    lib = await build_skill_library_for_tenant(session, tenant_id=uuid.uuid4())
    loaded = lib.load("verified-skill-forge")
    assert loaded is not None
    assert "Verified Skill" in loaded.title


def test_skill_library_tenant_overlay_takes_precedence() -> None:
    from app.application.services.supervisor.skills import SkillSnippet

    overlay = SkillSnippet(slug="context", title="Tenant Context", body="# Tenant\n", version="2.0.0", priority=99)
    lib = SkillLibrary(tenant_overlays={"context": overlay})
    item = lib.load("context")
    assert item is not None
    assert item.title == "Tenant Context"
