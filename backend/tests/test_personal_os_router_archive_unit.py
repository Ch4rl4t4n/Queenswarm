"""Unit tests for POS-G4 Personal OS commercial router archive."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.application.services.personal_os_router_archive import (
    personal_os_commercial_api_enabled,
    require_commercial_api,
)
from app.core.config import settings


def test_commercial_api_enabled_when_not_personal_os(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "personal_os_mode_enabled", False)
    assert personal_os_commercial_api_enabled() is True
    require_commercial_api()


def test_commercial_api_archived_in_personal_os(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "personal_os_mode_enabled", True)
    assert personal_os_commercial_api_enabled() is False
    with pytest.raises(HTTPException) as exc:
        require_commercial_api()
    assert exc.value.status_code == 404
