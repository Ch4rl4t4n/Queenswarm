"""Unit tests for self-extending tool marketplace proposals and simulation."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services import tool_marketplace_extensions as ext


def test_simulate_phase3_template_venice_verified() -> None:
    """Venice MCP preset passes structural manifest simulation."""

    payload = ext.simulate_phase3_template("venice_mcp")
    assert payload["verified"] is True
    assert payload["source"] == "phase3_template"
    assert any(c["status"] == "pass" for c in payload["checks"])


def test_simulate_phase3_template_unknown_fails() -> None:
    """Unknown template id returns verified=false."""

    payload = ext.simulate_phase3_template("not_a_real_template_xyz")
    assert payload["verified"] is False


@pytest.mark.asyncio
async def test_propose_marketplace_extensions_ranks_uninstalled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Proposals include uninstalled templates scored by goal overlap."""

    async def _fake_catalog(_session: object, *, dashboard_user_id: uuid.UUID) -> dict:
        _ = dashboard_user_id
        return {
            "phase3_templates": [
                {
                    "id": "venice_mcp",
                    "slug": "venice_mcp",
                    "title": "Venice MCP",
                    "summary": "Private AI inference MCP tools",
                    "installed": False,
                    "tool_count": 8,
                    "category": "ai",
                    "suggested_manager_slugs": ["research_intelligence"],
                },
            ],
        }

    monkeypatch.setattr(ext, "marketplace_catalog", _fake_catalog)
    out = await ext.propose_marketplace_extensions(
        SimpleNamespace(),
        dashboard_user_id=uuid.uuid4(),
        goal="private inference MCP",
        limit=4,
    )
    assert out["proposal_count"] >= 1
    first = out["proposals"][0]
    assert first["entry_id"] == "venice_mcp"
    assert first["install_ready"] is True


@pytest.mark.asyncio
async def test_install_verified_blocks_failed_simulation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install with require_simulation blocks when manifest checks fail."""

    monkeypatch.setattr(
        ext,
        "simulate_phase3_template",
        lambda _eid: {"verified": False, "entry_id": "bad"},
    )

    async def _no_install(*_a: object, **_k: object) -> tuple[str, None]:
        raise AssertionError("install should not run")

    monkeypatch.setattr(ext, "install_marketplace_entry", _no_install)
    payload = await ext.install_verified_marketplace_extension(
        SimpleNamespace(),
        dashboard_user_id=uuid.uuid4(),
        source="phase3_template",
        entry_id="bad",
    )
    assert payload["status"] == "simulation_failed"
