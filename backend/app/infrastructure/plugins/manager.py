"""Hot-reload user Python plugins from a writable directory (Compose volume)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

PLUGIN_DIR = Path(settings.plugin_user_dir)
PLUGIN_DIR.mkdir(parents=True, exist_ok=True)

_loaded_plugins: dict[str, dict[str, Any]] = {}


def discover_plugins() -> list[dict[str, Any]]:
    """Scan the user plugin directory and return metadata rows."""

    plugins: list[dict[str, Any]] = []
    for path in sorted(PLUGIN_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        plugins.append(_get_plugin_meta(path))
    return plugins


def _get_plugin_meta(path: Path) -> dict[str, Any]:
    """Best-effort metadata from filename + docstring prefix."""

    name = path.stem
    status = "active" if name in _loaded_plugins else "inactive"
    size = path.stat().st_size
    description = ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:800]
        if '"""' in text:
            start = text.index('"""') + 3
            end = text.index('"""', start)
            description = text[start:end].strip().split("\n", 1)[0].strip()
    except (OSError, ValueError):
        pass

    return {
        "id": name,
        "name": name.replace("_", " ").title(),
        "filename": path.name,
        "description": description or "User plugin (no docstring yet).",
        "status": status,
        "size_bytes": size,
        "version": str(_loaded_plugins.get(name, {}).get("version", "1.0.0")),
        "source": "user",
    }


def load_plugin(plugin_name: str) -> dict[str, Any]:
    """Import or reload a plugin module from disk."""

    stem = Path(plugin_name).name
    if stem != plugin_name or ".." in plugin_name or "/" in plugin_name or "\\" in plugin_name:
        msg = "Invalid plugin name."
        raise ValueError(msg)

    path = PLUGIN_DIR / f"{stem}.py"
    if not path.is_file():
        msg = f"Plugin {stem}.py not found under {PLUGIN_DIR}"
        raise FileNotFoundError(msg)

    mod_name = f"queenswarm_user_plugins.{stem}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        msg = f"Could not load spec for {path}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)

    version = getattr(module, "__version__", "1.0.0")
    _loaded_plugins[stem] = {"module": module, "path": str(path), "version": str(version)}
    logger.info("plugins.user.loaded", plugin=stem, version=str(version))
    return _get_plugin_meta(path)


def unload_plugin(plugin_name: str) -> None:
    """Drop a plugin from the import cache."""

    stem = Path(plugin_name).name
    _loaded_plugins.pop(stem, None)
    mod_name = f"queenswarm_user_plugins.{stem}"
    sys.modules.pop(mod_name, None)
    logger.info("plugins.user.unloaded", plugin=stem)


def get_plugin_tool(plugin_name: str, function_name: str = "run") -> Any:
    """Resolve a callable from a loaded (or freshly loaded) plugin."""

    stem = Path(plugin_name).name
    if stem not in _loaded_plugins:
        load_plugin(stem)
    module = _loaded_plugins[stem]["module"]
    if not hasattr(module, function_name):
        msg = f"Plugin {stem} has no function {function_name!r}"
        raise AttributeError(msg)
    return getattr(module, function_name)


__all__ = [
    "PLUGIN_DIR",
    "discover_plugins",
    "get_plugin_tool",
    "load_plugin",
    "unload_plugin",
]
