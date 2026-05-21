"""In-process hive plugin facade for operator dashboards."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_lock = threading.Lock()
_reload_generation = 0
_BUILTIN_STATE_FILENAME = "builtin_plugin_state.json"

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


def _builtin_state_path() -> Path:
    """Return writable JSON path co-located with user plugin uploads."""

    return Path(settings.plugin_user_dir) / _BUILTIN_STATE_FILENAME


def _known_builtin_ids() -> set[str]:
    """Return ids for bundled hive lattice modules."""

    return {str(row["id"]) for row in _DEFAULT_PLUGINS}


def _read_enabled_overrides() -> dict[str, bool]:
    """Load persisted enabled flags; missing file yields empty overrides."""

    path = _builtin_state_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        overrides = raw.get("enabled_overrides", {})
        if not isinstance(overrides, dict):
            return {}
        return {str(key): bool(value) for key, value in overrides.items()}
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("plugin_hub.state_read_failed", path=str(path), error=str(exc))
        return {}


def _write_enabled_overrides(overrides: dict[str, bool]) -> None:
    """Persist enabled overrides atomically beside user plugin uploads."""

    path = _builtin_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(tz=UTC).isoformat(),
        "enabled_overrides": overrides,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _merged_default_plugins() -> list[dict[str, Any]]:
    """Apply persisted overrides onto the static built-in catalog."""

    overrides = _read_enabled_overrides()
    merged: list[dict[str, Any]] = []
    for row in _DEFAULT_PLUGINS:
        plugin = dict(row)
        plugin_id = str(plugin["id"])
        if plugin_id in overrides:
            plugin["enabled"] = bool(overrides[plugin_id])
        merged.append(plugin)
    return merged


def bump_plugin_generation() -> int:
    """Increment hot-reload counter (UI forces config/cache bust hooks)."""

    global _reload_generation
    with _lock:
        _reload_generation += 1
        return _reload_generation


def set_builtin_plugin_enabled(plugin_id: str, *, enabled: bool) -> dict[str, Any]:
    """Persist a built-in plugin toggle and bump reload generation.

    Args:
        plugin_id: Stable built-in row id from the static catalog.
        enabled: Desired on/off state for operator dashboards.

    Returns:
        Updated plugin row after overrides merge.

    Raises:
        KeyError: When ``plugin_id`` is not a known built-in plugin.
    """

    normalized = str(plugin_id).strip()
    if normalized not in _known_builtin_ids():
        raise KeyError(normalized)

    overrides = _read_enabled_overrides()
    overrides[normalized] = bool(enabled)
    _write_enabled_overrides(overrides)
    gen = bump_plugin_generation()
    row = next(item for item in _merged_default_plugins() if str(item["id"]) == normalized)
    logger.info(
        "plugin_hub.builtin_toggled",
        plugin_id=normalized,
        enabled=bool(enabled),
        reload_generation=gen,
    )
    return row


def plugin_manifest() -> dict[str, Any]:
    """Return static catalog annotated with reload generation and persisted toggles."""

    with _lock:
        gen = _reload_generation
    return {
        "reload_generation": gen,
        "reloaded_at": datetime.now(tz=UTC).isoformat(),
        "plugins": _merged_default_plugins(),
    }


__all__ = [
    "bump_plugin_generation",
    "plugin_manifest",
    "set_builtin_plugin_enabled",
]
