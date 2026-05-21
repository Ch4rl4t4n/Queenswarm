"""Unit tests for LLM cost ledger FK safety."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.llm_router import _coerce_optional_uuid_fk, record_llm_cost


def test_coerce_optional_uuid_fk_accepts_uuid() -> None:
    uid = uuid.uuid4()
    assert _coerce_optional_uuid_fk(uid) == uid
    assert _coerce_optional_uuid_fk(str(uid)) == uid


def test_coerce_optional_uuid_fk_rejects_slug_labels() -> None:
    assert _coerce_optional_uuid_fk("orch_mt_pick-deadbeef") is None
    assert _coerce_optional_uuid_fk("") is None
    assert _coerce_optional_uuid_fk(None) is None


@pytest.mark.asyncio
async def test_record_llm_cost_skips_invalid_task_fk(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    session.flush = AsyncMock()
    session.expunge = MagicMock()
    response = MagicMock()
    response.usage = {"prompt_tokens": 12, "completion_tokens": 4}
    monkeypatch.setattr(
        "app.core.llm_router.litellm.completion_cost",
        lambda **_: 0.01,
    )

    await record_llm_cost(
        session,
        response=response,
        model_name="grok-test",
        agent_id="not-a-uuid",
        task_id=f"orch_mt_pick-{uuid.uuid4()}",
    )

    session.add.assert_called_once()
    entry = session.add.call_args[0][0]
    assert entry.task_id is None
    assert entry.agent_id is None
