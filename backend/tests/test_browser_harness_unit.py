"""Unit tests for browser harness manager guardrails and approval flow."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.infrastructure.persistence.models.browser_session import BrowserAutomationSession
from app.tools.browser_manager import BrowserGuardrailError, BrowserManager


class _FakeDb:
    def __init__(self) -> None:
        self.rows: list[Any] = []

    def add(self, row: Any) -> None:
        self.rows.append(row)

    async def flush(self) -> None:
        return None


class _FakePage:
    def __init__(self) -> None:
        self.url = "https://example.com/"

    async def goto(self, url: str, **_kwargs):  # noqa: ANN001
        self.url = url

    async def click(self, _selector: str, **_kwargs):  # noqa: ANN001
        return None

    async def fill(self, _selector: str, _text: str, **_kwargs):  # noqa: ANN001
        return None

    async def text_content(self, _query: str, **_kwargs):  # noqa: ANN001
        return "sample body text"

    async def screenshot(self, **_kwargs):  # noqa: ANN001
        return b"fakeimage"


@pytest.mark.asyncio
async def test_browser_guardrail_when_domain_not_allowed_then_blocks() -> None:
    """Manager should block disallowed domains."""

    db = _FakeDb()
    row = BrowserAutomationSession(
        tenant_id=uuid.uuid4(),
        mode="headless",
        status="running",
        start_url="https://example.com",
        current_url="https://example.com",
        allowed_domains=["example.com"],
        max_actions=10,
        actions_used=0,
        pending_approval_action={},
        is_headless=True,
    )
    with pytest.raises(BrowserGuardrailError):
        await BrowserManager.execute_action(
            db,  # type: ignore[arg-type]
            session_row=row,
            action_type="navigate",
            payload={"url": "https://forbidden.example.net"},
            approved=True,
        )


@pytest.mark.asyncio
async def test_browser_action_when_critical_without_approval_then_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    """Critical action should require explicit approval."""

    db = _FakeDb()
    row = BrowserAutomationSession(
        tenant_id=uuid.uuid4(),
        mode="headless",
        status="running",
        start_url="https://example.com",
        current_url="https://example.com",
        allowed_domains=["example.com"],
        max_actions=10,
        actions_used=0,
        pending_approval_action={},
        is_headless=True,
    )

    async def _runtime(_db, *, session_row):  # noqa: ANN001
        return SimpleNamespace(context=SimpleNamespace(close=lambda: None), page=_FakePage(), created_at=None)

    monkeypatch.setattr("app.tools.browser_manager.BrowserManager._ensure_runtime_session", _runtime)
    out = await BrowserManager.execute_action(
        db,  # type: ignore[arg-type]
        session_row=row,
        action_type="click",
        payload={"selector": "button[type='submit']"},
        approved=False,
    )
    assert out["status"] == "pending_approval"
    assert dict(row.pending_approval_action or {}).get("action_type") == "click"


@pytest.mark.asyncio
async def test_browser_pending_action_when_approved_then_executes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Approved pending action should be executed and clear pending state."""

    db = _FakeDb()
    row = BrowserAutomationSession(
        tenant_id=uuid.uuid4(),
        mode="headless",
        status="running",
        start_url="https://example.com",
        current_url="https://example.com",
        allowed_domains=["example.com"],
        max_actions=10,
        actions_used=0,
        pending_approval_action={
            "action_type": "click",
            "payload": {"selector": "button.cta"},
        },
        is_headless=True,
    )

    async def _runtime(_db, *, session_row):  # noqa: ANN001
        return SimpleNamespace(context=SimpleNamespace(close=lambda: None), page=_FakePage(), created_at=None)

    monkeypatch.setattr("app.tools.browser_manager.BrowserManager._ensure_runtime_session", _runtime)
    out = await BrowserManager.approve_pending_action(
        db,  # type: ignore[arg-type]
        session_row=row,
        approve=True,
    )
    assert out["status"] == "ok"
    assert dict(row.pending_approval_action or {}) == {}
