"""Unit tests for research runtime credentials."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.research_runtime_credentials import (
    resolve_research_keys,
    research_key_status,
)


@pytest.mark.asyncio
async def test_resolve_research_keys_prefers_vault_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "env-tavily-key")
    session = AsyncMock()
    row = MagicMock()
    row.provider = "tavily"
    row.ciphertext = "blob"
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[row])))

    with patch(
        "app.application.services.research_runtime_credentials.decrypt_credentials_blob",
        return_value={"api_key": "vault-tavily-key"},
    ):
        keys = await resolve_research_keys(session)

    assert keys["tavily"] == "vault-tavily-key"


@pytest.mark.asyncio
async def test_research_key_status_reports_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERPER_API_KEY", "serper-env-key-1234")
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))

    status = await research_key_status(session)
    assert status["serper"]["configured"] is True
    assert status["serper"]["masked"] == "••••1234"
    assert status["tavily"]["configured"] is False
