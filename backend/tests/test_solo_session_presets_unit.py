"""Unit tests for solo session presets."""

from __future__ import annotations

import pytest

from app.application.services.solo_session_presets import (
    get_solo_session_preset,
    list_solo_session_presets,
)


@pytest.mark.parametrize(
    "preset_id",
    [
        "bank-po-brief",
        "bank-po-backlog",
        "marketing-draft",
        "paper-trading-review",
        "web-redesign-discovery",
        "marketing-campaign",
        "competitor-research",
        "lead-gen-lane",
    ],
)
def test_get_solo_session_preset_when_known_returns_row(preset_id: str) -> None:
    row = get_solo_session_preset(preset_id)
    assert row is not None
    assert row.id == preset_id
    assert len(row.goal) > 40
    assert "critic" in row.roles or "researcher" in row.roles


def test_get_solo_session_preset_when_unknown_returns_none() -> None:
    assert get_solo_session_preset("missing") is None


def test_list_solo_session_presets_includes_bank_po(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "solo_mode_enabled", True)
    presets = list_solo_session_presets()
    assert len(presets) >= 8
    assert any(row.id == "bank-po-brief" for row in presets)
