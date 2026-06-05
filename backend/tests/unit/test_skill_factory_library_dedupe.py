"""Tests for library dedupe — one row per niche."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.skill_factory_library_dedupe import (
    archive_older_niche_skill_versions,
    dedupe_library_skills_latest,
)
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM


def _skill(
    slug: str,
    *,
    updated_at: datetime | None = None,
    skill_id: uuid.UUID | None = None,
) -> TenantSkillORM:
    return TenantSkillORM(
        id=skill_id or uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        slug=slug,
        title=slug,
        description="test",
        markdown_body="---\nname: test\n---\n",
        is_active=True,
        updated_at=updated_at or datetime.now(tz=UTC),
    )


def test_dedupe_library_skills_latest_keeps_newest_suffix() -> None:
    older = _skill(
        "n8n-automation-templates-for-agencies-4",
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    newer = _skill(
        "n8n-automation-templates-for-agencies-5",
        updated_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    other = _skill("seo-content-pipeline-with-simulate-first-guardrails-4")

    deduped, hidden = dedupe_library_skills_latest([older, newer, other])

    assert hidden == 1
    assert len(deduped) == 2
    assert {row.slug for row in deduped} == {
        "n8n-automation-templates-for-agencies-5",
        "seo-content-pipeline-with-simulate-first-guardrails-4",
    }


def test_dedupe_library_skills_latest_no_duplicates() -> None:
    rows = [_skill("alpha-1"), _skill("beta-2")]
    deduped, hidden = dedupe_library_skills_latest(rows)
    assert hidden == 0
    assert len(deduped) == 2


@pytest.mark.asyncio
async def test_archive_older_niche_skill_versions_deactivates_older() -> None:
    tenant_id = uuid.uuid4()
    keep_id = uuid.uuid4()
    older = TenantSkillORM(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        slug="n8n-automation-templates-for-agencies-4",
        title="n8n 4",
        description="test",
        markdown_body="---\nname: n8n\n---\n",
        is_active=True,
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    keep = TenantSkillORM(
        id=keep_id,
        tenant_id=tenant_id,
        slug="n8n-automation-templates-for-agencies-5",
        title="n8n 5",
        description="test",
        markdown_body="---\nname: n8n\n---\n",
        is_active=True,
        updated_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    other = TenantSkillORM(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        slug="seo-content-pipeline-3",
        title="seo",
        description="test",
        markdown_body="---\nname: seo\n---\n",
        is_active=True,
    )
    session = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = [older, other]
    session.scalars = AsyncMock(return_value=scalars_result)
    session.flush = AsyncMock()

    archived = await archive_older_niche_skill_versions(
        session,
        tenant_id=tenant_id,
        keep_skill_id=keep_id,
        slug="n8n-automation-templates-for-agencies-5",
    )

    assert archived == 1
    assert older.is_active is False
    assert keep.is_active is True
    assert other.is_active is True
