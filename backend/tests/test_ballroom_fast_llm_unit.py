"""Unit tests for direct Grok fast ballroom completions."""

from __future__ import annotations

import pytest

from app.application.services import ballroom_fast_llm


@pytest.mark.asyncio
async def test_grok_ballroom_reply_fast_parses_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fast lane returns trimmed assistant text from xAI JSON."""

    monkeypatch.setattr(ballroom_fast_llm, "provider_effective_grok", lambda: "test-key")

    class _FakeResponse:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {"choices": [{"message": {"content": "  On it — next step ready.  "}}]}

    class _FakeClient:
        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object) -> _FakeResponse:
            return _FakeResponse()

    monkeypatch.setattr(ballroom_fast_llm.httpx, "AsyncClient", lambda **kwargs: _FakeClient())

    out = await ballroom_fast_llm.grok_ballroom_reply_fast(user_text="hello")
    assert out == "On it — next step ready."
