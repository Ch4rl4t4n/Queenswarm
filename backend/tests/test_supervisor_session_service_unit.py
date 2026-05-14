"""Unit tests for supervisor runtime policy helpers."""

from __future__ import annotations

from app.application.services.supervisor.session_service import (
    coerce_runtime_mode,
    normalize_roles,
)
from app.core.config import settings


def test_normalize_roles_when_duplicates_and_invalid_then_filters() -> None:
    """Roles list keeps first valid unique values only."""

    out = normalize_roles(["Researcher", "coder", "coder", "unknown", "browser-operator"])
    assert out == ["researcher", "coder", "browser_operator"]


def test_normalize_roles_when_empty_then_falls_back() -> None:
    """Fallback roles are emitted for empty input."""

    assert normalize_roles([]) == ["researcher", "critic"]


def test_coerce_runtime_mode_when_durable_disabled_then_inprocess(monkeypatch) -> None:
    """Durable requests downgrade to inprocess when flag is off."""

    monkeypatch.setattr(settings, "supervisor_durable_mode_enabled", False)
    assert coerce_runtime_mode("durable") == "inprocess"


def test_coerce_runtime_mode_when_durable_enabled_then_kept(monkeypatch) -> None:
    """Durable mode remains durable when explicitly enabled."""

    monkeypatch.setattr(settings, "supervisor_durable_mode_enabled", True)
    assert coerce_runtime_mode("durable") == "durable"

