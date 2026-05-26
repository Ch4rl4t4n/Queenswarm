"""Unit tests for codebase atlas Redis cache."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.application.services import codebase_atlas as mod


@pytest.mark.asyncio
async def test_build_codebase_atlas_cached_returns_redis_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"generated_at": "2026-01-01T00:00:00+00:00", "total_lines": 42}

    async def fake_get_json(_key: str) -> dict[str, object]:
        return payload

    monkeypatch.setattr(mod, "get_json", fake_get_json)
    monkeypatch.setattr(mod, "set_json", AsyncMock())

    result = await mod.build_codebase_atlas_cached()
    assert result["cached"] is True
    assert result["total_lines"] == 42


@pytest.mark.asyncio
async def test_build_codebase_atlas_cached_scans_on_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    scan_payload = {"generated_at": "2026-01-02T00:00:00+00:00", "total_lines": 99}
    set_mock = AsyncMock()

    async def fake_get_json(_key: str) -> None:
        return None

    def fake_build(*, repo_root=None) -> dict[str, object]:  # noqa: ANN001, ARG001
        return scan_payload

    monkeypatch.setattr(mod, "get_json", fake_get_json)
    monkeypatch.setattr(mod, "set_json", set_mock)
    monkeypatch.setattr(mod, "build_codebase_atlas", fake_build)

    result = await mod.build_codebase_atlas_cached()
    assert result["cached"] is False
    assert result["total_lines"] == 99
    set_mock.assert_awaited_once()
