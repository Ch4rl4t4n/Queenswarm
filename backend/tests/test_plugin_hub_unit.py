"""Smoke tests for static plugin manifest reload hooks."""

from __future__ import annotations

import threading

from pathlib import Path

import pytest

from app.application.services import plugin_hub as hub
from app.core.config import settings


@pytest.fixture(autouse=True)
def restore_plugin_generation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Reset module-level generation and isolate state file per test."""

    state_dir = tmp_path / "plugins"
    state_dir.mkdir()
    monkeypatch.setattr(settings, "plugin_user_dir", str(state_dir), raising=False)
    with hub._lock:
        hub._reload_generation = 0
    yield
    with hub._lock:
        hub._reload_generation = 0


def test_bump_plugin_generation_increments_under_lock() -> None:
    gen1 = hub.bump_plugin_generation()
    gen2 = hub.bump_plugin_generation()
    assert gen2 == gen1 + 1
    assert type(hub._lock) is type(threading.Lock())


def test_plugin_manifest_includes_catalog_and_generation() -> None:
    hub.bump_plugin_generation()
    bundle = hub.plugin_manifest()
    assert bundle["reload_generation"] >= 1
    assert "reloaded_at" in bundle
    plugins = bundle["plugins"]
    assert len(plugins) == 4
    assert {p["id"] for p in plugins} >= {"workflow-breaker", "cost-governor"}


def test_set_builtin_plugin_enabled_persists_across_manifest_reads() -> None:
    hub.set_builtin_plugin_enabled("simulation-docker", enabled=False)

    first = hub.plugin_manifest()
    disabled = next(row for row in first["plugins"] if row["id"] == "simulation-docker")
    assert disabled["enabled"] is False

    hub.set_builtin_plugin_enabled("simulation-docker", enabled=True)
    second = hub.plugin_manifest()
    enabled = next(row for row in second["plugins"] if row["id"] == "simulation-docker")
    assert enabled["enabled"] is True
    assert hub._builtin_state_path().is_file()


def test_set_builtin_plugin_enabled_when_unknown_then_raises() -> None:
    with pytest.raises(KeyError):
        hub.set_builtin_plugin_enabled("not-a-plugin", enabled=True)
