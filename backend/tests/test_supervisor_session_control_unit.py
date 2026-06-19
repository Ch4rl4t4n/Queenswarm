"""Unit tests for supervisor session auto-approve control policy."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.supervisor_session_control import (
    auto_approve_pending_supervisor_sessions,
    explain_session_manual_approve,
    is_session_auto_approve_blocked,
    maybe_auto_approve_supervisor_session,
    merge_supervisor_sessions_patch,
    resolve_supervisor_sessions_auto_approve,
    serialize_supervisor_sessions_control_view,
)


def test_merge_supervisor_sessions_patch_persists_auto_approve() -> None:
    root = merge_supervisor_sessions_patch({}, {"auto_approve_enabled": True})
    assert root["supervisor_sessions"]["auto_approve_enabled"] is True
    assert root["supervisor_sessions"]["auto_approve_enabled_source"] == "tenant"


def test_resolve_supervisor_sessions_auto_approve_when_disabled_by_default() -> None:
    tenant = SimpleNamespace(operator_settings={})
    assert resolve_supervisor_sessions_auto_approve(tenant) is False


def test_resolve_supervisor_sessions_auto_approve_when_tenant_enabled() -> None:
    tenant = SimpleNamespace(operator_settings={"supervisor_sessions": {"auto_approve_enabled": True}})
    assert resolve_supervisor_sessions_auto_approve(tenant) is True


def test_serialize_supervisor_sessions_control_view_auto_mode() -> None:
    tenant = SimpleNamespace(operator_settings={"supervisor_sessions": {"auto_approve_enabled": True}})
    view = serialize_supervisor_sessions_control_view(tenant)
    assert view["auto_approve_enabled"] is True
    assert view["mode_label"] == "auto"


def test_serialize_supervisor_sessions_control_view_manual_mode() -> None:
    tenant = SimpleNamespace(operator_settings={})
    view = serialize_supervisor_sessions_control_view(tenant)
    assert view["auto_approve_enabled"] is False
    assert view["mode_label"] == "manual"


def test_is_session_auto_approve_blocked_when_social_intel_drop_verdict_then_false() -> None:
    raw = "Social intel forager: drop verdict=false on each claim."
    blocked = is_session_auto_approve_blocked(
        goal=raw,
        context_summary={"approval_required": True, "raw_goal": raw},
    )
    assert blocked is False


def test_is_session_auto_approve_blocked_when_critical_keyword() -> None:
    blocked = is_session_auto_approve_blocked(
        goal="Rotate production billing secrets",
        context_summary={"approval_required": True},
    )
    assert blocked is True


def test_explain_session_manual_approve_when_critical() -> None:
    hint = explain_session_manual_approve(
        status="needs_input",
        goal="Rotate production billing secrets",
        context_summary={"approval_required": True, "approval_reason": "Critical action keyword detected: billing"},
        auto_approve_enabled=True,
    )
    assert hint is not None
    assert "billing" in hint.lower()


def test_explain_session_manual_approve_when_eligible_then_none() -> None:
    hint = explain_session_manual_approve(
        status="needs_input",
        goal="Forager insights digest",
        context_summary={},
        auto_approve_enabled=True,
    )
    assert hint is None


def test_is_session_auto_approve_blocked_when_self_heal_only() -> None:
    blocked = is_session_auto_approve_blocked(
        goal="Summarize marketing digest",
        context_summary={"approval_required": False},
    )
    assert blocked is False


@pytest.mark.asyncio
async def test_maybe_auto_approve_when_policy_disabled_then_false() -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    row = MagicMock()
    row.status = "needs_input"
    row.tenant_id = tenant_id
    row.goal = "Digest"
    row.context_summary = {}
    row.id = uuid.uuid4()
    db.get = AsyncMock(return_value=SimpleNamespace(operator_settings={}))

    approved = await maybe_auto_approve_supervisor_session(db, session_row=row)
    assert approved is False


@pytest.mark.asyncio
async def test_maybe_auto_approve_when_hydrated_session_closed_then_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    row = MagicMock()
    row.status = "needs_input"
    row.tenant_id = tenant_id
    row.goal = "Digest"
    row.context_summary = {}
    row.id = uuid.uuid4()

    hydrated = MagicMock()
    hydrated.status = "stopped"

    db = AsyncMock()
    db.get = AsyncMock(return_value=SimpleNamespace(operator_settings={"supervisor_sessions": {"auto_approve_enabled": True}}))
    monkeypatch.setattr(
        "app.application.services.supervisor_session_control.get_supervisor_session",
        AsyncMock(return_value=hydrated),
    )
    apply_mock = AsyncMock()
    monkeypatch.setattr(
        "app.application.services.supervisor_session_control.apply_session_review",
        apply_mock,
    )

    approved = await maybe_auto_approve_supervisor_session(db, session_row=row)

    assert approved is False
    apply_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_approve_pending_when_policy_disabled_then_empty() -> None:
    db = AsyncMock()
    db.get = AsyncMock(return_value=SimpleNamespace(operator_settings={}))
    result = await auto_approve_pending_supervisor_sessions(db, tenant_id=uuid.uuid4())
    assert result["approved_count"] == 0
    assert result["session_ids"] == []


@pytest.mark.asyncio
async def test_auto_approve_pending_when_enabled_then_approves_non_critical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    session_id = uuid.uuid4()
    row = MagicMock()
    row.id = session_id
    row.goal = "Four Lane digest"
    row.context_summary = {}
    row.status = "needs_input"
    row.runtime_mode = "durable"

    async def _scalars(_stmt):  # noqa: ANN001
        result = MagicMock()
        result.all.return_value = [row]
        return result

    db.scalars = _scalars  # type: ignore[method-assign]
    db.get = AsyncMock(
        return_value=SimpleNamespace(
            operator_settings={"supervisor_sessions": {"auto_approve_enabled": True}},
        ),
    )
    apply_mock = AsyncMock()
    monkeypatch.setattr(
        "app.application.services.supervisor_session_control.apply_session_review",
        apply_mock,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor_session_control.get_supervisor_session",
        AsyncMock(return_value=row),
    )

    result = await auto_approve_pending_supervisor_sessions(db, tenant_id=tenant_id)
    assert result["approved_count"] == 1
    assert result["session_ids"] == [str(session_id)]
    apply_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_maybe_auto_approve_when_eligible_then_applies_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    row = MagicMock()
    row.status = "needs_input"
    row.tenant_id = tenant_id
    row.goal = "Digest"
    row.context_summary = {}
    row.id = uuid.uuid4()
    row.runtime_mode = "durable"

    hydrated = MagicMock()
    hydrated.status = "needs_input"
    hydrated.id = row.id
    hydrated.tenant_id = tenant_id
    hydrated.goal = row.goal
    hydrated.context_summary = {}

    db = AsyncMock()
    db.get = AsyncMock(
        return_value=SimpleNamespace(
            operator_settings={"supervisor_sessions": {"auto_approve_enabled": True}},
        ),
    )
    apply_mock = AsyncMock()
    monkeypatch.setattr(
        "app.application.services.supervisor_session_control.apply_session_review",
        apply_mock,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor_session_control.get_supervisor_session",
        AsyncMock(return_value=hydrated),
    )

    approved = await maybe_auto_approve_supervisor_session(db, session_row=row)

    assert approved is True
    apply_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_auto_approve_pending_skips_inprocess_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    row = MagicMock()
    row.id = uuid.uuid4()
    row.goal = "Routine digest"
    row.context_summary = {}
    row.status = "needs_input"
    row.runtime_mode = "inprocess"

    async def _scalars(_stmt):  # noqa: ANN001
        result = MagicMock()
        result.all.return_value = [row]
        return result

    db.scalars = _scalars  # type: ignore[method-assign]
    db.get = AsyncMock(
        return_value=SimpleNamespace(
            operator_settings={"supervisor_sessions": {"auto_approve_enabled": True}},
        ),
    )
    apply_mock = AsyncMock()
    monkeypatch.setattr(
        "app.application.services.supervisor_session_control.apply_session_review",
        apply_mock,
    )

    result = await auto_approve_pending_supervisor_sessions(db, tenant_id=tenant_id)
    assert result["approved_count"] == 0
    assert result["skipped_critical"] == 1
    apply_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_approve_pending_skips_critical_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    row = MagicMock()
    row.id = uuid.uuid4()
    row.goal = "Rotate production billing secrets"
    row.context_summary = {"approval_required": True}
    row.status = "needs_input"

    async def _scalars(_stmt):  # noqa: ANN001
        result = MagicMock()
        result.all.return_value = [row]
        return result

    db.scalars = _scalars  # type: ignore[method-assign]
    db.get = AsyncMock(
        return_value=SimpleNamespace(
            operator_settings={"supervisor_sessions": {"auto_approve_enabled": True}},
        ),
    )
    apply_mock = AsyncMock()
    monkeypatch.setattr(
        "app.application.services.supervisor_session_control.apply_session_review",
        apply_mock,
    )

    result = await auto_approve_pending_supervisor_sessions(db, tenant_id=tenant_id)

    assert result["approved_count"] == 0
    assert result["skipped_critical"] == 1
    apply_mock.assert_not_awaited()
