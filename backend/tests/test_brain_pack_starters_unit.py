"""Unit tests for Brain Pack starter templates and seed flow."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application.services.brain_pack_starters import BRAIN_PACK_STARTERS, starter_kinds
from app.application.services.curated_memory_service import CuratedMemoryService
from app.domain.memory.curated import CuratedFileKind
from app.infrastructure.persistence.models.curated_memory import CuratedFileKindORM


def test_starter_kinds_cover_all_brain_pack_slots() -> None:
    """Starter pack must include every curated kind used in brain pack export."""

    assert set(starter_kinds()) == set(BRAIN_PACK_STARTERS.keys())
    assert CuratedFileKind.SOUL in BRAIN_PACK_STARTERS
    assert CuratedFileKind.INSTRUCTIONS in BRAIN_PACK_STARTERS
    assert CuratedFileKind.BRAND in BRAIN_PACK_STARTERS


def test_starter_content_under_char_limit() -> None:
    """Each starter template must fit curated memory upsert limit."""

    from app.core.config import settings

    limit = settings.curated_memory_max_chars
    for kind, content in BRAIN_PACK_STARTERS.items():
        assert len(content) <= limit, f"{kind.value} exceeds {limit} chars"


@pytest.mark.asyncio
async def test_seed_starter_pack_fills_empty_only(monkeypatch) -> None:
    """Seed writes only empty kinds when overwrite is false."""

    tenant_id = uuid4()
    stored: dict[CuratedFileKind, str] = {CuratedFileKind.MISSION: "existing mission"}

    async def _fake_bundle(_tenant_id):  # noqa: ANN001
        return {
            CuratedFileKind.MISSION: stored.get(CuratedFileKind.MISSION, ""),
            CuratedFileKind.IDEAL_STATE: "",
            CuratedFileKind.SOUL: "",
            CuratedFileKind.SKILLS_HIERARCHY: "",
            CuratedFileKind.INSTRUCTIONS: "",
            CuratedFileKind.BRAND: "",
        }

    upsert_calls: list[CuratedFileKind] = []

    async def _fake_upsert(*, tenant_id, kind, content_md, user_id):  # noqa: ANN001
        upsert_calls.append(kind)
        stored[kind] = content_md
        return SimpleNamespace(
            tenant_id=tenant_id,
            kind=kind,
            content_md=content_md,
            version=1,
            updated_at=datetime.now(tz=UTC),
            updated_by_user_id=user_id,
            char_count=len(content_md),
        )

    service = CuratedMemoryService(db=SimpleNamespace())
    monkeypatch.setattr(service, "get_bundle", _fake_bundle)
    monkeypatch.setattr(service, "upsert", _fake_upsert)

    seeded, skipped = await service.seed_starter_pack(tenant_id, user_id=uuid4(), overwrite=False)

    assert CuratedFileKind.MISSION.value in skipped
    assert CuratedFileKind.MISSION not in upsert_calls
    assert len(seeded) == len(BRAIN_PACK_STARTERS) - 1
    assert stored[CuratedFileKind.SOUL] == BRAIN_PACK_STARTERS[CuratedFileKind.SOUL]


@pytest.mark.asyncio
async def test_seed_starter_pack_overwrite_all(monkeypatch) -> None:
    """Overwrite=true replaces existing curated content."""

    tenant_id = uuid4()

    async def _fake_bundle(_tenant_id):  # noqa: ANN001
        return {
            CuratedFileKind.MISSION: "old",
            CuratedFileKind.IDEAL_STATE: "old",
            CuratedFileKind.SOUL: "old",
            CuratedFileKind.SKILLS_HIERARCHY: "old",
            CuratedFileKind.INSTRUCTIONS: "old",
        }

    upsert_calls: list[CuratedFileKind] = []

    async def _fake_upsert(*, tenant_id, kind, content_md, user_id):  # noqa: ANN001
        upsert_calls.append(kind)
        return SimpleNamespace(
            tenant_id=tenant_id,
            kind=kind,
            content_md=content_md,
            version=2,
            updated_at=datetime.now(tz=UTC),
            updated_by_user_id=user_id,
            char_count=len(content_md),
        )

    service = CuratedMemoryService(db=SimpleNamespace())
    monkeypatch.setattr(service, "get_bundle", _fake_bundle)
    monkeypatch.setattr(service, "upsert", _fake_upsert)

    seeded, skipped = await service.seed_starter_pack(tenant_id, user_id=uuid4(), overwrite=True)

    assert len(seeded) == len(BRAIN_PACK_STARTERS)
    assert skipped == []
    assert len(upsert_calls) == len(BRAIN_PACK_STARTERS)
