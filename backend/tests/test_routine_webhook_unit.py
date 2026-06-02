"""Unit tests for supervisor routine webhook ingress."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.supervisor.routine_webhook import (
    enable_routine_webhook,
    extract_webhook_event_text,
    handle_routine_webhook,
    verify_routine_webhook_token,
)


def test_extract_webhook_event_text_prefers_text_field() -> None:
    assert extract_webhook_event_text({"text": "  hello  ", "payload": {"x": 1}}) == "hello"


def test_extract_webhook_event_text_falls_back_to_json_dump() -> None:
    body = {"foo": "bar"}
    assert '"foo"' in extract_webhook_event_text(body)


def test_verify_routine_webhook_token_roundtrip() -> None:
    token, payload = enable_routine_webhook(context_payload={})
    assert verify_routine_webhook_token(context_payload=payload, token=token)
    assert not verify_routine_webhook_token(context_payload=payload, token="wrong")


@pytest.mark.asyncio
async def test_handle_routine_webhook_when_enabled_then_triggers_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token, payload = enable_routine_webhook(context_payload={})
    routine = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        context_payload=payload,
    )
    session_id = uuid.uuid4()
    trigger = AsyncMock(return_value=session_id)
    monkeypatch.setattr(
        "app.application.services.supervisor.routine_service.trigger_supervisor_routine_now",
        trigger,
    )
    db = AsyncMock()
    db.flush = AsyncMock()

    result = await handle_routine_webhook(
        db,
        routine=routine,
        body={"text": "Meeting notes", "source": "fireflies"},
        source_header="fireflies",
    )
    assert result == session_id
    trigger.assert_awaited_once()
    assert routine.context_payload["webhook_ingress"]["trigger_count"] == 1
