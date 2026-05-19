"""Unit tests for tenant-scoped ForagerService."""

from __future__ import annotations

from types import SimpleNamespace
import uuid

import pytest

from app.application.services.forager_service import ForagerService
from app.infrastructure.persistence.models.agent_config import AgentConfig
from app.infrastructure.persistence.models.knowledge import KnowledgeItem


class _FakeScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def __iter__(self):  # noqa: ANN204
        return iter(self._rows)


class _FakeDb:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.scalar_value: object | None = None

    def add(self, row: object) -> None:
        self.added.append(row)

    async def flush(self) -> None:
        return None

    async def scalars(self, _stmt):  # noqa: ANN001
        return _FakeScalarResult([])

    async def scalar(self, _stmt):  # noqa: ANN001
        return self.scalar_value

    async def get(self, _model, _pk):  # noqa: ANN001
        return None

    async def execute(self, _stmt):  # noqa: ANN001
        return SimpleNamespace(rowcount=0)


@pytest.mark.asyncio
async def test_create_calls_routine_link(monkeypatch: pytest.MonkeyPatch) -> None:
    """Create should normalize fields and call routine-link helper."""

    db = _FakeDb()
    service = ForagerService(db=db)  # type: ignore[arg-type]
    tenant_id = uuid.uuid4()
    captured: dict[str, object] = {}

    async def _capture(**kwargs):  # noqa: ANN003
        captured.update(kwargs)

    monkeypatch.setattr(service, "_upsert_routine_link", _capture)

    row = await service.create(
        tenant_id=tenant_id,
        name="  News Scout  ",
        description="  scans daily feeds ",
        source_type="RSS",
        source_config={"urls": ["https://example.com/feed"]},
        filter_config={"default_tags": ["news"]},
        prompt_template="  summarize updates ",
        tools=[" rss ", "web_search", " "],
        is_active=True,
        agent_template_id=None,
        schedule={"enabled": True},
        created_by_subject="dashboard:test",
    )

    assert row.name == "News Scout"
    assert row.source_type == "rss"
    assert row.tools == ["rss", "web_search"]
    assert captured["tenant_id"] == tenant_id
    assert isinstance(captured["forager"], type(row))


@pytest.mark.asyncio
async def test_ingest_records_persists_knowledge_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ingest should create KnowledgeItem rows for valid content entries."""

    db = _FakeDb()
    service = ForagerService(db=db)  # type: ignore[arg-type]
    tenant_id = uuid.uuid4()
    forager = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        source_type="rss",
        filter_config={"default_tags": ["macro", "alpha"]},
    )

    async def _get(_tenant_id, _forager_id):  # noqa: ANN001
        return forager

    monkeypatch.setattr(service, "get_by_id", _get)
    inserted = await service.ingest_records(
        tenant_id=tenant_id,
        forager_id=forager.id,
        records=[
            {"source_url": "https://example.com/a", "content_text": "Signal A", "topic_tags": ["btc"]},
            {"source_url": "https://example.com/b", "content_text": " "},
        ],
    )

    assert inserted == 1
    knowledge_rows = [row for row in db.added if isinstance(row, KnowledgeItem)]
    assert len(knowledge_rows) == 1
    assert knowledge_rows[0].source_type == "forager:rss"
    assert "macro" in list(knowledge_rows[0].topic_tags)
    assert "btc" in list(knowledge_rows[0].topic_tags)


@pytest.mark.asyncio
async def test_spawn_agent_from_forager_uses_template_and_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """Spawn should merge template tools and include forager metadata in config."""

    db = _FakeDb()
    service = ForagerService(db=db)  # type: ignore[arg-type]
    tenant_id = uuid.uuid4()
    template_id = uuid.uuid4()
    forager = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Market Hunter",
        source_type="free_api",
        source_config={"endpoint": "https://api.example.com"},
        tools=["rss", "web_search"],
        prompt_template="",
        agent_template_id=template_id,
    )
    db.scalar_value = SimpleNamespace(
        id=template_id,
        tenant_id=tenant_id,
        category="research",
        prompt_template="You are a market researcher.",
        tools=["coingecko"],
    )

    async def _get(_tenant_id, _forager_id):  # noqa: ANN001
        return forager

    async def _fake_create_agent_record(  # noqa: ANN001
        _session,
        *,
        name,
        role,
        status,
        swarm_id,
        config,
    ):
        del name, role, status, swarm_id, config
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(service, "get_by_id", _get)
    monkeypatch.setattr("app.application.services.forager_service.create_agent_record", _fake_create_agent_record)

    out = await service.spawn_agent_from_forager(tenant_id=tenant_id, forager_id=forager.id)
    assert out is not None
    _agent, cfg = out
    assert isinstance(cfg, AgentConfig)
    assert "coingecko" in list(cfg.tools)
    assert "rss" in list(cfg.tools)
    assert cfg.output_config.get("forager_source_type") == "free_api"


@pytest.mark.asyncio
async def test_toggle_enabled_updates_forager_and_routine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Toggle should update both forager and linked routine active flags."""

    db = _FakeDb()
    service = ForagerService(db=db)  # type: ignore[arg-type]
    tenant_id = uuid.uuid4()
    forager = SimpleNamespace(id=uuid.uuid4(), supervisor_routine_id=uuid.uuid4(), is_active=True)
    routine = SimpleNamespace(is_active=True, status="scheduled")

    async def _get(_tenant_id, _forager_id):  # noqa: ANN001
        return forager

    async def _db_get(_model, _pk):  # noqa: ANN001
        return routine

    monkeypatch.setattr(service, "get_by_id", _get)
    monkeypatch.setattr(db, "get", _db_get)

    out = await service.toggle_enabled(tenant_id=tenant_id, forager_id=forager.id, enabled=False)
    assert out is not None
    assert out.is_active is False
    assert routine.is_active is False
    assert routine.status == "disabled"


@pytest.mark.asyncio
async def test_trigger_manual_run_ingests_and_triggers_routine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Manual trigger should ingest records and call routine trigger."""

    db = _FakeDb()
    service = ForagerService(db=db)  # type: ignore[arg-type]
    tenant_id = uuid.uuid4()
    routine_id = uuid.uuid4()
    forager = SimpleNamespace(
        id=uuid.uuid4(),
        is_active=True,
        supervisor_routine_id=routine_id,
        source_config={},
        filter_config={},
    )
    routine = SimpleNamespace(id=routine_id, is_active=True)
    captured: dict[str, object] = {"count": 0}

    async def _get(_tenant_id, _forager_id):  # noqa: ANN001
        return forager

    async def _db_get(_model, _pk):  # noqa: ANN001
        return routine

    async def _fake_ingest(*, tenant_id, forager_id, records):  # noqa: ANN001
        assert tenant_id is not None
        assert forager_id is not None
        assert len(records) == 1
        captured["count"] = 1
        return 1

    async def _fake_trigger(_db, *, routine):  # noqa: ANN001
        assert routine.id == routine_id
        return uuid.uuid4()

    monkeypatch.setattr(service, "get_by_id", _get)
    monkeypatch.setattr(db, "get", _db_get)
    monkeypatch.setattr(service, "ingest_records", _fake_ingest)
    monkeypatch.setattr("app.application.services.forager_service.trigger_supervisor_routine_now", _fake_trigger)

    out = await service.trigger_manual_run(
        tenant_id=tenant_id,
        forager_id=forager.id,
        records=[{"content_text": "alpha signal"}],
    )

    assert out is not None
    assert out["status"] == "triggered"
    assert out["ingested"] == 1
    assert out["routine_triggered"] is True
    assert captured["count"] == 1

