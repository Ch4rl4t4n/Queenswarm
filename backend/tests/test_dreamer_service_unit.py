"""Unit tests for DreamerService nightly consolidation behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from app.application.services.dreamer_service import DreamerService
from app.domain.dreaming.models import DreamCycleStatus
from app.infrastructure.persistence.models.dream_cycle import DreamCycleORM


@dataclass
class _Row:
    source_ref: str
    txt: str


class _FakeResult:
    def __init__(self, rows: list[_Row]) -> None:
        self._rows = rows

    def __iter__(self):  # noqa: ANN204
        return iter(self._rows)


class _FakeSession:
    def __init__(self, *, task_rows: list[_Row], output_rows: list[_Row], relay_rows: list[_Row]) -> None:
        self._task_rows = task_rows
        self._output_rows = output_rows
        self._relay_rows = relay_rows
        self._added: list[Any] = []
        self.last_cycle: DreamCycleORM | None = None
        self.commits = 0

    def add(self, row: Any) -> None:
        self._added.append(row)
        if isinstance(row, DreamCycleORM):
            self.last_cycle = row

    async def flush(self) -> None:
        for row in self._added:
            if isinstance(row, DreamCycleORM) and row.id is None:
                row.id = uuid4()
            elif hasattr(row, "id") and getattr(row, "id", None) is None:
                setattr(row, "id", uuid4())

    async def execute(self, stmt, _params=None):  # noqa: ANN001
        raw = str(stmt)
        if "FROM tasks" in raw:
            return _FakeResult(self._task_rows)
        if "FROM external_outputs" in raw:
            return _FakeResult(self._output_rows)
        if "FROM learning_logs" in raw:
            return _FakeResult(self._relay_rows)
        return _FakeResult([])

    async def scalar(self, _stmt):  # noqa: ANN001
        return None

    async def commit(self) -> None:
        self.commits += 1


class _FakeSessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        del exc_type, exc, tb
        return None

    def __call__(self) -> "_FakeSessionFactory":
        return self


@pytest.mark.asyncio
async def test_dreamer_service_empty_window_completes_with_zero_insights(monkeypatch) -> None:
    """Service completes cleanly when no recent learning items exist."""

    session = _FakeSession(task_rows=[], output_rows=[], relay_rows=[])
    service = DreamerService(
        postgres_session_factory=_FakeSessionFactory(session),  # type: ignore[arg-type]
        chroma_client=SimpleNamespace(),
        neo4j_driver=SimpleNamespace(),
        litellm_router=SimpleNamespace(),
    )
    async def _publish_noop(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return None

    async def _decay_noop() -> int:
        return 0

    monkeypatch.setattr("app.application.services.dreamer_service.publish_event", _publish_noop)
    monkeypatch.setattr(service, "_apply_memory_decay", _decay_noop)

    cycle = await service.run_cycle(window_hours=24)

    assert cycle.status == DreamCycleStatus.COMPLETED
    assert cycle.items_processed == 0
    assert cycle.items_consolidated == 0


@pytest.mark.asyncio
async def test_dreamer_service_three_near_duplicates_creates_one_insight(monkeypatch) -> None:
    """Near-duplicate rows collapse into one consolidated insight cluster."""

    near_dupe = [
        _Row(source_ref="1", txt="crypto market momentum signal high confidence"),
        _Row(source_ref="2", txt="crypto market momentum signal remains strong"),
        _Row(source_ref="3", txt="crypto market momentum signal confirmed"),
    ]
    session = _FakeSession(task_rows=near_dupe, output_rows=[], relay_rows=[])
    service = DreamerService(
        postgres_session_factory=_FakeSessionFactory(session),  # type: ignore[arg-type]
        chroma_client=SimpleNamespace(),
        neo4j_driver=SimpleNamespace(),
        litellm_router=SimpleNamespace(),
    )
    async def _publish_noop(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return None

    async def _decay_noop() -> int:
        return 0

    async def _neo4j_noop(**_kwargs) -> str:
        return "neo4j-1"

    async def _chroma_noop(**_kwargs) -> str:
        return "chroma-1"

    async def _summary_noop(_cluster) -> str:  # noqa: ANN001
        return "Consolidated recurring signal: crypto momentum has repeated across sources."

    monkeypatch.setattr("app.application.services.dreamer_service.publish_event", _publish_noop)
    monkeypatch.setattr(service, "_apply_memory_decay", _decay_noop)
    monkeypatch.setattr(service, "_upsert_neo4j_insight", _neo4j_noop)
    monkeypatch.setattr(service, "_upsert_chroma_insight", _chroma_noop)
    monkeypatch.setattr(service, "_summarize_cluster", _summary_noop)

    cycle = await service.run_cycle(window_hours=24)

    assert cycle.status == DreamCycleStatus.COMPLETED
    assert cycle.items_processed == 3
    assert cycle.items_consolidated == 1


@pytest.mark.asyncio
async def test_dreamer_service_when_chroma_fails_marks_cycle_failed(monkeypatch) -> None:
    """Unexpected downstream errors mark cycle as failed and propagate."""

    rows = [_Row(source_ref="1", txt="crypto market momentum signal high confidence")] * 2
    session = _FakeSession(task_rows=rows, output_rows=[], relay_rows=[])
    service = DreamerService(
        postgres_session_factory=_FakeSessionFactory(session),  # type: ignore[arg-type]
        chroma_client=SimpleNamespace(),
        neo4j_driver=SimpleNamespace(),
        litellm_router=SimpleNamespace(),
    )
    async def _decay_noop() -> int:
        return 0

    async def _neo4j_noop(**_kwargs) -> str:
        return "neo4j-1"

    async def _summary_noop(_cluster) -> str:  # noqa: ANN001
        return "Summary"

    async def _publish_noop(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(service, "_apply_memory_decay", _decay_noop)
    monkeypatch.setattr(service, "_upsert_neo4j_insight", _neo4j_noop)
    monkeypatch.setattr(service, "_summarize_cluster", _summary_noop)

    async def _raise_chroma(**_kwargs):  # noqa: ANN003
        raise RuntimeError("chroma unavailable")

    monkeypatch.setattr(service, "_upsert_chroma_insight", _raise_chroma)
    monkeypatch.setattr("app.application.services.dreamer_service.publish_event", _publish_noop)

    with pytest.raises(RuntimeError, match="chroma unavailable"):
        await service.run_cycle(window_hours=24)

    assert session.last_cycle is not None
    assert session.last_cycle.status.value == "failed"
