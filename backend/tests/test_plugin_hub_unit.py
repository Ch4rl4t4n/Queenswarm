"""Smoke tests for static plugin manifest reload hooks."""

from __future__ import annotations

import threading
import pytest

from app.services import plugin_hub as hub


@pytest.fixture(autouse=True)
def restore_plugin_generation() -> None:
    """Reset module-level generation around each case."""

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
