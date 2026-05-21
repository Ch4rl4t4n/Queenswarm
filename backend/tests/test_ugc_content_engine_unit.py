"""Tests for UGC lead magnet content engine."""

from __future__ import annotations

import pytest

from app.application.services.ugc_content_engine import (
    build_landing_payload,
    get_lead_magnet,
    list_lead_magnets,
)


def test_list_lead_magnets_includes_exec_assistant() -> None:
    rows = list_lead_magnets()
    ids = {row["template_id"] for row in rows}
    assert "exec-assistant" in ids
    assert len(rows) == 3


def test_build_landing_payload_exec_assistant_headline() -> None:
    payload = build_landing_payload("exec-assistant")
    assert "10 min" in payload["headline"]
    assert payload["agent_count"] == 3
    assert payload["cta_url"].endswith("template=exec-assistant&utm_source=lead_magnet")


def test_get_lead_magnet_unknown_returns_none() -> None:
    assert get_lead_magnet("missing") is None


def test_build_landing_payload_unknown_raises() -> None:
    with pytest.raises(ValueError):
        build_landing_payload("missing")
