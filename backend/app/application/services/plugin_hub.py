"""In-process hive plugin facade for operator dashboards."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

_lock = threading.Lock()
_reload_generation = 0

_DEFAULT_PLUGINS: list[dict[str, Any]] = [
    {
        "id": "workflow-breaker",
        "title": "Auto Workflow Breaker",
        "enabled": True,
        "description": "LLM decomposition plus Recipe Library semantic recall.",
    },
    {
        "id": "langgraph-runner",
        "title": "Sub-swarm LangGraph runner",
        "enabled": True,
        "description": "Colony-local execution graphs with imitation + waggle relays.",
    },
    {
        "id": "simulation-docker",
        "title": "Docker simulation ledger",
        "enabled": True,
        "description": "Sandbox gate before verified payloads exit the hive.",
    },
    {
        "id": "cost-governor",
        "title": "LiteLLM cost governor",
        "enabled": True,
        "description": "Daily envelopes + Postgres cost_records attribution.",
    },
]


def bump_plugin_generation() -> int:
    """Increment hot-reload counter (UI forces config/cache bust hooks)."""

    global _reload_generation
    with _lock:
        _reload_generation += 1
        return _reload_generation


def plugin_manifest() -> dict[str, Any]:
    """Return static catalog annotated with reload generation."""

    with _lock:
        gen = _reload_generation
    return {
        "reload_generation": gen,
        "reloaded_at": datetime.now(tz=UTC).isoformat(),
        "plugins": list(_DEFAULT_PLUGINS),
    }


__all__ = ["bump_plugin_generation", "plugin_manifest"]
