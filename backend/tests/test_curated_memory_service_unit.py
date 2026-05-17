"""Unit tests for tenant curated memory service."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application.services.curated_memory_service import CuratedMemoryService
from app.domain.memory.curated import CuratedFileKind
from app.infrastructure.persistence.models.curated_memory import CuratedFileKindORM


@pytest.mark.asyncio
async def test_upsert_rejects_oversize_content() -> None:
    """Reject payloads over 8000 characters."""

    service = CuratedMemoryService(db=SimpleNamespace())
    with pytest.raises(ValueError, match="8000"):
        await service.upsert(
            tenant_id=uuid4(),
            kind=CuratedFileKind.MISSION,
            content_md="x" * 8001,
            user_id=uuid4(),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        "token " + "s" + "k-" + "test1234567890abcdefghijklmnopq",
        "Authorization: " + "BE" + "ARER " + "AbCdEfGhIjKlMnOpQrStUvWxYz123456",
        "API" + "_KEY=" + "abcdefghijklmnopqrstuvwxyz123456",
    ],
    ids=["sk_token", "bearer_token", "third_pattern"],
)
async def test_upsert_rejects_secret_patterns(payload: str) -> None:
    """Reject obvious secret-shaped strings."""

    service = CuratedMemoryService(db=SimpleNamespace())
    with pytest.raises(ValueError, match="secret"):
        await service.upsert(
            tenant_id=uuid4(),
            kind=CuratedFileKind.SOUL,
            content_md=payload,
            user_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_get_bundle_returns_all_four_keys_with_missing_files(monkeypatch) -> None:
    """Bundle always contains all curated keys."""

    service = CuratedMemoryService(db=SimpleNamespace())

    async def _fake_list(_tenant_id):  # noqa: ANN001
        return [
            SimpleNamespace(
                tenant_id=uuid4(),
                kind=CuratedFileKind.MISSION.value,
                content_md="Mission text",
                version=1,
                updated_at=datetime.now(tz=UTC),
                updated_by_user_id=None,
                char_count=12,
            ),
        ]

    monkeypatch.setattr(service, "_list_rows_for_tenant", _fake_list)
    bundle = await service.get_bundle(uuid4())

    assert set(bundle.keys()) == {
        CuratedFileKind.MISSION,
        CuratedFileKind.IDEAL_STATE,
        CuratedFileKind.SOUL,
        CuratedFileKind.SKILLS_HIERARCHY,
    }
    assert bundle[CuratedFileKind.MISSION] == "Mission text"
    assert bundle[CuratedFileKind.SOUL] == ""


def test_render_prompt_prefix_stable_output() -> None:
    """Prompt prefix format must remain deterministic."""

    service = CuratedMemoryService(db=SimpleNamespace())
    bundle = {
        CuratedFileKind.MISSION: "M1",
        CuratedFileKind.IDEAL_STATE: "",
        CuratedFileKind.SOUL: "S1",
        CuratedFileKind.SKILLS_HIERARCHY: "",
    }

    rendered = service.render_prompt_prefix(bundle)
    assert "=== MISSION ===" in rendered
    assert "=== IDEAL STATE ===" in rendered
    assert "=== SOUL ===" in rendered
    assert "=== SKILLS HIERARCHY ===" in rendered
    assert rendered.endswith("=== END CONTEXT ===")


@pytest.mark.asyncio
async def test_upsert_bumps_version(monkeypatch) -> None:
    """Upsert increments existing version for same tenant/kind."""

    existing = SimpleNamespace(
        tenant_id=uuid4(),
        kind=CuratedFileKindORM.MISSION,
        content_md="old",
        version=2,
        updated_at=datetime.now(tz=UTC),
        updated_by_user_id=None,
        char_count=3,
    )

    async def _flush() -> None:
        return None

    service = CuratedMemoryService(db=SimpleNamespace(add=lambda _row: None, flush=_flush))

    async def _fake_get_row(_tenant_id, _kind):  # noqa: ANN001
        return existing

    monkeypatch.setattr(service, "_get_row", _fake_get_row)

    out = await service.upsert(
        tenant_id=existing.tenant_id,
        kind=CuratedFileKind.MISSION,
        content_md="new payload",
        user_id=uuid4(),
    )

    assert out.version == 3
