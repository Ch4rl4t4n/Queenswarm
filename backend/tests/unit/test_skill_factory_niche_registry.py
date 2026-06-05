"""Tests for factory niche originality guard."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.skill_factory_niche_registry import (
    FactoryNicheFingerprints,
    niche_key,
    niche_to_slug_base,
    research_skip_reason,
    resolve_canonical_skill_slug,
)
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM


def test_niche_key_strips_skill_pack_prefix() -> None:
    assert niche_key("Skill pack: SEO blog pipeline") == "seo blog pipeline"


def test_research_skip_when_sellable_slug_base_exists() -> None:
    base = niche_to_slug_base("SEO content pipeline with simulate-first guardrails")
    fp = FactoryNicheFingerprints(slug_bases_sellable={base})
    reason = research_skip_reason(
        niche="SEO content pipeline with simulate-first guardrails",
        fingerprints=fp,
        settings={},
    )
    assert reason == "sellable_skill_exists"


def test_research_skip_when_niche_abandoned_purged() -> None:
    key = niche_key("newsletter growth automation")
    fp = FactoryNicheFingerprints(abandoned_niches={key: "purged"})
    reason = research_skip_reason(
        niche="newsletter growth automation",
        fingerprints=fp,
        settings={},
    )
    assert reason == "niche_abandoned_purged"


@pytest.mark.asyncio
async def test_resolve_canonical_skill_slug_reuses_base() -> None:
    tenant_id = uuid.uuid4()
    older = TenantSkillORM(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        slug="seo-content-pipeline-with-simulate-first-guardrails-6",
        title="SEO pipeline",
        description="x",
        markdown_body="---\nname: x\n---\n",
        is_active=True,
    )
    session = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = [older]
    session.scalars = AsyncMock(return_value=scalars_result)
    session.scalar = AsyncMock(return_value=None)

    slug = await resolve_canonical_skill_slug(
        session,
        tenant_id=tenant_id,
        base_title="SEO Content Pipeline with Simulate-First Guardrails",
    )
    assert slug == "seo-content-pipeline-with-simulate-first-guardrails-6"
