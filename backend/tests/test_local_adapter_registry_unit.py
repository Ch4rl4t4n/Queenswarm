"""Unit tests for Track M LOC8 local adapter registry."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.local_adapter_registry_service import (
    LocalAdapterRegisterIn,
    compose_local_adapter_registry_snapshot,
    list_tenant_local_adapter_slugs,
    register_local_adapter,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant_local_adapter import TenantLocalAdapterORM


@pytest.mark.asyncio
async def test_list_tenant_local_adapter_slugs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_adapter_registry_enabled", True)
    tenant_id = uuid.uuid4()
    row = TenantLocalAdapterORM(
        tenant_id=tenant_id,
        name="Tenant v1",
        ollama_tag="queenswarm-v1",
        litellm_slug="ollama/queenswarm-v1",
        kind="gguf",
        is_active=True,
        metadata_json={},
    )
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = [row]
    session.scalars = AsyncMock(return_value=result)

    slugs = await list_tenant_local_adapter_slugs(session, tenant_id=tenant_id)
    assert slugs == ["ollama/queenswarm-v1"]


@pytest.mark.asyncio
async def test_register_local_adapter_creates_row(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_adapter_registry_enabled", True)
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    async def _refresh(row: TenantLocalAdapterORM) -> None:
        row.id = uuid.uuid4()

    session.refresh.side_effect = _refresh

    out = await register_local_adapter(
        session,
        tenant_id=tenant_id,
        payload=LocalAdapterRegisterIn(
            name="Queenswarm v1",
            ollama_tag="queenswarm-v1",
            kind="gguf",
            activate=True,
        ),
    )
    assert out.litellm_slug == "ollama/queenswarm-v1"
    assert out.is_active is True
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_compose_local_adapter_registry_snapshot_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "local_adapter_registry_enabled", True)
    tenant_id = uuid.uuid4()
    row = TenantLocalAdapterORM(
        tenant_id=tenant_id,
        name="Queenswarm v1",
        ollama_tag="queenswarm-v1",
        litellm_slug="ollama/queenswarm-v1",
        kind="gguf",
        is_active=True,
        metadata_json={},
    )
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = [row]
    session.scalars = AsyncMock(return_value=result)

    snap = await compose_local_adapter_registry_snapshot(session, tenant_id=tenant_id)
    assert snap.enabled is True
    assert snap.active_slug == "ollama/queenswarm-v1"
    assert len(snap.adapters) == 1


@pytest.mark.asyncio
async def test_activate_local_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    adapter_id = uuid.uuid4()
    row = TenantLocalAdapterORM(
        id=adapter_id,
        tenant_id=tenant_id,
        name="v1",
        ollama_tag="v1",
        litellm_slug="ollama/v1",
        kind="gguf",
        is_active=False,
        metadata_json={},
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    from app.application.services.local_adapter_registry_service import activate_local_adapter

    out = await activate_local_adapter(session, tenant_id=tenant_id, adapter_id=adapter_id)
    assert out.is_active is True


@pytest.mark.asyncio
async def test_delete_local_adapter() -> None:
    tenant_id = uuid.uuid4()
    adapter_id = uuid.uuid4()
    row = TenantLocalAdapterORM(
        id=adapter_id,
        tenant_id=tenant_id,
        name="v1",
        ollama_tag="v1",
        litellm_slug="ollama/v1",
        kind="gguf",
        is_active=False,
        metadata_json={},
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    from app.application.services.local_adapter_registry_service import delete_local_adapter

    await delete_local_adapter(session, tenant_id=tenant_id, adapter_id=adapter_id)
    session.delete.assert_called_once_with(row)


@pytest.mark.asyncio
async def test_register_local_adapter_updates_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_adapter_registry_enabled", True)
    tenant_id = uuid.uuid4()
    existing = TenantLocalAdapterORM(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Old",
        ollama_tag="queenswarm-v1",
        litellm_slug="ollama/queenswarm-v1",
        kind="gguf",
        is_active=False,
        metadata_json={},
    )
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=existing)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    out = await register_local_adapter(
        session,
        tenant_id=tenant_id,
        payload=LocalAdapterRegisterIn(name="Updated", ollama_tag="queenswarm-v1", kind="lora"),
    )
    assert out.name == "Updated"
    assert out.kind == "lora"
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_register_local_adapter_links_recipe_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_adapter_registry_enabled", True)
    monkeypatch.setattr(settings, "local_sovereign_recipe_tags_enabled", True)
    tenant_id = uuid.uuid4()
    recipe_id = uuid.uuid4()
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = AsyncMock()
    session.execute = AsyncMock()

    with patch(
        "app.application.services.local_sovereign_recipe_tags_service.apply_local_adapter_tags_to_recipes",
        new=AsyncMock(return_value=1),
    ) as tag_mock:
        await register_local_adapter(
            session,
            tenant_id=tenant_id,
            payload=LocalAdapterRegisterIn(
                name="Adapter",
                ollama_tag="queenswarm-v2",
                link_recipe_ids=[str(recipe_id)],
            ),
        )
    tag_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_compose_local_adapter_registry_snapshot_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", False)
    snap = await compose_local_adapter_registry_snapshot(AsyncMock(), tenant_id=uuid.uuid4())
    assert snap.enabled is False
