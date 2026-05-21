"""Unit tests for supervisor session audit trail."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.application.services.supervisor.session_audit import (
    list_supervisor_session_audit_logs,
    list_supervisor_session_context_history,
    serialize_supervisor_session_audit_csv,
    serialize_supervisor_session_audit_json,
    serialize_supervisor_session_merged_csv,
    serialize_supervisor_session_merged_json,
)


@pytest.mark.asyncio
async def test_list_supervisor_session_audit_logs_when_rows_exist_then_returns_dicts() -> None:
    """List helper maps tenant audit ORM rows into API-friendly dicts."""

    tenant_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    row = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        action="supervisor_session_control",
        target_type="supervisor_session",
        target_ref=str(session_id),
        actor_user_id=uuid.uuid4(),
        payload={"control_action": "resume"},
        created_at=now,
    )

    class _FakeDb:
        async def scalars(self, _stmt):  # noqa: ANN001
            class _Result:
                def all(self_inner):  # noqa: ANN001
                    return [row]

            return _Result()

    rows = await list_supervisor_session_audit_logs(
        _FakeDb(),  # type: ignore[arg-type]
        tenant_id=tenant_id,
        session_id=session_id,
        limit=10,
    )
    assert len(rows) == 1
    assert rows[0]["action"] == "supervisor_session_control"
    assert rows[0]["payload"]["control_action"] == "resume"


def test_serialize_supervisor_session_audit_csv_and_json() -> None:
    """Export serializers render operator audit rows."""

    rows = [
        {
            "id": "log-1",
            "tenant_id": "tenant-1",
            "action": "supervisor_session_review",
            "target_type": "supervisor_session",
            "target_ref": "sess-1",
            "actor_user_id": "user-1",
            "created_at": datetime(2026, 5, 19, 12, 0, tzinfo=UTC),
            "payload": {"decision": "approve"},
        },
    ]
    csv_out = serialize_supervisor_session_audit_csv(rows)
    assert "supervisor_session_review" in csv_out
    json_out = serialize_supervisor_session_audit_json(rows)
    assert '"decision": "approve"' in json_out


def test_serialize_supervisor_session_merged_json_and_csv() -> None:
    """Merged export bundles audit rows with session timeline events."""

    session_id = uuid.uuid4()
    audit_rows = [
        {
            "id": "log-1",
            "tenant_id": "tenant-1",
            "action": "supervisor_session_create",
            "target_type": "supervisor_session",
            "target_ref": str(session_id),
            "actor_user_id": "user-1",
            "created_at": datetime(2026, 5, 19, 12, 0, tzinfo=UTC),
            "payload": {"runtime_mode": "durable"},
        },
    ]
    event_rows = [
        {
            "id": "evt-1",
            "supervisor_session_id": str(session_id),
            "sub_agent_session_id": None,
            "event_type": "session_started",
            "level": "info",
            "message": "Session started",
            "occurred_at": datetime(2026, 5, 19, 12, 1, tzinfo=UTC),
            "created_at": datetime(2026, 5, 19, 12, 1, tzinfo=UTC),
            "payload": {},
        },
    ]
    json_out = serialize_supervisor_session_merged_json(
        session_id=session_id,
        audit_rows=audit_rows,
        event_rows=event_rows,
    )
    assert "supervisor_session_create" in json_out
    assert "session_started" in json_out
    csv_out = serialize_supervisor_session_merged_csv(audit_rows, event_rows)
    assert "record_type" in csv_out
    assert "audit" in csv_out
    assert "event" in csv_out


@pytest.mark.asyncio
async def test_list_supervisor_session_context_history_when_diff_rows_exist_then_filters() -> None:
    """Context history helper returns only control/review rows with context_diff."""

    tenant_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(tz=UTC)

    class _FakeDb:
        async def scalars(self, _stmt):  # noqa: ANN001
            class _Result:
                def all(self_inner):  # noqa: ANN001
                    return [
                        SimpleNamespace(
                            id=uuid.uuid4(),
                            tenant_id=tenant_id,
                            action="supervisor_session_control",
                            target_type="supervisor_session",
                            target_ref=str(session_id),
                            actor_user_id=uuid.uuid4(),
                            payload={
                                "control_action": "resume",
                                "context_diff": {"changed": {"requeued_sub_agents": {"before": 0, "after": 2}}},
                            },
                            created_at=now,
                        ),
                        SimpleNamespace(
                            id=uuid.uuid4(),
                            tenant_id=tenant_id,
                            action="supervisor_session_interact",
                            target_type="supervisor_session",
                            target_ref=str(session_id),
                            actor_user_id=uuid.uuid4(),
                            payload={"command_preview": "focus on latency"},
                            created_at=now,
                        ),
                    ]

            return _Result()

    rows = await list_supervisor_session_context_history(
        _FakeDb(),  # type: ignore[arg-type]
        tenant_id=tenant_id,
        session_id=session_id,
        limit=10,
    )
    assert len(rows) == 1
    assert rows[0]["control_action"] == "resume"
    assert rows[0]["context_diff"]["changed"]["requeued_sub_agents"]["after"] == 2


@pytest.mark.asyncio
async def test_write_supervisor_session_audit_log_invalidates_rollup_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """New supervisor audit rows drop stale cross-tenant rollup snapshots."""

    from app.application.services.supervisor import session_audit as session_audit_module

    tenant_id = uuid.uuid4()
    session_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    row = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        action="supervisor_session_review",
        target_type="supervisor_session",
        target_ref=str(session_id),
        actor_user_id=actor_id,
        payload={"decision": "approve"},
        created_at=now,
    )
    calls = {"invalidate": 0}

    async def _fake_write_tenant_audit_log(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return row

    async def _fake_publish(*_args, **_kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    async def _fake_invalidate(**_kwargs) -> int:  # noqa: ANN003
        calls["invalidate"] += 1
        return 2

    monkeypatch.setattr(session_audit_module, "write_tenant_audit_log", _fake_write_tenant_audit_log)
    monkeypatch.setattr(session_audit_module, "publish_supervisor_session_audit_event", _fake_publish)
    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.invalidate_supervisor_audit_rollup_cache",
        _fake_invalidate,
    )

    entry = await session_audit_module.write_supervisor_session_audit_log(
        object(),  # type: ignore[arg-type]
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        session_id=session_id,
        action="supervisor_session_review",
        payload={"decision": "approve"},
    )

    assert entry["action"] == "supervisor_session_review"
    assert calls["invalidate"] == 1
