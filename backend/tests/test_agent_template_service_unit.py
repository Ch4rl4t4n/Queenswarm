"""Unit tests for tenant-scoped agent template service."""

from __future__ import annotations

from types import SimpleNamespace
import uuid

import pytest

from app.application.services.agent_template_service import AgentTemplateService


class _FakeScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def __iter__(self):  # noqa: ANN204
        return iter(self._rows)


class _FakeDeleteResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _FakeDb:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self.rows = rows
        self.added: list[object] = []
        self.deleted_rowcount = 0

    def add(self, row: object) -> None:
        self.added.append(row)
        self.rows.append(row)  # mimic tracked session identity map

    async def flush(self) -> None:
        return None

    async def scalars(self, _stmt):  # noqa: ANN001
        return _FakeScalarResult(self.rows)

    async def scalar(self, _stmt):  # noqa: ANN001
        return self.rows[0] if self.rows else None

    async def execute(self, _stmt):  # noqa: ANN001
        return _FakeDeleteResult(self.deleted_rowcount)


def _template(*, tenant_id: uuid.UUID, name: str, is_default: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name,
        description="desc",
        icon="🐝",
        category="general",
        tools=["web_search"],
        prompt_template="You are a bee",
        is_default=is_default,
    )


@pytest.mark.asyncio
async def test_list_by_tenant_returns_rows() -> None:
    """List should return available rows for tenant scope."""

    tenant_id = uuid.uuid4()
    db = _FakeDb([_template(tenant_id=tenant_id, name="A"), _template(tenant_id=tenant_id, name="B")])
    service = AgentTemplateService(db=db)  # type: ignore[arg-type]
    out = await service.list_by_tenant(tenant_id)
    assert len(out) == 2


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(monkeypatch) -> None:
    """Get should return None for unknown id."""

    tenant_id = uuid.uuid4()
    db = _FakeDb([])
    service = AgentTemplateService(db=db)  # type: ignore[arg-type]

    async def _missing(_tenant_id, _template_id):  # noqa: ANN001
        return None

    monkeypatch.setattr(service, "get_by_id", _missing)
    out = await service.get_by_id(tenant_id, uuid.uuid4())
    assert out is None


@pytest.mark.asyncio
async def test_create_marks_single_default() -> None:
    """Creating default template should clear previous tenant default rows."""

    tenant_id = uuid.uuid4()
    existing_default = _template(tenant_id=tenant_id, name="Old", is_default=True)
    db = _FakeDb([existing_default])
    service = AgentTemplateService(db=db)  # type: ignore[arg-type]

    created = await service.create(
        tenant_id=tenant_id,
        name="New",
        description="New template",
        icon="📊",
        category="research",
        tools=["web_search", "rss"],
        prompt_template="You are new",
        is_default=True,
    )

    assert created.is_default is True
    assert existing_default.is_default is False


@pytest.mark.asyncio
async def test_update_changes_fields_and_default(monkeypatch) -> None:
    """Update should mutate target row and keep single default."""

    tenant_id = uuid.uuid4()
    old_default = _template(tenant_id=tenant_id, name="Old", is_default=True)
    target = _template(tenant_id=tenant_id, name="Target", is_default=False)
    db = _FakeDb([old_default, target])
    service = AgentTemplateService(db=db)  # type: ignore[arg-type]

    async def _get(_tenant_id, _template_id):  # noqa: ANN001
        return target

    monkeypatch.setattr(service, "get_by_id", _get)
    updated = await service.update(
        tenant_id=tenant_id,
        template_id=target.id,
        name="Updated",
        description="Updated desc",
        icon="🧠",
        category="analysis",
        tools=["wikipedia"],
        prompt_template="Updated prompt",
        is_default=True,
    )

    assert updated is not None
    assert updated.name == "Updated"
    assert updated.icon == "🧠"
    assert updated.is_default is True
    assert old_default.is_default is False


@pytest.mark.asyncio
async def test_delete_returns_false_when_no_rows_deleted() -> None:
    """Delete should return false when rowcount is zero."""

    tenant_id = uuid.uuid4()
    db = _FakeDb([])
    db.deleted_rowcount = 0
    service = AgentTemplateService(db=db)  # type: ignore[arg-type]
    out = await service.delete(tenant_id, uuid.uuid4())
    assert out is False
